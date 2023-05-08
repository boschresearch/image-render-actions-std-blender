#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \cathy\cls_cfg_cameraset.py
# Created Date: Thursday, December 3rd 2020, 12:09:24 pm
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

import copy
from catharsys.util import file
from catharsys.plugins.std.blender.util import camera


################################################################################################
# Class to handle camera sets
class CConfigCameraSet:

    ################################################################################################
    def __init__(self):
        self.bIsValid = False
        self.lCameraSet = None
        self.dicCameras = None

    # enddef

    ################################################################################################
    def IsValid(self):
        return self.bIsValid

    # enddef

    ################################################################################################
    # Init class from config dictionary
    def InitFromConfig(self, _dicData, **kwargs):

        bRaiseException = kwargs.pop("bRaiseException", True)
        self.bIsValid = False

        # attempt to load camera set list
        self.lCameraSet = camera.GetCameraSet(_dicData, bRaiseException=bRaiseException)
        if self.lCameraSet is None:
            return
        # endif

        # find unique set of cameras
        self.dicCameras = {}
        for dicCam in self.lCameraSet:
            sCamName = dicCam.get("sCamera")
            if sCamName not in self.dicCameras:
                self.dicCameras[sCamName] = copy.deepcopy(dicCam)
            # endif
        # endfor

        # print(self.lCameraSet)
        # print(self.dicCameras)

        self.bIsValid = True

    # enddef

    ################################################################################################
    # Get intrinsic and extrinsic data for all cameras from Blender
    def GetBlenderData(self):

        if not self.IsValid():
            raise Exception("CameraSet class not initialized")
        # endif

        try:
            from catharsys.plugins.std.blender.util.object import GetWorldMatrix
            from catharsys.plugins.std.blender.util.camera import GetCameraData
        except Exception:
            raise Exception("Can only read blender data in blender context")
        # endtry

        for sCamId in self.dicCameras:
            dicCam = self.dicCameras.get(sCamId)
            sObjId = dicCam.get("sCamera")
            if sObjId is None:
                raise Exception("No camera object id given")
            # endif
            dicCam["dicIntrinsics"] = GetCameraData(sObjId)
        # endfor

        for dicCam in self.lCameraSet:
            sObjId = dicCam.get("sParent")
            if sObjId is None:
                raise Exception("No parent object id given")
            # endif
            # This currently assumes that all objects in the camera set are cameras.
            # Their rotation matrices are transformed to agree with the "rbcv" convention,
            # where x, y, z axes are right, down, forward.
            dicCam["dicExtrinsics"] = GetWorldMatrix(sObjId, sType="decomposed", sConvention="rbcv")
        # endfor

        # print(self.lCameraSet)
        # print(self.dicCameras)

    # enddef

    ################################################################################################
    # Export camera set data in BOSCH CR/AEC camera calibration YAML format
    def SaveYaml(self, _sFilename):

        if not self.IsValid():
            raise Exception("CameraSet class not initialized")
        # endif

        if self.lCameraSet is None or self.dicCameras is None:
            raise Exception("No camera set defined")
        # endif

        lInvalidCameras = []

        sY = "version_major: 8\n"
        sY += "version_minor: 0\n\n"

        # Write sensor intrinsics
        sY += "sensors:\n"
        for sCamId in self.dicCameras:
            dicCam = self.dicCameras.get(sCamId)
            sCamName = dicCam.get("sCamera")
            if sCamName is None:
                raise Exception("No camera name given")
            # endif

            sCamName = sCamName.replace(".", "_")
            dicIntrinsics = dicCam.get("dicIntrinsics")
            if dicIntrinsics is None:
                raise Exception("No intrinics available for camera '{0}'".format(sCamName))
            # endif

            # print("===========================================")
            # print(dicIntrinsics)

            fFocLen_mm = dicIntrinsics.get("focal_length_mm")
            fSensorWidth_mm = dicIntrinsics.get("sensor_width_mm")
            # fSensorHeight_mm = dicIntrinsics.get("sensor_height_mm")
            iResX = dicIntrinsics.get("sensor_res_x")
            iResY = dicIntrinsics.get("sensor_res_y")
            iRenderResX = dicIntrinsics.get("render_res_x", iResX)
            iRenderResY = dicIntrinsics.get("render_res_y", iResY)

            fShiftX = dicIntrinsics.get("shift_x")
            fShiftY = dicIntrinsics.get("shift_y")

            iResMax = max(iRenderResX, iRenderResY)
            fPixShiftX = fShiftX * iResMax
            fPixShiftY = fShiftY * iResMax

            lCrop = dicIntrinsics.get("crop")
            if lCrop is not None:
                fPixCropLeft = lCrop[0] * iRenderResX
                fPixCropRight = lCrop[1] * iRenderResX - 1
                fPixCropBot = lCrop[2] * iRenderResY
                fPixCropTop = lCrop[3] * iRenderResY - 1
            else:
                fPixCropLeft = 0
                fPixCropRight = iRenderResX - 1
                fPixCropBot = 0
                fPixCropTop = iRenderResY - 1
            # endif

            fCtrX = (iRenderResX - 1.0) / 2.0 - fPixShiftX - fPixCropLeft
            # Output coordinate system is top-down
            fCtrY = iResY - ((iRenderResY - 1.0) / 2.0 - fPixShiftY - fPixCropBot)

            # print("iRenderResY: {0}".format(iRenderResY))
            # print("fPixCropBot: {0}".format(fPixCropBot))
            # print("fPixShiftY: {0}".format(fPixShiftY))
            # print("iResY: {0}".format(iResY))
            # print("fCtrY: {0}".format(fCtrY))

            fPixPerMM = iResX / fSensorWidth_mm
            fFocLen_pix = fFocLen_mm * fPixPerMM

            sBlenderCamType = dicIntrinsics.get("blender_type")

            sY_cam = ""
            sY_cam += "  - &{0} !cva_camera\n".format(sCamName)
            sY_cam += "    name: {0}\n".format(sCamName)
            sY_cam += "    image_size: [{0}, {1}]\n".format(iResX, iResY)

            if sBlenderCamType == "PERSP":
                sY_cam += "    projection_id: 1\n"
                sY_cam += "    intrinsics: [{0}, {0}, {1}, {2}, 0.0]\n".format(fFocLen_pix, fCtrX, fCtrY)

            elif sBlenderCamType == "PANO":
                sPanoType = dicIntrinsics.get("blender_pano_type")
                # print("sPanoType: " + sPanoType)

                if sPanoType == "FISHEYE_EQUIDISTANT":
                    sY_cam += "    projection_id: 4\n"
                    fFov_rad = dicIntrinsics.get("blender_pano_equidist_fov")
                    fScale = max(iRenderResX, iRenderResY) / fFov_rad
                    sY_cam += "    intrinsics: [{0}, {0}, {1}, {2}]\n".format(fScale, fCtrX, fCtrY)
                else:
                    lInvalidCameras.append(sCamName)
                    continue
                    # raise Exception("Panoramic Blender camera type '{0}' currently not supported.".format(sPanoType))
                # endif
            else:
                lInvalidCameras.append(sCamName)
                continue
                # raise Exception("Unsupported Blender camera type '{0}'.".format(sBlenderCamType))
            # endif
            sY += sY_cam
        # endfor

        # Write sensor extrinsics
        sY += "tf:\n"
        sY += "  - name: world\n"
        sY += "    convention: ISO8855\n"
        sY += "    children:\n"

        for dicCam in self.lCameraSet:

            sCamName = dicCam.get("sCamera")
            sCamName = sCamName.replace(".", "_")
            if sCamName in lInvalidCameras:
                continue
            # endif

            sCamPath = dicCam.get("sPath")
            sCamPath = sCamPath.replace("/", "_").replace(".", "_")
            dicExt = dicCam.get("dicExtrinsics")
            lT = dicExt.get("lTrans")
            lR = dicExt.get("lRot")

            sY += "      - name: {0}\n".format(sCamPath)
            sY += "        convention: RBCV\n"
            sY += "        type: !SE3_parent_T_child\n"
            sY += "          translation: [{0}, {1}, {2}]\n".format(lT[0], lT[1], lT[2])
            sY += "          rotation: [{0}, {1}, {2}, {3}]\n".format(lR[1], lR[2], lR[3], lR[0])
            sY += "        sensor: *{0}\n".format(sCamName)

        # endfor

        # print(sY)
        # print("\n\n\n\n")

        file.SaveText(_sFilename, sY)

    # enddef


# endclass
