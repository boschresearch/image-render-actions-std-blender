#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /rsexp.py
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

# Rolling Shutter Exposure class

import math


class CRsExp:

    ###################################################################################
    # Initialize class
    def __init__(
        self,
        fFPS=1.0,
        fFrameTime=1.0,
        iLineCount=1000,
        fScnFps=1000.0,
        iReadOutsPerRender=1,
        dicExp={},
    ):

        self.fTrgFps = fFPS
        self.fTrgFrameTime = fFrameTime
        self.iLineCount = iLineCount
        self.fScnFps = fScnFps
        self.iReadOutsPerRender = iReadOutsPerRender

        self.fTrgExpPerLine = dicExp.get("dExpPerLine")
        self.fTrgExpOffset = dicExp.get("dExpOffset", 0.0)
        self.lReadOutLinePattern = dicExp.get("lReadOutLinePattern", [0])

        if self.fTrgExpPerLine is None:
            raise Exception("No exposure per line given")
        # endif

        self.iTrgFrame = 0
        self.iScnFrame = 0
        self.fEffTrgTime = 0.0
        self.iExpStartScnFrame = 0

        self.iReadOutIdx = 0
        self.iLoopIdx = 0
        self.iReadOutBlockLineIdx = 0
        self.iRowTopOffset = 0
        self.iRowBotOffset = 0

        self.iReadOutOffset = 0
        self.iReadOutStep = 1
        self.iLoopCountMax = 0

        self.Update()

    # enddef

    ###################################################################################
    # Update class data
    def Update(self):

        # Expect read-out line pattern to have following structure:
        #   1. First element is always 0
        #   2. The separation between all consecutive elements is the same.
        #       For example: [0, 2] or [0, 2, 4] or [0, 3, 6], etc.
        self.iLinesPerReadOut = len(self.lReadOutLinePattern)

        if self.iLinesPerReadOut == 1:
            self.iReadOutsPerBlock = 1
            self.iReadOutBlockLines = 1
        elif self.iLinesPerReadOut > 1:
            self.iReadOutsPerBlock = self.lReadOutLinePattern[1]
            self.iReadOutBlockLines = self.iReadOutsPerBlock + max(self.lReadOutLinePattern)
        else:
            raise Exception("Invalid read out line pattern")
        # endif

        self.iReadOutCount = int(math.ceil(self.iLineCount / self.iLinesPerReadOut))

        self.dTrgReadOutDeltaTime = self.fTrgFrameTime / self.iReadOutCount
        # self.iScnReadOutDeltaFrames = int(round(self.dScnFps * self.dTrgReadOutDeltaTime, 0))

        # Number of scene frames per render
        self.iScnRenderDeltaFrames = int(round(self.fScnFps * self.dTrgReadOutDeltaTime * self.iReadOutsPerRender, 0))
        if self.iScnRenderDeltaFrames == 0:
            raise RuntimeError(
                "Insufficient scene frame resolution for rolling shutter render.\n"
                "Scene FPS needs to be at least {}".format(1.0 / (self.dTrgReadOutDeltaTime * self.iReadOutsPerRender))
            )
        # endif

        # self.dEffReadOutDeltaTime = self.iScnReadOutDeltaFrames / self.dScnFps
        self.dScnReadOutDeltaFrames = self.iScnRenderDeltaFrames / self.iReadOutsPerRender
        self.dEffReadOutDeltaTime = self.dScnReadOutDeltaFrames / self.fScnFps

        self.iReadOutsPerExp = max(1, int(round(self.fTrgExpPerLine / self.dEffReadOutDeltaTime, 0)))
        # self.iScnFramesPerExp = self.iReadOutsPerExp * self.iScnReadOutDeltaFrames
        self.dScnFramesPerExp = self.iReadOutsPerExp * self.dScnReadOutDeltaFrames

        self.dEffExpPerLine = self.dScnFramesPerExp / self.fScnFps
        self.iReadOutBlocksPerExp = max(1, int(math.ceil(self.iReadOutsPerExp / self.iReadOutsPerBlock)))
        self.iReadOutBlocksPerExpOffset = self.iReadOutsPerExp % self.iReadOutsPerBlock
        self.iBlockLinesPerExp = self.iReadOutBlocksPerExp * self.iReadOutBlockLines

        # self.iScnFramesPerTrgFrame = self.iScnReadOutDeltaFrames * self.iReadOutCount
        # self.iScnFramesPerTrgFrame = max(1, int(round(self.dScnFps / self.fTrgFps, 0)))
        self.dScnFramesPerTrgFrame = self.fScnFps / self.fTrgFps
        self.dEffTrgFps = self.fScnFps / round(self.dScnFramesPerTrgFrame)
        self.dEffTrgFrameTime = self.dEffReadOutDeltaTime * self.iReadOutCount

    # enddef

    ###################################################################################
    # Get relevant class data in single dictionary
    def GetData(self):
        return {
            "dTrgFps": self.fTrgFps,
            "dEffTrgFps": self.dEffTrgFps,
            "dTrgFrameTime": self.fTrgFrameTime,
            "dEffTrgFrameTime": self.dEffTrgFrameTime,
            "mTrgExp": {
                "dExpPerLine": self.fTrgExpPerLine,
                "dExpOffset": self.fTrgExpOffset,
                "lReadOutLinePattern": self.lReadOutLinePattern,
            },
            "iReadOutsPerRender": self.iReadOutsPerRender,
            "iLineCount": self.iLineCount,
            "iLinesPerReadOut": self.iLinesPerReadOut,
            "iReadOutsPerBlock": self.iReadOutsPerBlock,
            "iReadOutBlockLines": self.iReadOutBlockLines,
            "dScnFps": self.fScnFps,
            "iReadOutCount": self.iReadOutCount,
            "dTrgReadOutDeltaTime": self.dTrgReadOutDeltaTime,
            "dScnReadOutDeltaFrames": self.dScnReadOutDeltaFrames,
            "iScnRenderDeltaFrames": self.iScnRenderDeltaFrames,
            "dEffReadOutDeltaTime": self.dEffReadOutDeltaTime,
            "iReadOutsPerExp": self.iReadOutsPerExp,
            "dScnFramesPerExp": self.dScnFramesPerExp,
            "dEffExpPerLine": self.dEffExpPerLine,
            "iReadOutBlocksPerExp": self.iReadOutBlocksPerExp,
            "iReadOutBlocksPerExpOffset": self.iReadOutBlocksPerExpOffset,
            "iBlockLinesPerExp": self.iBlockLinesPerExp,
            "dScnFramesPerTrgFrame": self.dScnFramesPerTrgFrame,
        }

    # enddef

    ###################################################################################
    def GetDataStr(self):
        sT = ""

        sT += "=======================================================\n"
        sT += "Rolling shutter exposure data\n"
        sT += "=======================================================\n"

        sT += "Line count: {0}\n".format(self.iLineCount)
        sT += "Lines per RO: {0}\n".format(self.iLinesPerReadOut)
        sT += "RO Block lines: {0}\n".format(self.iReadOutBlockLines)
        sT += "RO per block: {0}\n".format(self.iReadOutsPerBlock)
        sT += "RO step: {0}\n".format(self.iReadOutStep)
        sT += "Effective RO count: {0}\n".format(math.floor(self.iReadOutCount / self.iReadOutStep))

        sT += "\n"
        sT += "Target fps: {0}\n".format(self.fTrgFps)
        sT += "Effective Target fps: {0}\n".format(self.dEffTrgFps)
        sT += "Scene fps: {0}\n".format(self.fScnFps)

        sT += "\n"
        sT += "Trg RO delta time: {0}\n".format(self.dTrgReadOutDeltaTime)
        sT += "Scene RO delta frames: {0}\n".format(self.dScnReadOutDeltaFrames)
        sT += "Eff RO delta time: {0}\n".format(self.dEffReadOutDeltaTime)

        sT += "\n"
        sT += "RO per Exp: {0}\n".format(self.iReadOutsPerExp)
        sT += "RO blocks per Exp: {0}\n".format(self.iReadOutBlocksPerExp)
        sT += "Block Lines per Exp: {0}\n".format(self.iBlockLinesPerExp)
        sT += "Scene frames per Exp: {0}\n".format(self.dScnFramesPerExp)
        sT += "Trg Exposure per Line: {0}\n".format(self.fTrgExpPerLine)
        sT += "Eff Exposure per Line: {0}\n".format(self.dEffExpPerLine)

        sT += "\n"
        sT += "Scene frames per trg frame: {0}\n".format(self.dScnFramesPerTrgFrame)
        sT += "Scene render delta frames: {0}\n".format(self.iScnRenderDeltaFrames)
        sT += "Trg frame time: {0}\n".format(self.fTrgFrameTime)
        sT += "Eff frame time: {0}\n".format(self.dEffTrgFrameTime)

        sT += "\n"
        sT += "=======================================================\n"
        sT += "\n"

        return sT

    # enddef

    ###################################################################################
    def PrintData(self):
        print(self.GetDataStr())

    # enddef

    ###################################################################################
    # Set the current target frame
    def SetTrgFrame(self, _iTrgFrame):

        self.iTrgFrame = _iTrgFrame
        self.iScnFrame = int(round(self.dScnFramesPerTrgFrame * self.iTrgFrame))
        self.fEffTrgTime = self.dEffTrgFrameTime * self.iTrgFrame

    # enddef

    ###################################################################################
    # Calculate the current read out step.
    # Returns False if the read out step is above the maximally allowed steps
    def _UpdateReadOutStep(self):
        self.iLoopIdx = int(math.floor((self.iReadOutIdx - self.iReadOutOffset) / self.iReadOutStep))

        # print("iLoopIdx: {0}".format(self.iLoopIdx))
        # print("iReadOutMaxStepCount: {0}".format(self.iReadOutMaxStepCount))

        # if a maximum read-out step count is given, the break if it is reached
        if self.iLoopCountMax > 0 and self.iLoopIdx >= self.iLoopCountMax:
            return False
        # endif

        self.iExpStartScnFrame = self.iScnFrame + int(round(self.iReadOutIdx * self.dScnReadOutDeltaFrames))
        self.iReadOutBlockLineIdx = int(math.floor(self.iReadOutIdx / self.iReadOutsPerBlock)) * self.iReadOutBlockLines
        self.iReadOutBlockSubIdx = self.iReadOutIdx % self.iReadOutsPerBlock

        # self.iRowTopOffset = max(0,
        #                          self.iReadOutBlockLineIdx - self.iBlockLinesPerExp + 1)
        self.iRowTopOffset = max(
            0,
            self.iReadOutBlockLineIdx - self.iBlockLinesPerExp + self.iReadOutBlockLines,
        )

        self.iRowBotOffset = min(
            self.iLineCount,
            self.iReadOutBlockLineIdx + self.iReadOutBlockLines * self.iReadOutsPerRender,
        )

        # print("Top: {0}, Bot: {1}".format(self.iRowTopOffset, self.iRowBotOffset))
        # print(f"iReadOutsPerBlock: {self.iReadOutsPerBlock}, iReadOutBlockLines: {self.iReadOutBlockLines}")
        # print(f"iReadOutBlockLineIdx: {self.iReadOutBlockLineIdx}, iReadOutBlockSubIdx: {self.iReadOutBlockSubIdx}")
        # print(self.GetExpRowList())

        if self.iRowTopOffset >= self.iRowBotOffset:
            return False
        # endif

        return True

    # endif

    ###################################################################################
    # Get list of row indices of lines that are exposed in this step
    def GetExpRowList(self):

        lRoRows = []
        for iReadOutIdx in range(self.iReadOutIdx, self.iReadOutIdx + self.iReadOutsPerRender):
            for iRoExpIdx in range(0, self.iReadOutsPerExp):
                iAbsRoIdx = iReadOutIdx - iRoExpIdx
                if iAbsRoIdx < 0:
                    break
                # endif

                iRoBlockLineIdx = int(math.floor(iAbsRoIdx / self.iReadOutsPerBlock)) * self.iReadOutBlockLines
                iRoBlockSubIdx = iAbsRoIdx % self.iReadOutsPerBlock

                iRoLine = iRoBlockLineIdx + iRoBlockSubIdx
                for iOffset in self.lReadOutLinePattern:
                    iLine = iRoLine + iOffset
                    if iLine >= 0 and iLine < self.iLineCount and iLine not in lRoRows:
                        lRoRows.append(iLine)
                    # endif
                # endfor
            # endfor
        # endfor

        lRoRows.sort()
        return lRoRows

    # enddef

    ###################################################################################
    # Initialized the read out loop.
    # Returns False, if loop is already finished.
    def StartReadOutLoop(self, iLoopOffset=0, iLoopStep=1, iLoopCountMax=0):

        self.iLoopCountMax = iLoopCountMax

        self.iReadOutStep = iLoopStep * self.iReadOutsPerRender
        if self.iReadOutStep <= 0:
            raise RuntimeError("Invalid read-out step: {}".format(self.iReadOutStep))
        # endif

        self.iReadOutOffset = int(round(self.fTrgExpOffset / self.dEffReadOutDeltaTime))
        self.iReadOutOffset += iLoopOffset * self.iReadOutsPerRender

        self.iReadOutIdx = self.iReadOutOffset

        return self._UpdateReadOutStep()

    # enddef

    ###################################################################################
    # Step the read out loop
    def StepReadOutLoop(self):

        self.iReadOutIdx += self.iReadOutStep

        return self._UpdateReadOutStep()

    # enddef

    ###################################################################################
    # Get the total number of read-out loop steps
    def GetReadOutLoopCount(self, iLoopOffset=0, iLoopStep=1, iLoopCountMax=0):

        iCnt = 0
        if self.StartReadOutLoop(iLoopOffset=iLoopOffset, iLoopStep=iLoopStep, iLoopCountMax=iLoopCountMax):
            while True:
                iCnt += 1
                if not self.StepReadOutLoop():
                    break
                # endif
            # endwhile
        # endif

        return iCnt

    # enddef

    ###################################################################################
    def GetExpStartSceneFrame(self):
        return self.iExpStartScnFrame

    # enddef

    ###################################################################################
    def GetExpLineBottomOffset(self):
        return self.iRowBotOffset

    # enddef

    ###################################################################################
    def GetExpLineTopOffset(self):
        return self.iRowTopOffset

    # enddef

    ###################################################################################
    def GetReadOutsPerExp(self):
        return self.iReadOutsPerExp

    # enddef

    ###################################################################################
    def GetEffExpPerLine(self):
        return self.dEffExpPerLine

    # enddef


# endclass
