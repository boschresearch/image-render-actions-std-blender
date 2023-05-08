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

from pathlib import Path

from catharsys.setup import util, conda
from catharsys.plugins.std.blender.config.cls_blender import CBlenderConfig
from catharsys.plugins.std.blender.config.cls_trial_blender import CConfigTrialBlender
from catharsys.plugins.std.blender.config.cls_exec_blender import CConfigExecBlender
from catharsys.config.cls_project import CProjectConfig
from catharsys.config.cls_launch import CConfigLaunch
from catharsys.action.cls_actionfactory import CActionFactory

from anybase import config
from anybase.cls_anycml import CAnyCML
from anybase.cls_any_error import CAnyError, CAnyError_Message


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

        # If no Blender file is given but an action name, then retrieve the
        # Blender filename from the appropriate trial configuration.
        sBlendFile = None
        if _dicArgs["sBlendFile"] is None and isinstance(_dicArgs["sAction"], str):
            xActFac = CActionFactory(xPrjCfg=_xPrjCfg)
            xAction = xActFac.CreateAction(sAction=_dicArgs["sAction"])
            xAction.Init()
            dicBlender = xAction.dicTrial.get("mBlender")
            if dicBlender is None:
                raise CAnyError_Message(
                    sMsg="No Blender configuration in trial for action '{}'".format(_dicArgs["sAction"])
                )
            # endif

            xBlender = CConfigTrialBlender(xPrjCfg=_xPrjCfg, dicBlender=dicBlender)
            sBlendFile = xBlender.pathBlenderFile.as_posix()

        else:
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

        xBlenderCfg.ExecBlender(
            sCwd=pathCwd.as_posix(),
            sPathBlendFile=sBlendFile,
            sPathScript=_dicArgs["sPathScript"],
            lScriptArgs=_dicArgs["lScriptArgs"],
            bDoPrint=(not _dicArgs["bQuiet"]),
            bDoPrintOnError=True,
            bBackground=_dicArgs["bBackground"],
        )
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
