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

import copy
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

import anyblend
from anyblend import collection

from anybase.cls_any_error import CAnyError_Message
from anybase import convert
from anybase import path as anypath
from anybase import file as anyfile
from anybase import config as anycfg
from anybase import util as anyutil
import anytruth.util as atu
import anytruth.ops_labeldb as atops

import ison
from ...modify import collections as modcln
from .object_std import _DoImportObjectObj
from anyblend import tools as anytools
from anyblend import viewlayer as anyvl

############################################################################################
def CreateCollections(_dicGenCln, **kwargs):

    dicClnObj = defaultdict(list)

    lCollections = _dicGenCln.get("lCollections")
    if lCollections is None:
        raise RuntimeError("Key 'lCollections' missing in create collection configuration")
    # endif

    for dicCln in lCollections:
        lClnTree = dicCln.get("lCollectionHierarchy")
        if lClnTree is None:
            raise RuntimeError("Key 'lCollectionHierarchy' missing in create collection configuration")
        # endif

        # Ensure that the root layer collection is active before creating a new collection
        anyblend.collection.MakeRootLayerCollectionActive(bpy.context)

        # Create the given collection hierarchy
        anyblend.collection.CreateCollectionHierarchy(bpy.context, lClnTree)

        xTrgCln = anyblend.collection.GetActiveCollection(bpy.context)

        # get collection modifier, if any
        lMods = dicCln.get("lModifiers")
        if lMods is not None:
            for dicMod in lMods:
                ison.util.data.AddLocalGlobalVars(dicMod, _dicGenCln, bThrowOnDisallow=False)
            # endfor

            # Apply all modifiers to collection
            modcln.ModifyCollection(xTrgCln, lMods)
        # endif

        dicClnObj[xTrgCln.name] = ["*"]
    # endfor

    return dicClnObj


# enddef


############################################################################################
def LoadCollections(_dicCln, **kwargs):

    dicClnObj = defaultdict(list)
    dicVars = kwargs.get("dicVars", {})

    sBlenderFilename = _dicCln.get("sBlenderFilename")
    if sBlenderFilename is None:
        raise RuntimeError("Key 'sBlenderFilename' missing in load collection configuration")
    # endif

    mCollections = _dicCln.get("mCollections")
    if mCollections is None:
        raise RuntimeError("Key 'mCollections' is missing in load collection configuration")
    # endif

    fExtUnitScale: float = convert.DictElementToFloat(_dicCln, "fMetersPerBlenderUnit", fDefault=1.0)
    fLocalUnitScale: float = bpy.context.scene.unit_settings.scale_length
    fImportScale = fExtUnitScale / fLocalUnitScale
    print(f"Scales: ext = {fExtUnitScale}, local = {fLocalUnitScale}, eff = {fImportScale}")

    # ### IMPORTANT ###
    # Loading the scene linked and then deleting it has
    # some unforseeable consequence, where the parenting of objects
    # can get lost. So we cannot extract the scale of the imported scene
    # easily.
    # #################

    # # Link default scene of external Blender file into this scene
    # # to obtain the unit scale of the external file.
    # with bpy.data.libraries.load(sBlenderFilename, link=True) as (xFrom, xTo):
    #     xTo.scenes = ["Scene"]
    # # endwith

    # fLocalUnitScale = bpy.context.scene.unit_settings.scale_length
    # fExtUnitScale = xTo.scenes[0].unit_settings.scale_length
    # fImportScale = fExtUnitScale / fLocalUnitScale
    # print(f"Scales: ext = {fExtUnitScale}, local = {fLocalUnitScale}, eff = {fImportScale}")

    # # Now remove the linked scene and its components
    # for xScn in xTo.scenes:
    #     # print(f"Scene: {xScn.name}")
    #     for xCln in xScn.collection.children:
    #         collection.RemoveCollection(xCln)
    #     # endfor
    # # endfor
    # bpy.data.scenes.remove(xTo.scenes[0])

    # Now we load everything we actually need.
    lImportClnNames = []
    with bpy.data.libraries.load(sBlenderFilename, link=False) as (data_from, data_to):
        for sSrcClnName in mCollections.keys():
            if sSrcClnName in data_from.collections:
                data_to.collections.append(sSrcClnName)
                lImportClnNames.append(sSrcClnName)
            # endif
        # endfor
    # endwith

    for clnImport, sImportClnName in zip(data_to.collections, lImportClnNames):

        dicTrgClnCfg = mCollections[sImportClnName]
        lTrgClnTree = dicTrgClnCfg.get("lCollectionHierarchy")
        if lTrgClnTree is None:
            raise RuntimeError("No target collection hierarchy given for source collection '{0}'".format(sSrcClnName))
        # endif
        sTrgClnName = ".".join(lTrgClnTree)

        # print(f"Children of {clnImport.name}")
        # for clnX in clnImport.children:
        #     print(f"{clnX.name}")
        # # endfor

        if sTrgClnName in bpy.data.collections and sTrgClnName != clnImport.name:
            # print(f"Moving to target collection {sTrgClnName}")
            # Move children to new collection and delete imported collection
            clnTrg = bpy.data.collections.get(sTrgClnName)
            for objX in clnImport.objects:
                clnImport.objects.unlink(objX)
                clnTrg.objects.link(objX)
                # Scale object by import scale and apply the scale
                anyblend.object.ScaleObject(objX, fImportScale, _bApply=True)
            # endif

            for clnX in clnImport.children:
                clnImport.children.unlink(clnX)
                clnTrg.children.link(clnX)
            # endif

            bpy.data.collections.remove(clnImport)

        elif sTrgClnName not in bpy.data.collections:
            # print(f"No name collision for {sTrgClnName}")
            # no name collision in dest collection name
            # simply add and rename

            if len(lTrgClnTree) > 1:
                anyblend.collection.CreateCollectionHierarchy(bpy.context, lTrgClnTree[0:-1])
                clnTrgParent = anyblend.collection.GetActiveCollection(bpy.context)
            else:
                clnTrgParent = anyblend.collection.GetRootCollection(bpy.context)
            # endif

            clnImport.name = sTrgClnName
            clnTrgParent.children.link(clnImport)
        else:
            # print(f"Just linking {clnImport.name}")
            bpy.context.scene.collection.children.link(clnImport)
        # endif

        # get collection modifier, if any
        lMods = dicTrgClnCfg.get("lModifiers")
        if lMods is not None:
            clnTrg = bpy.data.collections[sTrgClnName]

            # Apply all modifiers to collection
            modcln.ModifyCollection(clnTrg, lMods, dicVars=dicVars)
        # endif

        dicClnObj[sTrgClnName] = ["*"]
    # endfor

    # In case additional cameras were imported, update the camera list
    if hasattr(bpy.ops, "ac"):
        bpy.ops.ac.update_camera_obj_list()
        bpy.ops.ac.update_all_frustums()
    # endif

    return dicClnObj


