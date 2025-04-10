#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \class.py
# Created Date: Tuesday, May 17th 2022, 10:26:33 am
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
import ison
import anyblend
from anybase.cls_any_error import CAnyError_Message
from anybase.util import DictRecursiveUpdate
from anybase import convert
from catharsys.decs.decorator_log import logFunctionCall
from collections import defaultdict
from typing import Union
from . import util

from ..modify import objects as modobj


def _Print(_sMsg: str):
    print(_sMsg)
    logFunctionCall.PrintLog(_sMsg)
    pass


############################################################################################
def GenerateInProgram(_dicData: dict, *, sMode: str = "INIT", dicVars: dict = {}) -> dict[str, str]:
    dicResult = {}

    for sVarId in _dicData:
        if sVarId.startswith("__"):
            continue
        # endif

        lGens: list[dict] = _dicData[sVarId]
        if not isinstance(lGens, list):
            raise RuntimeError(f"Element '{sVarId}' is not of type 'list'")
        # endif

        dicClnObj: dict[str, str] = {}

        for iGenIdx, dicGen in enumerate(lGens):
            if not isinstance(dicGen, dict):
                raise RuntimeError(
                    f"Element {(iGenIdx+1)} of '{sVarId}' generator list is not a dictionary: '{dicGen}'"
                )
            # endif

            bEnabled = convert.DictElementToBool(dicGen, "bEnabled", bDefault=True)
            if bEnabled is False:
                continue
            # endif

            # copy locals and globals from dicData to modifier groups
            # so that they are available when parsing the modifiers with previously
            # incomplete references
            ison.util.data.AddLocalGlobalVars(dicGen, _dicData, bThrowOnDisallow=False)

            sGenDti = dicGen.get("sDTI")
            if sGenDti is None:
                raise RuntimeError("Element 'sDTI' missing in generator configuration")
            # endif

            lApplyModes = dicGen.get("lApplyModes", ["INIT"])
            if "*" not in lApplyModes and sMode not in lApplyModes:
                print(f"> {sMode}: NOT applying generator '{sGenDti}'")
                continue
            # endif
            print(f"> {sMode}: Applying generator '{sGenDti}'")

            funcGenCls = util.GetGenerateClassFunc(sGenDti, "/catharsys/blender/generate/*:*")

            dicGenClnObj = funcGenCls(dicGen, dicVars=dicVars)
            DictRecursiveUpdate(dicClnObj, dicGenClnObj)

        # endfor generator process functions

        dicResult[sVarId] = dicClnObj
    # endfor return variables

    return dicResult


# enddef


############################################################################################
@logFunctionCall
def GenerateObject(_dicObj, dicVars=None) -> dict[str, str]:
    dicGenObj = defaultdict(list)

    sFilePath = None
    dicLocals = _dicObj.get("__locals__")
    if isinstance(dicLocals, dict):
        sFilePath = dicLocals.get("filepath")
    # endif

    # General parameters that all generate objects configs share
    bEnabled = convert.DictElementToBool(_dicObj, "bEnabled", bDefault=True)
    if bEnabled:
        try:
            sDti = None
            sDti = _dicObj.get("sDTI")
            funcGenerate = util.GetGenerateFunction(sDti, "/catharsys/blender/generate/object/*:*")

            _Print(f"Applying object generator: {sDti}")

            if funcGenerate is None:
                raise Exception("No generator function available for type '{0}'".format(sDti))
            # endif funcGenerate

            xObjects: Union[bpy.types.Object, list[str]] = funcGenerate(_dicObj, dicVars=dicVars)

            # General parameter that all generate object configs share
            lCollectionHierarchy = _dicObj.get("lCollectionHierarchy", ["GeneratedObjects"])

            # setup the collection in which the object is about to be stored
            xCtx = bpy.context
            anyblend.collection.MakeRootLayerCollectionActive(xCtx)

            lObjects: list[bpy.types.Object] = None

            if isinstance(xObjects, bpy.types.Object):
                anyblend.collection.AddObjectToCollectionHierarchy(xCtx, xObjects, lCollectionHierarchy)
                lObjects = [xObjects]
            elif isinstance(xObjects, list):
                lObjects = []
                for sObjName in xObjects:
                    if not isinstance(sObjName, str):
                        raise RuntimeError(
                            f"Generator function for DTI '{sDti}' returned unsupported data type: {xObjects}"
                        )
                    # endif
                    objX = bpy.data.objects[sObjName]
                    anyblend.collection.MoveObjectToActiveCollection(bpy.context, objX, lCollectionHierarchy)
                    lObjects.append(objX)
                # endfor
            else:
                raise RuntimeError(f"Generator function for DTI '{sDti}' returned unsupported data type: {xObjects}")
            # endif

            # General parameter that all generate object configs share
            lMods = _dicObj.get("lModifiers")

            if lMods is not None:
                for dicMod in lMods:
                    ison.util.data.AddLocalGlobalVars(dicMod, _dicObj, bThrowOnDisallow=False)
                # endfor
                for objX in lObjects:
                    modobj.ModifyObject(objX, lMods, dicVars=dicVars)
                # endfor
            # endif

            # Store the names of the objects that are generated w.r.t. their collection name
            sClnName: str = lCollectionHierarchy[-1]
            for objX in lObjects:
                dicGenObj[sClnName].append(objX.name)
            # endfor

        except Exception as xEx:
            sMsg = f"Error executing object generator '{sDti}'"
            if isinstance(sFilePath, str):
                sMsg += f"\n> See file: {sFilePath}"
            # endif
            raise CAnyError_Message(sMsg=sMsg, xChildEx=xEx)
        # endtry
    # endif bEnabled

    return dict(dicGenObj)


