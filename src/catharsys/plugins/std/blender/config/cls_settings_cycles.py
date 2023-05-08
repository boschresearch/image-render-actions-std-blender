#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \cathy\cls_cfg_cycles.py
# Created Date: Monday, September 13th 2021, 8:39:56 am
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

import anyblend

from .cls_settings import CConfigSettings


class CConfigSettingsCycles(CConfigSettings):
    def __init__(self, _dicData):
        super().__init__(_dicData, "cycles:1")

    # enddef

    ##########################################################################
    # Apply cycles and render parameters
    def Apply(self, _xContext, bRestore=False):
        super().Apply(_xContext.scene.cycles, bRestore=bRestore)

        self.SelectComputeDevices(_xContext)

    # enddef

    ##########################################################################
    # Select compute devices for cycles
    def SelectComputeDevices(self, _xContext):

        sComputeDeviceType = self.dicData.get("sComputeDeviceType")
        if not isinstance(sComputeDeviceType, str):
            if _xContext.scene.cycles.device == "GPU":
                sComputeDeviceType = "CUDA"
            else:
                sComputeDeviceType = "CPU"
            # endif
        # endif

        bCombinedCpuCompute = self.dicData.get("bCombinedCpuCompute")
        if not isinstance(bCombinedCpuCompute, bool):
            bCombinedCpuCompute = False
        # endif

        lComputeDevs = anyblend.app.prefs.UseComputeDevices(
            xContext=_xContext,
            sComputeDeviceType=sComputeDeviceType,
            bCombinedCpuCompute=bCombinedCpuCompute,
            bPrintInfo=False,
        )
        if len(lComputeDevs) == 0:
            raise RuntimeError(f"No '{sComputeDeviceType}' devices found for rendering")
        # endif

        print("", flush=True)
        print(
            "==================================================================",
            flush=True,
        )
        print(f"Used compute devices of type '{sComputeDeviceType}':", flush=True)
        anyblend.app.prefs.PrintUsedDevices(lComputeDevs)
        print(
            "==================================================================",
            flush=True,
        )
        print("", flush=True)

    # enddef


# endclass
