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

from collections import defaultdict
# import ison
from ...modify import materials as modmat

############################################################################################
def LoadMaterials(_dicMat, **kwargs):
    dicMatObj = defaultdict(list)
    dicVars = kwargs.get("dicVars", {})

    sBlenderFilename = _dicMat.get("sBlenderFilename")
    if sBlenderFilename is None:
        raise RuntimeError("Key 'sBlenderFilename' missing in load materials configuration")
    # endif

    mMaterials = _dicMat.get("mMaterials")
    if mMaterials is None:
        raise RuntimeError("Key 'mMaterials' is missing in load materials configuration")
    # endif

    # Now we load everything we actually need.
    lImportMatNames = []
    with bpy.data.libraries.load(sBlenderFilename, link=False) as (data_from, data_to):
        for sSrcMatName in mMaterials.keys():
            if sSrcMatName in data_from.materials:
                data_to.materials.append(sSrcMatName)
                lImportMatNames.append(sSrcMatName)
            # endif
        # endfor
    # endwith

    for matImport in data_to.materials:
        dicTrgMatCfg = mMaterials[matImport.name]
        sTrgMatName = dicTrgMatCfg.get("sName", matImport.name)
        matImport.name = sTrgMatName
        matImport.use_fake_user = True

        # get material modifier, if any
        lMods = dicTrgMatCfg.get("lModifiers")
        if lMods is not None:
            matTrg = bpy.data.materials[sTrgMatName]

            # Apply all modifiers to collection
            modmat.ModifyMaterial(matTrg, lMods, dicVars=dicVars)
        # endif

        dicMatObj[sTrgMatName] = ["*"]
    # endfor

    return dicMatObj


# enddef

