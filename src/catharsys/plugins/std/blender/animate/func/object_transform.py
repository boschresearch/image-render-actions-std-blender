#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /rotate.py
# Created Date: Thursday, October 22nd 2020, 1:20:22 pm
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
import mathutils

from anybase.cls_any_error import CAnyError_Message
from anybase import convert
from catharsys.decs.decorator_ep import EntryPoint
from catharsys.util.cls_entrypoint_information import CEntrypointInformation

from catharsys.decs.decorator_log import logFunctionCall


@EntryPoint(CEntrypointInformation.EEntryType.ANIMATION)
def AnimRotConstRate(_sOrigName, _dicAnim):
    """
    <node>
        sDTI:{ value:"blender/animate/object/rotate/const:1", type="label", hint="entry point identification" },
        dDegPerSec:{ value="720", type="float", hint="degree per second", display="Degrees per Scond"},
        lAxis:{ value="0, 0, 1", type="float", vector="vec3", display="rotation axis",
                hint="the object will rotate arround that axis by setting bpy_obj.delta_rotation_euler" }
    <node/>

    """
    try:
        if "dDegPerSec" in _dicAnim:
            fDegPerSec = convert.DictElementToFloat(_dicAnim, "dDegPerSec")
        else:
            fDegPerSec = convert.DictElementToFloat(_dicAnim, "fDegPerSec")
        # endif

        lAxis = convert.DictElementToFloatList(_dicAnim, "lAxis", iLen=3)

        @logFunctionCall
        def handler(xScene, xDepsGraph):
            objOrig = bpy.data.objects.get(_sOrigName)
            if objOrig is None:
                return
            # endif

            dTime_s = xScene.frame_current * xScene.render.fps_base / xScene.render.fps
            dAngle_deg = dTime_s * fDegPerSec

            objOrig.delta_rotation_euler = mathutils.Matrix.Rotation(
                math.radians(dAngle_deg), 4, mathutils.Vector(lAxis)
            ).to_euler()

        # enddef

        return {"handler": handler}
    except Exception as xEx:
        raise CAnyError_Message(sMsg="Error initializing constant rotation animation handler", xChildEx=xEx)
    # endtry


# enddef


@EntryPoint(CEntrypointInformation.EEntryType.ANIMATION)
def AnimTranslateConstSpeed(_sOrigName, _dicAnim):

    try:
        fSpeed = convert.DictElementToFloat(_dicAnim, "fSpeed")
        fOffset_m = convert.DictElementToFloat(_dicAnim, "fOffset_m", fDefault=0.0)
        sSpeedUnit = convert.DictElementToString(_dicAnim, "sSpeedUnit", sDefault="m/s")
        lDir = convert.DictElementToFloatList(_dicAnim, "lDir", iLen=3)

        fSpeed_ms = None
        if sSpeedUnit == "m/s":
            fSpeed_ms = fSpeed
        elif sSpeedUnit == "km/h":
            fSpeed_ms = fSpeed / 3.6
        else:
            raise RuntimeError(f"Invalid unit '{sSpeedUnit}' for constant translation animation")
        # endif

        vDir = mathutils.Vector(lDir)
        vDir.normalize()

        @logFunctionCall
        def handler(xScene, xDepsGraph):
            objOrig = bpy.data.objects.get(_sOrigName)
            if objOrig is None:
                return
            # endif

            fTime_s = xScene.frame_current * xScene.render.fps_base / xScene.render.fps
            fDist_m = fTime_s * fSpeed_ms + fOffset_m
            objOrig.delta_location = fDist_m * vDir

        # enddef

        return {"handler": handler}
    except Exception as xEx:
        raise CAnyError_Message(sMsg="Error initializing constant translation animation handler", xChildEx=xEx)
    # endtry


# enddef
