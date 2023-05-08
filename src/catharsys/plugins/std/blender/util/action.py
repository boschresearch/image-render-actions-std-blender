#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \action.py
# Created Date: Friday, November 25th 2022, 1:37:36 pm
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

from anybase import assertion

from catharsys.config.cls_project import CProjectConfig
import catharsys.util.config as cathcfg
# import catharsys.util.path as cathpath
from catharsys.plugins.std.blender.config.cls_compositor import CConfigCompositor

# Since we want to access result images of a render, we need to process
# the render config settings.
g_sRenderDti: str = "blender/render/output/image:1"
g_sRenderOutputListDti: str = "blender/render/output-list:1"


##################################################################################################################
def GetRenderFolder(
    _xPrjCfg: CProjectConfig, _dicCfg: dict, _sImgTypeDti: str, _sWhere: str = None
) -> tuple[dict, str]:
    assertion.FuncArgTypes()

    global g_sRenderDti, g_sRenderOutputListDti

    sWhere: str
    if not isinstance(_sWhere, str):
        sWhere = "GetRenderFolder()"
    else:
        sWhere = _sWhere
    # endif

    dicConfig: dict = cathcfg.GetDictValue(_dicCfg, "mConfig", dict, sWhere=sWhere)
    dicData: dict = cathcfg.GetDictValue(dicConfig, "mData", dict, sWhere=sWhere)

    lRndTypeList = cathcfg.GetDataBlocksOfType(dicData, g_sRenderOutputListDti)
    if len(lRndTypeList) == 0:
        raise RuntimeError(
            "No render output configuration of type compatible to '{0}' given".format(g_sRenderOutputListDti)
        )
    # endif
    dicRndOutList = lRndTypeList[0]
    lRndOutTypes = cathcfg.GetDictValue(dicRndOutList, "lOutputs", list)
    if lRndOutTypes is None:
        raise RuntimeError("No render output types defined")
    # endif

    # Look for 'image' render output type
    dicRndOut = None
    for dicOut in lRndOutTypes:
        dicRes = cathcfg.CheckConfigType(dicOut, g_sRenderDti)
        if dicRes["bOK"] is True:
            dicRndOut = dicOut
            break
        # endif
    # endfor

    if dicRndOut is None:
        raise RuntimeError("No render output type 'image' specified in configuration")
    # endif

    dicComp = dicRndOut.get("mCompositor")
    cathcfg.AssertConfigType(dicComp, "/catharsys/blender/compositor:1")
    xComp = CConfigCompositor(xPrjCfg=_xPrjCfg, dicData=dicComp)

    lImgType = cathcfg.GetDataBlocksOfType(dicData, _sImgTypeDti)
    if len(lImgType) == 0:
        raise RuntimeError("No image type configuration of type compatible to '{0}' given.".format(_sImgTypeDti))
    # endif
    sImageType = lImgType[0]

    # Get compositor file format for given image type
    lCompFo = xComp.GetOutputsByFolderName()

    lImageFolderFo = lCompFo.get(sImageType, [])
    if len(lImageFolderFo) == 0:
        raise RuntimeError("Compositor configuration does not contain an output to folder '{0}'.".format(sImageType))
    elif len(lImageFolderFo) > 1:
        raise RuntimeError(
            "Compositor configuration contains more than one output to the folder '{0}'.".format(sImageType)
        )
    # endif
    dicImageFolderFo = lImageFolderFo[0]

    return dicImageFolderFo, sImageType


# enddef
