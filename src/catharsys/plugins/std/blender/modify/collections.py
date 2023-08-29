#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \data\collection.py
# Created Date: Saturday, August 21st 2021, 7:04:57 am
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

from anybase import convert
from anybase.cls_any_error import CAnyError_Message
import ison
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
def ModifyCollection(_clnX, _lMods, sMode="INIT", dicVars=None):

    if len(_lMods) > 0:
        _Print(f"\nApplying modifiers to collection: {_clnX.name}")
    # endif

    for dicMod in _lMods:
        sModType = dicMod.get("sDTI")
        if sModType is None:
            raise CAnyError_Message(sMsg=f"Modifier for collection '{_clnX.name}' is missing 'sDTI' element")
        # endif

        bEnabled = convert.DictElementToBool(dicMod, "bEnabled", bDefault=True)
        if bEnabled is False:
            continue
        # endif

        lApplyModes = dicMod.get("lApplyModes", ["INIT"])
        if sMode not in lApplyModes:
            _Print(f"-- {sMode}: NOT applying modifier '{sModType}'")
            continue
        # endif
        _Print(f">> {sMode}: Applying modifier '{sModType}'")

        funcModify = util.GetModifyFunction(sModType, "/catharsys/blender/modify/collection/*:*")
        if funcModify is None:
            raise Exception("Modification type '{0}' not supported".format(sModType))
        # endif

        try:
            funcModify(_clnX, dicMod, sMode=sMode, dicVars=dicVars)
        except Exception as xEx:
            raise CAnyError_Message(sMsg=f"Error executing modifier '{sModType}'", xChildEx=xEx)
        # endtry

    # endfor lMods
    _Print("")


# enddef


############################################################################################
@logFunctionCall
def ModifyCollections(_dicCfg, sMode="INIT", dicVars=None):

    if _dicCfg is None:
        return
    # endif

    dicCln = bpy.data.collections

    sFilePath = None
    dicLocals = _dicCfg.get("__locals__")
    if isinstance(dicLocals, dict):
        sFilePath = dicLocals.get("filepath")
    # endif

    for sClnId in _dicCfg:
        if sClnId.startswith("__"):
            continue
        # endif

        try:
            clnX = dicCln.get(sClnId)
            if clnX is None:
                raise Exception("Collection with id '{0}' not found".format(sClnId))
            # endif

            lMods = _dicCfg[sClnId]
            for dicMod in lMods:
                ison.util.data.AddLocalGlobalVars(dicMod, _dicCfg, bThrowOnDisallow=False)
            # endfor

            ModifyCollection(clnX, lMods, sMode=sMode, dicVars=dicVars)

        except Exception as xEx:
            sMsg = f"Error executing modifiers for collection '{sClnId}' in mode '{sMode}'"
            if isinstance(sFilePath, str):
                sMsg += f"\n> See file: {sFilePath}"
            # endif
            raise CAnyError_Message(sMsg=sMsg, xChildEx=xEx)
        # endtry

    # endfor collections


# enddef
