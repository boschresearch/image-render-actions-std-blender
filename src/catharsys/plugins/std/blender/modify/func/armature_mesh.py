#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \armature_mesh.py
# Created Date: Friday, August 12th 2022, 3:53:42 pm
# Created by: Christian Perwass (CR/AEC5)
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

import enum
import bpy
import mathutils
import re
import math
from typing import Optional, Union

from anybase.cls_any_error import CAnyError_Message
from anybase import convert
from anyblend.object import CreateEvaluatedMeshObject
from anyblend import collection as anycln
from anyblend.app.file import IterUsers


####################################################################################
def _ScaleImageNodes(*, clnNodes, setOldImageNames, setOldGroupNames, fImgScale):

    # Find all images used by texture image nodes
    for nodX in clnNodes:
        if nodX.type == "GROUP":
            ngX = nodX.node_tree
            sNewGroupName = f"Baked;{ngX.name}"

            if sNewGroupName in bpy.data.node_groups:
                ngY = bpy.data.node_groups[sNewGroupName]

            else:
                setOldGroupNames.add(ngX.name)

                ngY = ngX.copy()
                ngY.name = sNewGroupName

                _ScaleImageNodes(
                    clnNodes=ngY.nodes,
                    setOldImageNames=setOldImageNames,
                    setOldGroupNames=setOldGroupNames,
                    fImgScale=fImgScale,
                )
            # endif
            nodX.node_tree = ngY
            continue

        elif nodX.type != "TEX_IMAGE":
            continue
        # endif

        if nodX.image is None:
            continue
        # endif

        if nodX.image.name.startswith("Baked;"):
            continue
        # endif

        sNewImgName = f"Baked;{nodX.image.name}"
        if sNewImgName in bpy.data.images:
            imgSmall = bpy.data.images[sNewImgName]

        else:
            setOldImageNames.add(nodX.image.name)

            # Copy image
            imgSmall = nodX.image.copy()
            imgSmall.name = sNewImgName

            tSize = tuple(imgSmall.size)
            tNewSize = tuple((int(float(x) * fImgScale) for x in tSize))

            print(
                f">> Scaling image '{nodX.image.name}': {tSize} -> {tNewSize}",
                flush=True,
            )

            imgSmall.scale(tNewSize[0], tNewSize[1])
            imgSmall.pack()
        # endif

        nodX.image = imgSmall
    # endfor


# enddef


####################################################################################
def _BakeMaterial(*, matX, setOldMaterialNames, setOldImageNames, setOldGroupNames, fImgScale):

    # copy material
    sNewMatName = f"Baked;{matX.name}"
    if sNewMatName in bpy.data.materials:
        matY = bpy.data.materials[sNewMatName]

    else:
        setOldMaterialNames.add(matX.name)

        matY = matX.copy()
        matY.name = sNewMatName
        _ScaleImageNodes(
            clnNodes=matY.node_tree.nodes,
            setOldImageNames=setOldImageNames,
            setOldGroupNames=setOldGroupNames,
            fImgScale=fImgScale,
        )

    # endif

    return matY


# enddef


####################################################################################
def _SetDecimatePars(*, modDecimate, dicDecimate: dict, sObjectName: str):

    sDecType = dicDecimate.get("sType", "UNSUBDIV")
    if sDecType not in ["COLLAPSE", "UNSUBDIV", "PLANAR"]:
        raise CAnyError_Message(
            sMsg=f"Decimate type for mesh object '{sObjectName}' has to be one of ['COLLAPSE', 'UNSUBDIV', 'PLANAR']"
        )
    # endif

    if sDecType == "UNSUBDIV":
        modDecimate.decimate_type = sDecType
        modDecimate.iterations = convert.DictElementToInt(dicDecimate, "iIterations", iDefault=3)

    elif sDecType == "COLLAPSE":
        modDecimate.decimate_type = sDecType
        modDecimate.ratio = convert.DictElementToFloat(dicDecimate, "fRatio", fDefault=0.1)

    elif sDecType == "PLANAR":
        modDecimate.decimate_type = "DISSOLVE"
        modDecimate.angle_limit = math.radians(convert.DictElementToFloat(dicDecimate, "fAngleLimit_deg", fDefault=5.0))
        modDecimate.use_dissolve_boundaries = convert.DictElementToBool(
            dicDecimate, "bUseAllBoundaries", bDefault=False
        )
    # endif


