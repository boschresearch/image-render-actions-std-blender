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
import os

from .cls_render import NsConfigDTI
from .cls_render import CRender, CRenderOutputType
from .cls_render import NsMainTypesRenderOut, NsSpecificTypesRenderOut

from anybase.cls_any_error import CAnyError_Message
from catharsys.plugins.std.blender.config.cls_modify_list import CConfigModifyList
from catharsys.util import config as cathcfg

from catharsys.decs.decorator_log import logFunctionCall

import anyblend
import anycam


class CRenderStandard(CRender):
    ##############################################################
    def __init__(self, *, xPrjCfg, dicCfg):
        self.dicRenderFramesTypes: dict = None
        super().__init__(xPrjCfg=xPrjCfg, dicCfg=dicCfg, sDtiCapCfg="capture/std:1")

    # enddef

    ##############################################################
    def _EvalRenderFramesOutTypes(self):
        self.dicRenderFramesTypes = {}

        if self.bIsInitialized is False:
            raise CAnyError_Message(sMsg="Rendering is not initialized")
        # endif

        # Loop over all render outputs in config
        for iOutIdx, dicRndOut in enumerate(self.lRndOutTypes):
            self.Print("Checking render output type: {}".format(dicRndOut.get("sDTI")))

            xLocalRndOutType = self._GetRenderOutType(dicRndOut, NsConfigDTI.sDtiRenderOutputAll)

            # Loop over all frames
            self.iTargetFrame = self.iFrameFirst
            while True:
                lOutputFilenames = []
                lOutNewFilenames = []

                if xLocalRndOutType.sMainType == NsMainTypesRenderOut.blend:
                    sOutputFilename = os.path.join(
                        self.sPathTrgMain,
                        "Frame_{0:04d}.blend".format(self.iTargetFrame),
                    )
                    lOutputFilenames = lOutNewFilenames = [sOutputFilename]

                elif xLocalRndOutType.sMainType == NsMainTypesRenderOut.none:
                    sOutputFilename = None
                    lOutputFilenames = lOutNewFilenames = [sOutputFilename]
                else:
                    # Evaluate scene frame from target frame and scene fps
                    self.fTargetTime = self.iTargetFrame / self.fTargetFps
                    self.iSceneFrame = int(round(self.fSceneFps * self.fTargetTime, 0))

                    # Set the scene frame in Blender
                    # self.xScn.frame_set(self.iSceneFrame)
                    self.Print("Checking Frame Trg: {0} -> Scn: {1}".format(self.iTargetFrame, self.iSceneFrame))

                    self._ApplyCfgRenderOutputFiles(dicRndOut)
                    ### DEBUG ######
                    # print("ApplyCfgAnnotation with bApplyFilePathsOnly=True")
                    ################
                    self._ApplyCfgAnnotation(bApplyFilePathsOnly=True)

                    ######################################################
                    # Get output filenames for current frame and config
                    if xLocalRndOutType.JoinTypes() == CRenderOutputType.JoinRenderTypes(
                        NsMainTypesRenderOut.image, NsSpecificTypesRenderOut.image_openGL
                    ):
                        sFolder = self.lFileOut[0].get("sFolder")
                        sOutputFilename = os.path.join(
                            self.sPathTrgMain,
                            sFolder,
                            "openGL_{0:04d}.png".format(self.iTargetFrame),
                        )
                        lOutputFilenames = [sOutputFilename]
                    else:
                        lOutputFilenames = self.xCompFileOut.GetOutputFilenames(self.iSceneFrame)
                    # endif

                    # Construct output filenames we want to rename to later
                    lOutNewFilenames = []
                    for sFpOut in lOutputFilenames:
                        sPath = os.path.dirname(sFpOut)
                        sExt = os.path.splitext(sFpOut)[1]
                        sFpOutNew = os.path.normpath(
                            os.path.join(
                                sPath,
                                "Frame_{0:04d}{1}".format(self.iTargetFrame, sExt),
                            )
                        )
                        lOutNewFilenames.append(sFpOutNew)
                    # endfor
                # endif

                # self.Print("")
                # self.Print("self.iTargetFrame: {0}".format(self.iTargetFrame))
                # self.Print("lOutputFilenames: {0}".format(lOutputFilenames))
                # self.Print("")

                bMissing = False
                for sFo in lOutNewFilenames:
                    if sFo is None:
                        bMissing = True
                        break
                    # endif

                    self.Print("Test for rendered file: {0}".format(sFo))
                    if not os.path.isfile(sFo):
                        bMissing = True
                    elif self.bDoOverwrite:
                        self.Print("...removing file due to overwrite flag")
                        os.remove(sFo)
                    # endif
                # endfor

                if bMissing is True or self.bDoOverwrite is True:
                    dicRenderType = self.dicRenderFramesTypes.get(self.iTargetFrame)
                    if dicRenderType is None:
                        dicRenderType = self.dicRenderFramesTypes[self.iTargetFrame] = {}
                    # endif

                    dicRenderType[iOutIdx] = {
                        "lOutputFilenames": lOutputFilenames.copy(),
                        "lOutNewFilenames": lOutNewFilenames.copy(),
                    }
                else:
                    self.Print(
                        "Frame {0}, at scene frame {1} already exists. Skipping...".format(
                            self.iTargetFrame, self.iSceneFrame
                        )
                    )
                # endif

                self.iTargetFrame += self.iFrameStep
                if self.iTargetFrame > self.iFrameLast:
                    break
                # endif
            # endwhile target frames
        # endfor Render output types

    # enddef

    ##############################################################
    @logFunctionCall
    def Process(self):
        if self.bIsInitialized is False:
            raise CAnyError_Message(sMsg="Rendering is not initialized")
        # endif

        # Evaluate which frames/render output type combinations need to be rendered
        self._EvalRenderFramesOutTypes()

        if self.dicRenderFramesTypes is None:
            raise CAnyError_Message(sMsg="Render frames and types dictionary not initialized")
        # endif

        if len(self.dicRenderFramesTypes) == 0:
            self.Print("Nothing to render for configuration {}".format(self.dicCfg.get("iCfgIdx", "")))
            return False
        # endif

        # Initialize render by executing generators, setting camera, etc.
        # This call can take quite some time, if complex objects are generated.
        self.InitRender()

        for iFrameIdx, dicRenderTypes in self.dicRenderFramesTypes.items():
            self.iTargetFrame = iFrameIdx

            # Evaluate scene frame from target frame and scene fps
            self.fTargetTime = self.iTargetFrame / self.fTargetFps
            self.iSceneFrame = int(round(self.fSceneFps * self.fTargetTime, 0))

            # Set the scene frame in Blender
            self.xScn.frame_set(self.iSceneFrame)
            self.Print("Frame Trg: {0} -> Scn: {1}".format(self.iTargetFrame, self.iSceneFrame))

            # Apply only those modifiers that suppor mode 'FRAME_UPDATE'
            self._ApplyCfgModifier(sMode="FRAME_UPDATE")

            # Loop over all render outputs in config
            for iOutIdx, dicFiles in dicRenderTypes.items():
                dicRndOut = self.lRndOutTypes[iOutIdx]
                xRndOutType: CRenderOutputType = self._GetRenderOutType(dicRndOut, NsConfigDTI.sDtiRenderOutputAll)
                self.Print("Render output type: {}".format(dicRndOut.get("sDTI")))

                ######################################################
                # Apply modifier of render output type
                xCfgRndMod = None
                lRndMod = dicRndOut.get("lModifier")
                if lRndMod is not None:
                    xCfgRndMod = CConfigModifyList(lRndMod)
                    dicConstVars, dicRefVars = self._GetRuntimeVars()
                    xCfgRndMod.Apply(sMode="INIT", dicConstVars=dicConstVars, dicRefVars=dicRefVars)
                # endif

                lOutputFilenames = dicFiles["lOutputFilenames"]
                lOutNewFilenames = dicFiles["lOutNewFilenames"]

                if xRndOutType.sMainType not in [NsMainTypesRenderOut.blend, NsMainTypesRenderOut.none]:
                    # apply render output settings
                    self._ApplyCfgRenderOutputFiles(dicRndOut)
                    self._ApplyCfgRenderOutputSettings(dicRndOut)
                    ### DEBUG ######
                    # print(f"ApplyCfgAnnotation for frame {iFrameIdx}")
                    ################
                    # self._ApplyCfgAnnotation()

                    # ######################################################
                    # xRenderSettings = self._GetCfgRenderSettings(self.lRndSettings)
                    # dicMainSettings = xRenderSettings.mMain
                    # bTransformSceneToCameraFrame = dicMainSettings.get("bTransformSceneToCameraFrame", False)
                    # if bTransformSceneToCameraFrame is True:
                    #     anycam.ops.TransformSceneToCameraFrame(xContext=self.xCtx)
                    # # endif
                    # ######################################################

                    self._ApplyCfgAnnotation()
                # endif

                if xRndOutType.sSpecificType == NsSpecificTypesRenderOut.image_openGL:
                    bpy.ops.ac.update_camera_obj_list()
                    xAcProps = bpy.context.window_manager.AcProps
                    xAcProps.SelectCameraObject(self.sCameraName)

                    bpy.ops.ac.activate_selected_camera()
                    lRegion = [area.spaces[0].region_3d for area in bpy.context.screen.areas if area.type == "VIEW_3D"]
                    for xRegion in lRegion:
                        xRegion.view_perspective = "CAMERA"
                    # endfor
                    # anycam.ac_props_camset._SelCamSetEl(self=None, context=bpy.context)
                # endif use openGL and activate the correct camera

                ######################################################
                # Import of point clouds that vary per frame
                self._AnimPointClouds(self.iSceneFrame)
                ######################################################

                ######################################################
                # Export the label data to json
                if xRndOutType.sMainType != NsMainTypesRenderOut.none:
                    self._ExportLabelData(os.path.dirname(lOutNewFilenames[0]), self.iTargetFrame, False)
                # endif
                ######################################################

                ######################################################
                if xRndOutType.sMainType not in [NsMainTypesRenderOut.blend, NsMainTypesRenderOut.none]:
                    ######################################################
                    xRenderSettings = self._GetCfgRenderSettings(self.lRndSettings)
                    dicMainSettings = xRenderSettings.mMain
                    bTransformSceneToCameraFrame = dicMainSettings.get("bTransformSceneToCameraFrame", False)
                    if bTransformSceneToCameraFrame is True:
                        anycam.ops.TransformSceneToCameraFrame(xContext=self.xCtx)
                        self._UpdatePos3dOffset()
                    # endif
                    ######################################################
                # endif

                ######################################################
                # Perform the rendering
                if self.bDoRender and xRndOutType.sMainType != NsMainTypesRenderOut.none:
                    if xRndOutType.sMainType == NsMainTypesRenderOut.blend:
                        # Pack everything into the blender file
                        anyblend.app.file.PackAllLocal()
                        # Save the current blender file
                        bpy.ops.wm.save_mainfile(filepath=lOutNewFilenames[0])
                    else:
                        self.Print("\n>> Rendering using device {}".format(bpy.context.scene.cycles.device))
                        self.Print(">> Using render engine {}\n".format(bpy.context.scene.render.engine))

                        if xRndOutType.sSpecificType == NsSpecificTypesRenderOut.image_openGL:
                            anycam.ops.ActivateCamera(self.xCtx, self.sCameraName)
                            anycam.ac_props_camset._SelCamSetEl(self=None, context=bpy.context)

                            bpy.context.scene.render.filepath = lOutNewFilenames[0]
                            bpy.ops.render.opengl(write_still=True)
                            self.Print("\n>> Render OpenGL finished\n")
                        else:
                            bpy.ops.render.render(write_still=False)
                            self.Print("\n>> Render finished\n")

                            # Rename Exp files to Frame file for standard exposure
                            for i in range(len(lOutNewFilenames)):
                                sFpOut = lOutputFilenames[i]
                                sFpOutNew = lOutNewFilenames[i]
                                if os.path.isfile(sFpOut) and not os.path.isfile(sFpOutNew):
                                    self.Print(f"\n>> result file: {sFpOutNew}\n")
                                    os.rename(sFpOut, sFpOutNew)
                                # endif
                            # endfor output filenames
                        # endif UseOpenGL

                    # endif blender type
                # endif do render

                ######################################################
                # Save blender file, if enabled
                if self.bDoSaveRenderFile:
                    self._SaveBlenderFile(self.iTargetFrame)
                # endif

                ######################################################
                if xRndOutType.sMainType not in [NsMainTypesRenderOut.blend, NsMainTypesRenderOut.none]:
                    # If pos3d ground truth was rendered, some offset was applied for rendering.
                    # Transform the rendered image back to absolute 3d world coordinates.
                    # Furthermore, if the scene was transformed to the camera frame, then
                    # transform the data back.
                    self._PostProcLabelRender(
                        _sFpRender=lOutNewFilenames[0], _bTransformSceneToCameraFrame=bTransformSceneToCameraFrame
                    )

                    if bTransformSceneToCameraFrame is True:
                        anycam.ops.RevertTransformSceneToCameraFrame(xContext=self.xCtx)
                    # endif

                    # Restore scene if annotation had been applied
                    self._RestoreCfgAnnotation()
                    # restore render settings
                    self._RestoreCfgRenderSettings()
                # endif
            # endfor dicRndOut

        # endfor iFrameIdx, dicRenderFramesTypes

        return True

    # enddef


# endclass
