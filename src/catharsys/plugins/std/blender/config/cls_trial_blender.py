#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \cathy\cls_cfg_exec.py
# Created Date: Monday, April 26th 2021, 10:05:56 am
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
from pathlib import Path
from anybase import config, path
from anybase.cls_any_error import CAnyError_TaskMessage, CAnyError_Message
from .cls_render_project import CRenderProjectConfig


class CConfigTrialBlender:

    _xPrjCfg: CRenderProjectConfig = None
    _dicData: dict = None
    _pathBlenderFile: Path = None

    ########################################################################################
    def __init__(self, *, xPrjCfg, dicBlender):

        self._xPrjCfg = xPrjCfg
        self._dicData = copy.deepcopy(dicBlender)
        config.AssertConfigType(dicBlender, "/catharsys/trial/blender:1")

        if "sBlenderFile" not in self._dicData:
            raise CAnyError_TaskMessage(
                sTask="Initializing Blender trial configuration",
                sMsg="Element 'sBlenderFile' missing",
            )
        # endif

        pathBlenderFile = Path(self._dicData["sBlenderFile"])

        # Process filepath and check validity
        if pathBlenderFile.is_absolute():
            self._pathBlenderFile = path.NormPath(pathBlenderFile)
            if not self._pathBlenderFile.exists():
                raise CAnyError_Message(
                    sMsg="Blender file '{0}' not found".format(
                        self._pathBlenderFile.as_posix()
                    )
                )
            # endif
        else:
            self._pathBlenderFile = path.NormPath(
                self._xPrjCfg.pathLaunch / pathBlenderFile
            )
            if not self._pathBlenderFile.exists():
                raise CAnyError_Message(
                    sMsg="Blender file '{0}' not found at path: {1}".format(
                        pathBlenderFile.as_posix(), self._pathBlenderFile.as_posix()
                    )
                )
            # endif
        # endif

    # enddef

    ################################################################################
    # Properties

    @property
    def xPrjCfg(self):
        return self._xPrjCfg

    # enddef

    @property
    def dicData(self):
        return self._dicData

    # enddef

    @property
    def pathBlenderFile(self):
        return self._pathBlenderFile

    # enddef


# endclass
