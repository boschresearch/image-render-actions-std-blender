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

import sys

if sys.version_info < (3, 10):
    import importlib_resources as res
else:
    from importlib import resources as res
# endif

import math
import time
import psutil
from pathlib import Path

from catharsys.setup import conda
from catharsys.plugins.std.blender.config.cls_blender import CBlenderConfig

# from catharsys.plugins.std.blender.config.cls_trial_blender import CConfigTrialBlender
from catharsys.plugins.std.blender.config.cls_exec_blender import CConfigExecBlender
from catharsys.config.cls_project import CProjectConfig
from catharsys.config.cls_launch import CConfigLaunch

# from catharsys.action.cls_actionfactory import CActionFactory
import catharsys.plugins.std.blender

from anybase import config, debug
from anybase.cls_anycml import CAnyCML
from anybase.cls_any_error import CAnyError_Message


############################################################################
def StartBlender(_xPrjCfg, _lExecConfigFiles, _dicArgs):

    xParser = CAnyCML()
    xBlenderCfg = None
    sTrgVersion = _dicArgs["sVersion"]
    pathLA = _xPrjCfg.pathLaunch
    pathCwd = _dicArgs.get("pathCwd", Path.cwd())

    for sExecCfgFile in _lExecConfigFiles:
        pathCfg = pathLA / sExecCfgFile
        try:
            dicExecCfg = config.Load(pathCfg)
        except Exception as xEx:
            raise CAnyError_Message(
                sMsg="Error loading launch arguments file '{}' at path: {}".format(sExecCfgFile, pathCfg.as_posix()),
                xChildEx=xEx,
            )
        # endif

        dicResult = config.CheckConfigType(dicExecCfg, "/catharsys/exec/blender/*:2.1")
        if dicResult["bOK"] is False:
            # Only consider blender execution file types
            continue
        # endif

        dicExecCfg = xParser.Process(dicExecCfg)
        xExecCfg = CConfigExecBlender(dicExecCfg)

        try:
            sBlenderVersion = xExecCfg.sBlenderVersion
            sBlenderPath = xExecCfg.sBlenderPath
        except KeyError as xEx:
            raise RuntimeError(
                "Configuration element '{}' not specified in file: {}".format(str(xEx), pathCfg.as_posix())
            )
        # endtry

        if isinstance(sTrgVersion, str) and sTrgVersion != sBlenderVersion:
            continue
        # endif

        sBlendFile = None
        if _dicArgs["sBlendFile"] is not None:
            sBlendFile = _dicArgs["sBlendFile"]
        # endif

        try:
            xBlenderCfg = CBlenderConfig(
                pathLA=pathLA,
                sBlenderPath=sBlenderPath,
                sBlenderVersion=sBlenderVersion,
                sCondaEnvName=conda.GetActiveEnvName(),
            )
        except Exception as xEx:
            raise CAnyError_Message(
                sMsg="Error initializing Blender configuration for config file '{}'".format(pathCfg.as_posix()),
                xChildEx=xEx,
            )
        # endtry

        xScript = res.files(catharsys.plugins.std.blender).joinpath("scripts").joinpath("run-blender-debug.py")
        with res.as_file(xScript) as pathScript:
            sPort = _dicArgs["sPort"]
            lScriptArgs = [
                "--port",
                sPort,
            ]

            try:
                iPort = int(sPort)
            except Exception:
                raise RuntimeError(f"Port value cannot be converted to an integer: {sPort}")
            # endtry

            lScriptArgs.extend(_dicArgs["lScriptArgs"])
            fWaitSeconds: float = _dicArgs["fWaitSeconds"]

            # Unfortunately, I cannot make Blender to output its stdout to the subprocess.Popen() pipe
            # while Blender is runnning. All stdout and stderr outputs only arrive after Blender
            # has been closed.
            # Therefore, the next best thing is to wait a couple of seconds and then output
            # some text that can be captured by the problem matcher.

            xBlenderCfg.ExecBlender(
                sCwd=pathCwd.as_posix(),
                sPathBlendFile=sBlendFile,
                # lArgs=["--log-level 2"],
                sPathScript=pathScript.as_posix(),
                lScriptArgs=lScriptArgs,
                bDoPrint=(not _dicArgs["bQuiet"]),
                bDoPrintOnError=True,
                bBackground=_dicArgs["bBackground"],
                bNoWindowFocus=True,
                funcPostStart=debug.CreateHandler_CheckDebugPortOpen(
                    _fTimeoutSeconds=fWaitSeconds, _sIp="127.0.0.1", _iPort=iPort
                ),
            )
        # endwith
        break
    # endfor blender config file

    if xBlenderCfg is None:
        print("Blender version '{}' not found in package at path: {}".format(sTrgVersion, pathLA.as_posix()))
    # endif


# enddef


############################################################################
def Start(_dicArgs):

    sPathProject = _dicArgs.get("sPathProject")
    sConfig = _dicArgs.get("sConfig")

    xPrjCfg = CProjectConfig()

    if sPathProject is None and sConfig is None:
        # Uses CWD as launch path
        xPrjCfg.FromLaunchPath(None)
    else:
        # If project path is None, uses CWD as project path
        xPrjCfg.FromConfigName(xPathMain=sPathProject, sConfigName=sConfig)
    # endif

    xLaunch = CConfigLaunch()
    try:
        xLaunch.LoadFile(xPrjCfg)
    except Exception as xEx:
        raise CAnyError_Message(sMsg=f"Error loading 'launch.*' file at path: {xPrjCfg.sLaunchPath}", xChildEx=xEx)
    # endtry

    dicActions = xLaunch.GetActionDict()
    lExecFiles = []
    for sAct in dicActions:
        sExecFile = dicActions[sAct]["mConfig"].get("sExecFile")
        if sExecFile is not None:
            lExecFiles.append(sExecFile)
        # endif
    # endfor

    StartBlender(xPrjCfg, lExecFiles, _dicArgs)


# enddef
