#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \data\evaluate.py
# Created Date: Friday, April 1st 2022, 1:41:51 pm
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

from anybase.cls_any_error import CAnyError_Message
import ison
from . import util


############################################################################################
def Evaluate(_dicData, sMode="INIT", dicVars={}):
    dicResult = {}

    for sVarId in _dicData:
        if sVarId.startswith("__"):
            continue
        # endif

        dicEval = _dicData[sVarId]

        sEvalType = dicEval.get("sDTI")
        if sEvalType is None:
            raise RuntimeError("Element 'sDTI' missing for evaluator for variable id '{}'".format(sVarId))
        # endif

        lApplyModes = dicEval.get("lApplyModes", ["INIT"])
        if sMode not in lApplyModes:
            print(f"> {sMode}: NOT applying evaluator '{sEvalType}'")
            continue
        # endif
        print(f"> {sMode}: Applying evaluator '{sEvalType}'")

        funcEval = util.GetModifyFunction(sEvalType, "/catharsys/blender/modify/evaluate/*:*")
        if funcEval is None:
            raise RuntimeError("Evaluator '{}' not available".format(sEvalType))
        # endif

        ison.util.data.AddLocalGlobalVars(dicEval, _dicData, bThrowOnDisallow=False)

        try:
            dicResult[sVarId] = funcEval(dicEval, sMode=sMode, dicVars=dicVars)
        except Exception as xEx:
            raise CAnyError_Message(sMsg=f"Error executing evaluator '{sEvalType}'", xChildEx=xEx)
        # endtry
    # endfor

    return dicResult


# enddef
