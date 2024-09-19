#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \actions\blend\lib\render.py
# Created Date: Friday, August 20th 2021, 7:39:01 am
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

import os
import copy
import gc

import ison
from typing import Optional
from dataclasses import dataclass

from anybase.cls_anyexcept import CAnyExcept
from anybase.cls_any_error import CAnyError_Message
from anybase import assertion, convert

from anyblend.compositor.cls_fileout import CFileOut
from catharsys.plugins.std.blender.config.cls_settings_cycles import (
    CConfigSettingsCycles,
)
from catharsys.plugins.std.blender.config.cls_settings_eevee import (
    CConfigSettingsEevee,
)
from catharsys.plugins.std.blender.config.cls_settings_render import (
    CConfigSettingsRender,
)
from catharsys.plugins.std.blender.config.cls_modify_list import CConfigModifyList
from catharsys.plugins.std.blender.config.cls_generate_list import CConfigGenerateList
from catharsys.plugins.std.blender.util import camera as cbu_cam
from catharsys.plugins.std.blender.animate import objects as animobj
import catharsys.util as cathutil
import catharsys.util.config as cathcfg
from catharsys.config.cls_project import CProjectConfig

from catharsys.decs.decorator_log import logFunctionCall
from anybase.dec.cls_const_keyword_namespace import constKeywordNamespace

import anyblend
import anycam
import anypoints
import anytruth

from pathlib import Path
import numpy as np

# need to enable OpenExr explicitly
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2


#######################################################################################
class CRenderSettings:
    def __init__(self) -> None:
        self.mMain = dict()
        self.mCycles = dict()
        self.mEevee = dict()
        self.mRender = dict()

    # end def


# end class


#######################################################################################
# Activate GPUs if neede
def _ProvideGPU():
    """Check whether GPU is used in rendering. If yes, find all CUDA devices
    and initialize them for use in Blender.

    Raises:
        CAnyExcept: If no CUDA devices were found but GPU rendering is active.
    """

    print(">>>>>>> FUNCTION: ProvideCUDA")
    print("Rendering device set: {}".format(bpy.context.scene.cycles.device))
    bUseGPU = bpy.context.scene.cycles.device != "CPU"
    if bUseGPU:
        # Enable all CUDA devices found for rendering
        lCudaDevs = anyblend.app.prefs.UseAllCudaDevices()
        if len(lCudaDevs) == 0:
            raise CAnyExcept("No CUDA devices found for rendering")
        # endif
        print("", flush=True)
        print(
            "==================================================================",
            flush=True,
        )
        print("Used rendering devices:", flush=True)
        anyblend.app.prefs.PrintUsedDevices(lCudaDevs)
        print(
            "==================================================================",
            flush=True,
        )
        print("")
    # endif
    print("<<<<<<<<<<<<<<<<<<< END ProvideCUDA")

    return bUseGPU


# enddef


#######################################################################################
@constKeywordNamespace
class NsConfigDTI:
    # Config DTIs, with that decorator they are const
    sDtiRenderOutputList: str = "blender/render/output-list:1"
    sDtiRenderOutputAll: str = "/catharsys/blender/render/output/*:1"
    sDtiCompositor: str = "/catharsys/blender/compositor:1"
    sDtiAnim: str = "blender/animate:1"
    sDtiModify: str = "blender/modify:1"
    sDtiCamera: str = "blender/camera:1"
    sDtiCameraParent: str = "blender/camera_parent:1"
    sDtiGenerate: str = "blender/generate:1"
    sDtiPclRefSet: str = "point-cloud/reference/set:1"
    sDtiPclSelection: str = "point-cloud/selection:1"
    sDtiRenderSettingsMain: str = "/catharsys/blender/render/settings/main:1"
    sDtiRenderSettingsCycles: str = "/catharsys/blender/render/settings/cycles:1"
    sDtiRenderSettingsEevee: str = "/catharsys/blender/render/settings/eevee:1"
    sDtiRenderSettingsRender: str = "/catharsys/blender/render/settings/render:1"


# end class


# -------------------------------------------------------------------------------------
@constKeywordNamespace
class NsKeysOutputlist:
    lSettings: str
    lOutputs: str


# end class


# -------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------
@constKeywordNamespace
class NsMainTypesRenderOut:
    image: str
    anytruth: str
    blend: str
    none: str


@constKeywordNamespace
class NsSpecificTypesRenderOut:
    image_openGL: str = "openGL"
    anytruth_label: str = "label"
    anytruth_pos3d: str = "pos3d"
    anytruth_localpos3d: str = "local-pos3d"
    anytruth_objectidx: str = "object-idx"
    anytruth_objectloc3d: str = "object-loc3d"


# end class
@dataclass
class CRenderOutputType:
    sMainType: str
    sSpecificType: str
    sActualDti: str

    def JoinTypes(self) -> str:
        if self.sSpecificType is None:
            return self.sMainType
        # endif

        return self.sMainType + "/" + self.sSpecificType

    # enddef

    @classmethod
    def JoinRenderTypes(cls, _sMain: str, _sSpecific: str) -> str:
        assertion.FuncArgTypes()

        return _sMain + "/" + _sSpecific

    # enddef


# end class


#######################################################################################
#######################################################################################


