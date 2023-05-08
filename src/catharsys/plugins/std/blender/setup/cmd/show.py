#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \start.py
# Created Date: Thursday, May 5th 2022, 11:51:37 am
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


g_sCmdDesc = "Starts Blender for a given workspace configuration and action"


####################################################################
def AddArgParseArguments(_parseArgs):

    _parseArgs.add_argument("-a", "--action", nargs=1, dest="action", default=[None])
    _parseArgs.add_argument("-c", "--config", nargs=1, dest="config", default=[None])
    _parseArgs.add_argument("-p", "--path", nargs=1, dest="workspace_path", default=[None])
    _parseArgs.add_argument("-v", "--version", nargs=1, dest="version", default=[None])
    _parseArgs.add_argument("-f", "--blender-file", nargs=1, dest="blend_file", default=[None])
    _parseArgs.add_argument("-P", "--python-script", nargs=1, dest="script", default=[None])
    _parseArgs.add_argument("-s", "--script-args", nargs="*", dest="script_args", default=[])
    _parseArgs.add_argument("-b", "--background", dest="background", action="store_true", default=False)
    _parseArgs.add_argument("-q", "--quiet", dest="quiet", action="store_true", default=False)


# enddef


####################################################################
def RunCmd(_argsCmd, _lArgs):
    from pathlib import Path
    from . import show_impl as impl
    from catharsys.setup import args

    argsSubCmd = args.ParseCmdArgs(_argsCmd=_argsCmd, _lArgs=_lArgs, _funcAddArgs=AddArgParseArguments)

    dicArgs = {}

    dicArgs["sPathProject"] = argsSubCmd.workspace_path[0]
    dicArgs["sConfig"] = argsSubCmd.config[0]
    dicArgs["sVersion"] = argsSubCmd.version[0]
    dicArgs["sAction"] = argsSubCmd.action[0]
    dicArgs["sBlendFile"] = argsSubCmd.blend_file[0]
    dicArgs["sPathScript"] = argsSubCmd.script[0]
    dicArgs["lScriptArgs"] = argsSubCmd.script_args
    dicArgs["bBackground"] = argsSubCmd.background
    dicArgs["bQuiet"] = argsSubCmd.quiet

    dicArgs["pathCwd"] = Path.cwd()

    impl.Start(dicArgs)


# enddef
