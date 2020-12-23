# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#  Copyright (C) 2019 JPfeP
#
# ##### END GPL LICENSE BLOCK #####

import bpy
import rtmidi
# Creation of two MIDI ports
midiin = rtmidi.MidiIn()
midiout = rtmidi.MidiOut()

# for inhibiting saving
save_inh = False
midi_update_inh = False

# just to have a global namespace
last_osc_addr = None
blemote_midi_fb = []
osc_queue = []
blemote_fb = []

# OSC
osc_out_enable = False
osc_in_enable = False
osc_client = None

addroutes_in = {}
addroutes_osc_in = []
addroutes_blemote = {}

eval_ref = None
eval_prop = None

highest_rank = 0


def evalprop (toeval, withctx):
    for window in bpy.data.window_managers[0].windows:
        screen = window.screen

        for area in screen.areas:
            if area.type == withctx:
                override = {'window': window, 'screen': screen, 'area': area}
                bpy.ops.addroutes.getctx(override, s=toeval)


def get_item(i, j):
    if j == 0:
        return bpy.context.scene.MOM_Items[i]
    else:
        return bpy.context.preferences.addons['AddRoutes'].preferences.AddR_System_Routes[i]


def debugcopy(self, context):
    prefs = bpy.context.preferences.addons['AddRoutes'].preferences
    text = bpy.data.texts.get("AddRoutes: Debug in/out")
    if text is None and prefs.debug_copy:
        bpy.ops.text.new()
        text = bpy.data.texts[-1]
        text.name = 'AddRoutes: Debug in/out'
    return


Cont_types = [
            ('key_on', 'Key On number', ''),
            ('key_off', 'Key Off number', ''),
            ('key_on', 'Note On velocity', 'f_opt'),
            ('key_off', 'Note Off velocity', 'f_opt'),
            ('AT_mono', 'Aftertouch mono', ''),
            ('AT_poly', 'Aftertouch poly', 'f_forced'),
            ('pitchbend', 'Pitchbend 14bit', ''),
            ('pgm', 'Program Change', ''),
            ('cc7', 'Continous Controller 7bit', 'f_forced'),
            ('rpn', 'RPN 7bit', 'f_forced'),
            ('rpn14', 'RPN 14bit', 'f_forced'),
            ('nrpn', 'NRPN 7bit', 'f_forced'),
            ('nrpn14', 'NRPN 14bit', 'f_forced'),
            ]