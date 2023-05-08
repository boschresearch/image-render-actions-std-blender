#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \dev-import-object-type-hierarchy.py
# Created Date: Monday, December 5th 2022, 8:38:44 am
# Created by: Christian Perwass (CR/AEC5)
# <LICENSE id="All-Rights-Reserved">
# Copyright (c) 2022 Robert Bosch GmbH and its subsidiaries
# </LICENSE>
###

import bpy
import copy

from pathlib import Path
from anybase import file as anyfile
from anybase import config as anycfg
from anybase import util as anyutil
from anyblend import collection
import anyblend.object as anyobj
import anytruth.util as atu
import anytruth.ops_labeldb as atops
import catharsys.plugins.std.blender.generate.func.object_std as genobj


dicCln: dict = {
    "sPath": r"[path]\assets\objects\classes",
    "lCollectionHierarchy": ["Objects"],
}

pathTop: Path = Path(r"[path]\assets\objects\classes")
sObjectParsCfgName = "object-pars"


def CreatePerFolderHandler(
    _dicTypePathList: dict[str, list[Path]], _dicFolderCfg: dict[str, dict], _sObjectParsCfgName: str
):
    def Handler(_pathTop: Path, _sType: str) -> bool:

        dicCfg: dict = None

        sParentPath = _pathTop.parent.as_posix()
        dicParentCfg = _dicFolderCfg.get(sParentPath)
        if isinstance(dicParentCfg, dict):
            dicCfg = dicParentCfg
        # endif

        pathFileCfg: Path = _pathTop / _sObjectParsCfgName
        dicRes = anycfg.Load(
            pathFileCfg,
            bDoThrow=False,
            sDTI="/catharsys/blender/generate/collection/import/folder-type-hierarchy/per-folder-args:1",
        )

        if dicRes["bOK"] is True:
            if dicCfg is None:
                dicCfg = dicRes["dicCfg"]
            else:
                anyutil.DictRecursiveUpdate(dicCfg, dicRes["dicCfg"])
            # endif
        # endif

        if isinstance(dicCfg, dict):
            _dicFolderCfg[_pathTop.as_posix()] = dicCfg
        # endif

        for pathFile in _pathTop.iterdir():
            if not pathFile.is_file() or pathFile.suffix != ".obj":
                continue
            # endif

            # print(f"    {pathFile.name}")
            if _dicTypePathList.get(_sType) is None:
                _dicTypePathList[_sType] = [pathFile]
            else:
                _dicTypePathList[_sType].append(pathFile)
            # endif
        # endfor

        return True

    # enddef

    return Handler


# enddef

dicTypePathList = {}
dicFolderCfg = {}

dicTypeCfg = atu.GetTypeDictFromFolderHierarchy(
    pathTop, CreatePerFolderHandler(dicTypePathList, dicFolderCfg, sObjectParsCfgName)
)

# for sType in dicTypePathList:
#    print(f"{sType}: {(dicTypePathList[sType])}")
## endfor

pathTypes = pathTop / "anytruth-types.json"
anyfile.SaveJson(pathTypes, dicTypeCfg, iIndent=4)
atops.ImportLabelTypes(bpy.context, pathTypes.as_posix())

sTopCln = "Objects"
clnTop = collection.GetCollection(sTopCln)
# collection.SetActiveCollection(bpy.context, sTopCln)

dicImport = {
    "fScaleFactor": 0.01,
    "lLocation": [0, 0, 0],
    "mSetOrigin": {
        "bEnable": True,
        "sType": "ORIGIN_CENTER_OF_VOLUME",
        "sCenter": "MEDIAN",
    },
    "mSmoothSurface": {
        "bEnable": True,
        "fVoxelSize": 0.004,
    },
}


fDeltaX = 0.3
fDeltaY = -0.4

fOffsetX = -2.0
fOffsetY = -1.0

# print(dicFolderCfg)

for iTypeIdx, sType in enumerate(dicTypePathList):
    sClnName = f"{sTopCln};{sType}"
    collection.CreateCollection(bpy.context, sClnName, bActivate=True, clnParent=clnTop)
    atops.SetCollectionLabel(
        bpy.context, sCollectionName=sClnName, sLabelTypeId=sType, bHasLabel=True, sChildrenInstanceType="OBJECT"
    )

    lObjPaths: list[Path] = dicTypePathList[sType]

    dicCfg = copy.deepcopy(dicImport)
    dicObjCfg = dicFolderCfg.get(lObjPaths[0].parent.as_posix())
    #    print(f"Try {(lObjPaths[0].parent)} -> {(dicObjCfg)}\n")
    if dicObjCfg is not None:
        #        print(f"Load {(lObjPaths[0].parent)} -> {(dicObjCfg)}\n")
        anyutil.DictRecursiveUpdate(dicCfg, dicObjCfg)
    # endif

    for iObjIdx, pathObj in enumerate(lObjPaths):
        dicCfg["lLocation"] = [iObjIdx * fDeltaX + fOffsetX, iTypeIdx * fDeltaY + fOffsetY, 0.0]

        #        print(f"{(pathObj.parent)} -> {(dicCfg)}\n")
        genobj._DoImportObjectObj(pathObj, dicCfg)
    # endfor
# endfor
