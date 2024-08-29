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


############################################################################################
def _EnableRender(_objX, _bEnable, bRecursive=True):
    _objX.hide_render = not _bEnable
    if bRecursive:
        for objC in _objX.children:
            _EnableRender(objC, _bEnable, bRecursive=bRecursive)
        # endfor
    # endif


# enddef


############################################################################################
def Enable(_objX, _dicMod, **kwargs):
    assertion.IsTrue(g_bInBlenderContext)
    config.AssertConfigType(_dicMod, "/catharsys/blender/modify/object/enable:1.0")

    # sModType = convert.DictElementToString(
    #     _dicMod,
    #     "sType",
    #     sDefault=convert.DictElementToString(_dicMod, "sDTI", bDoRaise=False),
    # )

    bEnable = convert.DictElementToBool(_dicMod, "xValue")
    _EnableRender(_objX, bEnable, bRecursive=True)


# enddef


############################################################################################
def EnableIfBoundBox(_objX, _dicMod, **kwargs):
    """Enable/disable object depending on its' relation to a target object's bounding box.

    Parameters
    ----------
    _objX : Blender object
        The object
    _dicMod : dict
        Arguments

    Configuration Paramters
    -----------------------
    sTarget: string
        The name of the target object, whose bounding box will be used.
    bCompoundTarget: bool, optional
        If set to true, the bounding box is evaluated for the object sTarget and all its' children.
        If set to false, only the mesh of sTarget itself without children is used.
    fBorder: float, optional
        Size of border around target object's bounding box. Default is 0.0.
    sRelation: string, optional
        The relation to test. Must be one of ["INSIDE", "OUTSIDE", "INTERSECT"]. Default is "INSIDE".
    """
    assertion.IsTrue(g_bInBlenderContext)
    config.AssertConfigType(_dicMod, "/catharsys/blender/modify/object/enable-if/bound-box:1.0")

    fBorder = convert.DictElementToFloat(_dicMod, "fBorder", fDefault=0.0)
    sRelation = convert.DictElementToString(_dicMod, "sRelation", sDefault="INSIDE").upper()
    sTarget = convert.DictElementToString(_dicMod, "sTarget")
    bCompoundTarget = convert.DictElementToBool(_dicMod, "bCompoundTarget", bDefault=False)

    objTarget = bpy.data.objects.get(sTarget)
    if objTarget is None:
        raise RuntimeError(f"Target object '{sTarget}' not found")
    # endif

    boxTarget = CBoundingBox(_objX=objTarget, _bCompoundObject=bCompoundTarget, _bUseMesh=True)

    bEnable = None
    match sRelation:
        case "INSIDE":
            bEnable = boxTarget.IsObjectInside(_objX, _fBorder=fBorder)

        case "OUTSIDE":
            bEnable = boxTarget.IsObjectOutside(_objX, _fBorder=fBorder)

        case "INTERSECT":
            bEnable = boxTarget.IsObjectIntersect(_objX, _fBorder=fBorder)

    # endmatch

    if bEnable is None:
        raise RuntimeError(f"Unsupported relation '{sRelation}'. Expect one of ['INSIDE', 'OUTSIDE', 'INTERSECT']")
    # endif

    anyobj.Hide(_objX, bHide=not bEnable, bHideRender=not bEnable, bRecursive=True)

    # sName = f"{objTarget.name}.BoundBox"
    # if sName not in bpy.data.objects:
    #     xCln = anycln.FindCollectionOfObject(bpy.context, objTarget)
    #     print(f"boxTarget '{objTarget.name}': {boxTarget.lCorners}")

    #     boxTarget.CreateBlenderObject(_sName=sName, _xCollection=xCln)
    # # endif


# enddef


