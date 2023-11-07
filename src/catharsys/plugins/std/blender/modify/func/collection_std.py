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

try:
    import _bpy
    import bpy
    import mathutils

    g_bInBlenderContext = True
except Exception:
    g_bInBlenderContext = False  # don't worry, but don't call anything from here
# endtry

import math
import re
import random

g_bHasAnyTruth = False

if g_bInBlenderContext is True:
    try:
        from anytruth import ops_labeldb

        g_bHasAnyTruth = True
    except Exception:
        g_bHasAnyTruth = False
    # endtry

    from anyblend import object as anyobj
    from anyblend import collection
    from anyblend import viewlayer
    from anyblend import points
    from anyblend.cls_instances import CInstances, _CInstance
    from anycam import ops as camops
# endif

from anybase.cls_anycml import CAnyCML
from anybase.cls_any_error import CAnyError, CAnyError_Message
from anybase import convert
from anybase import assertion
from anybase import config
import ison

from catharsys.decs.decorator_log import logFunctionCall

from .. import objects


################################################################################
def SetCollectionLabel(_clnX, _dicMod, **kwargs):
    assertion.IsTrue(g_bInBlenderContext)

    sLabelTypeId = _dicMod.get("sLabelTypeId")
    bHasLabel = _dicMod.get("bHasLabel", True)
    bIgnore = _dicMod.get("bIgnore", False)
    sChildrenInstanceType = _dicMod.get("sChildrenInstanceType")

    ops_labeldb.SetCollectionLabel(
        bpy.context,
        sCollectionName=_clnX.name,
        sLabelTypeId=sLabelTypeId,
        bHasLabel=bHasLabel,
        bIgnore=bIgnore,
        sChildrenInstanceType=sChildrenInstanceType,
    )


# enddef


################################################################################
@logFunctionCall
def ForEachObject(_clnX, _dicMod, **kwargs):
    """Apply list of modifiers to each object in collection. The set of objects
    can be specialized further with an object type and a regular expression for
    the object name.

     Args:
         _clnX (bpy.types.Collection): The collection.
         _dicMod (dict): Configuration dictionary (see below).

     Raises:
         RuntimeError: if configuration elements are missing.

     Configuration Args:
         lModifier (list(dict)): list of modifier configurations that are applied per object.
         lObjectTypes (list(string), optional): list of objects types that are to be taken into account.
                                                 By default all object types are allowed.
         sObjectNamePattern (string, optional): Only objects with names that match this regular expression
                                                 are taken into account. By default this is not applied.
    """
    sMode = kwargs.get("sMode", "INIT")
    dicVars = kwargs.get("dicVars", {})
    lObjectTypes = _dicMod.get("lObjectTypes")
    sObjNamePattern = _dicMod.get("sObjectNamePattern")

    lModifiers = _dicMod.get("lModifiers")
    if lModifiers is None:
        raise RuntimeError("Element 'lModifiers' missing for collection modifier '{}'".format(_dicMod.get("sType")))
    # endif

    for dicModFunc in lModifiers:
        if isinstance(dicModFunc, str):
            continue
        elif isinstance(dicModFunc, dict):
            ison.util.data.AddLocalGlobalVars(dicModFunc, _dicMod, bThrowOnDisallow=False)
        else:
            raise RuntimeError("Invalid object type in 'lModifiers' list")
        # endif
    # endfor

    reObj = None
    if sObjNamePattern is not None:
        reObj = re.compile(sObjNamePattern)
    # endif

    iIdx = 0

    # create a list of objects to process since
    # _clnX.objects might be mutated in an unsafe
    # way during the following loop
    # lObjectsToProcess = [objX for objX in _clnX.objects if lObjectTypes is not None and objX.type in lObjectTypes]
    lObjectsToProcess = collection.GetCollectionObjects(
        _clnX, _bChildren=False, _bRecursive=True, _lObjectTypes=lObjectTypes
    )

    for sObjName in lObjectsToProcess:
        objX = bpy.data.objects[sObjName]

        if reObj is not None and reObj.match(objX.name) is None:
            continue
        # endif

        dicIter = {"for-each-object": {"idx": iIdx, "name": objX.name}}

        xParser = CAnyCML(dicConstVars=dicIter)
        ldicActMod = xParser.Process(_dicMod, lProcessPaths=["lModifiers"])
        lActMod = ldicActMod[0]["lModifiers"]
        dicIter.update(dicVars)

        logFunctionCall.PrintLog(f"try to apply modifier to {objX.name} mode:'{sMode}'")
        objects.ModifyObject(objX, lActMod, sMode=sMode, dicVars=dicIter)

        iIdx += 1
    # endfor


