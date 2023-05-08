#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \data\collection.py
# Created Date: Saturday, August 21st 2021, 7:04:57 am
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

import bpy

from anybase import config
from anybase.cls_anycml import CAnyCML
import anyblend
import ison
from ..generate import util


class CConfigGenerateList:

    # The configuration data
    lData: list = None
    dicGeneratedObjects: dict = {}

    ############################################################
    # The constructor
    def __init__(self, _lData):

        self.lData = _lData

    # enddef

    ############################################################
    def Apply(self, dicConstVars=None, dicRefVars=None):

        if self.lData is None:
            raise Exception("No generate configuration list given.")
        # endif

        lActData = self.lData
        # parse generator config data again with runtime variables
        if dicConstVars is not None or dicRefVars is not None:
            xParser = CAnyCML(dicConstVars=dicConstVars, dicRefVars=dicRefVars)
            lActData = xParser.Process(self.lData)
        # endif

        dicVars = {}
        if isinstance(dicConstVars, dict):
            dicVars.update(dicConstVars)
        # endif

        if isinstance(dicRefVars, dict):
            dicVars.update(dicRefVars)
        # endif

        self.dicGeneratedObjects = {}
        for dicCfgGen in lActData:
            config.AssertConfigType(dicCfgGen, "/catharsys/blender/generate:1")

            sCfgId = dicCfgGen.get("sId")
            lGens: list[dict] = dicCfgGen.get("lGenerators")
            if lGens is None:
                raise RuntimeError(
                    f"Config '{sCfgId}': Element 'lGenerators' missing in generator configuration"
                )
            # endif
            if not isinstance(lGens, list):
                raise RuntimeError(
                    f"Config '{sCfgId}': Element 'lGenerators' is not of type 'list'"
                )
            # endif

            for dicGen in lGens:
                if not isinstance(dicGen, dict):
                    raise RuntimeError(
                        f"Config '{sCfgId}': Element of 'lGenerators' list is not a dictionary: '{dicGen}'"
                    )
                # endif

                # copy locals and globals from dicData to modifier groups
                # so that they are available when parsing the modifiers with previously
                # incomplete references
                ison.util.data.AddLocalGlobalVars(
                    dicGen, dicCfgGen, bThrowOnDisallow=False
                )

                sGenDti = dicGen.get("sDTI")
                if sGenDti is None:
                    raise RuntimeError(
                        f"Config '{sCfgId}': Element 'sDTI' missing in generator configuration"
                    )
                # endif

                funcGenCls = util.GetGenerateClassFunc(
                    sGenDti, "/catharsys/blender/generate/*:*"
                )
                self.UpdateGeneratedDict(funcGenCls(dicGen, dicVars=dicVars))

            # endfor generator process functions
        # endfor generation configs

    # enddef

    ##############################################################
    # Clean up generated objects
    # We only remove the objects and not the collections,
    # since the collections may have existed before.
    def RemoveGenerated(self):

        for sCln in self.dicGeneratedObjects:
            bRemoveCollection = False
            lObjects = self.dicGeneratedObjects.get(sCln)
            for sObject in lObjects:
                if sObject == "*":
                    bRemoveCollection = True
                else:
                    if sObject in bpy.data.objects:
                        anyblend.object.RemoveObjectHierarchy(bpy.data.objects[sObject])
                    # endif
                # endif
            # endfor objects

            if bRemoveCollection is True and sCln in bpy.data.collections:
                anyblend.collection.RemoveCollection(sCln)
            # endif
        # endfor collections

        self.dicGeneratedObjects = {}

    # enddef

    ##############################################################
    def UpdateGeneratedDict(self, _dicNewGenObj):
        for sKey in _dicNewGenObj:
            lObj = self.dicGeneratedObjects.get(sKey)
            if lObj is None:
                self.dicGeneratedObjects[sKey] = _dicNewGenObj[sKey].copy()
            else:
                self.dicGeneratedObjects[sKey].extend(_dicNewGenObj[sKey])
            # endif
        # endfor collections

    # enddef


# endclass
