#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \obj_generate.py
# Created Date: Tuesday, May 17th 2022, 10:48:00 am
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
import mathutils

from collections import defaultdict
from pathlib import Path

from anybase import convert
from anybase import path as anypath

from anyblend import collection
from anyblend import object as anyobj


############################################################################################
def GenerateBlenderObject(_args, **kwargs):
    """Function to instanciate an abitrary blender object using the respective API call.
    The basic idea is to create a function from the parameters given and call it to
    create object data. Using this data, the new object is created.


    Parameters passed via _args:
    - sId: Name/Blender identifier of the object to be created
    - sFunction: String that indicates which function to use (for example "bpy.data.lights.new")
    - sParams: list of params to be concatenated and given as additional parameters to the call
            to the function that creates the object.

    Parameters
    ----------
    _args : dict
        Dictionary of args for creation of the objects

    Returns
    -------
    blender_object
        The newly created object in the current collection

    Raises
    ------
    Exception
        Anything fails during creation of the object
    """
    try:
        sParamString = ", ".join(["{}={}".format(key, value) for key, value in _args["lParams"].items()])
        sFunctionString = "{}(name='{}-data', {})".format(_args["sFunction"], _args["sId"], sParamString)

        object_data = eval(sFunctionString)

        new_object = bpy.data.objects.new(name=_args["sId"], object_data=object_data)

    except Exception as e:
        raise Exception("Could not generate blender object {}: {}".format(_args["sId"], e))
    # endtry

    return new_object


# enddef


############################################################################################
def LoadObject(_dicObj, **kwargs):
    sBlenderFilename = _dicObj.get("sBlenderFilename")
    if sBlenderFilename is None:
        raise RuntimeError("Key 'sBlenderFilename' missing in load object configuration")
    # endif

    sSrcObjName = _dicObj.get("sSrcName")
    if sSrcObjName is None:
        raise RuntimeError("Key 'sSrcName' is missing in load object configuration")
    # endif

    sDestObjName = _dicObj.get("sDestName", sSrcObjName)

    with bpy.data.libraries.load(sBlenderFilename, link=False) as (data_from, data_to):
        if sSrcObjName in data_from.objects:
            data_to.objects.append(sSrcObjName)
        else:
            raise RuntimeError("Object of name {} not found in {}".format(sSrcObjName, sBlenderFilename))
        # endif
    # endwith

    if len(data_to.objects) != 1:
        raise RuntimeError("Object of name {} could not be loaded from {}".format(sSrcObjName, sBlenderFilename))

    xObject = data_to.objects[0]

    bObjectRenamed = xObject.name != sSrcObjName
    if bObjectRenamed:
        raise RuntimeError("Blender object '{0}' already exists.".format(sDestObjName))

    xObject.name = sDestObjName

    return xObject


# enddef


############################################################################################
def _DoImportObjectAny(_pathFile: Path, _dicObj: dict, *, _sObjectName: str = None) -> list[str]:
    fScaleFactor: float = convert.DictElementToFloat(_dicObj, "fScaleFactor", bDoRaise=False)
    lLocation: list[float] = convert.DictElementToFloatList(_dicObj, "lLocation", iLen=3, lDefault=[0.0, 0.0, 0.0])
    lRotationEuler_deg: list[float] = convert.DictElementToFloatList(
        _dicObj, "lRotationEuler_deg", iLen=3, lDefault=None, bDoRaise=False
    )
    bJoinObjectGroups: bool = convert.DictElementToBool(_dicObj, "bJoinObjectGroups", bDefault=False)

    bDoSetOrigin: bool = False
    dicSetOrigin: dict = _dicObj.get("mSetOrigin")
    if isinstance(dicSetOrigin, dict):
        bDoSetOrigin: bool = convert.DictElementToBool(dicSetOrigin, "bEnable", bDefault=True)
        sSetOriginType: str = convert.DictElementToString(dicSetOrigin, "sType", sDefault="ORIGIN_CENTER_OF_VOLUME")
        sSetOriginCenter: str = convert.DictElementToString(dicSetOrigin, "sCenter", sDefault="MEDIAN")
    else:
        sSetOriginType = None
        sSetOriginCenter = None
    # endif

    bDoSmoothSurface: bool = False
    dicSmoothSurface: dict = _dicObj.get("mSmoothSurface")
    if isinstance(dicSmoothSurface, dict):
        bDoSmoothSurface: bool = convert.DictElementToBool(dicSmoothSurface, "bEnable", bDefault=True)
        fSmoothSurfaceVoxelSize: float = convert.DictElementToFloat(dicSmoothSurface, "fVoxelSize")
    else:
        fSmoothSurfaceVoxelSize = None
    # endif

    ############################################################################################################
    # Process
    lObjIn = anyobj.ImportObjectAny(
        _pathFile=_pathFile,
        _sNewName=_sObjectName,
        _fScaleFactor=fScaleFactor,
        _bDoSetOrigin=bDoSetOrigin,
        _sSetOriginType=sSetOriginType,
        _sSetOriginCenter=sSetOriginCenter,
        _lLocation=lLocation,
        _lRotationEuler_deg=lRotationEuler_deg,
        _bDoJoinObjects=bJoinObjectGroups,
    )

    if bDoSmoothSurface is True:
        for sObjIn in lObjIn:
            objIn = bpy.data.objects[sObjIn]
            if objIn.type == "EMPTY":
                lChildren: list[str] = anyobj.GetObjectChildrenNames(objIn, bRecursive=True)
                for sChild in lChildren:
                    objX: bpy.types.Object = bpy.data.objects[sChild]
                    if objX.type == "MESH":
                        anyobj.SmoothObjectSurface_VoxelRemesh(objX, fSmoothSurfaceVoxelSize)
                    # endif
                # endfor
            elif objIn.type == "MESH":
                anyobj.SmoothObjectSurface_VoxelRemesh(objIn, fSmoothSurfaceVoxelSize)
            # endif
        # endfor
    # endif

    return lObjIn


# enddef


############################################################################################
def ImportObjectAny(_dicObj, **kwargs) -> list[str]:
    xCtx = bpy.context

    sFilePath: str = convert.DictElementToString(_dicObj, "sFilePath")
    sObjectName: str = convert.DictElementToString(_dicObj, "sObjectName", bDoRaise=False)
    pathFile: Path = anypath.MakeNormPath(Path(sFilePath).absolute())

    if not pathFile.exists():
        raise RuntimeError(f"File not found for object import: {(pathFile.as_posix())}")
    # endif

    if not pathFile.is_file():
        raise RuntimeError(f"File path does not reference a file: {(pathFile.as_posix())}")
    # endif

    lSupportedTypes: list[str] = [".obj", ".fbx", ".glb", ".gltf"]
    if pathFile.suffix not in lSupportedTypes:
        sSupTypes: str = ", ".join(lSupportedTypes)
        raise RuntimeError(f"File type '{pathFile.suffix}' not supported. Supported types are: [{sSupTypes}]")
    # endif

    collection.MakeRootLayerCollectionActive(xCtx)

    return _DoImportObjectAny(pathFile, _dicObj, _sObjectName=sObjectName)


# enddef