# enddef


############################################################################################
def _CreatePerFolderHandler(
    _pathMain: Path,
    _dicTypePathList: dict[str, list[Path]],
    _dicFolderCfg: dict[str, dict],
    _sObjectParsCfgName: str = None,
    _lRePathInclude: list[str] = [".+"],
    _lRePathExclude: Optional[list[str]] = None,
):

    lCrePathInclude: list[re.Pattern] = []
    for sRe in _lRePathInclude:
        try:
            lCrePathInclude.append(re.compile(sRe))
        except Exception as xEx:
            raise CAnyError_Message(
                sMsg=f"Error compiling path include regular expression '{(str(sRe))}'", xChildEx=xEx
            )
        # endtry
    # endfor

    lCrePathExclude: list[re.Pattern] = []
    if isinstance(_lRePathExclude, list):
        for sRe in _lRePathExclude:
            try:
                lCrePathExclude.append(re.compile(sRe))
            except Exception as xEx:
                raise CAnyError_Message(
                    sMsg=f"Error compiling path exclude regular expression '{(str(sRe))}'", xChildEx=xEx
                )
            # endtry
        # endfor
    # endif

    print(lCrePathExclude)

    def Handler(_pathTop: Path, _sType: str) -> bool:

        pathRel = _pathTop.relative_to(_pathMain)
        sPathRel = pathRel.as_posix()

        # Check whether relative path is in include list
        rePath: re.Pattern
        bFound = False
        for rePath in lCrePathInclude:
            xMatch = rePath.match(sPathRel)
            if xMatch is not None:
                bFound = True
                break
            # endif
        # endfor
        if bFound is False:
            return False
        # endif

        # Check whether relative path is in exclude list
        bFound = False
        for rePath in lCrePathExclude:
            xMatch = rePath.match(sPathRel)
            if xMatch is not None:
                bFound = True
                break
            # endif
        # endfor
        if bFound is True:
            return False
        # endif

        dicCfg: dict = None
        sParentPath = _pathTop.parent.as_posix()
        dicParentCfg = _dicFolderCfg.get(sParentPath)
        if isinstance(dicParentCfg, dict):
            dicCfg = dicParentCfg
        # endif

        if isinstance(_sObjectParsCfgName, str):
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


