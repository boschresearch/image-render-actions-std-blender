#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \data\obj_modify.py
# Created Date: Friday, August 13th 2021, 8:12:19 am
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

import json
import re

try:
    import _bpy
    import bpy
    import mathutils
    from pathlib import Path
    from anyblend.cls_boundbox import CBoundingBox
    from anyblend import object as anyobj
    from anyblend import ops_object as objops
    from anyblend import collection as anycln
    from anyblend import viewlayer as anyvl
    from anycam import ops as camops
    from anybase import config, convert, path

    g_bInBlenderContext = True
except Exception:
    g_bInBlenderContext = False  # don't worry, but don't call anything from here

from anybase import assertion
from anybase.cls_any_error import CAnyError, CAnyError_Message

import ison
from anybase.cls_anycml import CAnyCML
from .. import materials



############################################################################################
def ForEachMaterial(_objX: bpy.types.Object, _dicMod, **kwargs):
    """Apply a list of modifiers to each material of the object.

    Parameters
    ----------
    _objX : blender object
        Object to be modified
    _dicMod : dict
        Attributes to be modified
        
    Raises
    ------
    Exception
        Raise an exception if anything fails during modification of the object

    """
    assertion.IsTrue(g_bInBlenderContext)

    sMode = kwargs.get("sMode", "INIT")
    dicVars = kwargs.get("dicVars", {})
    sMatNamePattern = _dicMod.get("sMaterialNamePattern")

    lModifiers = _dicMod.get("lModifiers")
    if not isinstance(lModifiers, list):
        raise RuntimeError(f"Element 'lModifiers' of type 'list' missing for object modifier '{_dicMod.get('sDTI')}'")
    # endif

    for dicModFunc in lModifiers:
        if isinstance(dicModFunc, str):
            continue
        elif isinstance(dicModFunc, dict):
            ison.util.data.AddLocalGlobalVars(dicModFunc, _dicMod, bThrowOnDisallow=False)
        else:
            raise RuntimeError("Invalid object type in 'lModifiers' list")
        # endif
    # endfor

    reMat = None
    if sMatNamePattern is not None:
        reMat = re.compile(sMatNamePattern)
    # endif

    iIdx = 0

    matX: bpy.types.Material

    lMaterialsToProcess: list[bpy.types.Material] = [x.material for x in _objX.material_slots]
    for matX in lMaterialsToProcess:
        if reMat is not None:
            sName = matX.name
            if not reMat.match(sName):
                continue
            # endif
        # endif

        dicIter = {"for-each-material": {"idx": iIdx, "name": matX.name}}

        # apply modifiers to material
        try:
            xParser = CAnyCML(dicConstVars=dicIter)
            ldicActMod = xParser.Process(_dicMod, lProcessPaths=["lModifiers"])
            lActMod = ldicActMod[0]["lModifiers"]
            dicIter.update(dicVars)

            materials.ModifyMaterial(matX, lActMod, sMode=sMode, dicVars=dicIter)

        except Exception as xEx:
            raise CAnyError_Message(
                sMsg=f"Error processing object '{matX.name}' with index {iIdx} of collection '{_objX.name}'",
                xChildEx=xEx,
            )
        # endtry

        iIdx += 1

# enddef


############################################################################################
def SetMaterial(_objX: bpy.types.Object, _dicMod, **kwargs):
    """Set an object's material(s).

    Parameters
    ----------
    _objX : blender object
        Object to be modified
    _dicMod : dict
        Attributes to be modified
        
    Raises
    ------
    Exception
        Raise an exception if anything fails during modification of the object

    """
    assertion.IsTrue(g_bInBlenderContext)
    sMode = kwargs.get("sMode", "INIT")
    dicVars = kwargs.get("dicVars", {})

    bCopyMaterial: bool = False

    lModifiers: list | None = _dicMod.get("lModifiers")
    if lModifiers is not None:
        if not isinstance(lModifiers, list):
            raise RuntimeError(f"Element 'lModifiers' must be of type 'list' in object modifier '{_dicMod.get('sDTI')}'")

        if len(lModifiers) > 0:
            bCopyMaterial = True

        for dicModFunc in lModifiers:
            if isinstance(dicModFunc, str):
                continue
            elif isinstance(dicModFunc, dict):
                ison.util.data.AddLocalGlobalVars(dicModFunc, _dicMod, bThrowOnDisallow=False)
            else:
                raise RuntimeError("Invalid object type in 'lModifiers' list")
            # endif
        # endfor
    # endif 

    bCopy: bool = convert.DictElementToBool(_dicMod, "bCopyMaterial", bDefault=False)
    bCopyMaterial = bCopyMaterial or bCopy

    sMaterialName: str = convert.DictElementToString(_dicMod, "sMaterial", sDefault=None)
    matX: bpy.types.Material = bpy.data.materials.get(sMaterialName)
    if matX is None:
        raise RuntimeError(f"Material '{sMaterialName}' not found in Blender data")
    
    if bCopyMaterial:
        matX = matX.copy()
        matX.name = f"{_objX.name}.{matX.name}"

    _objX.data.materials.clear()
    _objX.data.materials.append(matX)

    materials.ModifyMaterial(matX, lModifiers, sMode=sMode, dicVars=dicVars)

# enddef