# enddef


################################################################################
@logFunctionCall
def RndPlaceObjOnSurf(_clnX, _dicMod, **kwargs):
    """Place all objects and/or child collections in a given collection randomly onto surface.
       This can be specialized with a number of parameters:
       - Only place objects in the field of view of a given camera
       - Set a minimal/maximal distance from a camera
       - Set a minimal angular distance between objects as seen from a camera
       - Use a minimal and/or maximal distance between objects
       - Ensure that the object's bounding boxes do not overlap

       IMPORTANT:
            - At most one object will be placed on each target object face. That is, if the
              target object is a single plane, only one object can be placed. You can use a subdivision
              modifier to increase the number of faces to the desired resolution.
            - Do not use this function to distribute very large number of objects on a surface,
              like grass. Internally, each instance is created as a linked object and not as
              a Blender internal instance.

    Args:
        _clnX (bpy.types.Collection): The collection of objects that should be randomly placed on surface
        _dicMod (dict): A dictionary of placement parameters.

    Configuration Args:
        sTargetObject (str):
            The name of the target object. The collection objects will be placed on the surface
            of this object.

        lTargetObjects (list, optional):
            A list of target objects where to place source objects. Takes precedence over sTargetObject,
            if both are specified.

        sVertexGroup (str, optional):
            The name of the vertex group used for weighting the placement.
            If lTargetObjects is specified and no lVertexGroups, but sVertexGroup,
            the sVertexGroup name is used for all target objects.

        lVertexGroups (list[str], optional):
            A list of vertex groups, one per target object, that contain the respective
            vertex weighting.

        fMinimalDistance (float, optional):
            Minimal distance between objects. Defaults to zero.

        fMaximalDistance (float, optional):
            Maximal distance between objects. Defaults to no max. distance.

        lObjectTypes (list(str), optional):
            List of object type strings to place.

        iObjectInstanceCount (int, optional):
            Number of object instances to create. If set to zero (default), then each
            object is used once.

        sInstanceCollectionName (str, optional, default=None):
            Name of the newly created collection, if 'iObjectInstanceCount' is given.

        bCopyInstanceParentCollection (bool, optional, default=false):
            When instancing object, copy their respective parent collection including the collection's labelling,
            and place the instanced object in the copied collection, which is parented to the target collection.
            Only used if 'iObjectInstanceCount' is given.

        lOffset (list(float), optional):
            Position offset for evaluated positions.

        iSeed (int, optional):
            Random seed for placement of objects. Default is zero.

        fMinHorizViewAngleSep_deg (float, optional, default=0.0):
            The minimal horizontal view angle separation in degrees of the generated points.

        bFilterPolygons (bool, optional, default=false, only version 2.0):
            If true, weights all polygon vertices by the camera FoV and camera distance constraints.
            In this way, polygons that are outside the camera FoV or distance constraints will not
            be used for finding randomized points. This speeds up the search for points dramatically.
            Only works if the target surface has more than 4 polygons.

        bUseCameraFov (bool, optional, default=false):
            Constrains points to the camera field-of-view, if set to true.
            If the camera has been created with AnyCam, the FoV is obtained from the
            AnyCam meta information for non-standard cameras.

        lCamDistRange (list[float], optional, default=[0, inf]):
            Minimal and maximal distance from camera that are allowed.

        lCamFovBorderAngle_deg (list[float], optional, default=[0.0, 0.0]):
            Reduces the camera field of view used, by the given amounts for horizontal
            and vertical FoV. Only used when 'bUseCameraFov' is true.

        bUseBoundBox (bool, optional, default=false):
            If set to true, uses the bounding boxes of the objects passed in "lObjects"
            to determine their minimal distance. Defaults to false.

        xInstanceOrigin (list[float] or str, optional, default=[0,0,-0.5]):
            If it is a list it gives the origin of the instances' bounding box relative to their centers.
                For example, [0,0,-0.5] is the center of the bottom plane,
                and [0,0,0] is the center of the bounding box.
            If it is a string it can be one of the following:
                - "ORIG": uses the instance's origin for placement and not the bounding box

        sInstanceType (str, optional, default=CHILD_OBJ):
            Determines how the collection "_clnX" is instantiated.
            Has to be one of the following values: [OBJECT|CHILD_OBJ|CHILD_CLN]
            - OBJECT: The whole collection is regarded as one object.
            - CHILD_OBJ: All objects in the collection and all objects in its' child collections are separate objects.
            - CHILD_CLN: All objects in the collection and all child collections are separate objects.
                         That is, the child collections are regarded as single objects.

        bCopyInstanceParentCollection (bool, optional, default=false):
            When instancing object, copy their respective parent collection including the collection's labelling,
            and place the instanced object in the copied collection, which is parented to the target collection.

        lObstacles (list[dict], optional, default=None):
            Only used when bUseBoundBox is true. List of objects or collections of objects whose bounding boxes
            will not be intersected by the object's bounding boxes. Each element in the list
            must have one of the following element types:
            { "sCln": "[Collection name]", "sInstType": "[OBJECT|CHILD_OBJ|CHILD_CLN]" }
            { "sObj": "[Object name]"}
            'sInstType' values have the following meanings if 'sName' referes to a collection:
            - OBJECT: The whole collection is regarded as one object.
            - CHILD_OBJ: All objects in the collection and all objects in its' child collections are separate objects.
            - CHILD_CLN: All objects in the collection and all child collections are separate objects.
                         That is, the child collections are regarded as single objects.

        iMaxTrials (int, optional, default=20):
            Number of times a random point is generated and tested as a valid position.
            If, after this number of trials no valid point is found, the respective
            object is not moved.

        lInstRndRotEulerRange_deg (list[list[float]], optional, default=None):
            Random instance rotation Euler Angle ranges. List of three
            lists of two values, giving the rotation range per Euler angle
            in degrees.

        lInstRndRotOriginOffset (list[float], optional, default=[0,0,-0.5]):
            Rotation origin offset relative to bounding box center of instances,
            along bounding box axes. The bounding box center is [0,0,0], the center
            of the bottom (-Z) bounding box plane is [0,0,-0.5].

        bInstDrawBoundingBoxes (bool, optional, default=False):
            Generates bounding box as hidden object for each instance if true.

        bObstDrawBoundingBoxes (bool, optional, default=False):
            Generates bounding box as hidden object for each obstacle if true.
    """

    assertion.IsTrue(g_bInBlenderContext)

    try:
        # Get required elements
        lTrgObjNames = []
        sTrgObjName = convert.DictElementToString(_dicMod, "sTargetObject", bDoRaise=False)
        if isinstance(sTrgObjName, str):
            lTrgObjNames.append(sTrgObjName)
            sVexGrpName = convert.DictElementToString(_dicMod, "sVertexGroup", bDoRaise=False)
            if isinstance(sVexGrpName, str):
                lVexGrpNames = [sVexGrpName]
            else:
                lVexGrpNames = None
            # endif

        else:
            lTrgObjNames = convert.DictElementToStringList(_dicMod, "lTargetObjects")
            lVexGrpNames = convert.DictElementToStringList(_dicMod, "lVertexGroups", bDoRaise=False)
            if not isinstance(lVexGrpNames, list):
                sVertexGroup = convert.DictElementToString(_dicMod, "sVertexGroup", bDoRaise=False)
                if isinstance(sVertexGroup, str):
                    lVexGrpNames = [sVertexGroup] * len(lTrgObjNames)
                else:
                    lVexGrpNames = None
                # endif
            else:
                if len(lVexGrpNames) != len(lTrgObjNames):
                    raise RuntimeError("Different numbers of target object names and vertex groups")
                # endif
            # endif
        # endif

        # Optional elements
        sParentObjName = convert.DictElementToString(_dicMod, "sParentObject", bDoRaise=False)

        iSeed = convert.DictElementToInt(_dicMod, "iSeed", iDefault=0)
        iMaxTrials = convert.DictElementToInt(_dicMod, "iMaxTrials", iDefault=20)
        lObjectTypes = _dicMod.get("lObjectTypes")
        iObjectInstanceCount = convert.DictElementToInt(_dicMod, "iObjectInstanceCount", iDefault=0)
        bCopyInstanceParentCollection: bool = convert.DictElementToBool(
            _dicMod, "bCopyInstanceParentCollection", bDefault=False
        )

        sInstanceCollectionName = convert.DictElementToString(
            _dicMod, "sInstanceCollectionName", sDefault=f"{_clnX.name} instantiated"
        )
        sInstanceType = convert.DictElementToString(_dicMod, "sInstanceType", sDefault="CHILD_OBJ")
        bInstDrawBoundingBoxes = convert.DictElementToBool(_dicMod, "bInstDrawBoundingBoxes", bDefault=False)
        bObstDrawBoundingBoxes = convert.DictElementToBool(_dicMod, "bObstDrawBoundingBoxes", bDefault=False)

        fMinDist = convert.DictElementToFloat(_dicMod, "fMinimalDistance", fDefault=0.0)
        fMaxDist = convert.DictElementToFloat(_dicMod, "fMaximalDistance", fDefault=math.inf)
        fMinHorizViewAngleSep_deg = convert.DictElementToFloat(_dicMod, "fMinHorizViewAngleSep_deg", fDefault=0.0)
        bFilterPolygons = convert.DictElementToBool(_dicMod, "bFilterPolygons", bDefault=False)
        bUseCameraFov = convert.DictElementToBool(_dicMod, "bUseCameraFov", bDefault=False)
        lCamFovBorderAngle_deg = convert.DictElementToFloatList(
            _dicMod, "lCamFovBorderAngle_deg", iLen=2, lDefault=[0.0, 0.0]
        )
        lCamDistRange = convert.DictElementToFloatList(_dicMod, "lCamDistRange", iLen=2, lDefault=[0.0, math.inf])

        bUseBoundBox = convert.DictElementToBool(_dicMod, "bUseBoundBox", bDefault=False)
        xInstanceOrigin = _dicMod.get("xInstanceOrigin")
        if not isinstance(xInstanceOrigin, str):
            xInstanceOrigin = convert.DictElementToFloatList(_dicMod, "xInstanceOrigin", iLen=3, lDefault=[0.0, 0.0, -0.5])
        # endif

        random.seed(iSeed)
        lValidInstTypes = ["OBJECT", "CHILD_OBJ", "CHILD_CLN"]

        # ##############################################################################
        # Random instance rotation range
        lInstRndRotEulerRange_rad = None
        lInstRndRotEulerRange_deg = _dicMod.get("lInstRndRotEulerRange_deg")
        if isinstance(lInstRndRotEulerRange_deg, list):
            if len(lInstRndRotEulerRange_deg) != 3:
                raise RuntimeError(
                    "Expect 'lInstRndRotEulerRange_deg' element to be a list of three lists of two float values"
                )
            # endif
            lInstRndRotEulerRange_rad = []
            for lRange_deg in lInstRndRotEulerRange_deg:
                if not isinstance(lRange_deg, list):
                    raise RuntimeError(
                        "Expect 'lInstRndRotEulerRange_deg' element to be a list of three lists of two float values"
                    )
                # endif
                lRange_rad = []
                for xValue in lRange_deg:
                    lRange_rad.append(math.radians(convert.ToFloat(xValue)))
                # endfor
                lInstRndRotEulerRange_rad.append(lRange_rad)
            # endfor
        # endif

        lInstRndRotOriginOffset = convert.DictElementToFloatList(
            _dicMod, "lInstRndRotOriginOffset", iLen=3, lDefault=[0.0, 0.0, -0.5]
        )

        # ##############################################################################
        # Initialize obstacle instances
        lObstacles = _dicMod.get("lObstacles")
        xObstacles = CInstances(_sName=f"{_clnX.name} Obstacles")
        if bUseBoundBox is True and isinstance(lObstacles, list):
            for dicObst in lObstacles:
                if not isinstance(dicObst, dict):
                    raise RuntimeError("Elements of obstacles list must be dictionaries")
                # endif

                objX = None
                clnX = None

                if "sObj" in dicObst:
                    sName = convert.DictElementToString(dicObst, "sObj")
                    objX = bpy.data.objects.get(sName)
                    if objX is None:
                        raise RuntimeError(f"Obstacle object '{sName}' not available")
                    # endif

                    xObstacles.AddObject(_objX=objX)

                elif "sCln" in dicObst:
                    sName = convert.DictElementToString(dicObst, "sCln")
                    clnX = bpy.data.collections.get(sName)
                    if clnX is None:
                        raise RuntimeError(f"Obstacle collection '{sName}' not available")
                    # endif
                    sInstType = convert.DictElementToString(dicObst, "sInstType")
                    if sInstType == "OBJECT":
                        xObstacles.AddCollection(_clnX=clnX)
                    elif sInstType == "CHILD_OBJ":
                        xObstacles.AddCollectionElements(_clnX=clnX, _bChildCollectionsAsInstances=False)
                    elif sInstType == "CHILD_CLN":
                        xObstacles.AddCollectionElements(_clnX=clnX, _bChildCollectionsAsInstances=True)
                    else:
                        raise RuntimeError(f"Element 'sInstType' must be one of: {lValidInstTypes}")
                    # endif

                else:
                    raise RuntimeError("Neither 'sObj' nor 'sCln' are given in obstacle specification")
                # endif
            # endfor obstacles
        # endif

        if bObstDrawBoundingBoxes is True:
            for xObst in xObstacles:
                objBox: bpy.types.Object = xObst.xBoundBox.CreateBlenderObject(
                    _sName=f"_box_{xObst.sName}", _xCollection=collection.GetRootCollection(bpy.context)
                )
                objBox.hide_render = True
        # endif

        lOffset = convert.DictElementToFloatList(_dicMod, "lOffset", iLen=3, lDefault=[0.0, 0.0, 0.0])
        vOffset = mathutils.Vector(lOffset)

        xInstances = CInstances(_sName=_clnX.name)
        if sInstanceType == "OBJECT":
            xInstances.AddCollection(_clnX=_clnX, _lObjectTypes=lObjectTypes)
        elif sInstanceType == "CHILD_OBJ":
            xInstances.AddCollectionElements(_clnX=_clnX, _bChildCollectionsAsInstances=False, _lObjectTypes=lObjectTypes)
        elif sInstanceType == "CHILD_CLN":
            xInstances.AddCollectionElements(_clnX=_clnX, _bChildCollectionsAsInstances=True, _lObjectTypes=lObjectTypes)
        else:
            raise RuntimeError(f"Element 'sInstanceType' has to be one of: {lValidInstTypes}")
        # endif

        iObjCnt = len(xInstances)

        if iObjCnt == 0:
            return
        # endif

        # ######################################################################################
        # Create random instances

        def SetInstanceParentCollection(_xInst: _CInstance, _clnParentInst: bpy.types.Collection) -> bpy.types.Collection:
            global g_bHasAnyTruth

            clnParent = _xInst.GetParentCollection()
            sParentName = clnParent.name
            if ";" in sParentName:
                sParentName = sParentName[sParentName.index(";") + 1 :]
            # endif
            sInstClnName = f"{_clnParentInst.name};{sParentName}"
            clnInst = bpy.data.collections.get(sInstClnName)
            if clnInst is None:
                clnInst = collection.CreateCollection(bpy.context, sInstClnName, clnParent=_clnParentInst)
            # endif

            if g_bHasAnyTruth is True:
                ops_labeldb.CopyCollectionLabel(_sClnNameTrg=clnInst.name, _sClnNameSrc=clnParent.name)
            # endif

            return clnInst

        # enddef

        def CreateSetInstanceParentObjectHandler(_sParentObjName: str):
            def Handler(_xInst: _CInstance, _clnParentInst: bpy.types.Collection):
                # print(f"Setting parent '{_sParentObjName}' for instance '{_xInst.sName}'")
                _xInst.ParentTo(_sParentObjName, _bKeepTransform=True)

            # enddef
            return Handler

        # enddef

        funcProcInstance = None
        if isinstance(sParentObjName, str):
            funcProcInstance = CreateSetInstanceParentObjectHandler(sParentObjName)
        # endif

        xPlaceInst: CInstances
        if iObjectInstanceCount > 0:
            if bCopyInstanceParentCollection is True:
                xPlaceInst = xInstances.CreateRandomInstances(
                    _iInstanceCount=iObjectInstanceCount,
                    _bLinked=True,
                    _sName=sInstanceCollectionName,
                    _funcGetTargetCollection=SetInstanceParentCollection,
                    _funcProcInstance=funcProcInstance,
                )
            else:
                xPlaceInst = xInstances.CreateRandomInstances(
                    _iInstanceCount=iObjectInstanceCount,
                    _bLinked=True,
                    _sName=sInstanceCollectionName,
                    _funcProcInstance=funcProcInstance,
                )
            # endif

            # Exclude source collection
            collection.ExcludeCollection(bpy.context, _clnX.name, _bExclude=True)
        else:
            xPlaceInst = xInstances
        # endif

        # ######################################################################################
        # Randomly rotate instances
        if lInstRndRotEulerRange_rad is not None:
            xInst: _CInstance
            for xInst in xPlaceInst:
                lAngles_rad = [
                    random.uniform(lInstRndRotEulerRange_rad[i][0], lInstRndRotEulerRange_rad[i][1]) for i in range(3)
                ]
                xInst.RotateEuler(_lEulerAngles=lAngles_rad, _bAnglesInDeg=False, _lOriginOffset=lInstRndRotOriginOffset)
            # endfor
            viewlayer.Update()
        # endif

        iObjCnt = len(xPlaceInst)
        # print(f"Using {iObjCnt} instances")
        # logFunctionCall.PrintLog(f"Found {iObjCnt} objects in collection {_clnX.name}")

        if fMinHorizViewAngleSep_deg > 0.0 or bUseCameraFov is True:
            dicCamera = camops.GetAnyCam(bpy.context, bpy.context.scene.camera.name)
            lCamFov_deg = camops.GetAnyCamFov_deg(dicCamera["objCam"], dicCamera["dicAnyCam"])
            matCamWorld = dicCamera["objCam"].matrix_world
        else:
            matCamWorld = None
            lCamFov_deg = None
        # endif

        iMajorVersion = config.CheckDti(
            _dicMod.get("sDTI"), "/catharsys/blender/modify/collection/object-placement/rnd-surf"
        )["lCfgVer"][0]

        if iMajorVersion == 2:
            dicPnts = points.GetRndPointsOnSurfaceUniformly(
                lTrgObjNames=lTrgObjNames,
                iPntCnt=iObjCnt,
                lVexGrpNames=lVexGrpNames,
                fMinDist=fMinDist,
                fMaxDist=fMaxDist,
                iSeed=iSeed + 1,
                fMinHorizViewAngleSep_deg=fMinHorizViewAngleSep_deg,
                bUseCameraFov=bUseCameraFov,
                lCamFovBorder_deg=lCamFovBorderAngle_deg,
                lCamFov_deg=lCamFov_deg,
                lCamDistRange=lCamDistRange,
                matCamWorld=matCamWorld,
                bUseBoundBox=bUseBoundBox,
                xInstanceOrigin=xInstanceOrigin,
                xInstances=xPlaceInst,
                xObstacles=xObstacles,
                iMaxTrials=iMaxTrials,
                bFilterPolygons=bFilterPolygons,
            )
        else:
            dicPnts = points.GetRndPointsOnSurface(
                lTrgObjNames=lTrgObjNames,
                iPntCnt=iObjCnt,
                lVexGrpNames=lVexGrpNames,
                fMinDist=fMinDist,
                fMaxDist=fMaxDist,
                iSeed=iSeed + 1,
                fMinHorizViewAngleSep_deg=fMinHorizViewAngleSep_deg,
                bUseCameraFov=bUseCameraFov,
                lCamFovBorder_deg=lCamFovBorderAngle_deg,
                lCamFov_deg=lCamFov_deg,
                lCamDistRange=lCamDistRange,
                matCamWorld=matCamWorld,
                bUseBoundBox=bUseBoundBox,
                xInstanceOrigin=xInstanceOrigin,
                xInstances=xPlaceInst,
                xObstacles=xObstacles,
                iMaxTrials=iMaxTrials,
            )

        iFoundCnt = sum([1 if x is not None else 0 for i, x in dicPnts.items()])

        if iObjCnt > iFoundCnt:
            print(f"WARNING: Only {iFoundCnt} of {iObjCnt} objects could be distributed")
        # endif

        if bInstDrawBoundingBoxes is True and isinstance(sInstanceCollectionName, str):
            clnTrg = bpy.data.collections.get(sInstanceCollectionName)
            if clnTrg is None:
                clnTrg = collection.GetRootCollection(bpy.context)
            # endif
        # endif

        # There may be less points than objects, if the minimal distance is too large.
        for sName, vPos in dicPnts.items():
            xInst = xPlaceInst[sName]
            # print("Applying location to object '{}': {}".format(objX.name, tuple(objX.location)))

            if vPos is None:
                print(f"WARNING: Hiding object '{xInst.sName}'")
                xInst.Hide(True)

            else:
                xInst.MoveLocation(vPos + vOffset)
                if bInstDrawBoundingBoxes is True:
                    objBox: bpy.types.Object = xInst.xBoundBox.CreateBlenderObject(
                        _sName=f"_box_{xInst.sName}", _xCollection=clnTrg
                    )
                    objBox.hide_render = True
                # endif
            # endif
        # endfor

        viewlayer.Update()
    except Exception as xEx:
        import traceback
        print(traceback.format_exc(), flush=True)

        raise CAnyError_Message(sMsg="Error running random placement modifier", xChildEx=xEx)
    # endtry

