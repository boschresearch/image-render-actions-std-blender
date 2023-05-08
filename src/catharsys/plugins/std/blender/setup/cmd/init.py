#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \blender.py
# Created Date: Friday, April 29th 2022, 8:15:35 am
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
g_sCmdDesc = "Initializes Blender for a render configuration (e.g. installs addons)"


####################################################################
def AddArgParseArguments(_parseArgs):

    _parseArgs.add_argument(
        "-c",
        "--config",
        nargs=1,
        dest="config",
        default=[None],
        help=(
            "Specify the configuration you want to initialize."
            "This can be a relative path from the workspace folder, or the folder name of the "
            "configuration inside the  'config' folder."
        ),
    )

    _parseArgs.add_argument(
        "-p",
        "--path",
        nargs=1,
        dest="workspace_path",
        default=[None],
        help="Defines the workspace path explicitly. Otherwise, the current working directory "
        "is assumed to be the workspace path.",
    )

    _parseArgs.add_argument(
        "--force-dist",
        dest="force_dist",
        action="store_true",
        default=False,
        help=(
            "Force an install from the Catharsys distribution modules. This is only relevant for development, "
            "if you want to test "
            "whether the distribution modules work, while the current environment is based on repositories."
        ),
    )

    _parseArgs.add_argument(
        "--force-install",
        dest="force_install",
        action="store_true",
        default=False,
        help="Forces the install of all Catharsys modules, independent of their version",
    )

    _parseArgs.add_argument(
        "--clean-addons",
        dest="clean_up_addons",
        action="store_true",
        default=False,
        help="Uninstalls all Blender addons specified in the given configuration.",
    )

    _parseArgs.add_argument(
        "--clean-all",
        dest="clean_up_all",
        action="store_true",
        default=False,
        help=(
            "Uninstalls Catharsys modules and Blender addons for the specified configuration. "
            "Note that uninstalling the Catharsys modules, "
            "removes them for all workspaces and configurations that use the same Blender version and "
            "Python environment."
        ),
    )

    _parseArgs.add_argument(
        "--addons",
        dest="addons_only",
        action="store_true",
        default=False,
        help=(
            "Only install the Blender addons specified by the configuration and not the Catharsys modules. "
            "If you just need to initialize the addons for all configs in a workspace, for a Blender install "
            "that already has all Catharsys modules installed, you can use 'cathy blender init --addons --all'"
        ),
    )

    _parseArgs.add_argument(
        "--cath-sdist",
        dest="cath_sdist",
        action="store_true",
        default=False,
        help=(
            "Force installing the Catharsys modules from the source repositories. This is the default choice "
            "if you are calling this function from a development Catharsys isntall."
        ),
    )

    _parseArgs.add_argument(
        "--all",
        dest="all_configs",
        action="store_true",
        default=False,
        help="Perform the selected operation for all configurations in the workspace.",
    )


# enddef


############################################################################
def RunCmd(_argsCmd, _lArgs):

    from catharsys.plugins.std.blender.setup.cmd import init_impl as impl
    from catharsys.setup import args

    argsSubCmd = args.ParseCmdArgs(_argsCmd=_argsCmd, _lArgs=_lArgs, _funcAddArgs=AddArgParseArguments)

    sPathProject = argsSubCmd.workspace_path[0]
    sConfig = argsSubCmd.config[0]

    impl.Init(
        sConfig=sConfig,
        sPathProject=sPathProject,
        bForceDist=argsSubCmd.force_dist,
        bForceInstall=argsSubCmd.force_install,
        bCleanUpAddOns=argsSubCmd.clean_up_addons,
        bCleanUpAll=argsSubCmd.clean_up_all,
        bAddOnsOnly=argsSubCmd.addons_only,
        bCathSourceDist=argsSubCmd.cath_sdist,
        bAllConfigs=argsSubCmd.all_configs,
    )


# enddef
