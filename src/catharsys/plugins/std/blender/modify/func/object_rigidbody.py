#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \data\obj_modify.py
# Created Date: Thursday, November 10th 2022, 3:37:16 pm
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

from anybase import config, convert
from anyblend import rigidbody
from anyblend.cls_rigidbody_object_pars import CRigidBodyObjectPars


############################################################################################
def Add(_objX, _dicMod, **kwargs):
    """Add the given object to the currently active rigid body world.

    Parameters
    ----------
    _objX : Blender object
        The object to add.
    _dicMod : dict
        The rigid body configuration data.

    Configuration Parameters
    ------------------------
    sType : string
        The rigid body object type. Must be "ACTIVE" or "PASSIVE".
    fMass: float
        The mass of the object in kg.
    sMeshSource: string
        Must be one of "BASE", "DEFORM" or "FINAL"
    sCollisionShape: string
        Must be one of "CONVEX_HULL", "MESH", "SPHERE".
    bEnabled: bool
        Enable/disable rigid body object.
    bKinematic: bool
        If the object is animated, set this to true.
    bUseDeform: bool
        If the object is deformed by a modifier, set this to true.
    fFriction: float
        Friction of object surface
    fRestitution: float
        Bounciness
    bUseMargin: bool
        Use the given collision margin
    fCollisionMargin: float
        The collision margin in Blender units
    fLinearDamping: float
        Linear damping of movement
    fAngularDamping: float
        Angluar damping of movement

    lCollectionIndices: list[int]
        List of rigid body collision collection indices in range [0, 19], to which this object belongs.
    """

    config.AssertConfigType(_dicMod, "/catharsys/blender/modify/object/rigidbody/add:1.0")

    xPars = rigidbody.AddObject(_objX)

    lParNames = [
        "sType",
        "fMass",
        "sMeshSource",
        "sCollisionShape",
        "bEnabled",
        "bKinematic",
        "bUseDeform",
        "fFriction",
        "fRestitution",
        "bUseMargin",
        "fCollisionMargin",
        "fLinearDamping",
        "fAngularDamping",
    ]
    convert.SetAttributesFromDict(xPars, _dicMod, _lNames=lParNames, _bOptional=True)

    xPars.lCollisionCollectionIndices = convert.DictElementToIntList(_dicMod, "lCollectionIndices", lDefault=[0])

    xPars.ApplyToObject(_objX)


# enddef
