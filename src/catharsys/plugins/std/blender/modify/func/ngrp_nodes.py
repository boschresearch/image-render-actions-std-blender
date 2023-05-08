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
from anyblend.util import node
from anyblend import collection as anycln
from anyblend import object as anyobj
from anybase import convert


################################################################################
def _SetInOutValue(_ioX, _xValue, _sIoDir, _sIoName, _sNodeId, _sNgName):
    ## DEBUG
    # print(f"{_sIoDir} '{_sIoName}': {_xValue}")
    ##

    if _ioX.type == "VALUE":
        _ioX.default_value = convert.ToFloat(_xValue)

    elif _ioX.type == "OBJECT":
        sObjName = str(_xValue)
        objX = bpy.data.objects.get(sObjName)
        if objX is None:
            raise RuntimeError(
                "Object '{}' not found for {} '{}' of node '{}' of node group '{}'".format(
                    sObjName, _sIoDir, _sIoName, _sNodeId, _sNgName
                )
            )
        # endif

        # if the object is an armature, Blender throws an error, when it is referenced
        # in a geometry shader. So, we create an Empty as child to the armature and
        # reference that.
        if objX.type == "ARMATURE":
            sEmptyName = objX.name + "._origin_"
            lChildren = [x.name for x in objX.children]
            if sEmptyName not in lChildren:
                clnX = anycln.FindCollectionOfObject(bpy.context, objX)
                objE = anyobj.CreateEmpty(
                    bpy.context, objX.name + "._origin_", xCollection=clnX
                )
                anyobj.ParentObject(objX, objE, bKeepTransform=False)
                _ioX.default_value = objE
            else:
                _ioX.default_value = objX.children[sEmptyName]
            # endif
        else:
            _ioX.default_value = objX
        # endif

    elif _ioX.type == "STRING":
        _ioX.default_value = str(_xValue)

    elif _ioX.type == "VECTOR":
        if not isinstance(_xValue, list) or len(_xValue) != 3:
            raise RuntimeError(
                "{} '{}' of node '{}' of node group '{}' expects a 3-vector. "
                "Need to define a list of three elements.".format(
                    _sIoDir, _sIoName, _sNodeId, _sNgName
                )
            )
        # endif
        try:
            lValue = [convert.ToFloat(x) for x in _xValue]
            _ioX.default_value = lValue
        except Exception as xEx:
            raise RuntimeError(
                "Error setting vector property '{}' of node '{}' of node group '{}'".format(
                    _sIoName, _sNodeId, _sNgName
                )
            )
        # endtry
    else:
        raise RuntimeError(
            "{0} of type '{1}' for {0} '{2}' of node '{3}' of node group '{4}' not supported".format(
                _sIoDir, _ioX.type, _sIoName, _sNodeId, _sNgName
            )
        )
    # endif


# enddef