# enddef


################################################################################
def MoveObjectToCollection(_clnX, _dicMod, **kwargs):
    """Moves object/list of objects to collection
    Parameters:
    sObj (string): Name of an object to be moved
    lObj:(list of Strings): List of object names to be moved
    bSkipNonexistingObject (bool,optional,default=false): Control how to handle missing objects,
        false: throw an error
        true: skip object
    """

    assertion.IsTrue(g_bInBlenderContext)

    bSkipNonexistingObject = convert.DictElementToBool(_dicMod, "bSkipNonexistingObject", bDefault=False)

    # handling list parameter of objects, if nothing passed start with empty list
    lObj = convert.DictElementToStringList(_dicMod, "lObj", lDefault=[])

    # get single string parameter object, add to list if present
    sObj = convert.DictElementToString(_dicMod, "sObj", sDefault=None, bDoRaise=False)

    if sObj is not None:
        lObj.append(sObj)

    # get actual objects from string arguments
    xObjects = [bpy.data.objects.get(sObj) for sObj in lObj]
    # Change active Collection
    collection.SetActiveCollection(bpy.context, _clnX.name)

    for xObj, sObjName in zip(xObjects, lObj):
        if xObj is None:
            if not bSkipNonexistingObject:
                raise RuntimeError(f"Object '{sObjName}' to be moved to collection does not exist!")
            else:
                print(f"WARNING: Object '{sObjName}' to be moved to collection does not exist! Skipping modifier")
            # endif
        else:
            # Move Object to active collection, unless it already is a member
            if _clnX.objects.get(xObj.name) is None:
                collection.MoveObjectToActiveCollection(bpy.context, xObj)
        # endif


# enddef
