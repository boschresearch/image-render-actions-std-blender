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

import re
import sys
import json
import tempfile
import importlib
import pip
import shutil
from pathlib import Path
from packaging import version

if sys.version_info < (3, 10):
    import importlib_resources as res
else:
    from importlib import resources as res
# endif

import catharsys.setup
from catharsys.setup import util, module, conda
from catharsys.plugins.std.blender.config.cls_blender import CBlenderConfig
from catharsys.plugins.std.blender.config.cls_exec_blender import CConfigExecBlender
from catharsys.config.cls_project import CProjectConfig
from catharsys.config.cls_launch import CConfigLaunch
from catharsys.api.cls_workspace import CWorkspace
from anybase import config, link
from anybase import util as anyutil
from anybase.cls_anycml import CAnyCML
from anybase.cls_any_error import CAnyError, CAnyError_Message


############################################################################
g_rePyVer = re.compile(r"(\d+\.\d+\.\d+)")


############################################################################
def LoadDefaultBlenderSettings(*, xBlenderCfg, sPrintPrefix=""):
    reSetVer = re.compile(r"(\d+)-(\d+)\.json5")

    dicSet = None
    xMatch = re.match(r"(\d+).(\d+)", xBlenderCfg.sVersion)
    if xMatch is not None:
        tVer = (int(xMatch.group(1)), int(xMatch.group(2)))
        dicCandidates = {}

        # Load default Blender settings
        xData = res.files(catharsys.plugins.std.blender).joinpath("data")
        with xData as pathData:
            for pathFile in pathData.iterdir():
                xMatch = reSetVer.search(pathFile.name)
                if xMatch is not None:
                    # check whether major version of Blender is equal to major version of settings file
                    if int(xMatch.group(1)) == tVer[0]:
                        iVerMin = int(xMatch.group(2))
                        dicCandidates[iVerMin] = pathFile
                    # endif
                # endif
            # endfor

            # Look for the highest minor version of all settings candidates
            pathFile = None
            iTestVerMin = tVer[1]
            while iTestVerMin >= 0:
                pathFile = dicCandidates.get(iTestVerMin)
                if pathFile is not None:
                    break
                # endif
                iTestVerMin -= 1
            # endwhile

            if pathFile is not None:
                with res.as_file(pathFile) as pathDefSet:
                    print(sPrintPrefix + "Using default blender settings: {}".format(pathDefSet.name))
                    dicSet = config.Load(pathDefSet, sDTI="/catharsys/blender/settings:1")
                # endwith
            else:
                print(
                    sPrintPrefix
                    + "WARNING: No default Blender settings found for version {}".format(xBlenderCfg.sVersion)
                )
            # endif
        # endwith
    # endif

    if dicSet is None:
        dicSet = {}
    # endif

    return dicSet


# enddef


############################################################################
def ConfigureBlender(*, xBlenderCfg, dicSettings, sPrintPrefix=""):
    print("\n" + sPrintPrefix + "=================================================================")
    print(sPrintPrefix + "Configuring Blender...")

    dicSet = LoadDefaultBlenderSettings(xBlenderCfg=xBlenderCfg, sPrintPrefix=sPrintPrefix)

    anyutil.DictRecursiveUpdate(dicSet, dicSettings)

    # Create a temporary file to store the config.
    # This will be loaded when the blender init script is executed
    # in the Blender context.
    sFilename = None
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as xFile:
        sFilename = xFile.name
        json.dump(dicSet, xFile.file)
    # endwith

    xScript = res.files(catharsys.plugins.std.blender).joinpath("scripts").joinpath("run-blender-configure.py")
    with res.as_file(xScript) as pathScript:
        bOK = xBlenderCfg.ExecBlender(
            lArgs=["-noaudio"],
            sPathScript=pathScript.as_posix(),
            lScriptArgs=[sFilename],
            bBackground=True,
            bDoPrint=True,
            bDoPrintOnError=True,
            sPrintPrefix=sPrintPrefix + ">> ",
        )

        if bOK is False:
            print(sPrintPrefix + "> Error starting Blender to configure add-ons")
        # endif
    # endwith pathScript

    Path(sFilename).unlink()


