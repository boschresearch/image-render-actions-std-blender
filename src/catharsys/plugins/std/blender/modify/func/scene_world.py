#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /obj.py
# Created Date: Thursday, September 08, 2021
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
import math
from anyblend.util import node
from .. import nodegroups

############################################################################################
def SetHdriWorld(_scnX, _dicMod, **kwargs):

    sMode = kwargs.get("sMode", "INIT")
    dicVars = kwargs.get("dicVars", {})
    sWorldId = _dicMod.get("sId")
    lNodeHdrImageMap = _dicMod.get("lNodeHdrImageMap")
    lRot_deg = _dicMod.get("lRotation_deg")
    lLocation = _dicMod.get("lLocation")
    lModifyNodes = _dicMod.get("lModifyNodes")

    if sWorldId is None:
        raise Exception("No element 'sId' given for world settings")
    # endif

    xWorld = bpy.data.worlds.get(sWorldId)
    if xWorld is None:
        raise Exception("World with id '{0}' not found".format(sWorldId))
    # endif

    xModWorld = None
    lHdrImages = []

    if lRot_deg is not None or lNodeHdrImageMap is not None or lModifyNodes is not None:

        # Copy the original world to modify it
        if sMode == "INIT":
            xModWorld = xWorld.copy()
        else:
            xModWorld = xWorld
        # endif

        for lNodeHdr in lNodeHdrImageMap:
            sNode = lNodeHdr[0]
            sFpHdr = lNodeHdr[1]

            # Find node in material node tree, either by id or by label
            xNode = node.GetByIdOrLabel(xModWorld.node_tree, sNode)
            if xNode is None:
                raise Exception("Node with id or label '{0}' not found in world '{1}'".format(sNode, xModWorld.name))
            # endif

            # Check whether given node is an image texture node
            if xNode.type != "TEX_ENVIRONMENT":
                raise Exception(
                    "Node '{0}' of material '{1}' is not an environment texture node".format(sNode, xModWorld.name)
                )
            # endif

            try:
                imgHdr = bpy.data.images.load(filepath=sFpHdr)
            except Exception as xEx:
                raise Exception(
                    "Error loading environment texture for node '{0}' from path '{1}':\n{2}".format(
                        sNode, sFpHdr, str(xEx)
                    )
                )
            # endtry

            xNode.image = imgHdr
            lHdrImages.append(imgHdr.name)

        # endfor Node HDR image map

        if lRot_deg is not None:
            xNode = node.GetByIdOrLabel(xModWorld.node_tree, "Mapping")
            if xNode is None:
                raise Exception("Mapping node not available in world shader '{0}' to set rotation".format(sWorldId))
            elif xNode.type != "MAPPING":
                raise Exception("The node with name 'Mapping' is not a mapping node")
            # endif

            lRot_rad = [math.radians(x) for x in lRot_deg]
            xNode.inputs[2].default_value = lRot_rad
        # endif

        if lLocation is not None:
            xNode = node.GetByIdOrLabel(xModWorld.node_tree, "Mapping")
            if xNode is None:
                raise Exception("Mapping node not available in world shader '{0}' to set location".format(sWorldId))
            elif xNode.type != "MAPPING":
                raise Exception("The node with name 'Mapping' is not a mapping node")
            # endif

            xNode.inputs[1].default_value = lLocation
        # endif

        if lModifyNodes is not None:
            nodegroups.ModifyNodeTree(xModWorld.node_tree, lModifyNodes, sMode=sMode, dicVars=dicVars)
        # endif

        _scnX.world = xModWorld
    else:

        _scnX.world = xWorld
    # endif world is modified


# enddef


############################################################################################
def SetWorld(_scnX, _dicMod, **kwargs):

    sMode = kwargs.get("sMode", "INIT")
    # dicVars = kwargs.get("dicVars", {})
    sWorldId = _dicMod.get("sId")

    if sWorldId is None:
        raise RuntimeError("No element 'sId' given for world settings")
    # endif

    xWorld = bpy.data.worlds.get(sWorldId)
    if xWorld is None:
        raise RuntimeError("World with id '{0}' not found".format(sWorldId))
    # endif

    _scnX.world = xWorld


# enddef


##################################################################################
def SetWorldNodeValues(_scnX, _dicMod, **kwargs):

    sMode = kwargs.get("sMode", "INIT")
    dicVars = kwargs.get("dicVars", {})

    lModifyNodes = _dicMod.get("lModifyNodes")
    if lModifyNodes is not None:
        nodegroups.ModifyNodeTree(_scnX.world.node_tree, lModifyNodes, sMode=sMode, dicVars=dicVars)
    # endif


# enddef
