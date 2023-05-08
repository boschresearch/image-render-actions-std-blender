#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /install.py
# Created Date: Thursday, June 2nd 2022, 8:48:09 am
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


############################################################################
# Module Variables
g_sCmdDesc = "Installs Blender from a package file and necessary Catharsys modules in Blender python"


####################################################################
def AddArgParseArguments(_parseArgs):
    _parseArgs.add_argument("zip_file", nargs=1)
    _parseArgs.add_argument("--force-dist", dest="force_dist", action="store_true", default=False)
    _parseArgs.add_argument("--force", dest="force_install", action="store_true", default=False)
    _parseArgs.add_argument("--no-cath-install", dest="no_cath_install", action="store_true", default=False)
    _parseArgs.add_argument("--cath-sdist", dest="cath_sdist", action="store_true", default=False)


# enddef


############################################################################
def RunCmd(_argsCmd, _lArgs):
    from pathlib import Path
    from . import install_impl as impl
    from catharsys.setup import args

    argsSubCmd = args.ParseCmdArgs(_argsCmd=_argsCmd, _lArgs=_lArgs, _funcAddArgs=AddArgParseArguments)

    impl.InstallBlenderPackage(
        pathZip=Path(argsSubCmd.zip_file[0]),
        bForceDist=argsSubCmd.force_dist,
        bForceInstall=argsSubCmd.force_install,
        bNoCathInstall=argsSubCmd.no_cath_install,
        bCathSourceDist=argsSubCmd.cath_sdist,
    )


# enddef