# enddef


############################################################################
def UninstallAddOns(*, xBlenderCfg):
    print("=================================================================")
    print("Uninstalling add-ons\n")

    print("> Checking for linked add-ons...")
    lProcAddOns = []
    dicRemAddOns = {}
    for pathAddOn in xBlenderCfg.pathAddOns.iterdir():
        sPathAddOn = pathAddOn.as_posix()
        if link.islink(sPathAddOn) is True:
            print(">> Found: {}".format(pathAddOn.name))
            dicRemAddOns[pathAddOn.name] = pathAddOn

            lProcAddOns.append({"sName": pathAddOn.name, "bEnable": False})
        # endif
    # endfor
    dicSettings = dict(lAddOns=lProcAddOns)

    print("> Disabling add-ons in Blender...")

    # Configure the linked addons
    ConfigureBlender(xBlenderCfg=xBlenderCfg, dicSettings=dicSettings, sPrintPrefix=">> ")

    print("> Removing add-on links...")

    # Remove links to add-ons that are not needed.
    for sAddOn in dicRemAddOns:
        pathAddOn = dicRemAddOns[sAddOn]
        link.unlink(pathAddOn.as_posix())
    # endfor

    print("> Done")


# enddef


############################################################################
def InstallAddOns(*, xBlenderCfg, bForceDist, dicBlenderSettings):
    print("=================================================================")
    print("Installing add-ons\n")

    # Check whether we are in a development environment
    if bForceDist is True:
        pathRepos = None
    else:
        pathRepos = util.TryGetReposPath()
    # endif

    # Remove all links in Blender add-on folder, to ensure
    # that only the addons of the current project are active
    print("> Checking for already linked add-ons...")
    dicRemAddOns = {}
    for pathAddOn in xBlenderCfg.pathAddOns.iterdir():
        sPathAddOn = pathAddOn.as_posix()
        if link.islink(sPathAddOn) is True:
            dicRemAddOns[pathAddOn.name] = pathAddOn
        # endif
    # endfor
    print("")

    lBlenderAddOns = dicBlenderSettings.get("lAddOns", [])
    if len(lBlenderAddOns) > 0:
        print("> Linking Blender add-ons...")
    # endif

    # Loop over all specified addons
    for dicAddOn in lBlenderAddOns:
        # ignore empty dictionaries.
        # For example, if an add-on is not specified due to '__platform__' settings
        if len(dicAddOn) == 0:
            continue
        # endif

        try:
            sType = dicAddOn["sType"]
            sName = dicAddOn["sName"]
        except KeyError as xEx:
            raise RuntimeError("Add-on configuration element '{}' missing".format(str(xEx)))
        # endtry

        pathAddOnSrc = None

        if sType == "MODULE":
            if pathRepos is not None:
                # link add-on from current repo folder
                modAddOn = importlib.import_module(sName)
                pathAddOnSrc = Path(modAddOn.__file__).parent
                print(">> Linking module '{}' from repository at path: {}".format(sName, pathAddOnSrc.as_posix()))

            else:
                # if this is a distribution install, need to obtain path
                # to module from Blender python.
                sAddOnSrc = module.GetModulePath(sPathPythonProg=xBlenderCfg.sPathPythonProg, sModuleName=sName)
                if len(sAddOnSrc) == 0:
                    raise RuntimeError("Module '{}' not installed in Blender context".format(sName))
                # endif

                pathAddOnSrc = Path(sAddOnSrc).parent
                print(">> Linking module '{}' from path: {}".format(sName, pathAddOnSrc.as_posix()))
            # endif

        elif sType == "FOLDER":
            sPathModule = dicAddOn.get("sPath")
            if sPathModule is None:
                raise RuntimeError("Configuration for add-on '{}' has no element 'sPath'")
            # endif

            pathAddOnSrc = Path(sPathModule)
            if not pathAddOnSrc.exists():
                raise RuntimeError("Path to add-on '{}' not found: {}".format(sName, pathAddOnSrc.as_posix()))
            # endif

            print(">> Linking folder '{}' from path: {}".format(sName, pathAddOnSrc.as_posix()))
        else:
            raise RuntimeError("Unsupported add-on type '{}' for add-on '{}'".format(sType, sName))
        # endif addon type

        pathAddOnLink: Path = xBlenderCfg.pathAddOns / sName
        sPathAddOnLink: str = pathAddOnLink.as_posix()
        if link.islink(sPathAddOnLink):
            print(">> Replacing current add-on link: {}".format(sPathAddOnLink))
            link.unlink(sPathAddOnLink)
        elif pathAddOnLink.is_dir():
            print(f">> Removing directory: {sPathAddOnLink}")
            # When a config is copied including the _blender directory, the links are copied
            # as empty folders. Delete folder to fix this issue and avoid an error when
            # symlink() is called below.
            shutil.rmtree(sPathAddOnLink)
        elif pathAddOnLink.is_file():
            print(f">> Removing file: {sPathAddOnLink}")
            pathAddOnLink.unlink()
        # endif

        link.symlink(pathAddOnSrc.as_posix(), sPathAddOnLink)

        if sName in dicRemAddOns:
            del dicRemAddOns[sName]
        # endif

        dicAddOn["bEnable"] = True
    # endfor

    # Disable all previously installed add-ons
    # that are not specified now.
    for sAddOn in dicRemAddOns:
        lBlenderAddOns.append({"sName": sAddOn, "bEnable": False})
    # endfor

    # Configure the linked addons
    ConfigureBlender(xBlenderCfg=xBlenderCfg, dicSettings=dicBlenderSettings, sPrintPrefix=">> ")

    # Remove links to add-ons that are not needed.
    for sAddOn in dicRemAddOns:
        pathAddOn = dicRemAddOns[sAddOn]
        link.unlink(pathAddOn.as_posix())
    # endfor


