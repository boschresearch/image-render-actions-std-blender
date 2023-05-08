#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /util.py
# Created Date: Thursday, October 22nd 2020, 1:20:20 pm
# Author: Christian Perwass
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

import anyblend
from . import util

#####################################################################################
def RegisterAnimObject(_sObj, _dicAnim):

    sAnimType = _dicAnim.get("sDTI", _dicAnim.get("sType"))
    if sAnimType is None:
        raise RuntimeError("Element 'sDTI' missing in animation configuration")
    # endif

    funcFactory = util.GetAnimateHandlerFactory(
        sAnimType, "/catharsys/blender/animate/*:*"
    )
    if funcFactory is None:
        raise Exception("Unknown animation type '{0}'.".format(sAnimType))
    # endif

    anyblend.anim.util.RegisterAnimObject(_sObj, _dicAnim, funcFactory)


# enddef


#####################################################################################
# removes all anim handlers of object if no dicAnim is given.
# Otherwise, only the animation of the type specified in _dicAnim is removed.
def RemoveAnimObject(_sObj, dicAnim=None):

    anyblend.anim.util.RemoveAnimObject(_sObj, dicAnim=dicAnim)


# enddef


#####################################################################################
def RegisterAnimList(_dicAnimObj):

    for sObj in _dicAnimObj:
        lAnim = _dicAnimObj.get(sObj)
        for dicAnim in lAnim:
            RegisterAnimObject(sObj, dicAnim)
        # endfor
    # endif


# enddef


#####################################################################################
def UnRegisterAnimList(_dicAnimObj):

    for sObj in _dicAnimObj:
        lAnim = _dicAnimObj.get(sObj)
        for dicAnim in lAnim:
            RemoveAnimObject(sObj, dicAnim)
        # endfor
    # endif


# enddef
