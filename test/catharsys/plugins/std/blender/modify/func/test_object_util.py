#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: test_object_util.py
# Created Date: Friday, August 5th 2022, 1:47:21 pm
# Author: Fortmeier Dirk (BEG/ESD1)
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
import pytest
import json

import src.catharsys.plugins.std.blender.modify.func.object_util as object_util


def test_logging_console():
    _objX = bpy.data.objects["Cube"]

    attributes = ["name", "location"]

    dictMod = {"lAttributes": attributes}

    object_util.LogObject(_objX, dictMod)


def test_logging_file():
    _objX = bpy.data.objects["Cube"]

    attributes = ["name", "location"]

    dictMod = {"lAttributes": attributes, "sLogFile": "./dummy.json"}

    object_util.LogObject(_objX, dictMod)


def test_logging_dumped_params():
    _objX = bpy.data.objects["Cube"]

    _objX["generator_params"] = json.dumps({"color": "red"})

    attributes = [
        "generator_params",
    ]

    dictMod = {"lAttributes": attributes}

    object_util.LogObject(_objX, dictMod)


def test_missing_attrib():
    _objX = bpy.data.objects["Cube"]

    attributes = [
        "missing_attrib",
    ]

    dictMod = {"lAttributes": attributes}

    try:
        object_util.LogObject(_objX, dictMod)
    except KeyError as e:
        assert True
    # endtry