# enddef


############################################################################
def InitBlenderFromExecCfg(
    _xPrjCfg,
    _setExecConfigFiles,
    bForceDist=False,
    bForceInstall=False,
    bCleanUpAddOns=False,
    bCleanUpAll=False,
    bAddOnsOnly=False,
    bCathSourceDist=False,
):
    lBlenderPath = []
    xParser = CAnyCML()
    pathLA = _xPrjCfg.pathLaunch

    for sExecCfgFile in _setExecConfigFiles:
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
            dicBlenderSettings = xExecCfg.dicBlenderSettings
        except KeyError as xEx:
            raise RuntimeError(
                "Configuration element '{}' not specified in file: {}".format(str(xEx), pathCfg.as_posix())
            )
        # endtry

        bEffAddOnsOnly = bAddOnsOnly
        if sBlenderPath in lBlenderPath:
            # override addons only flag to avoid reinstalling modules
            bEffAddOnsOnly = True
        else:
            # Store initialized blender paths to avoid multiply initializing
            # the same Blender installation.
            lBlenderPath.append(sBlenderPath)
        # endif

        try:
            InitBlender(
                sBlenderPath=sBlenderPath,
                sBlenderVersion=sBlenderVersion,
                dicBlenderSettings=dicBlenderSettings,
                pathLA=pathLA,
                bForceDist=bForceDist,
                bForceInstall=bForceInstall,
                bCleanUpAddOns=bCleanUpAddOns,
                bCleanUpAll=bCleanUpAll,
                bAddOnsOnly=bEffAddOnsOnly,
                bCathSourceDist=bCathSourceDist,
            )
        except Exception as xEx:
            pathRelCfg = pathCfg.relative_to(_xPrjCfg.pathMain)
            raise CAnyError_Message(
                sMsg=(
                    f"Error initializing Blender {sBlenderVersion} for\n"
                    f"  config file '{(pathRelCfg.as_posix())}'\n"
                    f"  at path: {sBlenderPath}\n"
                    f"Maybe you need to install Blender {sBlenderVersion} with 'cathy blender install [Blender ZIP-file]'\n"
                    "You can download the various Blender versions from https://www.blender.org/download/"
                ),
                xChildEx=xEx,
            )
        # endtry
    # endfor


