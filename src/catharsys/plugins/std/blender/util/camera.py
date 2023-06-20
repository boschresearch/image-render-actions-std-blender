#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /configutil.py
# Created Date: Thursday, October 22nd 2020, 4:26:28 pm
# Author: Christian Perwass
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

# configuration utility functions, to simplify recurring config functionality
import bpy

import json
import copy
from catharsys.util import config
from anybase.cls_any_error import CAnyError_Message
from anybase import convert
from anycam.ops_camset_file import ImportCamera

from catharsys.decs.decorator_log import logFunctionCall


################################################################################
# Get Camera name or camera name and parent depending on whether only
# a camera name is given or a camera set with a pose name.
@logFunctionCall
def GetSelectedCameraName(_dicData, *, bDoRaise: bool = True):
    sCameraNameType = "camera-name:1"
    sCameraSetType = "camera-set:1"
    sCameraPoseType1 = "camera-pose-path:1"
    sCameraPoseType2 = "camera-set/pose-path:1"

    sCameraName = None
    sCameraParentName = None

    lCamName = config.GetDataBlocksOfType(_dicData, sCameraNameType)
    if len(lCamName) > 0:
        sCameraName = lCamName[0]
    else:
        lCamSet = config.GetDataBlocksOfType(_dicData, sCameraSetType)
        if len(lCamSet) == 0:
            if bDoRaise:
                raise Exception("No camera names of type compatible to '{0}' given".format(sCameraSetType))
            # endif
            logFunctionCall.PrintLog("returning None")
            return None
        # endif
        dicCamSet = lCamSet[0]

        # Get current camera pose. If no camera pose is given, then return None for camera name and parent.
        lCamPose = config.GetDataBlocksOfType(_dicData, sCameraPoseType1)
        if len(lCamPose) == 0:
            lCamPose = config.GetDataBlocksOfType(_dicData, sCameraPoseType2)
            if len(lCamPose) == 0:
                if bDoRaise:
                    raise Exception(
                        "No camera names of type compatible to '{0}' or '{1}' given".format(
                            sCameraPoseType1, sCameraPoseType2
                        )
                    )
                # endif
                logFunctionCall.PrintLog("returning None")
                return None
            # endif
        # endif
        sCamPosePath = lCamPose[0]

        dicCamPose = config.GetDictValue(
            dicCamSet,
            "mConfigs/" + sCamPosePath,
            dict,
            bAllowKeyPath=True,
            sWhere=f"camera set '{sCameraSetType}'",
        )

        sCameraParentName = dicCamPose.get("sParent")
        if sCameraParentName is None:
            if bDoRaise:
                raise Exception("Camera parent name not given in camera pose '{0}'.".format(sCamPosePath))
            # endif
            logFunctionCall.PrintLog("returning None")
            return None
        # endif

        if config.IsConfigType(dicCamPose, "/catharsys/camera-pose-import:1.0"):
            sCamSetId = convert.DictElementToString(dicCamSet, "sId")
            try:
                sCameraDbPath = convert.DictElementToString(dicCamPose, "sCameraDbPath")
                sCameraId = convert.DictElementToString(dicCamPose, "sCameraId")
                sCameraUserName = convert.DictElementToString(dicCamPose, "sCameraName")
                bReplace = convert.DictElementToBool(dicCamPose, "bReplace", bDefault=True)

                sCameraName = ImportCamera(
                    _sCamSetId=sCamSetId,
                    _sCamDbPath=sCameraDbPath,
                    _sCamPosePath=sCamPosePath,
                    _sCamId=sCameraId,
                    _sCamName=sCameraUserName,
                    _sParent=sCameraParentName,
                    _bReplace=bReplace,
                )
            except Exception as xEx:
                raise CAnyError_Message(sMsg=f"Error importing camera for camera set '{sCamSetId}'", xChildEx=xEx)
            # endtry

        elif config.IsConfigType(dicCamPose, "/catharsys/camera-pose:1.1"):
            sCameraName = dicCamPose.get("sCamera")
            if sCameraName is None:
                if bDoRaise:
                    raise Exception("Camera name not given in camera pose '{0}'.".format(sCamPosePath))
                # endif
                logFunctionCall.PrintLog("returning None")
                return None
            # endif

        else:
            sCamPoseDti = dicCamPose.get("sDTI")
            raise RuntimeError(f"Unsupported camera pose type '{sCamPoseDti}' for pose id '{sCamPosePath}'")
        # endif

    # endif

    logFunctionCall.PrintLog(f"sCameraName: {sCameraName}, sCameraParentName: {sCameraParentName}")
    return {"sCameraName": sCameraName, "sCameraParentName": sCameraParentName}


