#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /obj.py
# Created Date: Thursday, October 22nd 2020, 1:20:28 pm
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

import bpy
import mathutils

from anybase.cls_any_error import CAnyError, CAnyError_Message
from anybase import convert
import ison
from . import util

from catharsys.decs.decorator_log import logFunctionCall

# concentrate print functionality for further generic logging concept
def _Print(_sMsg: str):
    print(_sMsg)
    logFunctionCall.PrintLog(_sMsg)
    pass


############################################################################################
@logFunctionCall
def ModifyObject(_objX, _lMods, sMode="INIT", dicVars=None):

    if _lMods is None:
        return
    # endif

    if len(_lMods) > 0:
        _Print(f"\nApplying modifiers to object: {_objX.name}")
    # endif

    for dicMod in _lMods:
        sModType = dicMod.get("sDTI")
        if sModType is None:
            raise CAnyError_Message(sMsg=f"Modifier for object '{_objX.name}' is missing 'sDTI' element")
        # endif

        bEnabled = convert.DictElementToBool(dicMod, "bEnabled", bDefault=True)
        if bEnabled is False:
            _Print(f"-- DISABLED: NOT applying modifier '{sModType}' to object: {_objX.name}")
            continue
        # endif

        lApplyModes = dicMod.get("lApplyModes", ["INIT"])
        if "*" not in lApplyModes and sMode not in lApplyModes:
            _Print(f"-- {sMode}: NOT applying modifier '{sModType}' to object: {_objX.name}")
            continue
        # endif
        _Print(f">> {sMode}: Applying modifier '{sModType}' to object: {_objX.name}")

        funcModify = util.GetModifyFunction(sModType, "/catharsys/blender/modify/object/*:*")
        if funcModify is None:
            raise Exception("Modification type '{0}' not supported".format(sModType))
        # endif

        try:
            funcModify(_objX, dicMod, sMode=sMode, dicVars=dicVars)
        except Exception as xEx:
            raise CAnyError_Message(sMsg=f"Error executing modifier '{sModType}'", xChildEx=xEx)
        # endtry

    # endfor lMods


# enddef


############################################################################################
@logFunctionCall
def ModifyObjects(_dicModifyObjects, sMode="INIT", dicVars=None):

    if _dicModifyObjects is None:
        return
    # endif

    dicObj = bpy.data.objects

    sFilePath = None
    dicLocals = _dicModifyObjects.get("__locals__")
    if isinstance(dicLocals, dict):
        sFilePath = dicLocals.get("filepath")
    # endif

    for sObjId in _dicModifyObjects:
        if sObjId.startswith("__"):
            continue
        # endif

        try:
            objX = dicObj.get(sObjId)
            if objX is None:
                raise Exception("Object with id '{0}' not found".format(sObjId))
            # endif

            lMods = _dicModifyObjects.get(sObjId)
            if not isinstance(lMods, list):
                raise CAnyError_Message(sMsg=f"Expect modifier list for object '{sObjId}'")
            # endif

            for dicMod in lMods:
                if not isinstance(dicMod, dict):
                    raise CAnyError_Message(sMsg=f"Expect modifier list for obejct '{sObjId}' to contain dictionaries")
                # endif
                ison.util.data.AddLocalGlobalVars(dicMod, _dicModifyObjects, bThrowOnDisallow=False)
            # endfor

            ModifyObject(objX, lMods, sMode=sMode, dicVars=dicVars)

        except Exception as xEx:
            sMsg = f"Error executing modifiers for object '{sObjId}' in mode '{sMode}'"
            if isinstance(sFilePath, str):
                sMsg += f"\n> See file: {sFilePath}"
            # endif
            raise CAnyError_Message(sMsg=sMsg, xChildEx=xEx)
        # endtry
    # endfor objects


# enddef
