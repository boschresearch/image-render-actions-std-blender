#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \exec_blender.py
# Created Date: Friday, May 6th 2022, 8:22:09 am
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
import shutil
import platform
from pathlib import Path

from anybase import convert, debug, config
from anybase import assertion
from anybase import path as anypath
from anybase.cls_any_error import CAnyError, CAnyError_Message, CAnyError_TaskMessage

from catharsys.setup import util, conda
import catharsys.plugins.std
import catharsys.plugins.std.blender
import catharsys.util.version as cathversion
import catharsys.util.lsf as cathlsf

from catharsys.action.cmd.ws_launch import NsKeys as NsLaunchKeys

from catharsys.config.cls_exec_lsf import CConfigExecLsf
from catharsys.plugins.std.blender.config.cls_blender import CBlenderConfig
from catharsys.plugins.std.blender.config.cls_exec_blender import CConfigExecBlender
from catharsys.plugins.std.blender.config.cls_trial_blender import CConfigTrialBlender

from catharsys.decs.decorator_ep import EntryPoint
from catharsys.decs.decorator_log import logFunctionCall
from catharsys.util.cls_entrypoint_information import CEntrypointInformation


#########################################################################################################
@EntryPoint(CEntrypointInformation.EEntryType.EXE_PLUGIN)
def StartJob(*, xPrjCfg, dicExec, dicArgs):
    try:
        try:
            pathJobConfig = dicArgs["pathJobConfig"]
            sJobName = dicArgs["sJobName"]
            sJobNameLong = dicArgs["sJobNameLong"]
            dicTrial = dicArgs["dicTrial"]
            dicDebug = dicArgs["dicDebug"]
        except KeyError as xEx:
            raise CAnyError_Message(sMsg="Blender job argument '{}' missing".format(str(xEx)))
        # endtry

        # Blender data
        dicBlender = dicTrial.get("mBlender")
        if dicBlender is None:
            raise Exception("No Blender configuration given in trial data")
        # endif

        xBlender = CConfigTrialBlender(xPrjCfg=xPrjCfg, dicBlender=dicBlender)

        if sJobNameLong is None:
            sJobNameLong = sJobName
        # endif

        xExec = CConfigExecBlender(dicExec)
        xBlenderCfg = CBlenderConfig(
            sBlenderPath=xExec.sBlenderPath,
            sBlenderVersion=xExec.sBlenderVersion,
            pathLA=xPrjCfg.pathLaunch,
            sCondaEnvName=conda.GetActiveEnvName(),
        )

        if xExec.sType == "std" or xExec.sType == "*":
            _StartBlenderWithScript(
                pathBlenderFile=xBlender.pathBlenderFile,
                xBlenderCfg=xBlenderCfg,
                dicDebug=dicDebug,
                pathJobConfig=pathJobConfig,
                bPrintOutput=True,
            )

        elif xExec.sType == "lsf":
            xLsf = CConfigExecLsf(dicExec)

            _LsfStartBlenderWithScript(
                xBlenderCfg=xBlenderCfg,
                pathBlenderFile=xBlender.pathBlenderFile,
                pathJobConfig=pathJobConfig,
                sJobName=sJobName,
                sJobNameLong=sJobNameLong,
                xLsfCfg=xLsf,
                bPrintOutput=True,
            )
        else:
            sExecFile = "?"
            if isinstance(dicExec, dict):
                sExecFile = config.GetDictValue(dicExec, "__locals__/filepath", str, bOptional=True, bAllowKeyPath=True)
            # endif

            raise CAnyError_Message(
                sMsg=(
                    f"Unsupported Blender execution type '{xExec.sType}'. "
                    f"Have a look at your execution configuration file at: {sExecFile}.\n"
                    "Maybe the default execution 'sDTI' tag is not overwritten by "
                    "a matching '__platform__' block for your current platform."
                )
            )
        # endif
    except Exception as xEx:
        raise CAnyError_TaskMessage(sTask="Start Blender Job", sMsg="Unable to start job", xChildEx=xEx)
    # endtry


# enddef