############################################################################################
def ImportFolderTypeHierarchy(_dicCln, **kwargs):

    sPath: str = convert.DictElementToString(_dicCln, "sPath")
    pathTop: Path = anypath.MakeNormPath(Path(sPath).absolute())

    if not pathTop.exists():
        raise RuntimeError(f"Path not found for object import: {(pathTop.as_posix())}")
    # endif

    if not pathTop.is_dir():
        raise RuntimeError(f"Path does not reference a directory: {(pathTop.as_posix())}")
    # endif

    lClnTree = _dicCln.get("lCollectionHierarchy")
    if lClnTree is None:
        raise RuntimeError("Key 'lCollectionHierarchy' missing in create collection configuration")
    # endif

    sPerFolderConfigFilename: str = convert.DictElementToString(_dicCln, "sPerFolderConfigFilename", bDoRaise=False)

    lRePathInclude: list[str] = convert.DictElementToStringList(_dicCln, "lRePathInclude", lDefault=[".+"])
    lRePathExclude: list[str] = convert.DictElementToStringList(_dicCln, "lRePathExclude", bDoRaise=False)

    bDoSpreadObjects: bool = False
    dicSO: dict = _dicCln.get("mSpreadObjects")
    if dicSO is not None:
        bDoSpreadObjects = convert.DictElementToBool(dicSO, "bEnable", bDefault=True)
        lSpreadOrigin: list = convert.DictElementToFloatList(dicSO, "lOrigin", iLen=3, lDefault=[0.0, 0.0, 0.0])
        lSpreadRelativeDelta: list = convert.DictElementToFloatList(
            dicSO, "lRelativeDelta", iLen=3, lDefault=[2.0, 0.1, 0.2]
        )

        lSpreadDir: list = [[1, 0, 0], [1, 1, 0], [0, 0, 1]]
        lDir: list = dicSO.get("lDir")
        if isinstance(lDir, list):
            for iAxisIdx, lAxis in enumerate(lDir):
                if isinstance(lAxis, list):
                    lSpreadDir[iAxisIdx] = lAxis
                # endif
            # endfor
        # endif

        iSpreadMaxColCnt: int = convert.DictElementToInt(dicSO, "iMaxColumnCount", iDefault=0)
        bSpreadShowRowTitles: bool = convert.DictElementToBool(dicSO, "bShowRowTitles", bDefault=False)
        fSpreadRowTitleSize: float = convert.DictElementToFloat(dicSO, "fRowTitleSize", fDefault=1.0)
    # endif

    # ################################################################################
    # Process

    # Ensure that the root layer collection is active before creating a new collection
    collection.MakeRootLayerCollectionActive(bpy.context)

    # Create the given collection hierarchy
    collection.CreateCollectionHierarchy(bpy.context, lClnTree)

    clnTrg: bpy.types.Collection = anyblend.collection.GetActiveCollection(bpy.context)
    bIsExcluded = collection.IsExcluded(bpy.context, clnTrg.name)
    collection.ExcludeCollection(bpy.context, clnTrg.name, False)

    dicTypePathList = {}
    dicFolderCfg = {}

    dicTypeCfg = atu.GetTypeDictFromFolderHierarchy(
        pathTop,
        _CreatePerFolderHandler(
            pathTop, dicTypePathList, dicFolderCfg, sPerFolderConfigFilename, lRePathInclude, lRePathExclude
        ),
    )

    # for sType in dicTypePathList:
    #    print(f"{sType}: {(dicTypePathList[sType])}")
    # # endfor

    pathTypes = pathTop / "anytruth-types.json"
    anyfile.SaveJson(pathTypes, dicTypeCfg, iIndent=4)
    atops.ImportLabelTypes(bpy.context, pathTypes.as_posix())

    dicClnCreated: dict[str, list[str]] = {}

    for sType in dicTypePathList:
        sClnName = f"{clnTrg.name};{sType}"
        collection.CreateCollection(bpy.context, sClnName, bActivate=True, clnParent=clnTrg)
        atops.SetCollectionLabel(
            bpy.context, sCollectionName=sClnName, sLabelTypeId=sType, bHasLabel=True, sChildrenInstanceType="OBJECT"
        )

        lObjCreated = dicClnCreated[sClnName] = []
        lObjPaths: list[Path] = dicTypePathList[sType]

        dicCfg = copy.deepcopy(_dicCln)
        dicObjCfg = dicFolderCfg.get(lObjPaths[0].parent.as_posix())
        if dicObjCfg is not None:
            anyutil.DictRecursiveUpdate(dicCfg, dicObjCfg)
        # endif

        for pathObj in lObjPaths:
            collection.SetActiveCollection(bpy.context, sClnName)
            objIn = _DoImportObjectObj(pathObj, dicCfg)
            lObjCreated.append(objIn.name)
        # endfor
    # endfor

    if bDoSpreadObjects is True:
        anytools.SpreadObjectsIn2D(
            clnTrg.name,
            _lOffset=lSpreadOrigin,
            _lfRelDelta=lSpreadRelativeDelta,
            _lDirList=lSpreadDir,
            _iMaxColCnt=iSpreadMaxColCnt,
            _bShowRowTitles=bSpreadShowRowTitles,
            _fRowTitleSize=fSpreadRowTitleSize,
        )
    # endif

    collection.ExcludeCollection(bpy.context, clnTrg.name, bIsExcluded)

    return dicClnCreated


# enddef
