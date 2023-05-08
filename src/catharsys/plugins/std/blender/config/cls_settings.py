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

from typing import Optional

import copy
from catharsys.util import config


class CConfigSettings:
    def __init__(self, _dicData: dict, _sTypeVer: str):
        self.dicData = copy.deepcopy(_dicData)
        dicResult = config.AssertConfigType(
            _dicData, "/catharsys/blender/render/settings/{}".format(_sTypeVer)
        )
        self.lType = dicResult["lCfgType"]
        self.dicOrigData = {}

    # enddef

    ##########################################################################
    # Apply cycles and render parameters
    def Apply(self, _xObject, bRestore: bool = False, sSubDictId: Optional[str] = None):

        if bRestore is False:
            self.dicOrigData = {}
        # endif

        if sSubDictId is None:
            dicData = self.dicData
        else:
            dicData = self.dicData.get(sSubDictId)
            if dicData is None:
                raise RuntimeError(f"Invalid settings sub-dictionary id '{sSubDictId}'")
            # endif
        # endif

        # Set cycles attributes
        lAttributes = dir(_xObject)
        for sAttr in lAttributes:
            if sAttr.startswith("__"):
                continue
            # endif

            # print("Test attribute: {0}".format(sAttr))
            if bRestore is False:
                xData = self.dicData.get(sAttr)
            else:
                xData = self.dicOrigData.get(sAttr)
            # endif

            if xData is not None:
                try:
                    if bRestore is False:
                        xOrigData = getattr(_xObject, sAttr)
                        # print("Store '{}' with value: {}".format(sAttr, xOrigData))
                        self.dicOrigData[sAttr] = xOrigData
                    # endif

                    # if bRestore:
                    #     print("Restore setting '{}' with value: {}".format(sAttr, xData))
                    # else:
                    #     print("Try setting '{}' with value: {}".format(sAttr, xData))
                    # # endif

                    setattr(_xObject, sAttr, xData)
                except Exception as xEx:
                    raise Exception(
                        "Error setting parameter '{0}' with value '{1}':\n{2}".format(
                            sAttr, xData, str(xEx)
                        )
                    )
                # endtry
            # endif
        # endfor

    # enddef


# endclass