class CRender:
    ################################################################################
    def __init__(self, *, xPrjCfg: CProjectConfig, dicCfg: dict, sDtiCapCfg: str):
        self.bIsInitialized: bool = False
        self.bDoRender: bool = False
        self.bDoOverwrite: bool = False
        self.bDoSaveRenderFile: bool = False

        self.xPrjCfg: CProjectConfig = xPrjCfg
        self.dicCfg = copy.deepcopy(dicCfg)
        self.dicCap: dict = None
        self.dicRndOut: dict = None
        self.dicRndOutList: dict = None
        self.dicSceneElements: dict = None

        self.sDtiCapCfg = sDtiCapCfg
        self.sPathTrgMain: str = None
        self.sJobGroupId: str = None

        self.iFrameFirst: int = 0
        self.iFrameLast: int = 0
        self.iFrameStep: int = 1
        self.iRenderQuality: int = 4
        self.iSceneFrame: int = 0
        self.iTargetFrame: int = 0
        self.fTargetTime: float = 0.0
        self.fTargetFps: float = 0.0
        self.fSceneFps: float = 0.0

        self.lAnim: list = None
        self.lMod: list = None
        self.lGen: list = None
        self.lPclRefSet: list = None
        self.lPclSelection: list = None
        self.lFileOut: list = None
        self.lSceneElementTypes: list = None

        self.xCtx: bpy.types.Context = None
        self.xScn: bpy.types.Scene = None

        # Camera
        self.sCameraName: str = None
        self.sCameraParentName: str = None
        self.dicAnyCam: dict = None

        # Render Output Variables
        self.sRenderOutType: str = None
        self.xRndOutType: CRenderOutputType = None

        # renderOut: MainType == 'image'
        self.xCompFileOut: CFileOut = None

        # renderOut: MainType == 'label'
        self.bApplyAnnotation: bool = False
        self.sAnnotationType: str = None
        self.bLabelEvalBoxes2d: bool = False

        # Point Clouds
        self.xPclSet: anypoints.CPointCloudSet = None
        self.bHasPointClouds: bool = False
        self.xClnPcl: bpy.types.Collection = None
        self.lPclSels: list = None

        # Scene Settings Storage
        self.sWorldOrigId: str = None
        self.dicGeneratedObjects: dict = None

    # enddef

    ################################################################################
    # Check whether is GPU used in rendering
    @staticmethod
    def ProvideGPU():
        """Check whether GPU is used in rendering. If yes, find all CUDA devices
        and initialize them for use in Blender.

        Raises:
            CAnyExcept: If no CUDA devices were found but GPU rendering is active.
        """

        return _ProvideGPU()

    # enddef

    ################################################################################
    # Flushed printing
    def Print(self, _sText):
        logFunctionCall.PrintLog(_sText)
        print(_sText, flush=True)

    # enddef

    ################################################################################
    # Initialize Rendering with set of configs
    @logFunctionCall
    def Init(self):
        self.bIsInitialized = False

        self.xCtx = bpy.context
        self.xScn = self.xCtx.scene
        self.sFpBlendOrig = self.xCtx.blend_data.filepath

        # if we started with the default Blender scene and no Blender file,
        # then delete all objects.
        if self.sFpBlendOrig == "":
            lObj = [x.name for x in bpy.data.objects]
            for sObj in lObj:
                bpy.data.objects.remove(bpy.data.objects[sObj])
            # endfor
        # endif

        # Ensure that scene is in object mode.
        # Otherwise, many modifiers will not work properly.
        # bpy.ops.object.mode_set(mode="OBJECT")

        self.sJobGroupId = self.dicCfg["sJobGroupId"]

        dicData = self.dicCfg["mConfig"]["mData"]
        if dicData is None:
            raise CAnyExcept("No configuration data given")
        # endif

        # Make global variables available in separate configs
        ison.util.data.AddLocalGlobalVars(dicData, self.dicCfg, bThrowOnDisallow=False)

        # sys.stderr.write("\nself.dicCfg['__globals__']: {}\n".format(self.dicCfg.get("__globals__")))
        # sys.stderr.flush()

        # ########################################################
        # Load capture config
        lCap = cathcfg.GetDataBlocksOfType(dicData, self.sDtiCapCfg)
        if len(lCap) == 0:
            print(f"WARNING: No capture configuration of type compatible to '{self.sDtiCapCfg}' given.")
            self.dicCap = None
        else:
            self.dicCap = lCap[0]
        # endif

        # ########################################################
        # Load render output config
        lRndTypeList = cathcfg.GetDataBlocksOfType(dicData, NsConfigDTI.sDtiRenderOutputList)
        if len(lRndTypeList) == 0:
            raise CAnyExcept(
                "No render output configuration of type compatible to '{0}' given".format(
                    NsConfigDTI.sDtiRenderOutputList
                )
            )
        # endif
        self.dicRndOutList = lRndTypeList[0]
        self.lRndSettings = self.dicRndOutList.get(NsKeysOutputlist.lSettings)
        self.lRndOutTypes = self.dicRndOutList.get(NsKeysOutputlist.lOutputs)

        if self.lRndOutTypes is None:
            raise Exception("No render output types defined")
        # endif

        # If the render output type configs have modifier lists, we need to add
        # local and global variables of the render output config to these modifiers.
        for dicRndOut in self.lRndOutTypes:
            lModifier: list[dict] = dicRndOut.get("lModifier")
            if lModifier is None:
                continue
            # endif
            dicMod: dict
            for dicMod in lModifier:
                ison.util.data.AddLocalGlobalVars(dicMod, dicRndOut, bAllowOverwrite=False, bThrowOnDisallow=False)
            # endfor
        # endfor

        xRenderSettings: CRenderSettings = self._GetCfgRenderSettings(self.lRndSettings)
        self._ApplyCfgRenderSettings(xRenderSettings)

        # Get camera name and camera parent object if defined
        dicCameraName = cbu_cam.GetSelectedCameraName(dicData, bDoRaise=False)
        if dicCameraName is not None:
            self.sCameraName = dicCameraName.get("sCameraName")
            self.sCameraParentName = dicCameraName.get("sCameraParentName")
        else:
            self.sCameraName = None
            self.sCameraParentName = None
        # endif

        # Scene Configurations
        self.lAnim = cathcfg.GetDataBlocksOfType(dicData, NsConfigDTI.sDtiAnim)
        self.lMod = cathcfg.GetDataBlocksOfType(dicData, NsConfigDTI.sDtiModify)
        self.lGen = cathcfg.GetDataBlocksOfType(dicData, NsConfigDTI.sDtiGenerate)
        self.lPclRefSet = cathcfg.GetDataBlocksOfType(dicData, NsConfigDTI.sDtiPclRefSet)
        self.lPclSelection = cathcfg.GetDataBlocksOfType(dicData, NsConfigDTI.sDtiPclSelection)

        self.xCfgModifier = CConfigModifyList(self.lMod)
        self.xCfgGenerator = CConfigGenerateList(self.lGen)

        self.sPathTrgMain = self.dicCfg.get("sPathTrgMain")
        self.iFrameFirst = self.dicCfg.get("iFrameFirst", 0)
        self.iFrameLast = self.dicCfg.get("iFrameLast", 0)
        self.iFrameStep = self.dicCfg.get("iFrameStep", 1)
        self.iRenderQuality = self.dicCfg.get("iRenderQuality", 4)
        self.bDoRender = self.dicCfg.get("bDoProcess", self.dicCfg.get("iDoProcess", 1) != 0)
        self.bDoOverwrite = self.dicCfg.get("bDoOverwrite", self.dicCfg.get("iDoOverwrite", 0) != 0)
        self.bDoSaveRenderFile = self.dicCfg.get("bDoStoreProcessData", self.dicCfg.get("iDoStoreProcessData", 0) != 0)

        ################################################################################
        # Check & print command line parameters

        self.Print("Render main path: {0}".format(self.sPathTrgMain))
        self.Print("First rendered frame: {0}".format(self.iFrameFirst))
        self.Print("Last rendered frame: {0}".format(self.iFrameLast))
        self.Print("Frame step: {0}".format(self.iFrameStep))
        self.Print("Do render: {0}".format(self.bDoRender))

        ################################################################################
        # Prepare Render loop

        self.Print("Launch Path: {0}".format(self.xPrjCfg.sLaunchPath))

        if not os.path.exists(self.sPathTrgMain):
            cathutil.path.CreateDir(self.sPathTrgMain)
        # endif

        # General variables
        if self.dicCap is None:
            self.fTargetFps = self.xScn.render.fps
        else:
            self.fTargetFps = self.dicCap.get("dFPS")
            if self.fTargetFps is None:
                raise CAnyExcept("No element 'dFPS' given in capture configuration")
            # endif
        # endif

        self.fSceneFps = self.xScn.render.fps / self.xScn.render.fps_base
        self.iTargetFrame = self.iFrameFirst
        self.fTargetTime = self.iTargetFrame / self.fTargetFps
        self.iSceneFrame = int(round(self.fSceneFps * self.fTargetTime, 0))

        self.bIsInitialized = True

        self.xCfgCycles = None
        self.xCfgRender = None

        # could not find any info on how to remove shape_keys.
        self.lSceneElementTypes = [
            "worlds",
            "collections",
            "objects",
            "volumes",
            "armatures",
            "lights",
            "cameras",
            "meshes",
            "particles",
            "materials",
            "actions",
            "node_groups",
            "textures",
            "images",
        ]
        self.dicSceneElements = {}

        # switch off undo in blender, so that deleted objects
        # are not kept in memory.
        bpy.context.preferences.edit.use_global_undo = False
        bpy.context.preferences.edit.undo_steps = 0

    # enddef

    ################################################################################
    # Init Rendering
    @logFunctionCall
    def InitRender(self):
        """Initializes the rendering by calling generators, setting the camera, registering animations, etc."""

        self.Print("\n>>> Memory usage before render init:\n")
        bpy.ops.wm.memory_statistics()
        self.Print("\n")

        # Only needed when using RestoreScene().
        # However, we are reverting the whole scene to the original in Finalize().
        # self._StoreSceneState()

        # Initialize Scene based on config files
        # The order of the following function calls is important
        self._ApplyCfgGenerateObjects()
        self._ApplyCfgCamera()
        self._ApplyCfgModifier(sMode="INIT")
        self._ApplyCfgAnimation()
        self._ApplyCfgPointClouds()

    # enddef

    ##############################################################
    # Clean-up after rendering
    @logFunctionCall
    def Finalize(self):
        self.Print("\n>>> Memory usage after render finalize:\n")
        bpy.ops.wm.memory_statistics()

        # This seems to be the only way to get consistent behaviour
        self.Print("\n>>> Reverting Blender file\n")
        # Loads the original file again
        self._RestoreScene()

    # enddef

    ##############################################################
    # Activate selected anycam camera
    @logFunctionCall
    def _ApplyCfgCamera(self):
        if self.sCameraName is None:
            return
        # endif

        try:
            logFunctionCall.PrintLog(f"activating: {self.sCameraName}")
            anycam.ops.ActivateCamera(self.xCtx, self.sCameraName)
        except CAnyExcept as xEx:
            sMsg = "ERROR: Camera '{0}' cannot be activated: {1}".format(self.sCameraName, str(xEx))
            self.Print(sMsg)
            raise CAnyExcept(sMsg)
        except AttributeError:
            sMsg = "Anycam ist not installed"
            self.Print(sMsg)
            raise CAnyExcept(sMsg)
        # endtry

        if self.sCameraParentName is not None:
            anycam.ops.ParentAnyCam(sCamId=self.sCameraName, sParentId=self.sCameraParentName)
        # endif

        # Get anycam data from selected camera
        self.dicAnyCam = anycam.ops.GetAnyCam(self.xCtx, self.sCameraName).get("dicAnyCam")

        # Store anycam data of selected camera
        sFpAnyCam = os.path.join(self.sPathTrgMain, "AnyCam.json")
        self.Print("Writing AnyCam camera config to file: {0}".format(sFpAnyCam))
        anycam.ops.WriteCameraAnyCamData(self.xCtx, self.sCameraName, sFpAnyCam)

    # enddef

    ##############################################################
    # Get render settings from render output list and
    # current render output type

    def _GetCfgRenderSettings(self, _lSettings) -> CRenderSettings:
        xSetting = CRenderSettings()
        if _lSettings:
            for dicSettings in _lSettings:
                bIsMain = cathcfg.CheckConfigType(dicSettings, NsConfigDTI.sDtiRenderSettingsMain)["bOK"]
                bIsCycles = cathcfg.CheckConfigType(dicSettings, NsConfigDTI.sDtiRenderSettingsCycles)["bOK"]
                bIsEevee = cathcfg.CheckConfigType(dicSettings, NsConfigDTI.sDtiRenderSettingsEevee)["bOK"]
                bIsRender = cathcfg.CheckConfigType(dicSettings, NsConfigDTI.sDtiRenderSettingsRender)["bOK"]
                if bIsCycles is True:
                    xSetting.mCycles = copy.deepcopy(dicSettings)
                elif bIsEevee is True:
                    xSetting.mEevee = copy.deepcopy(dicSettings)
                elif bIsRender is True:
                    xSetting.mRender = copy.deepcopy(dicSettings)
                elif bIsMain is True:
                    xSetting.mMain = copy.deepcopy(dicSettings)
                else:
                    raise Exception("Unsupported settings type: {0}".format(dicSettings.get("sDTI", "no DTI given")))
                # endif
            # endfor
        # end if

        return xSetting

    # enddef

    ##############################################################
    # Combine different render settings
    def _GetCombinedCfgRenderSettings(
        self, _dicRndOut, dicCycles=None, dicEevee=None, dicRender=None, dicMain=None
    ) -> CRenderSettings:
        xSelfRenderSettings: CRenderSettings = self._GetCfgRenderSettings(self.lRndSettings)
        xDictRenderSettings: CRenderSettings = self._GetCfgRenderSettings(_dicRndOut.get("lSettings"))

        xSelfRenderSettings.mMain.update(xDictRenderSettings.mMain)
        xSelfRenderSettings.mCycles.update(xDictRenderSettings.mCycles)
        xSelfRenderSettings.mEevee.update(xDictRenderSettings.mEevee)
        xSelfRenderSettings.mRender.update(xDictRenderSettings.mRender)

        if dicCycles is not None:
            xSelfRenderSettings.mCycles.update(dicCycles)
        # endif

        if dicEevee is not None:
            xSelfRenderSettings.mEevee.update(dicEevee)
        # endif

        if dicRender is not None:
            xSelfRenderSettings.mRender.update(dicRender)
        # endif

        if dicMain is not None:
            xSelfRenderSettings.mMain.update(dicMain)
        # endif

        return xSelfRenderSettings

    # enddef

    ##############################################################
    def _ApplyCfgRenderSettings(self, _xRenderSettings: CRenderSettings):
        if len(_xRenderSettings.mCycles.keys()) > 0:
            # print(f">>> RENDER SETTINGS CYCLES: {_xRenderSettings.mCycles}")

            self.xCfgCycles = CConfigSettingsCycles(_xRenderSettings.mCycles)
            self.xCfgCycles.Apply(self.xCtx)
        # endif

        if len(_xRenderSettings.mEevee.keys()) > 0:
            self.xCfgEevee = CConfigSettingsEevee(_xRenderSettings.mEevee)
            self.xCfgEevee.Apply(self.xCtx)
        # endif

        if len(_xRenderSettings.mRender.keys()) > 0:
            self.xCfgRender = CConfigSettingsRender(_xRenderSettings.mRender)
            self.xCfgRender.Apply(self.xCtx)
        # endif

    # enddef

    ##############################################################
    def _ApplyCombinedCfgRenderSettings(self, _dicRndOut, dicCycles=None, dicEevee=None, dicRender=None, dicMain=None):
        xSettings: CRenderSettings = self._GetCombinedCfgRenderSettings(
            _dicRndOut, dicCycles=dicCycles, dicEevee=dicEevee, dicRender=dicRender, dicMain=dicMain
        )
        # self.Print("\nApplying render settings:\n{}\n\n".format(dicSet))
        self._ApplyCfgRenderSettings(xSettings)

    # enddef

    ##############################################################
    def _RestoreCfgRenderSettings(self):
        if self.xCfgCycles is not None:
            self.xCfgCycles.Apply(self.xCtx, bRestore=True)
            self.xCfgCycles = None
        # endif

        if self.xCfgRender is not None:
            self.xCfgRender.Apply(self.xCtx, bRestore=True)
            self.xCfgRender = None
        # endif

    # enddef

    ##############################################################
    # get the render output Type string (useful for factory)
    def _GetRenderOutType(self, _dicRndOut, _sTargetDti) -> CRenderOutputType:
        dicCfgType = cathcfg.CheckConfigType(_dicRndOut, _sTargetDti)
        if not dicCfgType.get("bOK"):
            raise CAnyExcept("Invalid render output configuration given")
        # endif

        lRndOutType = dicCfgType.get("lCfgType")[4:]  #  -> main, [optinal:specific] and version
        if len(lRndOutType) == 0:
            raise CAnyExcept("No specific render output type given")
        # endif

        return CRenderOutputType(
            lRndOutType[0],
            lRndOutType[1] if len(lRndOutType) > 1 else None,
            dicCfgType.get("sCfgDti"),
        )

    # enddef

    ##############################################################
    # Apply render output configuration
    def _ApplyCommonRenderOutputSettings(self, _dicRndOut):
        if self.xRndOutType is None:
            raise CAnyExcept("render output is not configured correctly")
        # endif

        self.sRenderOutType = self.xRndOutType.JoinTypes()
        self.bApplyAnnotation = False
        self.sAnnotationType = None
        self.bLabelEvalBoxes2d = False

        ###############################################################
        # Apply render settings from render output list and
        # current render output type

        if self.xRndOutType.sMainType == NsMainTypesRenderOut.image:
            self.lFileOut = None

            if self.xRndOutType.sSpecificType is None:
                # Apply compositor configuration
                dicComp = _dicRndOut.get("mCompositor")
                cathcfg.AssertConfigType(dicComp, NsConfigDTI.sDtiCompositor)
                self.lFileOut = dicComp.get("lFileOut")
            # endif

            if self.xRndOutType.sSpecificType == NsSpecificTypesRenderOut.image_openGL:
                # openGL go directly to lFileOut
                self.lFileOut = _dicRndOut.get("lFileOut")
            # endif

            if self.lFileOut is None:
                raise CAnyExcept("Unsupported AnyTruth render output type '{0}'".format(self.xRndOutType.sSpecificType))
            # endif

            for dicFo in self.lFileOut:
                dicFo["sFilename"] = "Exp_#######"
            # endfor

        elif self.xRndOutType.sMainType == NsMainTypesRenderOut.anytruth:
            if self.xRndOutType.sSpecificType is None:
                raise CAnyExcept("No specific AnyTruth render output type given")
            # endif

            if self.xRndOutType.sSpecificType == NsSpecificTypesRenderOut.anytruth_label:
                self.bApplyAnnotation = True
                self.sAnnotationType = "LABEL"
                self.bLabelEvalBoxes2d = convert.DictElementToBool(_dicRndOut, "bEvalBoxes2d", bDefault=False)

            elif self.xRndOutType.sSpecificType == NsSpecificTypesRenderOut.anytruth_pos3d:
                self.bApplyAnnotation = True
                self.sAnnotationType = "POS3D"

            elif self.xRndOutType.sSpecificType == NsSpecificTypesRenderOut.anytruth_localpos3d:
                self.bApplyAnnotation = True
                self.sAnnotationType = "LOCALPOS3D"

            elif self.xRndOutType.sSpecificType == NsSpecificTypesRenderOut.anytruth_objectidx:
                self.bApplyAnnotation = True
                self.sAnnotationType = "OBJIDX"

            elif self.xRndOutType.sSpecificType == NsSpecificTypesRenderOut.anytruth_objectloc3d:
                self.bApplyAnnotation = True
                self.sAnnotationType = "OBJLOC3D"

            else:
                raise CAnyExcept("Unsupported AnyTruth render output type '{0}'".format(self.xRndOutType.sSpecificType))
            # endif
        else:
            raise CAnyExcept("Render output type '{0}' not supported".format(self.xRndOutType.sActualDti))
        # endif

    # enddef

    ##############################################################
    # Apply render output configuration
    def _ApplyCfgRenderOutputFiles(
        self,
        _dicRndOut: dict,
        *,
        _sPathTrgMain: Optional[str] = None,
    ):
        sPathTrgMain: str = _sPathTrgMain if _sPathTrgMain is not None else self.sPathTrgMain

        self.xRndOutType = self._GetRenderOutType(_dicRndOut, NsConfigDTI.sDtiRenderOutputAll)
        self._ApplyCommonRenderOutputSettings(_dicRndOut)  # raise exception for unhandled, or bad configured

        try:
            self.xCompFileOut = CFileOut(self.xScn)
        except Exception as xEx:
            raise CAnyError_Message(
                sMsg="Error initializing Blender compositor for file output",
                xChildEx=xEx,
            )
        # endtry

        ###############################################################
        # Apply render settings from render output list and
        # current render output type
        if self.xRndOutType.sMainType == NsMainTypesRenderOut.image:
            if self.xRndOutType.sSpecificType is None:
                # Apply file out config to compositor
                self.xCompFileOut.SetFileOut(sPathTrgMain, self.lFileOut)
            # endif
        elif self.xRndOutType.sMainType == NsMainTypesRenderOut.anytruth:
            # nothing further to do
            pass

        else:
            raise CAnyExcept("Render output type '{0}' not supported".format(self.xRndOutType.sActualDti))
        # endif

    # enddef

    ##############################################################
    # Apply render output configuration
    def _ApplyCfgRenderOutputSettings(self, _dicRndOut):
        self.xRndOutType = self._GetRenderOutType(_dicRndOut, NsConfigDTI.sDtiRenderOutputAll)
        self._ApplyCommonRenderOutputSettings(_dicRndOut)  # raise exception for unhandled, or bad configured

        # Set default render quality from launch args
        # This may be overwritten by the render output type
        iRenderQuality = self.iRenderQuality

        ###############################################################
        # Apply render settings from render output list and
        # current render output type

        if self.xRndOutType.sMainType == NsMainTypesRenderOut.image:
            # Apply render/cycles parameters if available
            self._ApplyCombinedCfgRenderSettings(_dicRndOut)

        elif self.xRndOutType.sMainType == NsMainTypesRenderOut.anytruth:
            dicCamType = anycam.ops.GetAnyCamTypeFromId(self.xCtx, self.sCameraName)
            if dicCamType.get("sType") == "lft":
                raise Exception("AnyTruth does currently not support LFT cameras")
            # endif

            self._ApplyCombinedCfgRenderSettings(
                _dicRndOut, dicCycles={"sDTI": "/catharsys/blender/render/settings/cycles:1.0", "use_denoising": False}
            )

            # Override render quality as we only need single ray for all cameras
            # apart from LFT cameras.
            iRenderQuality = 1
        else:
            raise CAnyExcept("Render output type '{0}' not supported".format(self.xRndOutType.sActualDti))
        # endif

        # Force render border use, so that cameras work
        self.xScn.render.use_border = True
        self.xScn.render.use_crop_to_border = True

        if hasattr(self.xScn.cycles, "use_square_samples") is True:
            # Do not use square samples
            self.xScn.cycles.use_square_samples = False
        # endif

        if hasattr(self.xScn.cycles, "progressive") is True:
            # Set/get render quality AFTER anycam camera has been activated
            if iRenderQuality <= 0:
                if self.xScn.cycles.progressive == "BRANCHED_PATH":
                    iRenderQuality = self.xScn.cycles.aa_samples
                else:
                    iRenderQuality = self.xScn.cycles.samples
                # endif
            else:
                if self.xScn.cycles.progressive == "BRANCHED_PATH":
                    self.xScn.cycles.aa_samples = iRenderQuality
                else:
                    self.xScn.cycles.samples = iRenderQuality
                # endif
            # endif
        else:
            if iRenderQuality <= 0:
                iRenderQuality = self.xScn.cycles.samples
            else:
                self.xScn.cycles.samples = iRenderQuality
            # endif
        # endif

        self.Print("Render quality: {0}".format(iRenderQuality))

    # enddef

    ##############################################################
    # Create dictionary of runtime variables
    def _GetRuntimeVars(self):
        dicConstVars = {
            "render": {
                "target-frame-first": self.iFrameFirst,
                "target-frame-last": self.iFrameLast,
                "target-frame-step": self.iFrameStep,
                "target-frame": self.iTargetFrame,
                "target-time": self.fTargetTime,
                "target-fps": self.fTargetFps,
                "scene-fps": self.fSceneFps,
                "scene-frame": self.iSceneFrame,
                "active-camera": self.sCameraName,
                "active-camera-parent": self.sCameraParentName,
                "active-camera-anycam": self.dicAnyCam,
            }
        }

        dicRefVars = {"bpy": bpy}

        return dicConstVars, dicRefVars

    # enddef

    ##############################################################
    # Apply defined generations of objects, if available
    def _ApplyCfgGenerateObjects(self):
        dicConstVars, dicRefVars = self._GetRuntimeVars()
        self.xCfgGenerator.Apply(dicConstVars=dicConstVars, dicRefVars=dicRefVars)

    # enddef

    ##############################################################
    # Apply defined modifications to objects, if available
    def _ApplyCfgModifier(self, *, sMode):
        dicConstVars, dicRefVars = self._GetRuntimeVars()
        self.xCfgModifier.Apply(sMode=sMode, dicConstVars=dicConstVars, dicRefVars=dicRefVars)

    # enddef

    ###########################################################
    # Apply animation configs
    def _ApplyCfgAnimation(self):
        if len(self.lAnim) > 0:
            # clear all pre frame handler
            anyblend.anim.util.ClearAnim()

            for dicAnim in self.lAnim:
                # Apply animation config
                dicAnimObj = dicAnim.get("mObjects")

                # register all animations in list
                animobj.RegisterAnimList(dicAnimObj)
            # endfor
        # endif

    # enddef

    ###########################################################
    # Initialize Point Cloud Data
    def _ApplyCfgPointClouds(self):
        self.xPclSet = anypoints.CPointCloudSet()
        for dicPclRef in self.lPclRefSet:
            sFpConfig = dicPclRef.get("sConfig")
            if sFpConfig is None:
                raise CAnyExcept("Element 'sConfig' not defined in point cloud reference configuration file")
            # endif

            self.xPclSet.AddFromFile(sFpConfig)
        # endfor

        self.bHasPointClouds = self.xPclSet.GetCount() > 0

        if self.bHasPointClouds:
            # Initialize point cloud selection
            # Create point cloud objects in their own collection
            anyblend.collection.MakeRootLayerCollectionActive(self.xCtx)
            self.xClnPcl = anyblend.collection.CreateCollection(self.xCtx, "PointCloudSets")

            self.lPclSels = []
            for dicPclSelection in self.lPclSelection:
                xPclSelect = anypoints.CPointCloudSelection()
                xPclSelect.Init(dicSel=dicPclSelection, xPointCloudSet=self.xPclSet)
                self.lPclSels.append(xPclSelect)

                # Import static point clouds
                xPclSelect.Import(bUseAnimated=False)
            # endfor

            self.dicAnimPclSel = {}
        # endif

    # enddef

    ###########################################################
    # Import of point clouds that vary per frame
    def _AnimPointClouds(self, _iScnFrame):
        if self.bHasPointClouds:
            self.xPclSet.RemovePointCloudDict(self.dicAnimPclSel)
            anyblend.collection.SetActiveCollection(self.xCtx, self.xClnPcl.name)
            self.dicAnimPclSel = {}
            for xPclSelect in self.lPclSels:
                dicSel = xPclSelect.Import(bUseAnimated=True, iFrame=_iScnFrame)
                self.dicAnimPclSel.update(dicSel)
            # endfor
        # endif

    # enddef

    ###########################################################
    # Apply label render settings after modifications, animations
    # and point clouds are loaded and applied
    def _ApplyCfgAnnotation(
        self,
        *,
        _sPathTrgMain: Optional[str] = None,
        _bApplyFilePathsOnly=False,
    ):
        if self.bApplyAnnotation:
            # Disable auto-update of label data with frame change.
            anytruth.ops_labeldb.EnableAutoUpdateAnnotation(self.xCtx, False)

            if _sPathTrgMain is not None:
                sPathTrgMain = _sPathTrgMain
            else:
                sPathTrgMain = self.sPathTrgMain
            # endif

            anytruth.ops_labeldb.ApplyLabelRenderSettings(
                self.xCtx,
                sAnnotationType=self.sAnnotationType,
                sPathTrgMain=sPathTrgMain,
                xCompFileOut=self.xCompFileOut,
                sFilename="Exp_#######",
                bApplyFilePathsOnly=_bApplyFilePathsOnly,
                bEvalBoxes2d=self.bLabelEvalBoxes2d,
            )
        # endif

    # enddef

    ###########################################################
    def _UpdatePos3dOffset(self):
        if self.bApplyAnnotation and self.sAnnotationType == "POS3D":
            anytruth.ops_labeldb.UpdatePos3dOffset(self.xCtx)
        # endif

    # enddef

    ###########################################################
    # If an annotation has been applied to the scene
    # then restore the scene to normal, here.
    def _RestoreCfgAnnotation(self):
        if self.bApplyAnnotation:
            anytruth.ops_labeldb.ApplyAnnotation(self.xCtx, False, self.sAnnotationType)
        # endif

    # enddef

    ##############################################################
    def _ExportLabelData(
        self,
        _sPath,
        _iTrgFrame,
        *,
        _sFrameNamePattern: Optional[str] = None,
        _bUpdateLabelData3d: bool = True,
        _bEvalBoxes2d: bool = False,
    ):
        if _sFrameNamePattern is not None:
            sFrameNamePattern = _sFrameNamePattern
        else:
            sFrameNamePattern = "Frame_{0:04d}.json"
        # endif

        if self.sRenderOutType == "anytruth/label":
            pathExData: Path = self.xPrjCfg.pathProduction / "AT_CommonData"
            pathExData.mkdir(parents=True, exist_ok=True)

            sFpLabel = os.path.join(_sPath, sFrameNamePattern.format(_iTrgFrame))
            self.Print("Exporting label types to: {0}".format(sFpLabel))
            anytruth.ops_labeldb.ExportAppliedLabelTypes(
                bpy.context,
                sFpLabel,
                bOverwrite=False,
                bUpdateLabelData3d=_bUpdateLabelData3d,
                bEvalBoxes2d=_bEvalBoxes2d,
                _pathExData=pathExData,
            )

        elif self.sRenderOutType == "anytruth/pos3d":
            sFpLabel = os.path.join(_sPath, sFrameNamePattern.format(_iTrgFrame))
            self.Print("Exporting pos3d info to: {0}".format(sFpLabel))
            anytruth.ops_labeldb.ExportPos3dInfo(bpy.context, sFpLabel)
        # endif

    # enddef

    ##############################################################
    def _PostProcLabelRender(self, *, _sFpRender: str, _bTransformSceneToCameraFrame: bool):
        # If pos3d ground truth was rendered, some offset was applied for rendering.
        # Transform the rendered image back to absolute 3d world coordinates.
        # Furthermore, if the scene was transformed to the camera frame, then
        # transform the data back.
        if self.sRenderOutType == "anytruth/pos3d":
            lOffsetPos3d = anytruth.ops_labeldb.GetOffsetPos3d()

            lMatOrig: list = None
            if _bTransformSceneToCameraFrame is True:
                lMatOrig = anycam.ops.GetTransformCameraFrame()
            # endif

            imgSrc = cv2.imread(
                _sFpRender,
                cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH | cv2.IMREAD_UNCHANGED,
            )
            if imgSrc is None:
                raise RuntimeError(f"Error loading image for pos3d ground truth post-processing: {_sFpRender}")
            # endif
            iSrcRows, iSrcCols, iSrcChnl = tSrcShape = imgSrc.shape

            # pathSrc = Path(_sFpRender)
            # pathTrg = pathSrc.parent / (pathSrc.name + "_src.exr")
            # cv2.imwrite(pathTrg.as_posix(), imgSrc.astype(np.float32))

            # Transfrom from BGR to XYZ vector in RGB channels
            imgSrcVec = np.flip(imgSrc, axis=2)

            imgMask = np.logical_or(imgSrcVec[:, :, 0] > 0.0, imgSrcVec[:, :, 1] > 0.0)
            imgMask = np.logical_or(imgMask, imgSrcVec[:, :, 2] > 0.0)
            imgMask = np.logical_and(imgMask, imgSrcVec[:, :, 0] < 9e5)

            aRenderOffset = np.array(lOffsetPos3d)

            imgSrcVec = np.subtract(
                imgSrcVec, aRenderOffset[np.newaxis, np.newaxis, :], where=imgMask[:, :, np.newaxis]
            )
            imgSrcVec[~imgMask] = 0.0

            if lMatOrig is not None:
                aMatOrig = np.array(lMatOrig)
                aTrans = aMatOrig[0:3, 3].reshape(3)
                aRot = aMatOrig[0:3, 0:3]

                imgSrcVec = np.tensordot(aRot, imgSrcVec, axes=(1, 2))
                imgSrcVec = np.transpose(imgSrcVec, axes=(1, 2, 0))
                imgSrcVec = np.add(imgSrcVec, aTrans[np.newaxis, np.newaxis, :], where=imgMask[:, :, np.newaxis])
                imgSrcVec[~imgMask] = 0.0
            # endif

            # Flip back to BGR for OpenCV write function
            imgTrg = np.flip(imgSrcVec, axis=2)

            cv2.imwrite(_sFpRender, imgTrg.astype(np.float32))
        # endif

    # enddef

    ##############################################################
    def _SaveBlenderFile(self, _iTrgFrame):
        sRelPathRenderOutput = os.path.relpath(self.sPathTrgMain, self.xPrjCfg.sRenderPath)
        sRelPathRenderOutput = os.path.normpath(sRelPathRenderOutput)
        lRelPathRenderOutput = sRelPathRenderOutput.split(os.sep)

        sBlenderDebugFileSuffix = "-".join(lRelPathRenderOutput)

        if not isinstance(self.sRenderOutType, str):
            sOutType = "-"
        else:
            sOutType = self.sRenderOutType.replace("/", "-")
        # endif

        sBlenderDebugFilePath = bpy.path.abspath("//")
        if sBlenderDebugFilePath == "":
            sBlenderDebugFilePath = self.sPathTrgMain
        # endif

        sFpBlenderFile = os.path.normpath(
            os.path.join(
                sBlenderDebugFilePath,
                "Blender-{0}-{1:04d}-{2}.blend".format(sOutType, _iTrgFrame, sBlenderDebugFileSuffix),
            )
        )

        if os.path.exists(sFpBlenderFile):
            os.remove(sFpBlenderFile)
        # endif

        print("Saving Blender file: {}".format(sFpBlenderFile))
        try:
            anyblend.app.file.PackAllLocal()
        except Exception:
            print("PackAllLocal failed, attempting to pack individual images instead")
            for imgX in bpy.data.images:
                try:
                    imgX.pack()
                except Exception:
                    print(f"Packing of image {imgX.name} failed, skipping")
                    pass
                # endtry
            # endfor
        # endtry
        bpy.ops.wm.save_mainfile(filepath=sFpBlenderFile)

    # enddef

    ################################################################################
    # Store names of all collections, objects, materials, images, node_groups
    def _StoreSceneState(self):
        self.dicSceneElements = {}
        for sType in self.lSceneElementTypes:
            xData = getattr(bpy.data, sType)
            self.dicSceneElements[sType] = [x.name for x in xData]
        # endfor

    # enddef

    ##############################################################
    def _RestoreScene(self):
        ###########################################################
        # Need to clear animation explicitly, so that internal
        # book-keeping of animation handlers works.
        if len(self.lAnim) > 0:
            anyblend.anim.util.ClearAnim()
        # endif

        # Re-load the initial Blender file.
        # This is the easiest and most stable way to get back to the
        # original setup.
        bpy.ops.wm.open_mainfile(filepath=self.sFpBlendOrig)

        # explicitly do a garbage collection
        gc.collect()

    # enddef


# endclass