# enddef


################################################################################
# Get Camera Set dictionary
@logFunctionCall
def GetCameraSet(_dicData, **kwargs):
    bDoThrow = kwargs.pop("bRaiseException", True)

    sCameraSetType = "camera-set:1"

    lCamSet = config.GetDataBlocksOfType(_dicData, sCameraSetType)
    if len(lCamSet) == 0:
        if bDoThrow:
            raise Exception("No camera names of type compatible to '{0}' given".format(sCameraSetType))
        # endif
        return None
    # endif
    dicCamSet = lCamSet[0].get("mConfigs")
    # print("dicCamSet: {0}".format(dicCamSet))

    lPaths = config.GetDictPaths(dicCamSet, sDTI="camera-pose:1")

    lCfg = []
    for sPath in lPaths:
        dicCfg = copy.deepcopy(config.GetDictValue(dicCamSet, sPath, dict, bAllowKeyPath=True, sWhere="camera set"))
        # dicCfg = copy.deepcopy(config.GetElementAtPath(dicCamSet, sPath))
        dicCfg["sPath"] = sPath
        lCfg.append(dicCfg)
    # endfor

    return lCfg


# enddef


############################################################################################
@logFunctionCall
def GetCameraData(_sObjId):
    objX = bpy.data.objects.get(_sObjId)
    if objX is None:
        raise Exception("Object with id '{0}' not found".format(_sObjId))
    # endif

    camX = objX.data
    sCamType = camX.type
    if sCamType == "PANO":
        sCamPanoType = camX.cycles.panorama_type
        sCamPanoFishFov = camX.cycles.fisheye_fov
    else:
        sCamPanoType = None
    # endif

    dicCam = {
        "focal_length_mm": camX.lens,
        "blender_type": sCamType,
        "sensor_width_mm": camX.sensor_width,
        "sensor_height_mm": camX.sensor_height,
        "shift_x": camX.shift_x,
        "shift_y": camX.shift_y,
    }

    if sCamPanoType is not None:
        dicCam["blender_pano_type"] = sCamPanoType
        if sCamPanoType == "FISHEYE_EQUIDISTANT":
            dicCam["blender_pano_equidist_fov"] = sCamPanoFishFov
        elif sCamPanoType == "EQUIRECTANGULAR":
            dicCam["blender_pano_equirect_fov_range"] = [
                [camX.cycles.longitude_min, camX.cycles.longitude_max],
                [camX.cycles.latitude_min, camX.cycles.latitude_max],
            ]
        # endif
    # endif

    sAnyCam = objX.get("AnyCam")
    if sAnyCam is not None:
        dicAnyCam = json.loads(sAnyCam)
        iResX = dicAnyCam.get("iSenResX")
        iResY = dicAnyCam.get("iSenResY")
        dicCam["sensor_res_x"] = iResX
        dicCam["sensor_res_y"] = iResY
        dicCam["aspect_x"] = dicAnyCam.get("fAspectX")
        dicCam["aspect_y"] = dicAnyCam.get("fAspectY")
        dicCam["anycam_type"] = dicAnyCam.get("lType")
        dicCam["render_res_x"] = dicAnyCam.get("iRenderResX", iResX)
        dicCam["render_res_y"] = dicAnyCam.get("iRenderResY", iResY)
        dicCam["crop"] = dicAnyCam.get("lCrop", [0, 1, 0, 1])
    # endif sAnyCam

    return dicCam


# enddef
