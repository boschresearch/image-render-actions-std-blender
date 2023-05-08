#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \scene_rigidbody.py
# Created Date: Friday, November 11th 2022, 8:22:37 am
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

from anybase import config, convert
from anyblend import rigidbody
from anyblend.cls_rigidbody_world_pars import CRigidBodyWorldPars


############################################################################################
def BakeWorld(_scnX, _dicMod, **kwargs):
    """Bake rigid body world from given start to end frame.

    Parameters
    ----------
    _scnX : Blender scene
        Bakes the rigid body world of this scene.
    _dicMod : dict
        The configuration parameters


    Configuration Parameters
    ------------------------
    iFrameStart: int
        The first frame for baking.
    iFrameEnd: int
        The last frame for baking.
    fTimeScale: float
        Time scale of simulation
    iSubStepsPerFrame: int
        Number of sub-steps calculated per frame
    iSolverIterations: int
        Number of iteration for solver
    """

    config.AssertConfigType(_dicMod, "/catharsys/blender/modify/scene/rigidbody/bake:1.0")

    # Ensure that a rigid body world exists
    rigidbody.ProvideWorld(_scnX=_scnX)

    # Get current rigid body world parameters from scene
    xPars = CRigidBodyWorldPars(_scnX=_scnX)
    convert.SetAttributesFromDict(xPars, _dicMod, _bOptional=True)
    xPars.ApplyToScene(_scnX)

    rigidbody.BakeWorld(_scnX=_scnX)


# enddef


############################################################################################
def ClearWorld(_scnX, _dicMod, **kwargs):
    """Clear rigid body world.

    Parameters
    ----------
    _scnX : Blender scene
        Bakes the rigid body world of this scene.
    _dicMod : dict
        The configuration parameters


    Configuration Parameters
    ------------------------
    """

    config.AssertConfigType(_dicMod, "/catharsys/blender/modify/scene/rigidbody/clear:1.0")

    rigidbody.RemoveWorld(_scnX=_scnX)
    rigidbody.ProvideWorld(_scnX=_scnX)


# enddef