############################################################################################
def ModifyProperties(_objX, _dicMod, **kwargs):
    """Modify attributes of a blender object
    Modify custom properties of an object.

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

    dicValues = _dicMod.get("mValues")
    if not isinstance(dicValues, dict):
        raise RuntimeError("Missing element 'mValues' in modify properties modifier")
    # endif

    for sKey, xValue in dicValues.items():
        if not isinstance(sKey, str):
            raise RuntimeError("Invalid key type in modify attributes: {}".format(sKey))
        # endif

        if sKey not in _objX:
            raise RuntimeError(f"Property '{sKey}' not found in object '{_objX.name}'")
        # endif

        if isinstance(xValue, int) or isinstance(xValue, float) or isinstance(xValue, str):
            _objX[sKey] = xValue

        else:
            sType = convert.ToTypename(xValue)
            raise RuntimeError(f"Value for property '{sKey}' of unsupported type '{sType}'")
        # endif

    # endfor

    # Need to tag the object for updates,
    # so that drivers depending on the properties
    # are updated. Note that a driver update
    # can only be triggered by changing the
    # current scene frame, it seems.
    # You can use anyblend.scene.UpdateDrivers() for this.
    _objX.update_tag()


# enddef


############################################################################################
def ModifyAttributes(_objX, _dicMod, **kwargs):
    """Modify attributes of a blender object
    For each parameter in _dicMod, create a command to modify the object attributes.

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

    # "dValues" tag is deprecated
    dicValues = _dicMod.get("mValues", _dicMod.get("dValues"))
    if not isinstance(dicValues, dict):
        raise RuntimeError("Missing element 'mValues' in modify attributes modifier")
    # endif

    for sKey, xValue in dicValues.items():
        if not isinstance(sKey, str):
            raise RuntimeError("Invalid key type in modify attributes: {}".format(sKey))
        # endif

        lKey = sKey.split(".")
        objY = _objX
        sFinalKey = None
        lPath = [_objX.name]

        for iIdx, sSubKey in enumerate(lKey):
            if not hasattr(objY, sSubKey):
                raise RuntimeError("Object '{}' has no attribute '{}'".format(".".join(lPath), sSubKey))
            # endif

            if iIdx >= len(lKey) - 1:
                sFinalKey = sSubKey
                break
            # endif

            lPath.append(sSubKey)
            objY = getattr(objY, sSubKey)
        # endfor

        try:
            setattr(objY, sFinalKey, xValue)
        except Exception:
            raise Exception(
                "Could not set attribute '{}' of object '{}' to value: {} ".format(sKey, _objX.name, str(xValue))
            )
        # endtry
    # endfor


# enddef


################################################################################
def SetFollowPathOffset(_objX, _dicMod, **kwargs):
    """Set the offset of the Follow Path constraint of the modified object

    Configuration Args:
        fOffset (float): The offset value to set

    """
    fOffset = convert.DictElementToFloat(_dicMod, "fOffset")
    if _objX.constraints.get("Follow Path") is None:
        raise RuntimeError(f"Object '{_objX.name}' has no Follow Path constraint")
    _objX.constraints["Follow Path"].offset_factor = fOffset


################################################################################
def ParentToObject(_objX, _dicMod, **kwargs):
    """Parent object to another

    Args:
        _objX (bpy.types.Object): The object that is parented to a given object
        _dicMod (dict): A dictionary of placement parameters.

    Configuration Args:
        sParentObject (str): The name of the object to parent objX to.
        bKeepTransform (bool): Whether to keep the current absolute position of an object after parenting, or not.
        bSkipNonexistingParent (bool, optional) : Control how non existing parent target is handled. If set to true, modifier skips,
                        if set to false an error is thrown. Default behavior is throwing an error.
    """

    # Get required elements
    sParentObject = convert.DictElementToString(_dicMod, "sParentObject")
    bKeepTransform = convert.DictElementToBool(_dicMod, "bKeepTransform", bDefault=False)

    # Get optional elements
    bSkipNonexistingParent = convert.DictElementToBool(
        _dicMod,
        "bSkipNonexistingParent",
        bDefault=False,
    )

    if _objX.type == "CAMERA":
        camops.ParentAnyCam(sCamId=_objX.name, sParentId=sParentObject)

    else:
        objParent = bpy.data.objects.get(sParentObject)
        if objParent is None:
            if not bSkipNonexistingParent:
                raise RuntimeError(f"Object '{sParentObject}' not found for parenting")
            # endif
        else:
            anyobj.ParentObject(objParent, _objX, bKeepTransform=bKeepTransform)
        # endif
    # endif

    anyvl.Update()


# enddef


