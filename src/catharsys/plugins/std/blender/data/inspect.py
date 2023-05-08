#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \util.py
# Created Date: Monday, May 16th 2022, 3:53:46 pm
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

import os
from importlib.metadata import entry_points as EntryPoints

from catharsys.decs.decorator_log import logFunctionCall

############################################################################################
def ExtendSysPath():
    """wenn bpy nicht gefunden wird, dann braucht python den Hinweis wo es liegen könnte.
    Weg a) PYTHONPATH erweitern:
    !!! Weg b) Weil PythonPath innerhalb von Python zwar gesetzt werden kann,
            aber eine Aenderung vollkommen ignoriert wird
            Wenn ein Module nicht gefunden wird, wird in sys.path nachgeschaut, ob man da fuendig wird.
            sys.path Aenderungen haben Einflus !!!
    """

    bBpyIncluded = False
    paths = os.path.sys.path
    for p in paths:
        if "/bpy" in p:
            bBpyIncluded = True
        # endif
    # endfor all paths

    if not bBpyIncluded:
        sBpyPath = os.path.dirname(os.path.abspath(__file__)) + "/bpy"
        logFunctionCall.PrintLog(f"extending Search-Sys-Path:{sBpyPath}")
        os.path.sys.path.append(sBpyPath)
    # endif


# enf def
# --------------------------------------------------------------------
