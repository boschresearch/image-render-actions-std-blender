#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \render_std_results.py
# Created Date: Tuesday, June 7th 2022, 2:54:10 pm
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

import re
from typing import Optional
from pathlib import Path

from anybase import assertion, config
from anybase.cls_any_error import CAnyError, CAnyError_Message
from catharsys.plugins.std.action_class.manifest.cls_cfg_manifest_job import (
    CConfigManifestJob,
)
from catharsys.plugins.std.resultdata import CImageResultData
from catharsys.plugins.std.blender.config.cls_compositor import CConfigCompositor
import catharsys.plugins.std.resultdata.util as resultutil

########################################################################################
class CRenderResultData(CImageResultData):

    ####################################################################################
    def __init__(self, *, xJobCfg: CConfigManifestJob):

        # Assert init function argument types
        assertion.FuncArgTypes()

        # Initialize parent class
        super().__init__(xJobCfg=xJobCfg)

    # enddef

    ##########################################################################
    def Process(self, **kwargs):

        lSupportedArgs = [
            "lRenderImageTypes",
            "iFrameFirst",
            "iFrameLast",
            "iFrameStep",
            "bCheckImagesExist",
            "dicCfg",
        ]

        for sArgKey in kwargs:
            if sArgKey not in lSupportedArgs:
                raise CAnyError_Message(
                    sMsg=(
                        f"Unsupported argument '{sArgKey}' for function Process()\n"
                        "Supported arguments are:"
                        + CAnyError.ListToString(lSupportedArgs)
                    )
                )
            # endif
        # endfor

        sWhere = "process function arguments"
        lRenderImageTypes = config.GetDictValue(
            kwargs, "lRenderImageTypes", list, xDefault=["*"], sWhere=sWhere
        )
        iFrameFirst = config.GetDictValue(
            kwargs, "iFrameFirst", int, xDefault=0, sWhere=sWhere
        )
        iFrameLast = config.GetDictValue(
            kwargs, "iFrameLast", int, xDefault=-1, sWhere=sWhere
        )
        iFrameStep = config.GetDictValue(
            kwargs, "iFrameStep", int, xDefault=1, sWhere=sWhere
        )
        bCheckImagesExist = config.GetDictValue(
            kwargs, "bCheckImagesExist", bool, xDefault=True, sWhere=sWhere
        )
        dicCfg = config.GetDictValue(
            kwargs, "dicCfg", dict, bOptional=True, sWhere=sWhere
        )

        self.ProcessImages(
            lRenderImageTypes=lRenderImageTypes,
            iFrameFirst=iFrameFirst,
            iFrameLast=iFrameLast,
            iFrameStep=iFrameStep,
            bCheckImagesExist=bCheckImagesExist,
            dicCfg=dicCfg,
        )

    # enddef

    ##########################################################################
    def ProcessImages(
        self,
        *,
        lRenderImageTypes: list = ["*"],
        iFrameFirst: int = 0,
        iFrameLast: int = -1,
        iFrameStep: int = 1,
        bCheckImagesExist: bool = True,
        dicCfg: Optional[dict] = None,
    ):

        lSpecialTypes = ["AT_Label_Raw", "AT_Pos3d_Raw", "AT_Flow_Raw"]

        if iFrameFirst < 0:
            iStartIdx = 0
        else:
            iStartIdx = iFrameFirst
        # endif

        if iFrameLast < iStartIdx:
            iStopIdx = -1
        else:
            iStopIdx = iFrameLast
        # endif

        if iFrameStep < 0:
            iStepIdx = 1
        else:
            iStepIdx = iFrameStep
        # endif

        if dicCfg is None:
            lConfigs = self.xJobCfg.lConfigs
        else:
            lConfigs = [dicCfg]
        # endif

        self._dicImages = {}
        lTrgAction = [
            "/catharsys/action/std/blender/render/std:1",
            "/catharsys/action/std/blender/render/rs:1",
        ]

        for dicCfg in lConfigs:

            sPathTrgMain, iActIdx, sActionDti, sAction = self.xJobCfg._GetActionTrgPath(
                lTrgAction, dicCfg
            )
            if sPathTrgMain is None:
                continue
            # endif

            pathTrgMain = Path(sPathTrgMain)
            bIsRsRender = config.CheckDti(
                sActionDti, "/catharsys/action/std/blender/render/rs:1"
            )["bOK"]

            iCfgIdx = dicCfg.get("iCfgIdx")
            iCfgCnt = dicCfg.get("iCfgCnt")

            dicRelPaths = self.xJobCfg._GetActionRelPaths(sAction, dicCfg)
            sRelPathTrial = dicRelPaths["sRelPathTrial"]
            sRelPathCfg = dicRelPaths["sRelPathCfg"]

            dicData = dicCfg.get("mConfig").get("mData")
            if dicData is None:
                raise Exception("No configuration data given")
            # endif

            # Define expected type names
            sRenderTypeList = "blender/render/output-list:1"

            lRndOutList = config.GetDataBlocksOfType(dicData, sRenderTypeList)
            if len(lRndOutList) == 0:
                raise Exception(
                    "No render output configuration of type compatible to '{0}' given".format(
                        sRenderTypeList
                    )
                )
            # endif
            dicRndOutList = lRndOutList[0]
            lRndOutList = dicRndOutList.get("lOutputs", [])
            for dicRndOut in lRndOutList:
                bHasImages = False

                dicDti = config.SplitDti(dicRndOut["sDTI"])
                sRenderSubType = "/".join(dicDti["lType"][4:])
                # print("Render sub type: {0}".format(sRenderSubType))

                #########################################################
                # FIRST image dictionary level references:
                #       render configuration
                #########################################################
                dicImgCfg = self._dicImages.get(sRelPathCfg)
                if dicImgCfg is None:
                    dicImgCfg = self._dicImages[sRelPathCfg] = {}
                # endif

                #########################################################
                # SECOND image dictionary level references:
                #       render sub type, e.g. "image" or "anytruth/label"
                #########################################################
                dicImgCfgRnd = dicImgCfg[sRenderSubType] = {
                    "iCfgIdx": iCfgIdx,
                    "iCfgCnt": iCfgCnt,
                    "sRelPathCfg": sRelPathCfg,
                    "sRelPathTrial": sRelPathTrial,
                    "mOutputType": {},
                }
                #########################################################
                # THIRD image dictionary level references:
                #       fixed name 'mOutputType',
                #       dictionary of output types as defined in compositor,
                #       or special output names like "AT_Label_Raw"
                #########################################################
                dicImgCfgRndOut = dicImgCfgRnd.get("mOutputType")

                # Processing differers by render sub types
                if sRenderSubType == "image":
                    dicComp = dicRndOut.get("mCompositor")
                    config.AssertConfigType(dicComp, "/catharsys/blender/compositor:1")

                    xComp = CConfigCompositor(
                        xPrjCfg=self.xJobCfg.xPrjCfg, dicData=dicComp
                    )
                    dicOutByType = xComp.GetOutputsByType()
                    # Select either the render output types as specified by arguments.
                    # or use all output types as defined in the compositor
                    if len(lRenderImageTypes) > 0 and "*" in lRenderImageTypes:
                        lType = [x for x in dicOutByType]
                    else:
                        lType = lRenderImageTypes.copy()
                    # endif

                    # Loop over output types
                    for sType in lType:
                        if sType in lSpecialTypes:
                            continue
                        # endif

                        lOut = dicOutByType.get(sType)
                        if lOut is None:
                            print(
                                "Render output type '{}' not defined in compositor config.\n"
                                "Available types are: {}".format(
                                    sType, ", ".join(dicOutByType.keys())
                                )
                            )
                            continue
                        # endif
                        dicOut = lOut[0]
                        sFolder = dicOut.get("sFolder")
                        sFileExt = dicOut.get("sFileExt")

                        #########################################################
                        # FOURTH image dictionary level references:
                        #       render output type, as defined in compositor
                        #########################################################
                        dicImgCfgRndOutType = dicImgCfgRndOut[sType] = {
                            "sFolder": sFolder,
                            "sFileExt": sFileExt,
                            "mFrames": {},
                        }
                        #########################################################
                        # FIFTH image dictionary level references:
                        #       fixed name 'mFrames' that contains all frames
                        #########################################################
                        dicImgFrames = dicImgCfgRndOutType.get("mFrames")

                        ##########################################################
                        # Test if we are processing ROLLING SHUTTER render results
                        if bIsRsRender is True:
                            # pathImages = pathTrgMain / "Frame_{0:04d}".format(iFrame) / sFolder
                            pathFrames = pathTrgMain
                            reImageFolder = re.compile(r"Frame_(\d+)")
                            reImageFile = re.compile(r"Exp_(\d+)\.exr")
                            for pathImageFolder in pathFrames.iterdir():
                                if not pathImageFolder.is_dir():
                                    continue
                                # endif

                                xMatch = reImageFolder.match(pathImageFolder.name)
                                if xMatch is None:
                                    continue
                                # endif
                                iFrame = int(xMatch.group(1))
                                if (
                                    iFrame < iStartIdx
                                    or (iStopIdx >= 0 and iFrame > iStopIdx)
                                    or (iFrame - iStartIdx) % iStepIdx != 0
                                ):
                                    continue
                                # endif

                                pathImages = pathImageFolder / sFolder
                                lFileExp = []
                                for pathElement in pathImages.iterdir():
                                    if (
                                        pathElement.is_file()
                                        and reImageFile.match(pathElement.name)
                                        is not None
                                    ):
                                        lFileExp.append(pathElement.as_posix())
                                    # endif
                                # endfor

                                if len(lFileExp) > 0:
                                    bHasImages = True
                                    dicImgFrames[iFrame] = {
                                        "iFrameIdx": iFrame,
                                        "sFpImage": None,
                                        "lFpSubImages": lFileExp,
                                    }
                                else:
                                    self._lWarnings.append(
                                        "Rolling shutter exposures for frame '{0}' do not exist".format(
                                            iFrame
                                        )
                                    )
                                # endif
                            # endfor frame folder

                        ##########################################################
                        # else, we are processing STANDARD RENDER results
                        else:
                            pathFrames = pathTrgMain / sFolder
                            bHasImages = resultutil.AddFramesToDictFromPath(
                                pathFrames=pathFrames,
                                dicImageFrames=dicImgFrames,
                                sFileExt=sFileExt,
                                iFrameFirst=iStartIdx,
                                iFrameLast=iStopIdx,
                                iFrameStep=iStepIdx,
                            )
                        # endif
                        # # endfor frame
                    # endfor output types

                elif sRenderSubType == "anytruth/label":
                    if "AT_Label_Raw" in lRenderImageTypes or "*" in lRenderImageTypes:
                        sType = sFolder = "AT_Label_Raw"
                        sFileExt = ".exr"

                        dicImgCfgRndOutType = dicImgCfgRndOut[sType] = {
                            "sFolder": sFolder,
                            "sFileExt": sFileExt,
                            "mFrames": {},
                        }
                        dicImgFrames = dicImgCfgRndOutType.get("mFrames")

                        pathFrames = pathTrgMain / sFolder
                        bHasImages = resultutil.AddFramesToDictFromPath(
                            pathFrames=pathFrames,
                            dicImageFrames=dicImgFrames,
                            sFileExt=sFileExt,
                            iFrameFirst=iStartIdx,
                            iFrameLast=iStopIdx,
                            iFrameStep=iStepIdx,
                        )
                    # endif

                elif sRenderSubType == "anytruth/pos3d":
                    if "AT_Pos3d_Raw" in lRenderImageTypes or "*" in lRenderImageTypes:
                        sType = sFolder = "AT_Pos3d_Raw"
                        sFileExt = ".exr"

                        dicImgCfgRndOutType = dicImgCfgRndOut[sType] = {
                            "sFolder": sFolder,
                            "sFileExt": sFileExt,
                            "mFrames": {},
                        }
                        dicImgFrames = dicImgCfgRndOutType.get("mFrames")

                        pathFrames = pathTrgMain / sFolder
                        bHasImages = resultutil.AddFramesToDictFromPath(
                            pathFrames=pathFrames,
                            dicImageFrames=dicImgFrames,
                            sFileExt=sFileExt,
                            iFrameFirst=iStartIdx,
                            iFrameLast=iStopIdx,
                            iFrameStep=iStepIdx,
                        )
                    # endif

                    if "AT_Flow_Raw" in lRenderImageTypes or "*" in lRenderImageTypes:
                        sType = sFolder = "AT_Flow_Raw"
                        sFileExt = ".exr"

                        dicImgCfgRndOutType = dicImgCfgRndOut[sType] = {
                            "sFolder": sFolder,
                            "sFileExt": sFileExt,
                            "mFrames": {},
                        }
                        dicImgFrames = dicImgCfgRndOutType.get("mFrames")

                        pathFrames = pathTrgMain / sFolder
                        bHasImages = resultutil.AddFramesToDictFromPath(
                            pathFrames=pathFrames,
                            dicImageFrames=dicImgFrames,
                            sFileExt=sFileExt,
                            iFrameFirst=iStartIdx,
                            iFrameLast=iStopIdx,
                            iFrameStep=iStepIdx,
                        )
                    # endif

                else:
                    print(
                        "ERROR: Unsupported render output type '{0}'".format(
                            sRenderSubType
                        )
                    )
                # endif

                if not bHasImages:
                    del dicImgCfg[sRenderSubType]
                # endif
            # endfor render output types
        # endfor configurations

        # print(self._dicImages)

    # enddef


# endclass
