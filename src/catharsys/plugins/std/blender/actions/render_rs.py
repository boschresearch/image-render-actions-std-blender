#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: /do-render-rs.py
# Created Date: Thursday, October 22nd 2020, 4:26:28 pm
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

from catharsys.plugins.std.action_class.manifest.cls_cfg_manifest_job import (
    CConfigManifestJob,
)

################################################################################
# Return action definition
def GetDefinition():
    return {
        "sDTI": "/catharsys/action-class/python/manifest-based:2.0",
        "sActionDTI": "/catharsys/action/std/blender/render/rs:1.0",
        "sExecuteDTI": "exec/blender/*:*",
        "sProjectClassDTI": "/catharsys/project-class/std/blender/render:1.0",
        "sJobDistType": "per-frame;configs",
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


def Run(_xCfg):

    from anybase.cls_any_error import CAnyError_Message
    from catharsys.config.cls_config_list import CConfigList
    from .lib.cls_render_rs import CRenderRollingShutter

    if not isinstance(_xCfg, CConfigList):
        raise CAnyError_Message(sMsg="Invalid configuration type")
    # endif

    ####################################################################################
    def Render(_xPrjCfg, _dicCfg, **kwargs):

        iCfgIdx = kwargs.get("iCfgIdx")
        iCfgCnt = kwargs.get("iCfgCnt")
        if iCfgIdx is None or iCfgCnt is None:
            raise RuntimeError(
                "Render action parameters 'iCfgIdx' and 'iCfgCnt' not specified"
            )
        # endif

        xRender = CRenderRollingShutter(xPrjCfg=_xPrjCfg, dicCfg=_dicCfg)
        xRender.Init()
        if xRender.Process() is True and iCfgIdx + 1 < iCfgCnt:
            xRender.Finalize()
        # endif

    # enddef
    ####################################################################################

    _xCfg.ForEachConfig(Render)


# enddef