# enddef


############################################################################
def InitBlender(
    *,
    sBlenderPath: str,
    sBlenderVersion: str,
    dicBlenderSettings: dict = {},
    pathLA: Path = None,
    bForceDist: bool = False,
    bForceInstall: bool = False,
    bCleanUpAddOns: bool = False,
    bCleanUpAll: bool = False,
    bAddOnsOnly: bool = False,
    bModulesOnly: bool = False,
    bCathSourceDist: bool = False,
):
    global g_rePyVer

    try:
        xBlenderCfg = CBlenderConfig(
            pathLA=pathLA,
            sBlenderPath=sBlenderPath,
            sBlenderVersion=sBlenderVersion,
            sCondaEnvName=conda.GetActiveEnvName(),
        )
    except Exception as xEx:
        raise CAnyError_Message(sMsg="Error initializing Blender configuration", xChildEx=xEx)
    # endtry

    bOK, lStdOut = util.ExecShellCmd(
        sCmd='"{}" --version'.format(xBlenderCfg.sPathPythonProg),
        sCwd=xBlenderCfg.sPathPython,
        bDoPrint=False,
        bDoPrintOnError=True,
        bReturnStdOut=True,
    )

    xMatch = g_rePyVer.search(lStdOut[0])
    if xMatch is None:
        raise CAnyError_Message(sMsg="Python version could not be determined")
    # endif

    sPyVer = xMatch.group(1)

    if bCleanUpAddOns is True:
        sMode = "Cleaning up"
    else:
        sMode = "Initializing"
    # endif

    print("=================================================================")
    print("{} Blender {}".format(sMode, xBlenderCfg.sVersion))
    print("Blender path: {}".format(xBlenderCfg.sPathBlender))
    print("Blender Python path: {}".format(xBlenderCfg.sPathPythonProg))
    print("Blender Python version: {}".format(sPyVer))
    print("")

    if bAddOnsOnly is False and bCleanUpAddOns is False and bCleanUpAll is False:
        bEnsurePip = True
        bUpgradeBlenderPip = False
        bUpgradeLocalPip = False

        # Compare local pip version with Blender Python pip version
        print("Checking Blender Python pip version...")
        verPip = version.parse(pip.__version__)
        dicPipInfo = util.GetInstalledModuleInfo(sPathPythonProg=xBlenderCfg.sPathPythonProg, sModuleName="pip")
        sVerBlenderPip = dicPipInfo.get("Version")
        if sVerBlenderPip is not None:
            verBlenderPip = version.parse(sVerBlenderPip)
            # Upgrade Blender pip if it is older
            bUpgradeBlenderPip = verBlenderPip < verPip
            bUpgradeLocalPip = verBlenderPip > verPip
            bEnsurePip = False
            print("Local pip v{}, Blender pip v{}".format(pip.__version__, sVerBlenderPip))
        else:
            print("Blender Python does not seem to have pip installed.")
        # endif

        if bEnsurePip is True:
            print("=================================================================")
            print("Ensure that 'pip' is available in Blender bundled Python\n")
            bOK = util.ExecShellCmd(
                sCmd='"{}" -m ensurepip'.format(xBlenderCfg.sPathPythonProg),
                sCwd=xBlenderCfg.pathPython.as_posix(),
                bDoPrint=True,
                bDoRaiseOnError=True,
                sPrintPrefix=">> ",
            )
        # endif

        if bUpgradeLocalPip is True:
            print("=================================================================")
            print("Upgrading local Python 'pip' module\n")
            bOK = util.ExecShellCmd(
                sCmd="python -m pip install --upgrade pip",
                bDoPrint=True,
                bDoRaiseOnError=True,
                sPrintPrefix=">> ",
            )
        # endif

        if bUpgradeBlenderPip is True:
            print("=================================================================")
            print("Upgrading Blender Python 'pip' module\n")
            bOK = util.ExecShellCmd(
                sCmd='"{}" -m pip install --upgrade pip'.format(xBlenderCfg.sPathPythonProg),
                sCwd=xBlenderCfg.pathPython.as_posix(),
                bDoPrint=True,
                bDoRaiseOnError=True,
                sPrintPrefix=">> ",
            )
        # endif
    # endif

    if bCleanUpAddOns is True or bCleanUpAll is True:
        UninstallAddOns(xBlenderCfg=xBlenderCfg)
        if bCleanUpAll is True:
            module.UninstallModules(sPathPythonProg=xBlenderCfg.sPathPythonProg)
        # endif
    else:
        if bAddOnsOnly is False:
            module.InstallModules(
                sPathPythonProg=xBlenderCfg.sPathPythonProg,
                bForceDist=bForceDist,
                bForceInstall=bForceInstall,
                bSourceDist=bCathSourceDist,
            )
        # endif
        if bModulesOnly is False:
            InstallAddOns(
                xBlenderCfg=xBlenderCfg,
                bForceDist=bForceDist,
                dicBlenderSettings=dicBlenderSettings,
            )
        # endif
    # endif
    print("=================================================================\n")


