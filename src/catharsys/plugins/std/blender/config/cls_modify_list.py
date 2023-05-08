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

import sys

from ..modify import nodegroups
from ..modify import materials
from ..modify import objects
from ..modify import collections
from ..modify import scenes
from ..modify import program

from anybase import config
from anybase.cls_anycml import CAnyCML
import anyblend

import ison


class CConfigModifyList:

    # The configuration data
    lData: list = None

    ############################################################
    # The constructor
    def __init__(self, _lData):

        self.lData = _lData

    # enddef

    ############################################################
    def Apply(self, sMode="INIT", dicConstVars=None, dicRefVars=None):

        if self.lData is None:
            raise Exception("No modify configuration list given.")
        # endif

        lActData = self.lData
        # sys.stderr.write(f"\ndicConstVars: {dicConstVars}\n")
        # sys.stderr.write(f"\nlActData: {lActData}\n")

        if dicConstVars is not None or dicRefVars is not None:
            xParser = CAnyCML(dicConstVars=dicConstVars, dicRefVars=dicRefVars)
            lActData = xParser.Process(self.lData)
        # endif
        # sys.stderr.write(f"\nlActData: {lActData}\n")
        # sys.stderr.flush()

        dicVars = {}
        if isinstance(dicConstVars, dict):
            dicVars.update(dicConstVars)
        # endif

        if isinstance(dicRefVars, dict):
            dicVars.update(dicRefVars)
        # endif

        lModFuncs = [
            ("mNodeGroups", nodegroups.ModifyNodeGroups),
            ("mMaterials", materials.ModifyMaterials),
            ("mObjects", objects.ModifyObjects),
            ("mCollections", collections.ModifyCollections),
            ("mScenes", scenes.ModifyScenes),
            ("mProgram", program.Execute),
        ]

        for dicData in lActData:
            config.AssertConfigType(dicData, "/catharsys/blender/modify:1")

            for sModName, funcHandler in lModFuncs:
                dicMod = dicData.get(sModName)
                if dicMod is None:
                    continue
                # endif

                # copy locals and globals from dicData to modifier groups
                # so that they are available when parsing the modifiers with previously
                # incomplete references
                ison.util.data.AddLocalGlobalVars(dicMod, dicData, bThrowOnDisallow=False)

                # Execute the modify handler
                # funcHandler may return a single revert function or a list of functions
                funcHandler(dicMod, sMode=sMode, dicVars=dicVars)
            # endfor
        # endfor

        # After applying modifiers, which may object properties,
        # all drivers should be updated, so that follow up calls
        # to apply animations or evaluate object properties are
        # correct.
        # The only way I found on how to force an update of drivers
        # is to change the current scene frame.
        # So, here we are changing the frame by one and then back again.
        anyblend.scene.UpdateDrivers()

    # enddef


# endclass
