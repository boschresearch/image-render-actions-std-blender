#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \data\obj_modify.py
# Created Date: Friday, August 13th 2021, 8:12:19 am
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
import mathutils

from anybase import convert
from anyblend import viewlayer as anyvl


############################################################################################
def SelectNlaTrack(_objX, _dicMod, **kwargs):

    if _objX.type != "ARMATURE":
        raise Exception(
            "Action 'select_nla_track' is not available for object '{0}'" " as it is not an armature".format(_objX.name)
        )
    # endif
    sTrack = _dicMod.get("xValue")
    if sTrack not in _objX.animation_data.nla_tracks:
        raise Exception("NLA track '{0}' not found for object '{1}'".format(sTrack, _objX.name))
    # endif

    for xTrack in _objX.animation_data.nla_tracks:
        xTrack.mute = xTrack.name != sTrack
    # endfor


# enddef


############################################################################################
def ApplyActionFromFile(_objX, sBlenderFilename, sActionname, fOffset=0, fOffsetPercentage=None):
    """
    Apply an action (animation) from a blender file to an object.
    It is possible to specify an offset into the action in either terms of frames or
    a percentage of the animation.
    For the latter, the total length of the action is determined by the
    position of the last keyframe.
    Instead of giving a string for sActionname, it is possible to use something convertible
    to int to specify the index of the action.

    Parameters
    ----------
    _objX : blender object
        The object that should be animated
    sBlenderFilename : string
        filename of the blender file containing the action
    sActionname : string or convertible to int
        name of the action that should be loaded from the blender file
    fOffset : int, optional
        offset in frames, by default 0
    fOffsetPercentage : [type], optional
        offset in percentage, by default None

    """

    def isInt(s):
        try:
            int(s)
            return True
        except Exception:
            return False
        # endtry

    with bpy.data.libraries.load(sBlenderFilename, link=False) as (data_from, data_to):
        if sActionname in data_from.actions:
            data_to.actions.append(sActionname)
        elif len(data_from.actions) > 0 and isInt(sActionname):
            data_to.actions.append(data_from.actions[int(sActionname)])
        else:
            raise RuntimeError("Action of name {} not found in {}".format(sActionname, sBlenderFilename))
        # endif
    # endwith

    action_src = data_to.actions[0]

    _objX.animation_data_clear()
    _objX.animation_data_create()
    _objX.animation_data.action = action_src

    sequence_length = 0

    for fcurve in action_src.fcurves:
        for keypoint in fcurve.keyframe_points:
            if keypoint.co[0] > sequence_length:
                sequence_length = keypoint.co[0]
            # endif
        # endfor
    # endfor

    if fOffsetPercentage is not None:
        fOffset = sequence_length * fOffsetPercentage / 100.0

    for fcurve in action_src.fcurves:
        for keypoint in fcurve.keyframe_points:
            keypoint.co[0] -= fOffset
        # endfor
    # endfor


# enddef


############################################################################################
def ModifyAction(_objX, _dicMod, **kwargs):
    """
    Modify the action of an object.

    The parameter dictionary can contain:
    - sBlenderFilename: filename of the blender file
    - sActionname: name of the file in the blender file
    - fOffset: offset in terms of keyframes (optional)
    - fOffsetPercentage: offset in terms of percentage (optional)

    Parameters
    ----------
    _objX : blender object
        blender object to which the animation should be applied
    _dicMod : dict
        dictionary containing the settings for the modifier

    """
    if "sBlenderFilename" not in _dicMod:
        raise Exception("sBlenderFilename not given for loading action for '{}'".format(_objX.name))
    # endif
    sBlenderFilename = _dicMod["sBlenderFilename"]

    if "sActionname" not in _dicMod:
        raise Exception("sActionname not given for loading action for '{}'".format(_objX.name))
    # endif

    sActionname = _dicMod["sActionname"]

    fOffset = convert.DictElementToFloat(_dicMod, "fOffset", fDefault=0.0)
    fOffsetPercentage = convert.DictElementToFloat(_dicMod, "fOffsetPercentage", bDoRaise=False)

    ApplyActionFromFile(_objX, sBlenderFilename, sActionname, fOffset, fOffsetPercentage)


# enddef