# enddef


############################################################################
def Init(
    *,
    sConfig: str,
    sPathProject: str,
    bForceDist: bool,
    bForceInstall: bool,
    bCleanUpAddOns: bool,
    bCleanUpAll: bool,
    bAddOnsOnly: bool,
    bCathSourceDist: bool,
    bAllConfigs: bool,
    bIsDevelopInstall=util.IsDevelopInstall(),
):
    lPrjCfgs = []

    if bAllConfigs is True:
        wsMain = CWorkspace(xWorkspace=sPathProject)
        for sPrjId in wsMain.dicProjects:
            lPrjCfgs.append(wsMain.dicProjects[sPrjId].xConfig)
        # endfor

    else:
        xPrjCfg = CProjectConfig()

        if sPathProject is None and sConfig is None:
            # Uses CWD as launch path
            xPrjCfg.FromLaunchPath(None)
        else:
            # If project path is None, uses CWD as project path
            xPrjCfg.FromConfigName(xPathMain=sPathProject, sConfigName=sConfig)
        # endif

        lPrjCfgs = [xPrjCfg]
    # endif

    bEffAddOnsOnly = bAddOnsOnly
    for xPrjCfg in lPrjCfgs:
        xLaunch = CConfigLaunch()
        try:
            xLaunch.LoadFile(xPrjCfg)
        except Exception as xEx:
            raise CAnyError_Message(
                sMsg="Error loading 'launch.*' file at path: {}".format(xPrjCfg.sLaunchPath), xChildEx=xEx
            )
        # endtry

        dicActions = xLaunch.GetActionDict()
        setExecFiles = set()
        for sAct in dicActions:
            sExecFile = dicActions[sAct]["mConfig"].get("sExecFile")
            if sExecFile is not None:
                setExecFiles.add(sExecFile)
            # endif
        # endfor

        InitBlenderFromExecCfg(
            xPrjCfg,
            setExecFiles,
            bForceDist=bForceDist,
            bForceInstall=bForceInstall,
            bCleanUpAddOns=bCleanUpAddOns,
            bCleanUpAll=bCleanUpAll,
            bAddOnsOnly=bEffAddOnsOnly,
            bCathSourceDist=bCathSourceDist,
        )

        # If more than one configuration are initialized, then
        # do the full initialization only for the first.
        # For the remaining configs only the add-ons are initialized.
        bEffAddOnsOnly = True
    # endfor project configs


# enddef
