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

import bpy
import mathutils

import random

############################################################################################
def RandomizeMesh(_objX, _dicMod, **kwargs):

    sModType = _dicMod.get("sType", _dicMod.get("sDTI"))
    lMeshes = _dicMod.get("lMeshes")
    sMesh = random.choice(lMeshes)

    if sMesh not in bpy.data.meshes:
        raise Exception(
            "Mesh '{0}' not found in modifier '{1}'".format(sMesh, sModType)
        )
    _objX.data = bpy.data.meshes[sMesh]


# enddef
