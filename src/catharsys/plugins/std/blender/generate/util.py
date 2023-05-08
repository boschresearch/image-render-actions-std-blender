#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \util.py
# Created Date: Tuesday, May 17th 2022, 9:46:04 am
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


from anybase import plugin, config


############################################################################################
def GetGenerateClassFunc(_sModTypeDti, _sDtiClass):

    if config.CheckDti(_sModTypeDti, _sDtiClass)["bOK"] is False:
        raise RuntimeError("Generator '{}' is not of type '{}'".format(_sModTypeDti, _sDtiClass))
    # endif

    epFunc = plugin.SelectEntryPointFromDti(
        sGroup="catharsys.blender.generate_class",
        sTrgDti=_sModTypeDti,
        sTypeDesc="Generator class",
    )
    return epFunc.load()


# enddef


############################################################################################
def GetGenerateFunction(_sModTypeDti, _sDtiClass):

    if config.CheckDti(_sModTypeDti, _sDtiClass)["bOK"] is False:
        raise RuntimeError("Modifier '{}' is not of type '{}'".format(_sModTypeDti, _sDtiClass))
    # endif

    epFunc = plugin.SelectEntryPointFromDti(
        sGroup="catharsys.blender.generate", sTrgDti=_sModTypeDti, sTypeDesc="Generator"
    )
    return epFunc.load()


# enddef
