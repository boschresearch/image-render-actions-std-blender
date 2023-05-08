#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /compositor.py
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

# Class to handle Compositor data structures
import copy
from catharsys.util import config, path
from catharsys.util.cls_configcml import CConfigCML


class CConfigCompositor:
    def __init__(self, *, xPrjCfg, dicData={}):

        self.xPrjCfg = xPrjCfg
        self.dicData = copy.deepcopy(dicData)
        if self.dicData is not None:
            self.AddFileExtToFileOutList(self.dicData)
        # endif

    # enddef

    ######################################################################################
    # Add the file extensions for the given file formats
    def AddFileExtToFileOutList(self, _dicData):

        for dicFo in _dicData.get("lFileOut"):

            sFileFormat = dicFo.get("mFormat").get("sFileFormat")
            if sFileFormat == "OPEN_EXR":
                dicFo["sFileExt"] = ".exr"
            elif sFileFormat == "JPEG":
                dicFo["sFileExt"] = ".jpg"
            elif sFileFormat == "PNG":
                dicFo["sFileExt"] = ".png"
            else:
                raise Exception(
                    "Unknown compositor file output format type '{0}'.".format(
                        sFileFormat
                    )
                )
            # endif
        # endfor

    # enddef

    ######################################################################################
    # Load Compositor from file
    def LoadFile(self, _xPath):

        pathFile = path.MakeNormPath(_xPath)

        self.dicData = config.Load(_xPath, sDTI="compositor:1.0", bAddPathVars=True)
        xCML = CConfigCML(xPrjCfg=self.xPrjCfg, sImportPath=pathFile.as_posix())
        self.dicData = xCML.Process(self.dicData)

        self.AddFileExtToFileOutList(self.dicData)

    # enddef

    ######################################################################################
    # Get file outputs by output type
    # For the same output type there may be multiple output files of different types
    # to different folders.
    # This function also adds the file extension used.
    def GetOutputsByType(self):

        dicOut = {}
        lFileOut = self.dicData.get("lFileOut")
        if lFileOut is None:
            raise Exception("Compositor data block does not contain 'lFileOut' block.")
        # endif

        for dicFo in lFileOut:

            sOutType = dicFo.get("sOutput")
            if sOutType is None:
                raise Exception("Missing 'sOutput' field in compositor data block.")
            # endif

            lOut = dicOut.get(sOutType)
            if lOut is None:
                dicOut[sOutType] = []
                lOut = dicOut.get(sOutType)
            # endif

            lOut.append(dicFo)
        # endfor

        return dicOut

    # enddef

    ######################################################################################
    # Get file outputs by folder name
    # For the same output type there may be multiple output files of different types
    # to different folders.
    # This function also adds the file extension used.
    def GetOutputsByFolderName(self) -> dict:

        dicOut = {}
        lFileOut = self.dicData.get("lFileOut")
        if lFileOut is None:
            raise Exception("Compositor data block does not contain 'lFileOut' block.")
        # endif

        for dicFo in lFileOut:

            sOutType = dicFo.get("sFolder")
            if sOutType is None:
                raise Exception("Missing 'sFolder' field in compositor data block.")
            # endif

            lOut = dicOut.get(sOutType)
            if lOut is None:
                dicOut[sOutType] = []
                lOut = dicOut.get(sOutType)
            # endif

            lOut.append(dicFo)
        # endfor

        return dicOut

    # enddef


# endclass
