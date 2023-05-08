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

import re
import lzma
from tqdm import tqdm
import tarfile
import platform
from glob import glob
from zipfile import ZipFile
from pathlib import Path

import catharsys.setup.version
import catharsys.setup.util
from anybase import link as anylink
from anybase.cls_any_error import CAnyError, CAnyError_Message
from catharsys.plugins.std.blender.setup.cmd import init_impl


############################################################################
# Module Variables
g_reVersion = re.compile(r"blender-(\d+\.\d+\.\d+)-([^.-]+)-([^.]+)")


############################################################################
class CBlenderVersion:
    def __init__(self, pathPkg: Path):
        xMatch = g_reVersion.search(pathPkg.name)
        if xMatch is None:
            raise CAnyError_Message(
                sMsg="Could not determine Blender version from package filename '{}'\n".format(pathPkg.name)
            )
        # endif

        self._sVersion = xMatch.group(1)
        self._sSystem = xMatch.group(2)
        self._sArch = xMatch.group(3)
        self._sType = f"{self._sSystem}-{self._sArch}"
        self._lVersion = self._sVersion.split(".")
        self._sMajor = self._lVersion[0]
        self._sMajMin = ".".join(self._lVersion[0:2])

    # enddef

    def __str__(self):
        return f"{self.sVersion}-{self.sSystem}-{self.sArch}"

    # enddef

    def __getitem__(self, _iIdx: int):
        iIdx = int(_iIdx)
        if iIdx < 0 or iIdx > 2:
            raise RuntimeError(f"Invalid version index '{iIdx}'")
        # endif
        return self.lVersion[iIdx]

    # enddef

    def __getslice__(self, _iMin: int, _iMax: int):
        iMin = int(_iMin)
        iMax = int(_iMax)
        return self.lVersion[iMin:iMax]

    # enddef

    @property
    def sVersion(self) -> str:
        return self._sVersion

    @property
    def sSystem(self) -> str:
        return self._sSystem

    @property
    def sArch(self) -> str:
        return self._sArch

    @property
    def sType(self) -> str:
        return self._sType

    @property
    def lVersion(self) -> list:
        return self._lVersion

    @property
    def sMajor(self) -> str:
        return self._sMajor

    @property
    def sMajMin(self) -> str:
        return self._sMajMin


# endclass


############################################################################
def _UnpackTar(*, tarFile: tarfile.TarFile, pathCathBlender, bForceInstall, sPathExtract):
    lNames = tarFile.getnames()
    sBlenderFolder = lNames[0].split("/")[0]
    pathUnpack = pathCathBlender / sBlenderFolder
    if pathUnpack.exists() and bForceInstall is False:
        raise CAnyError_Message(sMsg="Blender install already exists at: {}".format(pathUnpack.as_posix()))
    # endif

    # xFileTar.extractall(pathCathBlender.as_posix())
    for xMember in tqdm(tarFile.getmembers(), desc="Extracting "):
        try:
            tarFile.extract(xMember, sPathExtract)
        except Exception as xEx:
            raise CAnyError_Message(sMsg="Error extracting file: {}".format(tarFile.name), xChildEx=xEx)
        # endtry
    # endfor

    return pathUnpack


# enddef


############################################################################
def _GetInstalledBlenderVersions(*, pathInst):

    pathSearch = pathInst / "blender-*"
    lFolders = glob(pathSearch.as_posix())
    dicInst = {}
    for sFolder in lFolders:
        pathFolder = Path(sFolder)
        if not pathFolder.is_dir():
            continue
        # endif
        try:
            verBlender = CBlenderVersion(pathFolder)
        except Exception:
            continue
        # endtry

        dicVerMaj: dict = dicInst.get(verBlender.sType)
        if dicVerMaj is None:
            dicVerMaj = dicInst[verBlender.sType] = {}
        # endif
        dicVerMin = dicVerMaj.get(verBlender[0])
        if dicVerMin is None:
            dicVerMin = dicVerMaj[verBlender[0]] = {}
        # endif
        setVerRev = dicVerMin.get(verBlender[1])
        if setVerRev is None:
            setVerRev = dicVerMin[verBlender[1]] = set()
        # endif
        setVerRev.add(int(verBlender[2]))
    # endfor

    return dicInst


# enddef


############################################################################
def _CheckInstallerFileVersion(*, verInst: CBlenderVersion, dicInst: dict, bForceInstall: bool, pathInst: Path):

    dicVerMaj = dicInst.get(verInst.sType)
    if dicVerMaj is not None:
        dicVerMin = dicVerMaj.get(verInst[0])
        if dicVerMin is not None:
            setVerRev = dicVerMin.get(verInst[1])
            if setVerRev is not None:
                iVerRev = int(verInst[2])
                if iVerRev < max(setVerRev):
                    raise CAnyError_Message(
                        sMsg="The newer revision '{}.{}.{}' of Blender {} is already installed in: {}".format(
                            verInst[0],
                            verInst[1],
                            max(setVerRev),
                            verInst.sMajMin,
                            pathInst.as_posix(),
                        )
                    )
                elif iVerRev in setVerRev:
                    if bForceInstall is False:
                        raise CAnyError_Message(
                            sMsg="Blender version {} already installed in: {}".format(verInst, pathInst.as_posix())
                        )
                    else:
                        print(">> Re-installing Blender version {}".format(verInst))
                    # endif
                # endif revision
            # endif minor version
        # endif major version
    # endif install type