################################################################################################
# Start rendering with standard suprocess call
@logFunctionCall
def _StartBlenderWithScript(*, xBlenderCfg, pathBlenderFile, pathJobConfig, dicDebug=None, bPrintOutput=True):
    lScriptArgs = [pathJobConfig.as_posix()]

    if assertion.IsEnabled():
        lScriptArgs.append("--debug")
    # endif

    funcPostStart = None
    bBackground = True

    if dicDebug is not None:
        lScriptArgs.append("---")

        # calling cathy with e.g:  --script-vars dbg-port=portNumder option2=val2
        # every argument after --script-vars wil be split up and creates an
        # arg-pair -option val afterwards for the following script
        dicDebugScriptArgs = dicDebug.get(NsLaunchKeys.script_args, dict())
        if logFunctionCall.IsEnabled():
            dicDebugScriptArgs["log-call"] = "True"
        # endif

        for sKey, sValue in dicDebugScriptArgs.items():
            lScriptArgs.append(f"--{sKey}")
            if sValue is not None:  # it may happens and makes sense, that only keys are provided
                lScriptArgs.append(sValue)
            # endif
        # endfor

        iDebugPort = dicDebug.get(NsLaunchKeys.iDebugPort)
        if iDebugPort is not None:
            lScriptArgs.extend(["--debug-port", f"{iDebugPort}"])
        else:
            bBreak = convert.DictElementToBool(dicDebugScriptArgs, "break", bDefault=False)
            if bBreak is True:
                iDebugPort = convert.DictElementToInt(dicDebugScriptArgs, "dbg-port", iDefault=5678, bDoRaise=False)
            # endif
        # endif

        fDebugTimeout = convert.DictElementToFloat(dicDebug, NsLaunchKeys.fDebugTimeout, fDefault=10.0)

        bDebugSkipAction = dicDebug.get(NsLaunchKeys.bSkipAction)
        if bDebugSkipAction is True:
            lScriptArgs.extend(["--debug-skip-action", f"{bDebugSkipAction}"])
        # endif

        bShowGui = dicDebug.get(NsLaunchKeys.bShowGui)
        if bShowGui is not None:
            bBackground = not bShowGui
        else:
            bBackground = convert.DictElementToBool(dicDebugScriptArgs, "background", bDefault=True)
        # endif

        if iDebugPort is not None:
            funcPostStart = debug.CreateHandler_CheckDebugPortOpen(
                _fTimeoutSeconds=fDebugTimeout, _sIp="127.0.0.1", _iPort=iDebugPort
            )
        # endif

    # endif

    # Unfortunately, I cannot make Blender to output its stdout to the subprocess.Popen() pipe
    # while Blender is runnning. All stdout and stderr outputs only arrive after Blender
    # has been closed.
    # Therefore, the next best thing is to wait a couple of seconds and then output
    # some text that can be captured by the problem matcher.

    if isinstance(pathBlenderFile, Path):
        sPathBlenderFile = pathBlenderFile.as_posix()
    else:
        sPathBlenderFile = None
    # endif

    xScript = res.files(catharsys.plugins.std).joinpath("scripts").joinpath("run-action.py")
    with res.as_file(xScript) as pathScript:
        bOK, lStdOut = xBlenderCfg.ExecBlender(
            lArgs=["-noaudio"],
            sPathBlendFile=sPathBlenderFile,
            sPathScript=pathScript.as_posix(),
            lScriptArgs=lScriptArgs,
            bBackground=bBackground,
            bDoPrint=bPrintOutput,
            bDoPrintOnError=True,
            bDoReturnStdOut=True,
            sPrintPrefix="",
            funcPostStart=funcPostStart,
        )
    # endwith pathScript

    return {"bOK": bOK, "sOutput": "".join(lStdOut)}


# enddef


################################################################################################
# Start rendering blender jobs with LSF calls
@logFunctionCall
def _LsfStartBlenderWithScript(
    *,
    xBlenderCfg: CBlenderConfig,
    pathBlenderFile: Path,
    pathJobConfig: Path,
    sJobName: str,
    sJobNameLong: str,
    xLsfCfg: CConfigExecLsf,
    bPrintOutput: bool = True,
):
    # Only supported on Linux platforms
    if platform.system() != "Linux":
        raise CAnyError_Message(sMsg="Unsupported system '{}' for LSF job creation".format(platform.system()))
    # endif

    sSetBlenderPath = "export PATH={0}:$PATH".format(xBlenderCfg.sPathBlender)

    ##################################################################################
    # Copy execution script to permament place from resources
    pathCathScripts = anypath.MakeNormPath("~/.catharsys/{}/scripts".format(cathversion.MajorMinorAsString()))
    pathCathScripts.mkdir(exist_ok=True, parents=True)
    pathBlenderScript = pathCathScripts / "run-action.py"

    xScript = res.files(catharsys.plugins.std).joinpath("scripts").joinpath("run-action.py")
    with res.as_file(xScript) as pathScript:
        shutil.copy(pathScript.as_posix(), pathBlenderScript.as_posix())
    # endwith
    ##################################################################################

    sScriptArgs = pathJobConfig.as_posix()
    sScriptFile = pathBlenderScript.as_posix()
    if isinstance(pathBlenderFile, Path):
        sBlenderFile = pathBlenderFile.as_posix()
    else:
        sBlenderFile = ""
    # endif
    sBlenderUserConfig = xBlenderCfg.pathConfig.as_posix()
    sBlenderUserScripts = xBlenderCfg.pathScripts.as_posix()

    sScript = f"""
        mkdir lsf
        mkdir lsf/$LSB_BATCH_JID

        # Enable blender either by loading the corresponding module
        # or by setting a path to a Blender install.
        {sSetBlenderPath}

        echo
        echo "Starting Standard rendering jobs..."
        echo
        echo "CUDA Visible Devices: " $CUDA_VISIBLE_DEVICES

        export BLENDER_USER_CONFIG={sBlenderUserConfig}
        echo Blender User Config: $BLENDER_USER_CONFIG

        export BLENDER_USER_SCRIPTS={sBlenderUserScripts}
        echo Blender User Scripts: $BLENDER_USER_SCRIPTS

        echo "Blender file = {sBlenderFile}"
        echo "Script = {sScriptFile}"
        echo "Pars = {sScriptArgs}"

        blender -noaudio -b {sBlenderFile} -P {sScriptFile} -- {sScriptArgs}
    """

    print("Submitting job '{0}'...".format(sJobNameLong))

    bOk, lStdOut = cathlsf.Execute(
        _sJobName=sJobName, _xCfgExecLsf=xLsfCfg, _sScript=sScript, _bDoPrint=True, _bDoPrintOnError=True
    )

    return {"bOK": bOk, "sOutput": "\n".join(lStdOut)}


# enddef
