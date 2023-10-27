#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \data\scene.py
# Created Date: Friday, September 3rd 2021, 3:00:26 pm
# Author: Dirk Fortmeier (BEG/ESD1)
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
import ison

from anybase import convert
from anybase.cls_any_error import CAnyError_Message
from . import util

from catharsys.decs.decorator_log import logFunctionCall


# concentrate print functionality for further generic logging concept
def _Print(_sMsg: str):
    print(_sMsg)
    logFunctionCall.PrintLog(_sMsg)
    pass


# enddef


############################################################################################
@logFunctionCall
def ModifyScene(_scnX, _lMods, sMode="INIT", dicVars=None):
    if _lMods is None:
        return
    # endif

    if len(_lMods) > 0:
        _Print(f"Applying modifiers to scene: {_scnX.name}")
    # endif

    for dicMod in _lMods:
        sModType = dicMod.get("sDTI")
        if sModType is None:
            raise CAnyError_Message(sMsg=f"Modifier for scene '{_scnX.name}' is missing 'sDTI' element")
        # endif

        bEnabled = convert.DictElementToBool(dicMod, "bEnabled", bDefault=True)
        if bEnabled is False:
            _Print(f"-- DISABLED: NOT applying modifier '{sModType}'")
            continue
        # endif

        lApplyModes = dicMod.get("lApplyModes", ["INIT"])
        if "*" not in lApplyModes and sMode not in lApplyModes:
            _Print(f"-- {sMode}: NOT applying modifier '{sModType}'")
            continue
        # endif
        _Print(f">> {sMode}: Applying modifier '{sModType}'")

        funcModify = util.GetModifyFunction(sModType, "/catharsys/blender/modify/scene/*:*")
        if funcModify is None:
            raise Exception("Modification type '{0}' not supported".format(sModType))
        # endif

        try:
            funcModify(_scnX, dicMod, sMode=sMode, dicVars=dicVars)
        except Exception as xEx:
            raise CAnyError_Message(sMsg=f"Error executing modifier '{sModType}'", xChildEx=xEx)
        # endtry

    # endfor lMods


# enddef


############################################################################################
def ModifyScenes(_dicModifyScenes, sMode="INIT", dicVars=None):
    if _dicModifyScenes is None:
        return
    # endif

    dicScn = bpy.data.scenes

    sFilePath = None
    dicLocals = _dicModifyScenes.get("__locals__")
    if isinstance(dicLocals, dict):
        sFilePath = dicLocals.get("filepath")
    # endif

    for sScnId in _dicModifyScenes:
        if sScnId.startswith("__"):
            continue
        # endif

        try:
            scnX = dicScn.get(sScnId)
            if scnX is None:
                raise Exception("Scene with id '{0}' not found".format(sScnId))
            # endif

            lMods = _dicModifyScenes.get(sScnId)
            for dicMod in lMods:
                ison.util.data.AddLocalGlobalVars(dicMod, _dicModifyScenes, bThrowOnDisallow=False)
            # endfor

            ModifyScene(scnX, lMods, sMode=sMode, dicVars=dicVars)

        except Exception as xEx:
            sMsg = f"Error executing modifiers for scene '{sScnId}' in mode '{sMode}'"
            if isinstance(sFilePath, str):
                sMsg += f"\n> See file: {sFilePath}"
            # endif
            raise CAnyError_Message(sMsg=sMsg, xChildEx=xEx)
        # endtry

    # endfor objects


# enddef
