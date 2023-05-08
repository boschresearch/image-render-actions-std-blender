#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \object.py
# Created Date: Thursday, October 6th 2022, 4:12:15 pm
# Created by: Christian Perwass (CR/AEC5)
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


############################################################################################
def GetWorldMatrix(_sObjId, *, sType, sConvention="default"):

    objX = bpy.data.objects.get(_sObjId)
    if objX is None:
        raise Exception("Object with id '{0}' not found".format(_sObjId))
    # endif

    matObj = objX.matrix_world

    if sConvention == "rbcv":
        # transform rotation matrix to RB-computer vision convention,
        # where X-axis points right, y-axis down and z-axis forward into the scene.
        matRotX = mathutils.Matrix([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]])
        matObj = matObj @ matRotX
    elif sConvention != "default":
        raise Exception("World matrix convention '{0}' is not supported.".format(sConvention))
    # endif

    xResult = None
    if sType == "matrix":
        xResult = [[c for c in r] for r in matObj]

    elif sType == "decomposed":
        tParts = matObj.decompose()
        xResult = {
            "lMatrix": [[c for c in r] for r in matObj],
            "lTrans": [x for x in tParts[0]],
            "lRot": [x for x in tParts[1]],
            "lScale": [x for x in tParts[2]],
        }
    else:
        raise Exception("Unsupported return type '{0}'.".format(sType))
    # endif

    return xResult


# enddef
