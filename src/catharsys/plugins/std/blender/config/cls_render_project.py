#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \vars.py
# Created Date: Friday, April 22nd 2022, 2:43:25 pm
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
# Basic project structure:
# [main_project_folder]
# |- config
#    |- [config name 1]
#       | - launch[.json, .json5, .ison]
#    |- [config name 2]
#       | - launch[.json, .json5, .ison]
# |- package.json
#
# launch.json:
#   - fundamental parameters for launching actions
#   - parameter set per action
#
# package.json:
#   - version of project
#   - Catharsys version needed
###

from anybase import config
from catharsys.config.cls_project import CProjectConfig
from anybase.cls_any_error import CAnyError_Message


# Project paths for a given configuration
class CRenderProjectConfig(CProjectConfig):

    _sFolderRender: str = "_render"

    #######################################################################
    # getter functions
    @property
    def sRenderFolderName(self):
        return self._sFolderRender

    @property
    def sRenderPath(self):
        return self._pathProduction.as_posix()

    @property
    def pathRender(self):
        return self._pathProduction

    #############################################################################
    # Constructor
    def __init__(self):
        super().__init__()
        self._sFolderProduction = self._sFolderRender

    # enddef

    #############################################################################
    def _Update(self):
        self._sFolderProduction = self._sFolderRender
        self._pathProduction = self._pathMain / self._sFolderProduction
        self._pathActProd = self._pathProduction / self._sFolderActProd

    # enddef

    #############################################################################
    def FromLaunchPath(self, _xPathLaunch):
        super().FromLaunchPath(_xPathLaunch)
        self._Update()

    # enddef

    #############################################################################
    def FromConfigName(self, *, xPathMain, sConfigName):
        super().FromConfigName(xPathMain=xPathMain, sConfigName=sConfigName)
        self._Update()

    # enddef

    #############################################################################
    def FromProject(self, _xPrjCfg):
        super().FromProject(_xPrjCfg)
        self._Update()

    # enddef

    #######################################################################
    def FromData(self, _dicSerialized):
        super().FromData(_dicSerialized)

        try:
            self._sFolderRender = _dicSerialized["sRenderFolderName"]

        except KeyError as xEx:
            raise CAnyError_Message(
                sMsg="Missing element '{}' in serialized project configuration".format(
                    str(xEx)
                ),
                xChildEx=xEx,
            )
        # endif

        self._Update()

    # enddef

    #######################################################################
    # This function can be overwritten by derived classes to
    # modify the project parameters
    def ApplyConfig(self, _dicCfg):
        dicResult = config.CheckConfigType(_dicCfg, "/catharsys/launch/args:1")
        if dicResult["bOK"] is False:
            raise CAnyError_Message(
                sMsg="Unsupported configuration: {}".format(dicResult["sMsg"])
            )
        # endif

        sTopFolder = _dicCfg.get("sTopFolder")
        if sTopFolder is None:
            iRenderQuality = _dicCfg.get("iRenderQuality")
            if iRenderQuality is None:
                raise CAnyError_Message(
                    sMsg="Neither 'sTopFolder' nor 'iRenderQuality' given in launch arguments"
                )
            # endif
            sTopFolder = "rq{:04d}".format(iRenderQuality)
        # endif

        self._sFolderActProd = sTopFolder
        self._pathActProd = self._pathProduction / self._sFolderActProd

    # enddef

    #######################################################################
    def Serialize(self):
        dicData = super().Serialize()

        dicData.update(
            {
                "sDTI": "/catharsys/project-class/std/blender/render:1.0",
                "sRenderFolderName": self.sRenderFolderName,
            }
        )

        return dicData

    # enddef

    ################################################################
    def GetFilepathVarDict(self, _xFilepath):

        dicVar = super().GetFilepathVarDict(_xFilepath)
        dicVar.update(
            {
                "path-render": self.sProductionPath,
            }
        )

        return dicVar

    # enddef


# endclass
