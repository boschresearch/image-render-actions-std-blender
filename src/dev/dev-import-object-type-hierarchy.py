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


from pathlib import Path
from anybase import file as anyfile
import anytruth.util as atu
from anybase import config as anycfg

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
        pathFileCfg: Path = _pathTop / _sObjectParsCfgName
        dicRes = anycfg.Load(
            pathFileCfg,
            bDoThrow=False,
            sDTI="/catharsys/blender/generate/object/import/folder-type-hierarchy/per-folder-args:1",
        )
        if dicRes["bOK"] is True:
            dicCfg = dicRes["dicCfg"]
        # endif

        if isinstance(dicCfg, dict):
            _dicFolderCfg[_pathTop.as_posix()] = dicCfg
        else:
            sPath = _pathTop.parent.as_posix()
            dicCfg = _dicFolderCfg.get(sPath)
            if isinstance(dicCfg, dict):
                _dicFolderCfg[_pathTop.as_posix()] = dicCfg
            # endif
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
#     print(f"{sType}: {(dicTypePathList[sType])}")
# # endfor

for sPath in dicFolderCfg:
    print(f"{sPath}: {(dicFolderCfg[sPath]['sId'])}")
# endfor

pathTypes = pathTop / "anytruth-types.json"
anyfile.SaveJson(pathTypes, dicTypeCfg, iIndent=4)
