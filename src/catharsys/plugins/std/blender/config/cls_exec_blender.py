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
import catharsys.setup.util
from pathlib import Path
from anybase import config, path
from anybase.cls_any_error import CAnyError_TaskMessage


class CConfigExecBlender:
    def __init__(self, _dicExec):
        self._dicData = copy.deepcopy(_dicExec)
        dicResult = config.AssertConfigType(_dicExec, "/catharsys/exec/blender/*:2.1")
        self._lType = dicResult["lCfgType"]

        if "mBlender" not in self._dicData:
            raise CAnyError_TaskMessage(
                sTask="Initializing Blender execution configuration",
                sMsg="Element 'mBlender' missing",
            )
        # endif
        self._dicBlender = self._dicData["mBlender"]

        if "sVersion" not in self._dicBlender:
            raise CAnyError_TaskMessage(
                sTask="Initializing Blender execution configuration",
                sMsg="Element 'mBlender.sVersion' missing",
            )
        # endif

        sPathBlender = self._dicBlender.get("sPath")
        if sPathBlender is None:
            self._pathBlender = catharsys.setup.util.GetCathUserPath(_bCheckExists=True) / "blender-{}".format(
                self.sBlenderVersion
            )
        else:
            self._pathBlender = path.MakeNormPath(sPathBlender)
        # endif

    # enddef

    ################################################################################
    # Properties

    @property
    def sType(self):
        return self._lType[3]

    @property
    def sBlenderVersion(self):
        return self._dicBlender.get("sVersion")

    @property
    def sBlenderPath(self) -> str:
        return self._pathBlender.as_posix()

    @property
    def pathBlender(self) -> Path:
        return self._pathBlender

    @property
    def dicBlender(self) -> dict:
        return self._dicBlender

    # enddef

    @property
    def dicBlenderSettings(self) -> dict:
        return self._dicBlender.get("mSettings")

    # enddef


# endclass
