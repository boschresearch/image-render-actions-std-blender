#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# File: \blender\run-enable-addons.py
# Created Date: Friday, October 1st 2021, 2:12:43 pm
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


# enable python add-on via command line
import sys
import json
from anybase import config

try:
    import _bpy
    import bpy
except Exception:
    print("Script has to be run from within blender.")
# endtry

################################################################################
# Read command line arguments if any
lArgv = sys.argv
try:
    lArgv = lArgv[lArgv.index("--") + 1 :]
    if len(lArgv) >= 1:
        bValidCall = True
    else:
        sMsg = "Expect name of config json file"
    # endif

except ValueError:
    sMsg = "No or invalid command line arguments given."
# endtry

if not bValidCall:
    raise Exception("Invalid call: {0}".format(sMsg))
# endif

sFpCfg = lArgv[0]
dicCfg = config.Load(sFpCfg, sDTI="/catharsys/blender/settings:1")


###########################################################################
# Configure Preferences
dicPrefs = dicCfg.get("mPreferences")
if dicPrefs is not None:

    xPrefs = bpy.context.preferences
    for sGrp in dicPrefs:
        if not hasattr(xPrefs, sGrp):
            print(">> WARNING: Preference group '{}' not found".format(sGrp))
            continue
        # endif

        xGrp = getattr(xPrefs, sGrp)
        dicGrp = dicPrefs[sGrp]
        for sPref in dicGrp:
            if not hasattr(xGrp, sPref):
                print(
                    ">> WARNING: Preference '{}' not found in group '{}'".format(
                        sPref, sGrp
                    )
                )
                continue
            # endif
            print(
                ">> Setting preference: {}.{} = {}".format(sGrp, sPref, dicGrp[sPref])
            )
            setattr(xGrp, sPref, dicGrp[sPref])
        # endfor preferences
    # endfor preference groups
# endif has preferences

###########################################################################
# Configure AddOns
lProcAddOns = dicCfg.get("lAddOns")
if lProcAddOns is None:
    raise RuntimeError("Configuration setting 'lProcAddOns' not found")
# endif

for dicAddOn in lProcAddOns:
    if len(dicAddOn) == 0:
        continue
    # endif

    sName = dicAddOn.get("sName")
    if sName is None:
        raise RuntimeError("Missing element 'sName' in add-on configuration")
    # endif

    bRemove = dicAddOn.get("bRemove", False)
    if bRemove is True:
        print(">> Removing addon '{}'".format(sName))
        bpy.ops.preferences.addon_remove(module=sName)
        continue
    # endif

    bEnable = dicAddOn.get("bEnable", True)
    if bEnable is True:
        print(">> Enabling addon '{}'".format(sName))
        bpy.ops.preferences.addon_enable(module=sName)

    elif bEnable is False:
        print(">> Disabling addon '{}'".format(sName))
        bpy.ops.preferences.addon_disable(module=sName)
    # endif

    dicPref = dicAddOn.get("mPreferences")
    if dicPref is not None:
        print(">> Setting preferences for addon '{}':".format(sName))
        xAddOn = bpy.context.preferences.addons[sName]
        xPrefs = xAddOn.preferences
        if bpy.app.version >= (4, 0, 0):
            for sKey, sValue in dicPref.items():
                print(">>>> {} => {}".format(sKey, sValue))
                setattr(xPrefs, sKey, sValue)
            # endfor
        else:
            # For Blender 3.x, we need to set preferences differently
            # as the preferences are not directly accessible as attributes.
            for sKey, sValue in dicPref.items():
                print(">>>> {} => {}".format(sKey, sValue))
                xAddOn.preferences[sKey] = sValue
            # endfor
        # endif
# endfor

bpy.ops.wm.save_userpref()