################################################################################
def SetNodeValues(_ngX, _dicMod, **kwargs):
    """Set input, output and property values of nodes.

    Args:
        _ngX (bpy.types.NodeGroup): The node group whose nodes are to be modified.
        _dicMod (dict): The configuration parameters (see below).

    Raises:
        RuntimeError: Raises exception if values cannot be set.

    Configuration Args:
        sNode (string): The label or name of the node.
        lInputs (list): List of dictionaries that define input values.
        lOutputs (list): List of dictionaries that define output values.
        lProperties (list): List of dictionaries that define property values.

    "lInputs", "lOutputs" element args:
        "sName" (string): Name of the input/output.
        "xValue" (string, list, value): Value of the input/output.
                Has to be a list of three elements for vectors.
                Has to be a string for objects.

    "lProperties" element args:
        "sName" (string): Name of the property. For example, for a "Math" node,
                            the "operation" property can be set to determine which
                            mathematical operation is performed. Properties are
                            typically strings all in uppercase letters (enums).
        "sValue" (string): Value of string property.
        "xValue" (string, int, float, bool): Value of property.

    "mImage" (dictionary): Property of an image to use with the node.
                            This can only be used for nodes that actually support
                            images, like the "Image Texture" and "Environment Texture" nodes.
                            Possible elements of dictionary are:

        "sType" (string"): Type of image. Currently, has to be one of ["LOAD", "SELECT"].
            Type "LOAD":
                "sName" (string): Filepath to an image to load and use as image for this node.

            Type "SELECT":
                "sName" (string): Name of an image that is already available in the Blender file.
    """
    # Get required elements
    try:
        sNodeId = _dicMod["sNode"]
    except KeyError as xEx:
        raise RuntimeError(
            "Configuration element {} missing for setting node values".format(str(xEx))
        )
    # endtry

    ndX = node.GetByLabelOrId(_ngX, sNodeId)
    if ndX is None:
        raise RuntimeError(
            "Node {} not found in node group {}".format(sNodeId, _ngX.name)
        )
    # endif

    # Optional elements
    lCfgIn = _dicMod.get("lInputs", [])
    lCfgOut = _dicMod.get("lOutputs", [])
    lCfgProp = _dicMod.get("lProperties", [])
    dicImage = _dicMod.get("mImage")

    for dicCfg in lCfgIn:
        try:
            sName = dicCfg["sName"]
            xValue = dicCfg["xValue"]
        except KeyError as xEx:
            raise RuntimeError(
                "Node input configuration element '{}' missing for node '{}' in node group '{}'".format(
                    str(xEx), sNodeId, _ngX.name
                )
            )
        # endtry

        ioX = ndX.inputs.get(sName)
        if ioX is None:
            raise RuntimeError(
                "Input '{}' of node '{}' of node group '{}' not found".format(
                    sName, sNodeId, _ngX.name
                )
            )
        # endif

        _SetInOutValue(ioX, xValue, "input", sName, sNodeId, _ngX.name)
    # endfor

    for dicCfg in lCfgOut:
        try:
            sName = dicCfg["sName"]
            xValue = dicCfg["xValue"]
        except KeyError as xEx:
            raise RuntimeError(
                "Node output configuration element '{}' missing for node '{}' in node group '{}'".format(
                    str(xEx), sNodeId, _ngX.name
                )
            )
        # endtry

        ioX = ndX.outputs.get(sName)
        if ioX is None:
            raise RuntimeError(
                "Output '{}' of node '{}' of node group '{}' not found".format(
                    sName, sNodeId, _ngX.name
                )
            )
        # endif

        _SetInOutValue(ioX, xValue, "output", sName, sNodeId, _ngX.name)
    # endfor

    for dicCfg in lCfgProp:
        try:
            sName = dicCfg["sName"]
            xValue = dicCfg.get("sValue")
            if xValue is None:
                xValue = dicCfg["xValue"]
            # endif
        except KeyError as xEx:
            raise RuntimeError(
                "Node property configuration element '{}' missing for node '{}' in node group '{}'".format(
                    str(xEx), sNodeId, _ngX.name
                )
            )
        # endtry

        try:
            xProp = getattr(ndX, sName)
        except Exception as xEx:
            raise RuntimeError(
                "Property '{}' of node '{}' of node group '{}' does not exist.\n{}".format(
                    sName, sNodeId, _ngX.name, str(xEx)
                )
            )
        # endtry

        try:
            if isinstance(xProp, str):
                xCastValue = convert.ToString(xValue)

            elif isinstance(xProp, int):
                xCastValue = convert.ToInt(xValue)

            elif isinstance(xProp, float):
                xCastValue = convert.ToFloat(xValue)

            elif isinstance(xProp, bool):
                xCastValue = convert.ToBool(xValue)

            else:
                raise RuntimeError("Unsupported property type")
            # endif

            setattr(ndX, sName, xCastValue)
        except Exception as xEx:
            raise RuntimeError(
                "Error setting property '{}' of node '{}' of node group '{}' to value '{}'.\n{}".format(
                    sName, sNodeId, _ngX.name, str(xValue), str(xEx)
                )
            )
        # endif
    # endfor

    if dicImage is not None:

        if ndX.type not in ["TEX_ENVIRONMENT", "TEX_IMAGE"]:
            raise RuntimeError(
                "An image cannot be specified for node '{}' of type '{}'".format(
                    sNodeId, ndX.type
                )
            )
        # endif

        sType = dicImage.get("sType")
        if sType is None:
            raise RuntimeError(
                "Element 'sType' not specified for image dictionary for node '{}'".format(
                    sNodeId
                )
            )
        # endif

        sName = dicImage.get("sName")
        if not isinstance("sName", str):
            raise RuntimeError(
                "Element 'sName' for image specification of node '{}' is not given or not a string".format(
                    sNodeId
                )
            )
        # endif

        if sType == "LOAD":
            try:
                imgX = bpy.data.images.load(filepath=sName)
            except Exception as xEx:
                raise Exception(
                    "Error loading image for node '{0}' from path '{1}':\n{2}".format(
                        sNodeId, sName, str(xEx)
                    )
                )
            # endtry

            ndX.image = imgX

        elif sType == "SELECT":
            lImgNames = [x.name for x in bpy.data.images]
            if sName not in lImgNames:
                raise RuntimeError(
                    "Image '{}' not found in Blender file for node '{}'".format(
                        sName, sNodeId
                    )
                )
            # endif

            ndX.image = bpy.data.images[sName]

        else:
            raise RuntimeError(
                "Invalid image specification type '{}' for node '{}'".format(
                    sType, sNodeId
                )
            )
        # endif image spec type
    # endif has image spec


# enddef