################################################################################
def RenameObject(_objX, _dicMod, **kwargs):
    """Rename object with regular expression

    Args:
        _objX (bpy.types.Object): The object that is parented to a given object
        _dicMod (dict): A dictionary of placement parameters.

    Configuration Args:
        sReplace (str):
            The new object name. If bUseRegEx == true, this is expected to be a
            regular expression, that can use the capture groups of the search term
            to create the new name.

        bUseRegEx (bool, optional, default=False):
            Determines whether a regular expression is used for renaming or not.
            The argument 'sSearch' is only used, if this argument is true.
            This modifier uses the python function 're.sub()'. See its' documentation
            for more information on how to use capture groups:
                https://docs.python.org/3/library/re.html

        sSearch (str, required if bUseRegEx == true):
            The regular expression search string used for regular expression replacement.
            Should define capture groups for replacement.
    """

    sName = _objX.name

    sReplace = convert.DictElementToString(_dicMod, "sReplace")
    if sReplace is None:
        raise RuntimeError("Element 'sReplace' not given in object rename modifier")
    # endif

    bUseRegEx = convert.DictElementToBool(_dicMod, "sUseRegEx", bDefault=False)

    sNewName = None
    if bUseRegEx:
        sSearch = convert.DictElementToString(_dicMod, "sSearch")
        if sSearch is None:
            raise RuntimeError("Element 'sSearch' not given in object rename modifier")
        # endif

        sNewName = re.sub(sSearch, sReplace, sName)
    else:
        sNewName = sReplace
    # endif

    _objX.name = sNewName


# enddef


################################################################################
def LogObject(_objX, _dicMod, **kwargs):
    """Log object attributes to json file

    Args:
        _objX (bpy.types.Object): The object that shall be logged
        _dicMod (dict): A dictionary of logging parameters

    Configuration Args:
        lAttributes (list):
            List of names of attributes that shall be logged

        sLogFile (str):
            The filename of the json file to be written. If not given
            or None, the attributes will be logged to the console.
    """
    lAttributes = _dicMod.get("lAttributes")

    if lAttributes is None:
        raise RuntimeError("List of object attribute names not given")
    # endif

    sLogFile = _dicMod.get("sLogFile")

    dicJson = {}

    for sAttr in lAttributes:
        # some objects do not support setting an attribute via setattr
        # but by []
        # this is handled here

        if sAttr in _objX:
            xAttribute = _objX[sAttr]
        elif hasattr(_objX, sAttr):
            xAttribute = getattr(_objX, sAttr)
        else:
            raise KeyError(f"Attribute {sAttr} not in {_objX.name}")
        # endif

        # it is assumed that xAttribute is a json parsable string like object,
        # in which case it will be converted to the respective python object
        # if this assumption does not hold, xAttribute will be directly used
        try:
            dicJson[sAttr] = json.loads(xAttribute)
        except:
            dicJson[sAttr] = xAttribute
        # end try
    # endfor

    if sLogFile is not None:
        print("=== Logging", _objX.name, " to file", sLogFile, "===")

        def default_serializer(_obj):
            return str(_obj)

        with open(sLogFile, "w") as file:
            json.dump(dicJson, file, indent=4, default=default_serializer)
        # endwith
    else:
        print("=== Logging", _objX.name, "===")
        print(dicJson)
    # endif


# enddef


################################################################################
def ExportObjectObj(_objX, _dicMod, **kwargs):
    sFilePath = convert.DictElementToString(_dicMod, "sFilePath")
    bCreatePath = convert.DictElementToBool(_dicMod, "bCreatePath", bDefault=False)
    pathFile = path.MakeNormPath(sFilePath)

    if not pathFile.is_absolute():
        pathBlend = Path(bpy.path.abspath("//"))
        pathFile = path.MakeNormPath(pathBlend / pathFile)
    # endif

    if not pathFile.parent.exists() and bCreatePath is True:
        pathFile.parent.mkdir(parents=True, exist_ok=True)
    # endif

    if not pathFile.parent.exists():
        raise RuntimeError(f"Export path for object ' {_objX.name}' does not exist: {(pathFile.parent.as_posix())}")
    # endif

    objops.ExportFromScene_Obj(pathFile, _objX)


# enddef