# enddef


############################################################################
def InstallBlenderPackage(
    *,
    pathZip: Path,
    bForceDist: bool = False,
    bForceInstall: bool = False,
    bNoCathInstall: bool = False,
    bCathSourceDist: bool = False,
):

    if not pathZip.exists():
        raise CAnyError_Message(sMsg="Blender package file not found: {}".format(pathZip.as_posix()))
    elif not pathZip.is_file():
        raise CAnyError_Message(sMsg="Blender package not a file: {}".format(pathZip.as_posix()))
    # endif

    sCathVersion = catharsys.setup.version.MajorMinorAsString()

    pathCath = catharsys.setup.util.GetCathUserPath(_bCheckExists=False)
    pathCathBlender = pathCath / "Blender"
    pathCathBlender.mkdir(parents=True, exist_ok=True)

    # Get list of installed Blender versions
    dicInst = _GetInstalledBlenderVersions(pathInst=pathCathBlender)
    verBlender = CBlenderVersion(pathZip)

    print(
        ">> Installing Blender {} ({}) for Catharsys version {}".format(
            verBlender.sVersion, verBlender.sType, sCathVersion
        )
    )

    if verBlender.sSystem.lower() != platform.system().lower():
        raise CAnyError_Message(
            sMsg="Blender package '{}' is not compatible with current system '{}'".format(
                pathZip.name, platform.system()
            )
        )
    # endif

    _CheckInstallerFileVersion(
        verInst=verBlender,
        dicInst=dicInst,
        pathInst=pathCathBlender,
        bForceInstall=bForceInstall,
    )

    print(">> Unpacking to: {}".format(pathCathBlender.as_posix()))
    pathUnpack = None
    sBlenderFolder = None
    sPathExtract = pathCathBlender.as_posix()

    if pathZip.as_posix().endswith(".tar.xz"):
        with lzma.open(pathZip, "rb") as xzFile:
            with tarfile.open(fileobj=xzFile) as tarFile:
                try:
                    pathUnpack = _UnpackTar(
                        tarFile=tarFile,
                        sPathExtract=sPathExtract,
                        pathCathBlender=pathCathBlender,
                        bForceInstall=bForceInstall,
                    )
                except Exception as xEx:
                    raise CAnyError_Message(
                        sMsg="Error extracting file: {}".format(pathZip.as_posix()),
                        xChildEx=xEx,
                    )
                # endtry
            # endwith
        # endwith

    elif pathZip.suffix == ".tar":
        with tarfile.open(pathZip.as_posix()) as tarFile:
            try:
                pathUnpack = _UnpackTar(
                    tarFile=tarFile,
                    sPathExtract=sPathExtract,
                    pathCathBlender=pathCathBlender,
                    bForceInstall=bForceInstall,
                )
            except Exception as xEx:
                raise CAnyError_Message(
                    sMsg="Error extracting file: {}".format(pathZip.as_posix()),
                    xChildEx=xEx,
                )
            # endtry
        # endwith

    elif pathZip.suffix == ".zip":

        with ZipFile(pathZip.as_posix(), "r") as zipFile:
            lNames = zipFile.namelist()
            sBlenderFolder = lNames[0].split("/")[0]
            pathUnpack = pathCathBlender / sBlenderFolder
            if pathUnpack.exists() and bForceInstall is False:
                raise CAnyError_Message(sMsg="Blender install already exists at: {}".format(pathUnpack.as_posix()))
            # endif

            # zipFile.extractall(pathCathBlender.as_posix())
            for xMember in tqdm(zipFile.infolist(), desc="Extracting "):
                try:
                    zipFile.extract(xMember, sPathExtract)
                except Exception as xEx:
                    raise CAnyError_Message(
                        sMsg="Error extracting file: {}".format(pathZip.as_posix()),
                        xChildEx=xEx,
                    )
                # endtry
            # endfor zip members
        # endwith

    else:
        raise CAnyError_Message(sMsg="Unsupported file package format '{}'".format(pathZip.suffix))
    # endif

    print(">> Unpacked to: {}".format(pathUnpack.as_posix()))

    print(f">> Installed Blender version {verBlender}")

    pathLink = pathCath / f"blender-{verBlender.sMajMin}"
    if pathLink.exists() and anylink.islink(pathLink.as_posix()):
        anylink.unlink(pathLink.as_posix())
    # endif

    anylink.symlink(pathUnpack.as_posix(), pathLink.as_posix())
    print(">> Created link to new Blender install: {}".format(pathLink.as_posix()))

    if bNoCathInstall is False:
        print(f">> Installing Catharsys in Blender {verBlender}")
        init_impl.InitBlender(
            sBlenderPath=pathLink.as_posix(),
            sBlenderVersion=verBlender.sMajMin,
            bForceDist=bForceDist,
            bForceInstall=bForceInstall,
            bModulesOnly=True,
            bCathSourceDist=bCathSourceDist,
        )
        print("\n>> Catharsys modules installed in Blender")
    # endif

    print("\n>> Don't forget to initialize the Blender addons for your rendering configuration")
    print(">> using the command from the rendering workspace folder:")
    print(">> ")
    print(">>         cathy blender init -c [configuration folder] --addons")
    print(">> \n")


# enddef
