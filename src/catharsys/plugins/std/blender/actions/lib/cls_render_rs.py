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
import math
from timeit import default_timer as timer
from datetime import datetime

import os
from .cls_render import CRender, CRenderSettings, CRenderOutputType
from .cls_render import NsConfigDTI
from .cls_render import NsMainTypesRenderOut, NsSpecificTypesRenderOut

from .cls_rsexp import CRsExp
from anybase.cls_any_error import CAnyError_Message
from anybase import time as anytime
from catharsys.plugins.std.blender.config.cls_modify_list import CConfigModifyList
from catharsys.util import file as cathfile
from catharsys.util import path as cathpath
from catharsys.util import config as cathcfg

import anyblend
import anycam


class CRenderRollingShutter(CRender):
    ##############################################################
    def __init__(self, *, xPrjCfg, dicCfg):
        super(CRenderRollingShutter, self).__init__(xPrjCfg=xPrjCfg, dicCfg=dicCfg, sDtiCapCfg="capture/rs:1")

    # enddef

    ##############################################################
    def Process(self):
        if self.bIsInitialized is False:
            raise CAnyError_Message(sMsg="Rendering is not initialized")
        # endif

        if len(self.lRndOutTypes) > 1:
            raise Exception("Rolling shutter rendering currently " "only supports a single render output type")
        # endif

        # Get render output config
        dicRndOut = self.lRndOutTypes[0]
        xRndOutType: CRenderOutputType = self._GetRenderOutType(dicRndOut, NsConfigDTI.sDtiRenderOutputAll)
        self.Print("Render output type: {}".format(dicRndOut.get("sDTI")))

        # Initialize render by executing generators, setting camera, etc.
        # This call can take quite some time, if complex objects are generated.
        self.InitRender()

        # !!! Annotation currently not supported
        # self._ApplyCfgAnnotation()

        # Get sub-frame offset and step that have been set by job distribution system,
        # to have multiple threads work on same result frame.
        iSubFrameOffset = self.dicCfg.get("iSubFrameOffset")
        iSubFrameStep = self.dicCfg.get("iSubFrameStep")

        # Frame time is the time from the start of the exposure of the first line of frame n,
        # until the start of the exposure of the first line of frame n+1
        dTrgFps = self.dicCap.get("dFPS")
        dTrgFrameTime = self.dicCap.get("dFrameTime")
        iReadOutsPerRender = self.dicCap.get("iReadOutsPerRender", 1)

        # iReadOutOffset = self.dicCap.get("iReadOutOffsetEx", 0)
        # iReadOutStep = self.dicCap.get("iReadOutStep", 1)
        # iReadOutMaxStepCount = self.dicCap.get("iReadOutMaxStepCount", 0)

        dicExposure = self.dicCap.get("mExp")
        if dicExposure is None:
            raise Exception("No exposure data given in image capture config")
        # endif

        iRenderResX = self.xScn.render.resolution_x
        iRenderResY = self.xScn.render.resolution_y
        iBorderMinY = int(round(iRenderResY * self.xScn.render.border_min_y, 0))
        iBorderMaxY = int(round(iRenderResY * self.xScn.render.border_max_y, 0))

        # Offset of first line to render from top of image
        iBorderTop = iRenderResY - iBorderMaxY
        # Number of lines to render
        iLineCount = self.dicAnyCam.get("iSenResY")

        # Create RS exposure class instance
        xRsExp = CRsExp(
            fFPS=dTrgFps,
            fFrameTime=dTrgFrameTime,
            iLineCount=iLineCount,
            fScnFps=self.fSceneFps,
            iReadOutsPerRender=iReadOutsPerRender,
            dicExp=dicExposure,
        )

        xRsExp.PrintData()
        dicRsExp = xRsExp.GetData()

        # Write RS paramters to JSON file for image construction script
        dicRS = {
            "iRenderResX": iRenderResX,
            "iRenderResY": iRenderResY,
            "iBorderMinY": iBorderMinY,
            "iBorderMaxY": iBorderMaxY,
            "iBorderTop": iBorderTop,
            "mRsExp": dicRsExp,
        }

        # Copy sensor data if it is available in dicAnyCam
        dicAnyCamEx = self.dicAnyCam.get("mEx")
        if isinstance(dicAnyCamEx, dict):
            dicSensor = dicAnyCamEx.get("mSensor")
            if isinstance(dicSensor, dict):
                dicRS["mSensor"] = dicSensor
            # endif
        # endif

        cathcfg.Save((self.sPathTrgMain, "RsCfg"), dicRS, sDTI="rs-config:1.1")

        # Loop over frames
        iTrgFrame = self.iFrameFirst
        iTrgFrameIdx = 0
        iTrgFrameCnt = int(math.floor((self.iFrameLast - self.iFrameFirst) / self.iFrameStep)) + 1

        xRsExp.SetTrgFrame(iTrgFrame)
        iRoLoopCnt = xRsExp.GetReadOutLoopCount(iLoopOffset=iSubFrameOffset, iLoopStep=iSubFrameStep)
        self.Print("iRoLoopCnt: {0}".format(iRoLoopCnt))
        iTotalRoLoopCnt = iTrgFrameCnt * iRoLoopCnt

        while True:
            if iTrgFrame > self.iFrameLast:
                break
            # endif

            xRsExp.SetTrgFrame(iTrgFrame)

            # Create the render path for this frame
            sFrameName = "Frame_{0:04d}".format(iTrgFrame)

            sPathRenderFrame = os.path.join(self.sPathTrgMain, sFrameName)

            sFileLog = "log_frame-{0:02d}_offset-{1:02d}.txt".format(iTrgFrame, iSubFrameOffset)
            sPathLog = os.path.join(sPathRenderFrame, "_log")
            sFpLog = os.path.join(sPathLog, sFileLog)
            cathpath.CreateDir(sPathLog)

            dtNow = datetime.now()
            sLog = ""
            sLog += "\n"
            sLog += "Start processing frame {0}\n".format(iTrgFrame)
            sLog += "Start Date: {0}\n".format(dtNow.strftime("%Y-%m-%d"))
            sLog += "Start Time: {0}\n".format(dtNow.strftime("%H:%M:%S"))
            sLog += "\n"
            sLog += "First frame: {0}\n".format(self.iFrameFirst)
            sLog += "Last frame: {0}\n".format(self.iFrameLast)
            sLog += "Frame step: {0}\n".format(self.iFrameStep)
            sLog += "\n"
            sLog += "Sub-frame offset: {0}\n".format(iSubFrameOffset)
            sLog += "Sub-frame step: {0}\n".format(iSubFrameStep)
            sLog += "Renders per frame: {0}\n".format(iRoLoopCnt)
            sLog += "Total renders: {0}\n".format(iTotalRoLoopCnt)
            sLog += "\n"
            sLog += "Render quality (aa samples): {0}\n".format(self.iRenderQuality)
            sLog += "\n"
            sLog += xRsExp.GetDataStr()

            try:
                # self.Print("Writing log to file: {0}".format(sFpLog))
                cathfile.SaveText(sFpLog, sLog)
            except Exception:
                self.Print("ERROR: Can not write log to file: {0}".format(sFpLog))
            # endtry

            ######################################################
            # Apply modifier of render output type
            xCfgRndMod = None
            lRndMod = dicRndOut.get("lModifier")
            if lRndMod is not None:
                xCfgRndMod = CConfigModifyList(lRndMod)
                xCfgRndMod.Apply()
            # endif

            # apply render output settings
            self._ApplyCfgRenderOutputFiles(dicRndOut)
            self._ApplyCfgRenderOutputSettings(dicRndOut)

            self._ApplyCfgAnnotation(_sPathTrgMain=sPathRenderFrame)

            lOutNewFilenames = self.xCompFileOut.GetOutputFilenames(self.iTargetFrame)

            ######################################################
            # Apply render type modifiers that should be executed
            # after the annotation has been applied.
            if xCfgRndMod is not None:
                dicConstVars, dicRefVars = self._GetRuntimeVars()
                xCfgRndMod.Apply(sMode="POST_ANNOTATION", dicConstVars=dicConstVars, dicRefVars=dicRefVars)
            # endif

            ######################################################
            # Import of point clouds that vary per frame.
            # This is not changed per rolling shutter exposure
            self._AnimPointClouds(iTrgFrame)
            ######################################################

            ######################################################
            xRenderSettings: CRenderSettings = self._GetCfgRenderSettings(self.lRndSettings)
            dicMainSettings = xRenderSettings.mMain
            bTransformSceneToCameraFrame = dicMainSettings.get("bTransformSceneToCameraFrame", False)
            ######################################################

            # Set the base render path
            # Apply file out config to compositor
            # self.xCompFileOut.SetFileOut(sPathRenderFrame, self.lFileOut)
            sLog += "Using render path: {0}\n".format(sPathRenderFrame)

            # Loop over all exposures for frame
            iRoLoopIdx = 0
            # Define every how many loops a log output is generated
            iRoLoopLogStep = 1
            dTimeRenderDelta = 0.0

            sTimeDelta = "n/a"
            sTimeLeft = "n/a"
            dTimeStart = timer()
            if xRsExp.StartReadOutLoop(iLoopOffset=iSubFrameOffset, iLoopStep=iSubFrameStep):
                while True:
                    # Fast forward to first exposure that has not been rendered
                    bFinished = False
                    while True:
                        iTotalRoLoopIdx = iTrgFrameIdx * iRoLoopCnt + iRoLoopIdx
                        dRoLoopPart = 100.0 * (iRoLoopIdx / iRoLoopCnt)
                        dTotalRoLoopPart = 100.0 * (iTotalRoLoopIdx / iTotalRoLoopCnt)

                        self.iSceneFrame = xRsExp.GetExpStartSceneFrame()
                        lOutputFilenames = self.xCompFileOut.GetOutputFilenames(self.iSceneFrame)

                        bMissing = False
                        for sFo in lOutputFilenames:
                            # self.Print("Test for rendered file: {0}".format(sFo))
                            if not os.path.isfile(sFo):
                                bMissing = True
                            elif self.bDoOverwrite:
                                self.Print("...removing file due to overwrite flag")
                                os.remove(sFo)
                            # endif
                        # endfor

                        if bMissing or self.bDoOverwrite:
                            break
                        # endif

                        sLog += "Frame {0}, exposure {1} already exists. Skipping...\n".format(
                            iTrgFrame, self.iSceneFrame
                        )

                        iRoLoopIdx += 1
                        if not xRsExp.StepReadOutLoop():
                            bFinished = True
                            break
                        # endif
                    # endwhile fast-forward

                    # If we reached the end of the exposure loop during fast-forward, end loop
                    if bFinished:
                        break
                    # endif

                    # Calculate render border
                    iRenderBorderMin = iBorderMaxY - xRsExp.GetExpLineBottomOffset() + 1
                    iRenderBorderMin = max(0, iRenderBorderMin)

                    iRenderBorderMax = iBorderMaxY - xRsExp.GetExpLineTopOffset()
                    iRenderBorderMax = min(iRenderResY, iRenderBorderMax)

                    # sLog += "Render Border: {} -> {}\n".format(iRenderBorderMin, iRenderBorderMax)

                    # To ensure that Blender ends up with the same Borders in pixels
                    # need to add 0.25 to the line indices before converting to
                    # image size ratios. In this way, Blender will get the same values
                    # with floor() and round() after multiplying the ratios with
                    # the render resolution integer.
                    self.xScn.render.border_min_y = (iRenderBorderMin - 0.75) / iRenderResY
                    self.xScn.render.border_max_y = (iRenderBorderMax + 0.25) / iRenderResY

                    sLog += "{0}: Min = {1}, Max = {2}, Size = {3}\n".format(
                        self.iSceneFrame,
                        iRenderBorderMin,
                        iRenderBorderMax,
                        iRenderBorderMax - iRenderBorderMin + 1,
                    )

                    # sLog += ("{0}: {1} -> {2} -> {3} -> {4}\n"
                    #          .format(self.iSceneFrame,
                    #               iRenderBorderMin,
                    #               self.xScn.render.border_min_y,
                    #               self.xScn.render.border_min_y * iRenderResY,
                    #               math.floor(self.xScn.render.border_min_y * iRenderResY)
                    #               ))

                    # sLog += ("{0}: {1} -> {2} -> {3} -> {4}\n\n"
                    #          .format(self.iSceneFrame,
                    #               iRenderBorderMax,
                    #               self.xScn.render.border_max_y,
                    #               self.xScn.render.border_max_y * iRenderResY,
                    #               math.floor(self.xScn.render.border_max_y * iRenderResY)
                    #               ))

                    dTimeRenderStart = timer()

                    # Perform the rendering
                    if self.bDoRender:
                        ######################################################
                        # Export the label data to json
                        if xRndOutType.sMainType != NsMainTypesRenderOut.none:
                            self._ExportLabelData(
                                os.path.dirname(lOutNewFilenames[0]),
                                self.iSceneFrame,
                                _bUpdateLabelData3d=False,
                                _sFrameNamePattern="Exp_{0:07d}.json",
                            )
                        # endif
                        ######################################################

                        ##############################################################################
                        # Set the frame to render
                        self.xScn.frame_set(self.iSceneFrame)
                        self.xCtx.view_layer.update()

                        ##############################################################################
                        # Apply only those modifiers that support mode 'FRAME_UPDATE'
                        self._ApplyCfgModifier(sMode="FRAME_UPDATE")

                        ##############################################################################
                        if bTransformSceneToCameraFrame is True:
                            anycam.ops.TransformSceneToCameraFrame(xContext=self.xCtx)
                        # endif

                        ##############################################################################
                        # perform rendering
                        bpy.ops.render.render(write_still=False)

                        ##############################################################################
                        # If pos3d ground truth was rendered, some offset was applied for rendering.
                        # Transform the rendered image back to absolute 3d world coordinates.
                        # Furthermore, if the scene was transformed to the camera frame, then
                        # transform the data back.
                        self._PostProcLabelRender(
                            _sFpRender=lOutNewFilenames[0],
                            _bTransformSceneToCameraFrame=bTransformSceneToCameraFrame,
                        )

                        ##############################################################################
                        if bTransformSceneToCameraFrame is True:
                            anycam.ops.RevertTransformSceneToCameraFrame(xContext=self.xCtx)
                        # endif
                        ##############################################################################
                    # endif

                    dTimeRenderDelta += timer() - dTimeRenderStart

                    ##############################################################################
                    # Save log data at each nth read out step
                    if iRoLoopIdx % iRoLoopLogStep == 0:
                        sTimeRenderDelta = anytime.SecondsToHmsStr(dTimeRenderDelta / iRoLoopLogStep)

                        if iRoLoopIdx > 0:
                            dTimeNow = timer()
                            dTimeDelta = dTimeNow - dTimeStart
                            sTimeDelta = anytime.SecondsToHmsStr(dTimeDelta)
                            dTimeLeft = (iTotalRoLoopCnt / iTotalRoLoopIdx - 1.0) * dTimeDelta
                            sTimeLeft = anytime.SecondsToHmsStr(dTimeLeft)
                        # endif

                        sLog += "Time: {0} + {1} | {2:5.1f}% | {3:5.1f}% | Last render time {4}\n".format(
                            sTimeDelta,
                            sTimeLeft,
                            dRoLoopPart,
                            dTotalRoLoopPart,
                            sTimeRenderDelta,
                        )

                        sLogFull = self.CreateLogHead(True, dTimeStart, iRoLoopIdx, iRoLoopCnt) + sLog

                        try:
                            cathfile.SaveText(sFpLog, sLogFull)
                        except Exception as xEx:
                            self.Print("Writing log exception: {0}".format(xEx))
                        # endtry

                        dTimeRenderDelta = 0.0
                    # endif

                    iRoLoopIdx += 1
                    # if iRoLoopIdx > 1:
                    #     break
                    # # endif

                    # Next read out step
                    if not xRsExp.StepReadOutLoop():
                        break
                    # endif
                # endwhile read-out loop
            # endif start read-out loop

            dTimeNow = timer()
            dTimeDelta = dTimeNow - dTimeStart
            sTimeDelta = anytime.SecondsToHmsStr(dTimeDelta)

            sLog += "\n\n"
            sLog += "Total processing time: {0}\n".format(sTimeDelta)

            sLogFull = self.CreateLogHead(False, dTimeStart, iRoLoopIdx, iRoLoopCnt) + sLog

            try:
                cathfile.SaveText(sFpLog, sLogFull)
            except Exception:
                self.Print("ERROR: Can not write log to file: {0}".format(sFpLog))
            # endtry

            iTrgFrame += self.iFrameStep
            iTrgFrameIdx += 1

        # endwhile iTrgFrame

    # enddef

    ################################################################################
    def CreateLogHead(self, _bRunning, _dTimeStart, _iRoLoopIdx, _iRoLoopCnt):
        sT = ""
        sT += "\n"
        sT += "=================================================\n"
        sT += "\n"

        dTimeDelta = timer() - _dTimeStart
        sTimeDelta = anytime.SecondsToHmsStr(dTimeDelta)

        sTimePerRo = "n/a"
        sTimeLeft = "n/a"
        if _iRoLoopIdx > 0:
            dTimePerRo = dTimeDelta / _iRoLoopIdx
            sTimePerRo = anytime.SecondsToHmsStr(dTimePerRo)

            dTimeLeft = (_iRoLoopCnt / _iRoLoopIdx - 1.0) * dTimeDelta
            sTimeLeft = anytime.SecondsToHmsStr(dTimeLeft)
        # endif

        dRoPercent = 100.0 * (_iRoLoopIdx / _iRoLoopCnt)

        if _bRunning:
            sT += "Status: running\n"
            sT += "Time running/left: {0} / {1}\n".format(sTimeDelta, sTimeLeft)
            sT += "Renders: {0} of {1} ({2:5.2f}%)\n".format(_iRoLoopIdx, _iRoLoopCnt, dRoPercent)
            sT += "Average render time per frame: {0}\n".format(sTimePerRo)
        else:
            sT += "Status: stopped\n"
            sT += "Runtime: {0}\n".format(sTimeDelta)
            sT += "Renders: {0} of {1} ({2:5.2f}%)\n".format(_iRoLoopIdx, _iRoLoopCnt, dRoPercent)
            sT += "Average render time per frame: {0}\n".format(sTimePerRo)
        # endif

        sT += "\n"
        sT += "=================================================\n"
        sT += "\n"

        return sT

    # enddef


# endclass
