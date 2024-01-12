#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \actions\blend\lib\cls_render_std.py
# Created Date: Friday, August 20th 2021, 12:06:38 pm
# Author: Christian Perwass (CR/AEC5)
# <LICENSE id="GPL-3.0">
#
#   Image-Render standard Blender actions module
#   Copyright (C) 2022 Robert Bosch GmbH and its subsidiaries
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#
# </LICENSE>
###

import bpy
import mathutils

import os
import copy

from .cls_render import CRender
from anybase.cls_anyexcept import CAnyExcept
from anybase.cls_anycml import CAnyCML

from catharsys.plugins.std.blender.config.cls_cameraset import CConfigCameraSet
from catharsys.plugins.std.blender.util.camera import GetCameraData
from catharsys.plugins.std.blender.util.object import GetWorldMatrix

from catharsys.util import config as cathcfg
from catharsys.util import file as cathfile


class CLogObj(CRender):
    dicLogObj: dict = None
    xCameraSet: CConfigCameraSet = None

    dicLog: dict = None

    ##############################################################
    def __init__(self, *, xPrjCfg, dicCfg):
        super().__init__(xPrjCfg=xPrjCfg, dicCfg=dicCfg, sDtiCapCfg="capture/*:*")

        dicData = self.dicCfg["mConfig"]["mData"]
        if dicData is None:
            raise CAnyExcept("No configuration data given")
        # endif

        sLogObjDti = "blender/log-objects:1.0"
        lLogObj = cathcfg.GetDataBlocksOfType(dicData, sLogObjDti)
        if len(lLogObj) == 0:
            raise Exception("No object logging configuration of type compatible to '{0}' given.".format(sLogObjDti))
        # endif
        self.dicLogObj = lLogObj[0]

        self.xCameraSet = CConfigCameraSet()
        self.xCameraSet.InitFromConfig(dicData, bRaiseException=False)

    # enddef

    ##############################################################
    def Process(self):
        if self.bIsInitialized is False:
            raise CAnyExcept("Rendering is not initialized")
        # endif

        # Initialize render by executing generators, setting camera, etc.
        # This call can take quite some time, if complex objects are generated.
        self.InitRender()

        # Initialize log dictionary object
        self.LogObjectsInit(
            {
                "sDTI": "/catharysy/blender/log-obj-data:1.0",
                "sId": self.sJobGroupId,
                "sBlenderFile": os.path.basename(bpy.data.filepath),
                "mConfigs": {
                    "capture": self.dicCap,
                    "modify": self.lMod,
                    "animation": self.lAnim,
                    "log-obj": self.dicLogObj,
                },
                "iFrameFirst": self.iFrameFirst,
                "iFrameLast": self.iFrameLast,
                "fTargetFps": self.fTargetFps,
                "fSceneFps": self.fSceneFps,
                "sCameraName": self.sCameraName,
                "sCameraParentName": self.sCameraParentName,
            }
        )

        self.Print("")
        self.Print("Start creating log...")
        self.Print("")

        # The actual list of objects to log
        dicLogObjects = self.dicLogObj.get("mObjects")

        # Flag whether to write out the camera set configuration
        bLogCameraSet = self.dicLogObj.get("bLogCameraSet", True)

        # Replace camera set related log config variables
        # dicLogVarData = {
        #     "ActiveCamera": sCameraName,
        #     "ActiveCameraParent": sCameraParentName,
        #     "CameraSet": lCameraSet
        # }
        # dicLogObjects = cathy.configvars.Process(dicLogObjects, dicLogVarData)

        iLogIdx = 0
        while True:
            if self.iTargetFrame > self.iFrameLast:
                break
            # endif

            # Evaluate scene frame from target frame and scene fps
            self.fTargetTime = self.iTargetFrame / self.fTargetFps
            self.iSceneFrame = int(round(self.fSceneFps * self.fTargetTime, 0))

            self.Print("Frame Trg: {0} -> Scn: {1}".format(self.iTargetFrame, self.iSceneFrame))
            self.xScn.frame_set(self.iSceneFrame)

            # Apply only those modifiers that suppor mode 'FRAME_UPDATE'
            self._ApplyCfgModifier(sMode="FRAME_UPDATE")

            self.LogObjects(
                dicLogObjects,
                iLogIdx,
                Data={
                    "iTargetFrame": self.iTargetFrame,
                    "fTargetTime": self.fTargetTime,
                    "iSceneFrame": self.iSceneFrame,
                    "fSceneTime": self.iSceneFrame / self.fSceneFps,
                },
            )

            if self.xCameraSet.IsValid() and bLogCameraSet is True:
                self.xCameraSet.GetBlenderData()
                sFpCamSet = os.path.join(self.sPathTrgMain, "CamSet_{0:04d}.yaml".format(self.iTargetFrame))
                self.Print("Writing camera set to: {0}".format(sFpCamSet))
                self.xCameraSet.SaveYaml(sFpCamSet)
            # endif

            iLogIdx += 1
            self.iTargetFrame += 1

        # endfor iTrgFrame

        sFpLog = os.path.join(self.sPathTrgMain, "LogObjects.json")
        self.Print("Writing log to: {0}".format(sFpLog))
        cathfile.SaveJson(sFpLog, self.dicLog, iIndent=4)

        self.Print("finished.")
        self.Print("")

    # enddef Process

    ############################################################################################
    def LogObjectsInit(self, _dicData):
        self.dicLog = copy.deepcopy(_dicData)
        self.dicLog["lLog"] = []

    # enddef

    ############################################################################################
    def LogObjects(self, _dicLogObjects, _iLogIdx, **kwargs):
        dicData = kwargs.pop("Data", {})
        # xScene = kwargs.pop("Scene", bpy.context.scene)

        dicObj = bpy.data.objects
        dicEntry = copy.deepcopy(dicData)
        dicEntry["iIdx"] = _iLogIdx

        # process log objects dictionary for current render variables
        dicConstVars, dicRefVars = self._GetRuntimeVars()
        xParser = CAnyCML(dicConstVars=dicConstVars, dicRefVars=dicRefVars)
        dicProcLogObj = xParser.Process(_dicLogObjects)

        for sObjId in dicProcLogObj:
            if sObjId.startswith("__"):
                continue
            # endif

            lLogObj = dicProcLogObj.get(sObjId)

            objX = dicObj.get(sObjId)
            if objX is None:
                raise Exception("Object with id '{0}' not found".format(sObjId))
            # endif

            bHasLogData = False
            dicObjData = {}
            for dicLogObj in lLogObj:
                bDoLog = False
                iFreq = dicLogObj.get("iFreq", 1)
                if iFreq >= 0 and _iLogIdx == 0:
                    bDoLog = True
                elif iFreq > 0 and (_iLogIdx % iFreq) == 0:
                    bDoLog = True
                # endif iFreq

                if bDoLog:
                    bHasLogData = True
                    sType = dicLogObj.get("sType")
                    if sType == "matrix_world":
                        dicObjData["matrix_world"] = GetWorldMatrix(sObjId, sType="matrix")

                    elif sType == "camera":
                        dicObjData["camera"] = GetCameraData(sObjId)

                    elif sType == "property":
                        sName = dicLogObj.get("sName")
                        xProp = objX.get(sName)
                        if xProp is None:
                            raise Exception("Property '{0}' not found in object '{1}'".format(sName, sObjId))
                        # endif
                        dicObjData[sName] = xProp

                    else:
                        raise Exception("Unsupported log data type '{0}' for object '{1}'".format(sType, sObjId))
                    # endif
                # endif bDoLog
            # endfor dicLogObj

            if bHasLogData:
                dicEntry[sObjId] = dicObjData
            # endif
        # endfor sObjId

        lLog = self.dicLog.get("lLog")
        lLog.append(dicEntry)

    # enddef


# endclass