# enddef


############################################################################################
@logFunctionCall
def GenerateCollection(_dicCln, dicVars=None) -> dict[str, str]:
    dicClnObj = defaultdict(list)

    sFilePath = None
    dicLocals = _dicCln.get("__locals__")
    if isinstance(dicLocals, dict):
        sFilePath = dicLocals.get("filepath")
    # endif

    # General parameters that all generate objects configs share
    bEnabled = convert.DictElementToBool(_dicCln, "bEnabled", bDefault=True)
    if bEnabled:
        try:
            sDti = None
            sDti = _dicCln.get("sDTI")
            funcGenerate = util.GetGenerateFunction(sDti, "/catharsys/blender/generate/collection/*:*")
            _Print(f"Applying collection generator: {sDti}")

            if funcGenerate is None:
                raise Exception("No generator function available for type '{0}'".format(sDti))
            # endif funcGenerate

            dicClnObj = funcGenerate(_dicCln, dicVars=dicVars)

        except Exception as xEx:
            sMsg = f"Error executing collection generator '{sDti}'"
            if isinstance(sFilePath, str):
                sMsg += f"\n> See file: {sFilePath}"
            # endif
            raise CAnyError_Message(sMsg=sMsg, xChildEx=xEx)
        # endtry
    # endif

    return dict(dicClnObj)


# enddef

############################################################################################
@logFunctionCall
def GenerateMaterial(_dicMat, dicVars=None) -> dict[str, str]:
    dicMatObj = defaultdict(list)

    sFilePath = None
    dicLocals = _dicMat.get("__locals__")
    if isinstance(dicLocals, dict):
        sFilePath = dicLocals.get("filepath")
    # endif

    # General parameters that all generate objects configs share
    bEnabled = convert.DictElementToBool(_dicMat, "bEnabled", bDefault=True)
    if bEnabled:
        try:
            sDti = None
            sDti = _dicMat.get("sDTI")
            funcGenerate = util.GetGenerateFunction(sDti, "/catharsys/blender/generate/material/*:*")
            _Print(f"Applying material generator: {sDti}")

            if funcGenerate is None:
                raise Exception("No generator function available for type '{0}'".format(sDti))
            # endif funcGenerate

            dicMatObj = funcGenerate(_dicMat, dicVars=dicVars)

        except Exception as xEx:
            sMsg = f"Error executing material generator '{sDti}'"
            if isinstance(sFilePath, str):
                sMsg += f"\n> See file: {sFilePath}"
            # endif
            raise CAnyError_Message(sMsg=sMsg, xChildEx=xEx)
        # endtry
    # endif

    return dict(dicMatObj)


# enddef
