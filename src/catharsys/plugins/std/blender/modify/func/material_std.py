#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /manifest.py
# Created Date: Thursday, September 6th 2021
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

import os
import re
import bpy

from anybase import path
from anyblend import util
from . import ngrp_nodes

##################################################################################
def _DoSetTexture(_xNode, _sImgId, _sRemoveImgId):

    # Set the texture image
    if _sImgId is None:
        _xNode.image = None
    elif _sImgId in bpy.data.images:
        _xNode.image = bpy.data.images[_sImgId]
    else:
        raise Exception("Image '{0}' not available in blender file".format(_sImgId))
    # endif

    if _sRemoveImgId is not None and _sRemoveImgId in bpy.data.images and bpy.data.images[_sRemoveImgId].users == 0:
        bpy.data.images.remove(bpy.data.images[_sRemoveImgId])
    # endif


# enddef


##################################################################################
def _DoSetMaterial(_objectX, _slotId, _destMaterial):
    _objectX.material_slots[_slotId].material = _destMaterial


# enddef


##################################################################################
def SetTexturesFromFolder(_matX, _dicMod, **kwargs):

    sTexPath = _dicMod.get("sTexPath")
    if sTexPath is None:
        raise Exception("Textures from folder material modifier misses 'sTexPath' parameter")
    # endif
    sTexPath = path.NormPath(sTexPath)

    sRePath = _dicMod.get("sRePath")

    lNodeTexFileMap = _dicMod.get("lNodeTexFileMap")
    if lNodeTexFileMap is None:
        raise Exception("Textures from folder material modifier misses 'lNodeTexFileMap' parameter")
    # endif

    xMatch = None
    if sRePath is not None:
        xMatch = re.search(sRePath, sTexPath)
        if xMatch is None:
            raise Exception("Pattern '{0}' not found in path '{1}'".format(sRePath, sTexPath))
        # endif
    # endif

    reRep = re.compile(r"\\(\d+)")

    for lTexFile in lNodeTexFileMap:
        sNode = lTexFile[0]
        sFile = lTexFile[1]

        if sRePath is None:
            sFileTex = sFile

        else:
            # Replace elements \1, \2, etc. in the filename
            # with the capture groups of the folder.
            iStart = 0
            sFileTex = ""
            for xRep in reRep.finditer(sFile):
                sFileTex += sFile[iStart : xRep.start()]
                iIdx = int(xRep.group(1))
                sFileTex += xMatch.group(iIdx)
                iStart = xRep.end()
            # endfor
            sFileTex += sFile[iStart:]
        # endif
        sFpTex = path.NormPath(os.path.join(sTexPath, sFileTex))

        # Find node in material node tree, either by id or by label
        xNode = util.node.GetByLabelOrId(_matX.node_tree, sNode)
        if xNode is None:
            raise Exception("Node with id or label '{0}' not found in material '{1}'".format(sNode, _matX.name))
        # endif

        # Check whether given node is an image texture node
        if xNode.type != "TEX_IMAGE":
            raise Exception("Node '{0}' of material '{1}' is not an image texture node".format(sNode, _matX.name))
        # endif

        # See if image is already available in blend file
        imgTex = bpy.data.images.get(sFileTex)
        if imgTex is None:
            try:
                imgTex = bpy.data.images.load(filepath=sFpTex)
            except Exception as xEx:
                raise Exception(
                    "Error loading texture for node '{0}' from path '{1}':\n{2}".format(sNode, sFpTex, str(xEx))
                )
            # endtry
        # endif

        if xNode.image is None:
            sFileOrigTex = None
        else:
            sFileOrigTex = xNode.image.name
        # endif

        _DoSetTexture(xNode, sFileTex, None)
    # endfor


# enddef


##################################################################################
def SwapMaterial(_matX, _dicMod, **kwargs):

    sMode = kwargs.get("sMode", "INIT")
    sDestMaterialName = _dicMod.get("sMaterial")

    if sDestMaterialName is None:
        raise Exception("Material to replace not set ('sMaterial' not set)")

    for objectX in bpy.data.objects:
        # replace in all objects
        # TODO make selectable by regexp or list of object names
        bMatchedName = True
        if bMatchedName:
            for (slotId, materialSlot) in enumerate(objectX.material_slots):
                if materialSlot.name == sDestMaterialName:

                    # prevent old material from being purged accidentally
                    # between this call and the call of the revert modifier
                    bResetFakeUser = not materialSlot.material.use_fake_user

                    if sMode == "INIT":

                        def RevertModifier(objectX, slotId, material, bResetFakeUser):
                            def func():
                                _DoSetMaterial(objectX, slotId, material)
                                if bResetFakeUser:
                                    material.use_fake_user = False

                            # enddef
                            return func

                        # enddef

                    # endif

                    materialSlot.material.use_fake_user = True

                    _DoSetMaterial(objectX, slotId, _matX)

                    # print(objectX, slotId, _matX)
                # endif
            # endfor
        # endif
    # endfor


# enddef


##################################################################################
def SetNodeValues(_matX, _dicMod, **kwargs):

    sMode = kwargs.get("sMode", "INIT")
    dicVars = kwargs.get("dicVars", {})

    ngrp_nodes.SetNodeValues(_matX.node_tree, _dicMod, sMode=sMode, dicVars=dicVars)


# enddef
