#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \data\arm_modify.py
# Created Date: Thursday, September 16th 2021, 8:12:19 am
# Author: Dirk Fortmeier (BEG/ESD1)
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

from typing import Any
import bpy
import re
from anybase import convert


############################################################################################
def ApplyPoseFromFile(
    armature_dst, sBlenderFilename, sPosename, lBones=[".*"], fWeight=1.0, bMirror=False
):

    with bpy.data.libraries.load(sBlenderFilename, link=False) as (data_from, data_to):
        if sPosename in data_from.objects:
            data_to.objects.append(sPosename)
        else:
            raise RuntimeError(
                "Object of name {} not found in {}".format(sPosename, sBlenderFilename)
            )
        # endif
    # endwith

    armature_src = data_to.objects[0]

    # print("posing from {}".format(sBlenderFilename))

    for sBoneExpr in lBones:
        # print(sBoneExpr)
        for sBone in armature_src.pose.bones:
            sBoneName = sBone.name

            if re.match(sBoneExpr, sBoneName):
                # print(" ... match with {}".format(sBoneName))

                bone_source = armature_src.pose.bones[sBoneName]

                if bMirror:
                    if sBoneName[-2:] == ".L":
                        sBoneName = sBoneName[0:-2] + ".R"
                    elif sBoneName[-2:] == ".R":
                        sBoneName = sBoneName[0:-2] + ".L"
                try:
                    bone_target = armature_dst.pose.bones[sBoneName]
                except KeyError:
                    print(
                        "Warning: bone {} not in destination armature".format(sBoneName)
                    )
                    continue
                # endtry

                bone_target.rotation_mode = "QUATERNION"
                bone_source.rotation_mode = "QUATERNION"

                if bMirror:
                    bone_source.rotation_quaternion.y *= -1.0
                    bone_source.rotation_quaternion.z *= -1.0

                # print(" - old orientation: {}".format(bone_target.rotation_quaternion))
                # print(" - src orientation: {}".format(bone_source.rotation_quaternion))

                q1 = bone_target.rotation_quaternion
                q2 = bone_source.rotation_quaternion
                bone_target.rotation_quaternion = q1.slerp(q2, fWeight)
                # print(" - dst orientation: {}".format(bone_target.rotation_quaternion))
            # endif
        # endfor
    # endfor


# enddef

############################################################################################
def Posing(_objX: bpy.types.Object, _dicMod: dict[str, Any], **kwargs: Any) -> None:

    if "lPoseFiles" in _dicMod:
        mPoseConfig: dict[str, Any]
        for mPoseConfig in _dicMod["lPoseFiles"]:
            if "sBlenderFilename" not in mPoseConfig:
                raise Exception(
                    "sBlenderFilename not given for posing of '{}'".format(_objX.name)
                )
            # endif
            sBlenderFilename: str = convert.DictElementToString(mPoseConfig, "sBlenderFilename")

            if "sPosename" not in mPoseConfig:
                raise Exception(
                    "sPosename not given for posing of '{}'".format(_objX.name)
                )
            # endif

            sPosename: str = convert.DictElementToString(mPoseConfig, "sPosename")

            lBones: list[str] = convert.DictElementToStringList(mPoseConfig, "lBones", lDefault=[".*"])
            fWeight: float = convert.DictElementToFloat(mPoseConfig, "fWeight", 1.0)
            bMirror: bool = convert.DictElementToBool(mPoseConfig, "bMirror", False)

            ApplyPoseFromFile(
                _objX, sBlenderFilename, sPosename, lBones, fWeight, bMirror
            )
        # endfor
    else:
        raise Exception(
            f"No 'lPoseFiles' element given for posing of '{_objX.name}'"
        )
    # endif


# enddef
