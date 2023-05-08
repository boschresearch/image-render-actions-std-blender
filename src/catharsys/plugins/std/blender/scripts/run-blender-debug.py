#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \run-blender-debug.py
# Created Date: Tuesday, December 20th 2022, 8:57:59 am
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

try:
    import _bpy
    import bpy
except Exception:
    print("Script has to be run from within blender.")
# endtry

import sys
import argparse

from pathlib import Path
from anybase.debug import ExtendPathForDebugPy

import catharsys.decs.decorator_log as logging_dec


################################################################################################################
# Parse Arguments
parseMain = argparse.ArgumentParser(
    prog="cathy blender debug", description="Catharsys Blender debugging", exit_on_error=False
)
parseMain.add_argument("-p", "--port", dest="port", nargs=1, default=[None])

# Default Values
iDebugPort: int = 5678

# Parse
if "--" in sys.argv:
    lArgs = sys.argv[sys.argv.index("--") + 1 :]
    argsMain = parseMain.parse_args(lArgs)

    sValue = argsMain.port[0]
    if sValue is not None:
        try:
            iDebugPort = int(argsMain.port[0])
        except Exception:
            raise RuntimeError("Debug port argument 'port' has to be an integer")
        # endtry
    # endif

# endif has arguments

################################################################################################################
# Start Debug
ExtendPathForDebugPy()
try:
    import debugpy
except Exception as xEx:
    raise RuntimeError(f"Error importing 'debugpy': {(str(xEx))}")
# endtry

logging_dec.logFunctionCall.PrintLog(f"Blender waits for attaching debugger on port '{iDebugPort}'")

debugpy.listen(iDebugPort)
print("Waiting for debugger attach...")
debugpy.wait_for_client()
debugpy.breakpoint()
print("Now you can call every python script and set breakpoints in Visual Code and watch variables")
