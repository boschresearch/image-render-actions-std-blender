#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \version.py
# Created Date: Thursday, June 2nd 2022, 11:21:05 am
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


__version__ = "3.2.1"


def AsString() -> str:
    return __version__


# enddef


def AsList() -> list:
    return __version__.split(".")


# enddef


def MajorAsString() -> str:
    return AsList()[0]


# enddef


def MajorMinorAsString() -> str:
    return ".".join(AsList()[0:2])


# enddef