############################################################################################
def ApplyActionFromFile2(
    _objX,
    *,
    sBlenderFilename,
    sActionName,
    fStartRelative=0.0,
    lSceneFrameRange=None,
    fActionScale=1.0,
    bActionReverse=False,
    bActionToggleReverse=False
):
    """
    Apply an action (animation) from a blender file to an object.

    Instead of giving a string for sActionname, it is possible to use something convertible
    to int to specify the index of the action.

    Parameters
    ----------
    _objX : blender object
        The object that should be animated
    sBlenderFilename : string
        filename of the blender file containing the action
    sActionName : string or convertible to int
        name of the action that should be loaded from the blender file

    fActionScale: (float, [1e-4, inf], optional, default=1.0)
        A factor the action is scaled with.

    bActionReverse: (bool, optional, default=true)
        If set 'true' the action is reversed.

    bActionToggleReverse: (bool, optional, default=false)
        Everytime the action needs to be repeated, it's direction is reversed.
        In this way, any action can be repeated smoothly.

    fStartRelative (float, [0,1], optional):
            relative action start. Default zero.
            Determines which frame of the action is placed at scene frame zero or the
            the scene frame given as the first element of 'lTargetFrameRange'.
            For example, value '0.5' places the central keyframe of the action
            at scene frame zero, if 'lTargetFrameRange' is not specified.

    lSceneFrameRange (list (int), optional):
            ensures that there is an active NLA track within this scene frame range.
            If the action is too short, it is repeated so that at least this
            frame range is covered.
            If the list contains a single value, the second value is deduced from the
            length of the action.
            Default is that the action is run exactly once.
    """

    def isInt(xValue):
        try:
            int(xValue)
            return True
        except Exception:
            return False
        # endtry

    # enddef

    # print("Load animation:")
    # print(f"| sBlenderFilename: {sBlenderFilename}")
    # print(f"| fStartRelative: {fStartRelative}")
    # print("")

    with bpy.data.libraries.load(sBlenderFilename, link=False) as (data_from, data_to):
        if sActionName in data_from.actions:
            data_to.actions.append(sActionName)
        elif len(data_from.actions) > 0 and isInt(sActionName):
            data_to.actions.append(data_from.actions[int(sActionName)])
        else:
            raise RuntimeError("Action of name {} not found in {}".format(sActionName, sBlenderFilename))
        # endif
    # endwith

    actX = data_to.actions[0]

    _objX.animation_data_clear()
    _objX.animation_data_create()
    # _objX.animation_data.action = actX

    # Remove action from objects, as the nla strip now encodes the action
    # _objX.animation_data.action = None

    # clamp to range [0,1]
    fStartRel = max(0.0, min(fStartRelative, 1.0))

    iTotalActionFrameStart = int(round(actX.frame_range[0]))
    iTotalActionFrameEnd = int(round(actX.frame_range[1]))
    iTotalActionFrameCnt = int(iTotalActionFrameEnd - iTotalActionFrameStart + 1)
    iTotalActSceneFrameCnt = int(round(fActionScale * iTotalActionFrameCnt))

    if lSceneFrameRange is None:
        lSceneFrameRange = [0, iTotalActSceneFrameCnt - 1]
    elif len(lSceneFrameRange) == 1:
        lSceneFrameRange.append(lSceneFrameRange[0] + iTotalActSceneFrameCnt - 1)
    elif lSceneFrameRange[1] <= lSceneFrameRange[0]:
        raise RuntimeError("Invalid scene frame range: [{}, {}]".format(lSceneFrameRange[0], lSceneFrameRange[1]))
    # endif

    # Create an NLA track for the whole action
    trackX = _objX.animation_data.nla_tracks.new()

    bCurActReverse = bActionReverse

    # Create NLA strips within the track for all partial animations
    iSceneFrameStart = lSceneFrameRange[0]
    while iSceneFrameStart <= lSceneFrameRange[1]:
        # create a strip.
        stripX = trackX.strips.new(actX.name, iSceneFrameStart, actX)
        # we want to set all strip and action frame values without automated calculations
        stripX.use_sync_length = False

        iActFrameStartRel = int(round(fStartRel * (iTotalActionFrameCnt - 1)))
        iActFrameStart = int(round(stripX.action_frame_start + iActFrameStartRel))
        iActionFrameCnt = iTotalActionFrameCnt - iActFrameStartRel
        iActSceneFrameCnt = int(round(fActionScale * iActionFrameCnt))
        iSceneFrameEnd = iSceneFrameStart + iActSceneFrameCnt - 1

        if iSceneFrameEnd > lSceneFrameRange[1]:
            iActSceneFrameCnt = lSceneFrameRange[1] - iSceneFrameStart + 1
            iActionFrameCnt = int(round(iActSceneFrameCnt / fActionScale))
            iSceneFrameEnd = lSceneFrameRange[1]
        # endif
        iActFrameEnd = iActFrameStart + iActionFrameCnt - 1

        if bCurActReverse is False:
            stripX.action_frame_end = iActFrameEnd
            stripX.action_frame_start = iActFrameStart
        else:
            stripX.action_frame_end = iTotalActionFrameEnd - iActFrameStart
            stripX.action_frame_start = iTotalActionFrameEnd - iActFrameEnd
        # endif

        stripX.frame_end = iSceneFrameEnd
        stripX.frame_start = iSceneFrameStart
        stripX.use_reverse = bCurActReverse

        # Reset relative start of action to beginning
        fStartRel = 0.0

        # Toggle reverse if needed
        if bActionToggleReverse is True:
            bCurActReverse = not bCurActReverse
        # endif

        iSceneFrameStart = iSceneFrameEnd + 1
    # endwhile


