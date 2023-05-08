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

from anybase.cls_any_error import CAnyError_Message
from . import util

from catharsys.decs.decorator_log import logFunctionCall

# concentrate print functionality for further generic logging concept
def _Print(_sMsg: str):
    print(_sMsg)
    logFunctionCall.PrintLog(_sMsg)
    pass


############################################################################################
@logFunctionCall
def ModifyNodeTree(_ngX, _lMods, sMode="INIT", dicVars=None):

    for dicMod in _lMods:
        sModType = dicMod.get("sDTI")
        if sModType is None:
            raise CAnyError_Message(sMsg=f"Modifier for node group '{_ngX.name}' is missing 'sDTI' element")
        # endif
        
        lApplyModes = dicMod.get("lApplyModes", ["INIT"])
        if sMode not in lApplyModes:
            _Print(f"-- {sMode}: NOT applying modifier '{sModType}'")
            continue
        # endif
        _Print(f">> {sMode}: Applying modifier '{sModType}'")

        funcModify = util.GetModifyFunction(sModType, "/catharsys/blender/modify/nodegroup/*:*")
        if funcModify is None:
            raise Exception("Modification type '{0}' not supported".format(sModType))
        # endif

        try:
            funcModify(_ngX, dicMod, sMode=sMode, dicVars=dicVars)
        except Exception as xEx:
            raise CAnyError_Message(sMsg=f"Error executing modifier '{sModType}'", xChildEx=xEx)
        # endtry

    # endfor lMods


# enddef


############################################################################################
@logFunctionCall
def ModifyNodeGroup(_ngX, _lMods, sMode="INIT", dicVars=None):

    if _lMods is None:
        return
    # endif

    # Make a copy of the node group which is modified,
    # to be able to revert back to the original later.
    ngMod = _ngX.copy()
    # Ensure that original is not deleted by Blender
    _ngX.use_fake_user = True
    # Replace all references to the original node group in blend file
    # by the new modified node group.
    _ngX.user_remap(ngMod)
    # Update the view layer
    bpy.context.view_layer.update()

    if len(_lMods) > 0:
        _Print(f"Applying modifiers to nodegroup: {_ngX.name}")
    # endif

    ModifyNodeTree(ngMod, _lMods, sMode=sMode, dicVars=dicVars)


# enddef


############################################################################################
@logFunctionCall
def ModifyNodeGroups(_dicCfg, sMode="INIT", dicVars=None):

    if _dicCfg is None:
        return
    # endif

    dicNg = bpy.data.node_groups

    for sNgId in _dicCfg:
        if sNgId.startswith("__"):
            continue
        # endif

        ngX = dicNg.get(sNgId)
        if ngX is None:
            raise Exception("Collection with id '{0}' not found".format(sNgId))
        # endif

        lMods = _dicCfg[sNgId]
        ModifyNodeGroup(ngX, lMods, sMode=sMode, dicVars=dicVars)
    # endfor collections


# enddef
