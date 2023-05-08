#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \actions\blend\render_std.py
# Created Date: Wednesday, April 21st 2021, 10:55:42 am
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
from catharsys.config.cls_config_list import CConfigList
from catharsys.plugins.std.action_class.manifest.cls_cfg_manifest_job import (
    CConfigManifestJob,
)

from catharsys.decs.decorator_ep import EntryPoint

from catharsys.util.cls_entrypoint_information import CEntrypointInformation

################################################################################
# Return action definition
def GetDefinition():
    return {
        "sDTI": "/catharsys/action-class/python/manifest-based:2.0",
        "sActionDTI": "/catharsys/action/std/blender/render/std:1.0",
        "sExecuteDTI": "exec/blender/*:*",
        "sProjectClassDTI": "/catharsys/project-class/std/blender/render:1.0",
        "sJobDistType": "frames;configs",
        "mArgs": {
            "iFrameFirst": {"sType": "int", "xDefault": 0},
            "iFrameLast": {"sType": "int", "xDefault": 0},
            "iRenderQuality": {"sType": "int", "xDefault": 4, "bOptional": True},
            "iConfigGroups": {"sType": "int", "xDefault": 1, "bOptional": True},
            "iFrameGroups": {"sType": "int", "xDefault": 1, "bOptional": True},
            "bDoProcess": {"sType": "bool", "xDefault": True, "bOptional": True},
        },
    }


# enddef

################################################################################
def ResultData(xJobCfg: CConfigManifestJob):
    from .lib.cls_render_result_data import CRenderResultData

    return CRenderResultData(xJobCfg=xJobCfg)


# enddef

################################################################################
# Has to be called from within Blender
@EntryPoint(CEntrypointInformation.EEntryType.COMMAND)
def Run(_xCfg: CConfigList):
    assertion.FuncArgTypes()

    from anybase.cls_any_error import CAnyError_Message
    from .lib.cls_render_std import CRenderStandard

    ####################################################################################
    def Render(_xPrjCfg, _dicCfg, **kwargs):

        iCfgIdx = kwargs.get("iCfgIdx")
        iCfgCnt = kwargs.get("iCfgCnt")
        if iCfgIdx is None or iCfgCnt is None:
            raise CAnyError_Message(
                sMsg="Render action parameters 'iCfgIdx' and 'iCfgCnt' not specified"
            )
        # endif

        xRender = CRenderStandard(xPrjCfg=_xPrjCfg, dicCfg=_dicCfg)
        xRender.Init()
        if xRender.Process() is True and iCfgIdx + 1 < iCfgCnt:
            xRender.Finalize()
        # endif

    # enddef
    ####################################################################################

    _xCfg.ForEachConfig(Render)

    lsQuit = _xCfg.GetArg("--quit-blender")
    if isinstance(lsQuit, list) and lsQuit[0].lower() == "true":
        # lazy import, needed only in exiting the application, but speed up execution not to import it every time
        import bpy

        if not bpy.app.background:
            bpy.ops.wm.quit_blender()
    # endif quit handling

# enddef