# enddef


############################################################################################
def ModifyAction2(_objX, _dicMod, **kwargs):
    """
    Modify the action of an object version 2.
    This version creates NLA tracks from the imported action.
    This allows for a simplified repositioning of the start frame,
    as well as a scaling and repetition of the animation.

    The parameter dictionary can contain:
    - sBlenderFilename (str):
            filename of the blender file

    - sActionName (str):
            name of the action in the blender file

    - fActionFps (float, optional):
            The original fps the action was designed for. The modifier automatically
            scales the action to fit the target capture and scene framerates.
            Default, action is not scaled.

    - fActionScale (float, optional):
            Additional animation scale. Default, is unity.

    - bActionReverse: (bool, optional, default=true)
            If set 'true' the action is reversed.

    - bActionToggleReverse: (bool, optional, default=false)
            Everytime the action needs to be repeated, it's direction is reversed.
            In this way, any action can be repeated smoothly.

    - fStartRelative (float, [0,1], optional):
            relative action start. Default zero.
            Determines which frame of the action is placed at scene frame zero or the
            the scene frame given as the first element of 'lTargetFrameRange'.
            For example, value '0.5' places the central keyframe of the action
            at scene frame zero, if 'lTargetFrameRange' is not specified.

    - lTargetFrameRange (list (int), optional):
            ensures that there is an active NLA track within this target frame range.
            If the action is too short, it is repeated so that at least this
            frame range is covered. Default is that the action is run exactly once.
            Note that, the target frames may differ from scene frames, depending
            on the capture configuration and scene fps. This is accounted for
            automatically in this modifier.

    Parameters
    ----------
    _objX : blender object
        blender object to which the animation should be applied
    _dicMod : dict
        dictionary containing the settings for the modifier
    dicVars: [dict] (optional)
        variables passed from the calling render action.
        They are needed to adapt the animation fps to the scene.

    """

    sBlenderFilename = _dicMod.get("sBlenderFilename")
    if sBlenderFilename is None:
        raise RuntimeError("Element 'sBlenderFilename' not given for loading action for '{}'".format(_objX.name))
    # endif

    sActionName = _dicMod.get("sActionName")
    if sActionName is None:
        raise RuntimeError("Element 'sActionName' not given for loading action for '{}'".format(_objX.name))
    # endif

    dicVars = kwargs.get("dicVars")

    fStartRelative = convert.DictElementToFloat(_dicMod, "fStartRelative", fDefault=0.0)
    lTargetFrameRange = _dicMod.get("lTargetFrameRange")

    if dicVars is None:
        raise RuntimeError("Needed runtime variables not given to apply action modifier")
    # endif

    try:
        dicRender = dicVars["render"]
    except Exception as xEx:
        raise RuntimeError("Missing runtime variable in apply action modifier:\n{}".format(str(xEx)))
    # endif

    fTargetFps = convert.DictElementToFloat(dicRender, "target-fps")
    fSceneFps = convert.DictElementToFloat(dicRender, "scene-fps")

    fActionFps = convert.DictElementToFloat(_dicMod, "fActionFps", fDefault=fSceneFps)
    fActionScale = convert.DictElementToFloat(_dicMod, "fActionScale", fDefault=1.0)
    bActionReverse = convert.DictElementToBool(_dicMod, "bActionReverse", bDefault=False)
    bActionToggleReverse = convert.DictElementToBool(_dicMod, "bActionToggleReverse", bDefault=False)

    # Calculate scaling of action due to scene/action fps and user defined scale
    fActScale = fActionScale * fSceneFps / fActionFps

    # Convert the frame range from target frames to scene frames
    lSceneFrameRange = None
    if lTargetFrameRange is not None:
        lSceneFrameRange = [int(round(x * fSceneFps / fTargetFps, 0)) for x in lTargetFrameRange]
    # endif

    ApplyActionFromFile2(
        _objX,
        sBlenderFilename=sBlenderFilename,
        sActionName=sActionName,
        fStartRelative=fStartRelative,
        lSceneFrameRange=lSceneFrameRange,
        fActionScale=fActScale,
        bActionReverse=bActionReverse,
        bActionToggleReverse=bActionToggleReverse,
    )

    anyvl.Update()


# enddef
