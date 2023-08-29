#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \data\program.py
# Created Date: Friday, April 1st 2022, 11:31:57 am
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

import copy
import ison
import anybase
import anybase.config
from anybase import convert
from anybase.cls_anycml import CAnyCML
from anybase.cls_any_error import CAnyError_Message
from . import util as modutil
from ..generate import util as genutil

import enum


class EModifierType(enum.Enum):
    NONE = enum.auto()
    MODIFIER = enum.auto()
    EVALUATOR = enum.auto()
    GENERATOR = enum.auto()


# endclass


############################################################################################
def Execute(_dicProgram, sMode="INIT", dicVars=None):
    if _dicProgram is None:
        return
    # endif

    dicProgram = copy.deepcopy(_dicProgram)

    lMods = dicProgram.get("lModifier")
    if lMods is None:
        return
    # endif

    lApplyModes = dicProgram.get("lApplyModes", ["INIT", "FRAME_UPDATE"])
    if sMode not in lApplyModes:
        return
    # endif

    sFilePath = None
    dicLocals = dicProgram.get("__locals__")
    if isinstance(dicLocals, dict):
        sFilePath = dicLocals.get("filepath")
    # endif

    dicEvalVars = {}

    for iModIdx, dicMod in enumerate(lMods):
        try:
            sDTI = dicMod.get("sDTI")
            if not isinstance(sDTI, str):
                raise RuntimeError("Element 'sDTI' not given for modifier {} in program".format(iModIdx))
            # endif

            dicData = dicMod.get("mData")
            if not isinstance(dicData, dict):
                raise RuntimeError("Element 'mData' not given for modifier {} in program".format(iModIdx))
            # endif

            sElTypeName: str = None
            eModType = EModifierType.NONE
            if anybase.config.IsDti(sDTI, "/catharsys/blender/modify/evaluate:*"):
                eModType = EModifierType.EVALUATOR
                sElTypeName = "Evaluator"
            elif anybase.config.IsDti(sDTI, "/catharsys/blender/modify/?:*"):
                eModType = EModifierType.MODIFIER
                sElTypeName = "Modifier"
            elif anybase.config.IsDti(sDTI, "/catharsys/blender/generate/?:*"):
                eModType = EModifierType.GENERATOR
                sElTypeName = "Generator"
            else:
                raise RuntimeError("Type '{}' not supported in modifier program element {}".format(sDTI, iModIdx))
            # endif

            if eModType in [EModifierType.EVALUATOR, EModifierType.MODIFIER]:
                funcHandler = modutil.GetModifyFunction(sDTI, "/catharsys/blender/modify/?:*")
            elif eModType == EModifierType.GENERATOR:
                funcHandler = genutil.GetGenerateClassFunc(sDTI, "/catharsys/blender/generate/?:*")
            # endif

            if funcHandler is None:
                raise RuntimeError(f"{sElTypeName} type '{sDTI}' not supported in modifier program element {iModIdx}")
            # endif

            ison.util.data.AddLocalGlobalVars(dicData, dicProgram, bThrowOnDisallow=False)
            ison.util.data.AddLocalGlobalVars(dicData, dicMod, bThrowOnDisallow=False)

            if len(dicEvalVars) > 0:
                xParser = CAnyCML(dicConstVars=dicEvalVars)
                dicData = xParser.Process(dicData)
            # endif

            try:
                if eModType == EModifierType.EVALUATOR:
                    dicResultVars = funcHandler(dicData, sMode=sMode, dicVars=dicVars)
                    if len(dicResultVars) > 0:
                        dicEvalVars.update(dicResultVars)
                    # endif
                    # print(dicEvalVars)
                elif eModType == EModifierType.GENERATOR:
                    dicResultVars = funcHandler(dicData, sMode=sMode, dicVars=dicVars)
                    if len(dicResultVars) > 0:
                        dicEvalVars.update(dicResultVars)
                    # endif
                else:
                    funcHandler(dicData, sMode=sMode, dicVars=dicVars)
                # endif
            except Exception as xEx:
                raise CAnyError_Message(
                    sMsg="Error executing program modifier {} of type '{}'".format(iModIdx, sDTI),
                    xChildEx=xEx,
                )
            # endtry

        except Exception as xEx:
            sMsg = f"Error executing program modifier {iModIdx} in mode '{sMode}'"
            if isinstance(sFilePath, str):
                sMsg += f"\n> See file: {sFilePath}"
            # endif
            raise CAnyError_Message(sMsg=sMsg, xChildEx=xEx)
        # endtry

    # endfor program lines


# enddef