# enddef


####################################################################################
def _SetRemeshPars(*, modRemesh, dicRemesh: dict, sObjectName: str):

    sModType = dicRemesh.get("sType")
    if sModType not in ["VOXEL", "SHARP", "SMOOTH", "BLOCKS"]:
        raise CAnyError_Message(
            sMsg=f"Remesh type for mesh object '{sObjectName}' has to be one of ['VOXEL', 'SHARP', 'SMOOTH', 'BLOCKS']"
        )
    # endif

    modRemesh.mode = sModType

    if sModType == "VOXEL":
        modRemesh.voxel_size = convert.DictElementToFloat(dicRemesh, "fVoxelSize", fDefault=0.01)
        modRemesh.adaptivity = convert.DictElementToFloat(dicRemesh, "fAdaptivity", fDefault=0.0)
        modRemesh.use_smooth_shade = convert.DictElementToBool(dicRemesh, "bSmoothShade", bDefault=False)

    # endif


# enddef


############################################################################################
def BakeMesh(_objX, _dicMod, **kwargs):

    sModType = _dicMod.get("sType", _dicMod.get("sDTI"))

    if _objX.type != "ARMATURE":
        raise CAnyError_Message(sMsg=f"Object '{_objX.name}' is not an armature in modifier '{sModType}'")
    # endif

    bpy.context.view_layer.update()

    dicDefMeshSet = {
        "sReNameFilter": ".+",
        "bOnlyDecimateIfNoHair": True,
        "mDecimate": {"sType": "COLLAPSE", "fRatio": 0.1},
        "mPartSysHair": {
            "fChildCountFactor": 0.1,
            "iMaxChildCount": 5,
            "sConvertType": "MESH",
            "fCurveBevelDepth": 0.0005,
            "iCurveBevelResolution": 1,
            "mDecimate": {"sType": "COLLAPSE", "fRatio": 0.1},
        },
    }

    lMeshSettings: list = _dicMod.get("lMeshSettings", [])
    if not isinstance(lMeshSettings, list):
        raise CAnyError_Message(sMsg="Element 'lMeshSettings' is not a list")
    # endif
    lMeshSettings.append(dicDefMeshSet)

    setOldMaterialNames = set()
    setOldImageNames = set()
    setOldGroupNames = set()

    clnX = anycln.FindCollectionOfObject(bpy.context, _objX)
    anycln.SetActiveCollection(bpy.context, clnX.name)

    # Get Dependency graph
    # xDG = bpy.context.evaluated_depsgraph_get()

    print(
        "\nMODIFIER: /catharsys/blender/modify/object/armature/bake-mesh:1.0\n",
        flush=True,
    )

    # Loop over all meshes of armature
    for objMesh in _objX.children:
        if objMesh.type != "MESH":
            continue
        # endif

        dicMeshSet = None
        # Find mesh settings whose name filter fits to current mesh
        for dicSet in lMeshSettings:
            sReNameFilter = dicSet.get("sReNameFilter")
            if sReNameFilter is None:
                raise CAnyError_Message(
                    sMsg="Mesh settings for armature bake mesh modifier has no element 'sReNameFilter'"
                )
            # endif

            if re.match(sReNameFilter, objMesh.name) is not None:
                dicMeshSet = dicSet
                break
            # endif
        # endfor

        if dicMeshSet is None:
            raise CAnyError_Message(sMsg=f"Mesh object '{objMesh.name}' does not satisfy any mesh settings filter")
        # endif

        fImageScale: float = convert.DictElementToFloat(dicMeshSet, "fImageScale", fDefault=0.1)
        dicDecimate: Optional[dict] = dicMeshSet.get("mDecimate")
        bOnlyDecimateIfNoHair = convert.DictElementToBool(dicMeshSet, "bOnlyDecimateIfNoHair", bDefault=False)
        bDecimateMesh = isinstance(dicDecimate, dict)

        dicPartSysHair: Optional[dict] = dicMeshSet.get("mPartSysHair")
        if isinstance(dicPartSysHair, dict):
            bProcessPartSysHair = True
            sPartSysHairConvertType: str = convert.DictElementToString(dicPartSysHair, "sConvertType", sDefault="NONE")
            fChildCountFactor: float = convert.DictElementToFloat(dicPartSysHair, "fChildCountFactor", fDefault=1.0)
            iMaxChildCount: int = convert.DictElementToInt(dicPartSysHair, "iMaxChildCount", iDefault=10000)
            fCurveBevelDepth: float = convert.DictElementToFloat(dicPartSysHair, "fCurveBevelDepth", fDefault=0.0005)
            iCurveBevelResolution: int = convert.DictElementToInt(dicPartSysHair, "iCurveBevelResolution", iDefault=1)
            dicPartDecimate: Optional[dict] = dicPartSysHair.get("mDecimate")
            dicPartRemesh: Optional[dict] = dicPartSysHair.get("mRemesh")
        else:
            bProcessPartSysHair = False
            fChildCountFactor = None
            iMaxChildCount = None
            fCurveBevelDepth = None
            iCurveBevelResolution = None
            sConvertType = None
            dicPartDecimate = None
            dicPartRemesh = None
        # endif

        print(f"\n>> Processing Mesh '{objMesh.name}'", flush=True)
        bpy.context.view_layer.objects.active = objMesh

        sName = f"{objMesh.name}"
        sBakeName = f"Baked;{objMesh.name}"
        objEval = bpy.data.objects.get(sBakeName)
        if objEval is not None:
            bpy.data.objects.remove(objEval)
        # endif

        # Process all hair particle systems of mesh if needed
        lPsNames = []
        lObjPartMesh = []
        lObjPartMeshVexGrps = []
        iPartSysHairCnt = 0
        for modX in objMesh.modifiers:
            if modX.type != "PARTICLE_SYSTEM":
                continue
            # endif

            partsysX = modX.particle_system
            psetX = partsysX.settings
            if psetX.type != "HAIR":
                continue
            # endif

            iPartSysHairCnt += 1

            sMatName = str(psetX.material_slot)
            print(
                f">> Processing particle system '{modX.name}, {partsysX.name}' with material '{sMatName}'",
                flush=True,
            )

            if sMatName in bpy.data.materials:
                print(f">>>> Processing material '{sMatName}'")
                matBaked = _BakeMaterial(
                    matX=bpy.data.materials[sMatName],
                    fImgScale=fImageScale,
                    setOldMaterialNames=setOldMaterialNames,
                    setOldGroupNames=setOldGroupNames,
                    setOldImageNames=setOldImageNames,
                )
            # endif

            if bProcessPartSysHair is True:
                print(f">>>> Scaling hair child count by factor {fChildCountFactor} to max {iMaxChildCount} children")
                iChildCnt = psetX.rendered_child_count
                iChildCnt = int(round(float(iChildCnt) * fChildCountFactor))
                if iChildCnt < 1:
                    iChildCnt = 1
                # endif

                iChildCnt = min(iChildCnt, iMaxChildCount)
                psetX.rendered_child_count = iChildCnt
                psetX.child_nbr = iChildCnt
                print(f">>>> Children count set to {iChildCnt}")

                if sPartSysHairConvertType == "MESH":
                    print(f">>>> Converting to MESH")
                    lPsNames.append(modX.name)

                    bpy.ops.object.select_all(action="DESELECT")
                    objMesh.select_set(True)
                    bpy.context.view_layer.objects.active = objMesh
                    # Convert particle system modifier to mesh
                    setResult: set = bpy.ops.object.modifier_convert(modifier=modX.name)

                    if "FINISHED" not in setResult:
                        print(f">>>> ERROR converting particle system to mesh")
                        continue
                    # endif

                    # Get newly created mesh object
                    objPartMesh = bpy.context.view_layer.objects.active
                    objPartMesh.select_set(True)

                    # Convert mesh object to curve object
                    bpy.ops.object.convert(target="CURVE")
                    bpy.ops.object.select_all(action="DESELECT")

                    # Activate mesh object again
                    bpy.context.view_layer.objects.active = objMesh

                    # Set curve bevel diameter to get solid hair objects
                    objPartMesh.data.bevel_depth = fCurveBevelDepth
                    objPartMesh.data.bevel_resolution = iCurveBevelResolution

                    # Find all vertex groups of objMesh where the hair curves start
                    matMeshInv = objMesh.matrix_world.inverted()
                    # objEvalMesh = objMesh.evaluated_get(xDG)
                    # meshEval = bpy.data.meshes.new_from_object(objEvalMesh)
                    # objEvalNew = objMesh.copy()
                    # print(f"{objMesh.type}, {objEvalNew.type}", flush=True)
                    # objEvalNew.data = meshEval

                    # Find out which bone controls all vertices that the hair particles
                    # emanate from. This code assumes that there is such a common bone.
                    dicVexGrpCmb = {}
                    for iSplIdx, splX in enumerate(objPartMesh.data.splines):
                        setVexGrpNames = set()
                        pntX_l = (matMeshInv @ splX.points[0].co.to_3d().to_4d()).to_3d()

                        (bHit, vPos, vNorm, iPolyIdx) = objMesh.closest_point_on_mesh(pntX_l)  # , depsgraph=xDG)
                        if bHit is True:
                            plyX = objMesh.data.polygons[iPolyIdx]
                            for iVexIdx in plyX.vertices:
                                for xVexGrp in objMesh.data.vertices[iVexIdx].groups:
                                    sVexGrp = objMesh.vertex_groups[xVexGrp.group].name
                                    if sVexGrp in _objX.data.bones:
                                        setVexGrpNames.add(sVexGrp)
                                    # endif
                                # endfor
                            # endfor
                            zetVexGrpNames = frozenset(setVexGrpNames)
                            iKey = hash(zetVexGrpNames)
                            if not iKey in dicVexGrpCmb:
                                dicVexGrpCmb[iKey] = {
                                    "setSplIdx": set([iSplIdx]),
                                    "zetVexGrpNames": zetVexGrpNames,
                                }
                            else:
                                dicVexGrpCmb[iKey]["setSplIdx"].add(iSplIdx)
                            # endif
                        # endif
                    # endfor

                    zetI = None
                    for iIdx, iKey in enumerate(dicVexGrpCmb):
                        dicData = dicVexGrpCmb[iKey]

                        zetVexGrpNames = dicData["zetVexGrpNames"]
                        if zetI is None:
                            zetI = zetVexGrpNames
                        else:
                            zetI = zetI.intersection(zetVexGrpNames)
                        # endif
                    # endfor

                    if zetI is not None:
                        print(f">>>> Particle systems vertex group intersection set: {zetI}")
                    # endif

                    bpy.ops.object.select_all(action="DESELECT")
                    bpy.context.view_layer.objects.active = objPartMesh
                    objPartMesh.select_set(True)

                    if isinstance(dicPartRemesh, dict):
                        print(">>>> Applying remesh modifier of type {} to hair mesh".format(dicPartRemesh["sType"]))
                        modPartRem = objPartMesh.modifiers.new("Bake-Remesh", "REMESH")
                        _SetRemeshPars(
                            modRemesh=modPartRem,
                            dicRemesh=dicPartRemesh,
                            sObjectName=objMesh.name,
                        )
                    # endif

                    if isinstance(dicPartDecimate, dict):
                        print(
                            ">>>> Applying decimate modifier of type {} to hair mesh".format(dicPartDecimate["sType"])
                        )
                        modPartDec = objPartMesh.modifiers.new("Bake-Decimate", "DECIMATE")
                        _SetDecimatePars(
                            modDecimate=modPartDec,
                            dicDecimate=dicPartDecimate,
                            sObjectName=objMesh.name,
                        )
                    # endif

                    print(">>>> Converting hair to mesh")
                    # Convert beveld curve object back to mesh
                    bpy.ops.object.convert(target="MESH")

                    objPartMesh.data.materials.append(matBaked)

                    # Store particle system mesh object for later
                    lObjPartMesh.append(objPartMesh)
                    lObjPartMeshVexGrps.append(zetI)

                    ##################################################################
                    # Separate objects per vex group combination
                    # for iIdx, iKey in enumerate(dicVexGrpCmb):
                    #     dicData = dicVexGrpCmb[iKey]
                    #     objT = objPartMesh.copy()
                    #     objT.data = objPartMesh.data.copy()
                    #     clnX.objects.link(objT)
                    #     objT.name = f"PS.{partsysX.name}.{iIdx}"

                    #     setSplIdx = dicData["setSplIdx"]
                    #     lRemList = []
                    #     for iSplIdx, splX in enumerate(objT.data.splines):
                    #         if iSplIdx not in setSplIdx:
                    #             lRemList.append(splX)
                    #         # endif
                    #     # endfor
                    #     for splX in lRemList:
                    #         objT.data.splines.remove(splX)
                    #     # endfor

                    #     bpy.ops.object.select_all(action="DESELECT")
                    #     bpy.context.view_layer.objects.active = objT
                    #     objT.select_set(True)

                    #     # Convert beveld curve object back to mesh
                    #     bpy.ops.object.convert(target="MESH")

                    #     objT.data.materials.append(matBaked)

                    #     # Store particle system mesh object for later
                    #     lObjPartMesh.append(objT)
                    #     lObjPartMeshVexGrps.append(dicData["zetVexGrpNames"])

                    # # endfor

                    # crvPart = objPartMesh.data
                    # bpy.data.objects.remove(objPartMesh)
                    # bpy.data.curves.remove(crvPart)
                    ##################################################################

                    # Activate mesh object again
                    bpy.ops.object.select_all(action="DESELECT")
                    bpy.context.view_layer.objects.active = objMesh
                    objMesh.select_set(True)
                # endif convert to mesh
            # endif process hair particle systems
        # endfor hair particle systems

        # print(f"{bDecimateMesh}, {bOnlyDecimateIfNoHair}, {iPartSysHairCnt}")

        if bDecimateMesh is True and (
            bOnlyDecimateIfNoHair is False or (bOnlyDecimateIfNoHair is True and iPartSysHairCnt == 0)
        ):
            print(f">> Decimating mesh '{objMesh.name}'")
            # Remove particle system modifiers
            for sPsName in lPsNames:
                objMesh.modifiers.remove(objMesh.modifiers[sPsName])
            # endfor

            # Add decimate modifier to mesh object
            modDec = objMesh.modifiers.new("Bake-Decimate", "DECIMATE")
            # bpy.context.view_layer.objects.active = objMesh
            # bpy.ops.object.modifier_move_to_index(modifier="Bake-Decimate", index=0)
            # bpy.context.view_layer.objects.active = None

            _SetDecimatePars(modDecimate=modDec, dicDecimate=dicDecimate, sObjectName=objMesh.name)

            print(">>>> Evaluating mesh...", flush=True)
            objEval = CreateEvaluatedMeshObject(bpy.context, objMesh, sBakeName)

            # Reduce size of image textures
            print(">>>> Processing materials")
            for iMatIdx, matX in enumerate(objEval.data.materials):
                matY = _BakeMaterial(
                    matX=matX,
                    fImgScale=fImageScale,
                    setOldMaterialNames=setOldMaterialNames,
                    setOldGroupNames=setOldGroupNames,
                    setOldImageNames=setOldImageNames,
                )

                objEval.data.materials[iMatIdx] = matY
            # endfor

            if len(lObjPartMesh) > 0:
                print(">>>> Joining particle systems' meshes with parent mesh")
                zetI = None
                for zetVexGrpNames in lObjPartMeshVexGrps:
                    if zetI is None:
                        zetI = zetVexGrpNames
                    else:
                        zetI = zetI.intersection(zetVexGrpNames)
                    # endif
                # endfor

                print(f">>>>>> Common vertex group: {zetI}")

                # Join all converted particle system meshes with objMesh
                # and assign vertices to vertex groups that are related to bones of _objX
                # determined earlier
                for objPartMesh in lObjPartMesh:

                    print(
                        f">>>>>> Joining '{objPartMesh.name}' with '{objMesh.name}'",
                        flush=True,
                    )
                    # Deselect all vertices in objMesh
                    for vexX in objEval.data.vertices:
                        vexX.select = False
                    # endfor

                    for vexX in objPartMesh.data.vertices:
                        vexX.select = True
                    # endfor

                    # Join particle mesh with mesh object
                    bpy.ops.object.select_all(action="DESELECT")

                    objEval.select_set(True)
                    objPartMesh.select_set(True)
                    bpy.context.view_layer.objects.active = objEval
                    bpy.ops.object.join()

                    if len(zetI) > 0:

                        # print(f">>>>>> Assigning to vertex groups: {zetI}", flush=True)
                        # Get indices of all selected vertices
                        lVexIdx = []
                        for vexX in objEval.data.vertices:
                            if vexX.select is True:
                                lVexIdx.append(vexX.index)
                            # endif
                        # endfor

                        # Loop over all vertex groups found before
                        for sVexGrp in zetI:
                            objEval.vertex_groups[sVexGrp].add(lVexIdx, 1.0, "REPLACE")
                        # endfor
                    # endif
                # endfor
            # endif join part sys meshes with main mesh

            # Activate mesh object again
            bpy.context.view_layer.objects.active = objMesh

            meshX = objMesh.data
            bpy.data.objects.remove(objMesh, do_unlink=True)
            bpy.data.meshes.remove(meshX, do_unlink=True)

            objEval.name = sName
            modArm = objEval.modifiers.new("Armature", "ARMATURE")
            modArm.object = _objX
            modArm.use_vertex_groups = True

        else:
            print(f">> Converting materials of mesh '{objMesh.name}'")
            # Reduce size of image textures
            for iMatIdx, matX in enumerate(objMesh.data.materials):

                matY = _BakeMaterial(
                    matX=matX,
                    fImgScale=fImageScale,
                    setOldMaterialNames=setOldMaterialNames,
                    setOldGroupNames=setOldGroupNames,
                    setOldImageNames=setOldImageNames,
                )

                objMesh.data.materials[iMatIdx] = matY
            # endfor
        # endif convert to mesh
    # endfor armature children

    for sMaterial in setOldMaterialNames:
        print(f">> Removing material: {sMaterial}", flush=True)
        bpy.data.materials.remove(bpy.data.materials[sMaterial], do_unlink=True)
        sBakeName = f"Baked;{sMaterial}"
        bpy.data.materials[sBakeName].name = sMaterial
    # endfor

    for sGroup in setOldGroupNames:
        print(f">> Removing node group: {sGroup}", flush=True)
        bpy.data.node_groups.remove(bpy.data.node_groups[sGroup], do_unlink=True)
        sBakeName = f"Baked;{sGroup}"
        bpy.data.node_groups[sBakeName].name = sGroup
    # endfor

    for sImage in setOldImageNames:
        print(f">> Removing image: {sImage}", flush=True)
        imgX = bpy.data.images[sImage]
        if imgX.users > 0:
            print(f">>>> Image '{imgX.name}' has {imgX.users} user(s)")
        # endif

        bpy.data.images.remove(imgX, do_unlink=True)
        sBakeName = f"Baked;{sImage}"
        bpy.data.images[sBakeName].name = sImage
    # endfor

    anycln.RemoveOrphaned()


# enddef
