#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \data\evaluators.py
# Created Date: Friday, April 1st 2022, 1:45:34 pm
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

import math
import bpy
import mathutils

import runpy

from pathlib import Path
from anybase.cls_any_error import CAnyError_Message
import anybase.util
from anybase import convert

################################################################################################
def ObjectInfo(_dicEval, **kwargs):

    sObjectId = _dicEval.get("sObjectId")
    if sObjectId is None:
        raise RuntimeError(
            "Element 'sObjectId' missing in evaluator " "'/catharsys/modify/evaluate/object/info:1' configuration"
        )
    # endif

    objX = bpy.data.objects.get(sObjectId)
    if objX is None:
        raise RuntimeError("Object with id '{}' not found in blender file".format(sObjectId))
    # endif

    lBoundBox = [objX.matrix_world @ mathutils.Vector(x) for x in objX.bound_box]
    vCenter = mathutils.Vector((0, 0, 0))
    for vX in lBoundBox:
        vCenter += vX
    # endfor
    vCenter /= len(lBoundBox)

    lBoundBox = [list(x) for x in lBoundBox]

    dicResult = {
        "location": list(objX.location),
        "rotation-euler": [math.degrees(x) for x in list(objX.rotation_euler)],
        "scale": list(objX.scale),
        "bound-box": lBoundBox,
        "bound-box-center": list(vCenter),
    }

    return dicResult


# enddef


################################################################################################
def LookAtRotZ(_dicEval, **kwargs):

    # print("=================================================")
    # print(_dicEval)

    lOrigin = convert.DictElementToFloatList(_dicEval, "lOrigin", iLen=3, lDefault=[0.0, 0.0, 0.0])
    lTarget = convert.DictElementToFloatList(_dicEval, "lTarget", iLen=3)

    sUnit = _dicEval.get("sUnit", "rad")

    # print(f"lOrigin: {lOrigin}")
    # print(f"lTarget: {lTarget}")

    lOrig = lOrigin[0:2]
    lOrig.append(0.0)

    lTrg = lTarget[0:2]
    lTrg.append(0.0)

    # print(f"lOrig: {lOrig}")
    # print(f"lTrg: {lTrg}")

    vOrig = mathutils.Vector(lOrig)
    vTrg = mathutils.Vector(lTrg)

    vDir = (vTrg - vOrig).normalized()
    # print(f"vDir: {vDir}")

    fRotZ_rad = math.atan2(vDir[1], vDir[0])

    fResult = None
    if sUnit == "rad":
        fResult = fRotZ_rad
    elif sUnit == "deg":
        fResult = math.degrees(fRotZ_rad)
    else:
        raise RuntimeError("Invalid value for element 'sUnit': {}".format(sUnit))
    # endif

    # print(f"fResult: {fResult}")
    # print("=================================================")

    return fResult


# enddef


################################################################################################
def RunPyScript(_dicEval, **kwargs):

    sMode: str = kwargs.get("sMode", "INIT")
    dicVars: dict = kwargs.get("dicVars", {})

    # print("==============================================================================")
    # print("RunPyScript: START")

    # print(f"_dicEval: {_dicEval}")

    sScriptFilename: str = _dicEval.get("sScriptFilename")
    if sScriptFilename is None:
        raise CAnyError_Message(sMsg="No python script filename give in element 'sScriptFilename'")
    # endif

    pathScript = Path(sScriptFilename)
    if not pathScript.is_absolute():
        sPath: str = None
        dicLocals: dict = _dicEval.get("__locals__")
        if isinstance(dicLocals, dict):
            sPath = dicLocals.get("path")
        # endif
        if sPath is None:
            raise CAnyError_Message(sMsg="Filepath of evaluator JSON file is not stored in evaluator data")
        # endif

        pathScript = Path(sPath) / sScriptFilename
    # endif

    if not pathScript.exists():
        raise CAnyError_Message(
            sMsg="Python script '{}' not found at path: {}".format(sScriptFilename, pathScript.as_posix())
        )
    # endif

    dicUserGlobals = _dicEval.get("mGlobals", {})

    dicGlobals = {"sMode": sMode}

    anybase.util.DictRecursiveUpdate(dicGlobals, dicVars)
    anybase.util.DictRecursiveUpdate(dicGlobals, dicUserGlobals)

    try:
        dicResultGlobals = runpy.run_path(
            pathScript.as_posix(),
            init_globals=dicGlobals,
            run_name="catharsys.evaluator",
        )
    except Exception as xEx:
        raise CAnyError_Message(
            sMsg="Error executing evaluator python script '{}' at path: {}".format(
                sScriptFilename, pathScript.as_posix()
            ),
            xChildEx=xEx,
        )
    # endtry

    dicResultAll = dicResultGlobals.get("dicResult")
    dicResult = {}

    if isinstance(dicResultAll, dict):
        for sKey, xVar in dicResultAll.items():
            if not sKey.startswith("__") and (
                isinstance(xVar, int)
                or isinstance(xVar, float)
                or isinstance(xVar, str)
                or isinstance(xVar, list)
                or isinstance(xVar, dict)
                or isinstance(xVar, bool)
            ):
                dicResult[sKey] = xVar
            # endif
        # endfor
    # endif

    # print(dicResult)
    # print("RunPyScript: END")
    # print("==============================================================================")

    return dicResult


# enddef
