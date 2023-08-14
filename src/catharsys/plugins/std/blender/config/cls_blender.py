#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \cls_blender.py
# Created Date: Tuesday, May 3rd 2022, 9:10:22 am
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
import platform
from pathlib import Path
from typing import Callable, Optional

from anybase import shell
from anybase.cls_process_handler import CProcessHandler
from catharsys.decs.decorator_log import logFunctionCall


#####################################################################
class CBlenderConfig:
    pathBlender: Path = None
    pathBlenderProg: Path = None
    pathUser: Path = None
    pathScripts: Path = None
    pathAddOns: Path = None
    pathModules: Path = None
    pathPython: Path = None
    pathPythonProg: Path = None
    pathPkg: Path = None
    pathConfig: Path = None

    sBlenderVersion: str = None

    @property
    def sVersion(self):
        return self.sBlenderVersion

    # enddef

    @property
    def sPathBlender(self):
        return self.pathBlender.as_posix()

    # enddef

    @property
    def sPathBlenderProg(self):
        return self.pathBlenderProg.as_posix()

    # enddef

    @property
    def sPathModules(self):
        return self.pathModules.as_posix()

    # enddef

    @property
    def sPathPython(self):
        return self.pathPython.as_posix()

    # enddef

    @property
    def sPathPythonProg(self):
        return self.pathPythonProg.as_posix()

    # enddef

    #####################################################################
    def __init__(self, *, sBlenderPath, sBlenderVersion, pathLA=None, sCondaEnvName):
        self.sBlenderVersion = sBlenderVersion
        self.pathBlender = Path(self._NormPath(sBlenderPath))
        if not self.pathBlender.exists():
            raise RuntimeError("Blender not found at path: {}".format(self.pathBlender.as_posix()))
        # endif

        self.pathPkg = pathLA
        if self.pathPkg is not None and not self.pathPkg.exists():
            raise RuntimeError("Launch args path does not exist: {}".format(self.pathPkg.as_posix()))
        # endif

        self.pathPython = self.pathBlender / self.sBlenderVersion / "python"
        if not self.pathPython.exists():
            raise RuntimeError("Blender python path does not exist: {}".format(self.pathPython.as_posix()))
        # endif

        sBlenderCfgFolder = f"_blender/{sCondaEnvName}"

        if platform.system() == "Windows":
            if self.pathPkg is None:
                self.pathUser = Path(
                    self._NormPath("%appdata%\\Blender Foundation\\Blender\\{}".format(self.sBlenderVersion))
                )
            else:
                self.pathUser = self.pathPkg / sBlenderCfgFolder / f"{self.sBlenderVersion}"
                self.pathUser.mkdir(parents=True, exist_ok=True)
            # endif

            self.pathPythonProg = self.pathPython / "bin" / "python.exe"
            self.pathBlenderProg = self.pathBlender / "blender.exe"

        elif platform.system() == "Linux":
            if self.pathPkg is None:
                self.pathUser = Path(self._NormPath("~/.config/blender/{}".format(self.sBlenderVersion)))
            else:
                self.pathUser = self.pathPkg / sBlenderCfgFolder / f"{self.sBlenderVersion}"
                self.pathUser.mkdir(parents=True, exist_ok=True)
            # endif

            self.pathPythonProg = None
            pathPythonBin = self.pathPython / "bin"
            for pathPy in pathPythonBin.iterdir():
                if pathPy.is_file() and pathPy.name.startswith("python"):
                    self.pathPythonProg = pathPy
                    break
                # endif
            # endfor

            if self.pathPythonProg is None:
                raise RuntimeError("Python executable not found at path: {}".format(self.pathPython.as_posix()))
            # endif

            self.pathBlenderProg = self.pathBlender / "blender"

        else:
            raise RuntimeError("Unsupported platform: {0}".format(platform.system()))
        # endif

        # if not self.pathUser.exists():
        #     raise RuntimeError("Blender {} user path not found: {}"
        #                     .format(self.sBlenderVersion, self.pathUser.as_posix()))
        # # endif

        self.pathConfig = self.pathUser / "config"
        self.pathScripts = self.pathUser / "scripts"
        self.pathAddOns = self.pathScripts / "addons"
        self.pathModules = self.pathScripts / "modules"

        self.pathConfig.mkdir(parents=True, exist_ok=True)
        self.pathAddOns.mkdir(parents=True, exist_ok=True)
        self.pathModules.mkdir(parents=True, exist_ok=True)

    # enddef

    #################################################################################################################
    def _NormPath(self, _sPath):
        return os.path.normpath(os.path.expanduser(os.path.expandvars(_sPath)))

    # enddef

    #################################################################################################################
    @logFunctionCall
    def ExecBlender(
        self,
        *,
        lArgs=None,
        sPathBlendFile=None,
        sPathScript=None,
        lScriptArgs=None,
        bBackground=True,
        bNoWindowFocus=False,
        sCwd=None,
        bDoPrint=False,
        bDoPrintOnError=True,
        bDoReturnStdOut=False,
        sPrintPrefix="",
        xProcHandler: Optional[CProcessHandler] = None,
    ):
        sProgram: str = f"{self.sPathBlenderProg}"

        lProgArgs = []
        if bBackground is True:
            lProgArgs.append("-b")
        # endif

        if bNoWindowFocus is True:
            lProgArgs.append("--no-window-focus")
        # endif

        if isinstance(lArgs, list):
            lProgArgs.extend(lArgs)
        # endif

        if isinstance(sPathBlendFile, str):
            lProgArgs.append(sPathBlendFile)
        # endif

        if isinstance(sPathScript, str):
            lProgArgs.append("-P")
            lProgArgs.append(sPathScript)
        # endif

        if isinstance(lScriptArgs, list):
            lProgArgs.append("--")
            lProgArgs.extend(lScriptArgs)
        # endif

        if sCwd is None:
            sEffCwd = self.sPathBlender
        else:
            sEffCwd = sCwd
        # endif

        dicEnv = {
            "BLENDER_USER_CONFIG": self.pathConfig.as_posix(),
            "BLENDER_USER_SCRIPTS": self.pathScripts.as_posix(),
        }

        if bDoReturnStdOut is True:
            bOK, lLines = shell.ExecProgram(
                sProgram=sProgram,
                lArgs=lProgArgs,
                sCwd=sEffCwd,
                bDoPrint=bDoPrint,
                bDoPrintOnError=bDoPrintOnError,
                sPrintPrefix=sPrintPrefix,
                dicEnv=dicEnv,
                bReturnStdOut=True,
                xProcHandler=xProcHandler,
            )

            return bOK, lLines

        else:
            bOK = shell.ExecProgram(
                sProgram=sProgram,
                lArgs=lProgArgs,
                sCwd=sEffCwd,
                bDoPrint=bDoPrint,
                bDoPrintOnError=bDoPrintOnError,
                sPrintPrefix=sPrintPrefix,
                dicEnv=dicEnv,
                bReturnStdOut=False,
                xProcHandler=xProcHandler,
            )

            return bOK
        # endif

    # enddef


# endclass
