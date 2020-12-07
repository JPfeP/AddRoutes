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
from bpy.utils import register_class, unregister_class
from bpy.app.handlers import persistent
from bpy_extras.io_utils import ImportHelper

import rtmidi
from rtmidi.midiutil import open_midiinput
from rtmidi.midiutil import open_midioutput

import platform

from . import g_vars

midi_in_list = []
midi_out_list = []
midi_in_sys_list = []
midi_out_sys_list = []

midi_in_pt = None
midi_out_pt = None


def update_midi_mode(self, context):
    update_midi_in(self, context)
    update_midi_out(self, context)


def update_midi_in(self, context):
    global midi_in_pt

    if g_vars.midi_update_inh:
        return

    prefs = bpy.context.preferences.addons['AddRoutes'].preferences
    bcw = bpy.context.window_manager
    if bcw.addroutes_midi_settings == 'Project':
        bcw.addroutes_midi_in_device = bcw.addroutes_midi_in_enum
        midiin_dev = bcw.addroutes_midi_in_device
    else:
        prefs.midi_in_device = bcw.addroutes_sys_midi_in_enum
        midiin_dev = prefs.midi_in_device
    try:
        midi_in_pt = midiin_dev
        set_midiin(None, None)
        bcw.addroutes_midi_in_alert = False
    except:
        bcw.addroutes_midi_in_alert = True


def update_midi_out(self, context):
    global midi_out_pt

    if g_vars.midi_update_inh:
        return

    prefs = bpy.context.preferences.addons['AddRoutes'].preferences
    bcw = bpy.context.window_manager
    if bcw.addroutes_midi_settings == 'Project':
        bcw.addroutes_midi_out_device = bcw.addroutes_midi_out_enum
        midiout_dev = bcw.addroutes_midi_out_device
    else:
        prefs.midi_out_device = bcw.addroutes_sys_midi_out_enum
        midiout_dev = prefs.midi_out_device
    try:
        midi_out_pt = midiout_dev
        set_midiout(None, None)
        bcw.addroutes_midi_out_alert = False
    except:
        bcw.addroutes_midi_out_alert = True


def set_midiin(self, context):
    global midi_in_pt

    port = midi_in_pt
    if g_vars.midiin.is_port_open():
        g_vars.midiin.close_port()
        g_vars.midiin.delete()
        g_vars.midiin = rtmidi.MidiIn()
    if port != "None":
        if port != "Virtual Port":
            g_vars.midiin, portname = open_midiinput(port=port, interactive=False, client_name="Blender In")
        else:
            g_vars.midiin, portname = open_midiinput(use_virtual=True, interactive=False, client_name="Blender Virtual In" )

        print("MIDI Input: " + portname)


def set_midiout(self, context):
    global midi_out_pt

    port = midi_out_pt
    if g_vars.midiout.is_port_open():
        g_vars.midiout.close_port()
        g_vars.midiout.delete()
        g_vars.midiout = rtmidi.MidiOut()
    if port != "None":
        if port != "Virtual Port":
            g_vars.midiout, portname = open_midioutput(port=port, interactive=False, client_name="Blender Out")
        else:
            g_vars.midiout, portname = open_midioutput(use_virtual=True, interactive=False, client_name="Blender Virtual Out")
        print("MIDI Output: " + portname)


def refresh_devices(self, context):
    global midi_in_list, midi_out_list, midi_in_sys_list, midi_out_sys_list
    bcw = bpy.context.window_manager
    prefs = bpy.context.preferences.addons['AddRoutes'].preferences

    # for input
    m_in_ports = g_vars.midiin.get_ports()

    targets = [(bcw.addroutes_midi_in_device, midi_in_list), (prefs.midi_in_device, midi_in_sys_list)]

    for midiin_dev, mlist in targets:
        mlist.clear()
        if (midiin_dev in m_in_ports) is False and midiin_dev != "None" and midiin_dev != "Virtual Port" and midiin_dev !="":
            a = (midiin_dev, midiin_dev, midiin_dev)
            mlist.append(a)

        b = ("None", "None", "None")
        mlist.append(b)

        if platform.system() != "Windows":
            c = ("Virtual Port", "Virtual Port", "Virtual Port")
            mlist.append(c)

        for i in m_in_ports:
            d = (i, i, i)
            mlist.append(d)

    # for output
    m_out_ports = g_vars.midiout.get_ports()

    targets = [(bcw.addroutes_midi_out_device, midi_out_list), (prefs.midi_out_device, midi_out_sys_list)]

    for midiout_dev, moutlist in targets:
        moutlist.clear()
        if (midiout_dev in m_out_ports) is False and midiout_dev != "None" and midiout_dev != "Virtual Port" and midiout_dev != "":
            a = (midiout_dev, midiout_dev, midiout_dev)
            moutlist.append(a)

        b = ("None", "None", "None")
        moutlist.append(b)
        c = ("Virtual Port", "Virtual Port", "Virtual Port")
        moutlist.append(c)

        for i in m_out_ports:
            d = (i, i, i)
            moutlist.append(d)


def refresh_midi_in_devices(self, context):
    global midi_in_list
    return midi_in_list


def refresh_midi_out_devices(self, context):
    global midi_out_listm
    return midi_out_list


def refresh_sys_midi_in_devices(self, context):
    global midi_in_sys_list
    return midi_in_sys_list


def refresh_sys_midi_out_devices(self, context):
    global midi_out_sys_list
    return midi_out_sys_list


class AddRoutes_RefreshDevices(bpy.types.Operator):
    """Refresh the list of MIDI devices"""
    bl_idname = "addroutes.refresh_devices"
    bl_label = "Refresh MIDI devices"

    def execute(self, context):
        bcw = bpy.context.window_manager
        prefs = bpy.context.preferences.addons['AddRoutes'].preferences
        refresh_devices(self, context)
        g_vars.midi_update_inh = True
        try:
            bcw.addroutes_midi_in_enum = bcw.addroutes_midi_in_device
        except:
            pass
        try:
            bcw.addroutes_midi_out_enum = bcw.addroutes_midi_out_device
        except:
            pass
        try:
            bcw.addroutes_sys_midi_in_enum = prefs.midi_in_device
        except:
            pass
        try:
            bcw.addroutes_sys_midi_out_enum = prefs.midi_out_device
        except:
            pass
        g_vars.midi_update_inh = False
        update_midi_mode(self, context)
        return{'FINISHED'}


class AddRoutes_StartMidi(bpy.types.Operator):
    """Start the MIDI service"""
    bl_idname = "addroutes.start_midi"
    bl_label = "Start the MIDI service"

    def execute(self, context):
        update_midi_in(self, context)
        update_midi_out(self, context)
        return{'FINISHED'}



cls = (
    AddRoutes_RefreshDevices,
    AddRoutes_StartMidi,
  )


def register():
    bpy.types.WindowManager.addroutes_midi_settings = bpy.props.EnumProperty(
        name="MIDI configuration",
        items=[('System', 'System', 'System', 0),
               ('Project', 'Project', 'Project', 1)],
        update=update_midi_mode
    )
    bpy.types.WindowManager.addroutes_midi_in_device = bpy.props.StringProperty(default="None")
    bpy.types.WindowManager.addroutes_midi_out_device = bpy.props.StringProperty(default="None")

    bpy.types.WindowManager.addroutes_midi_in_enum = bpy.props.EnumProperty(name="MIDI In Ports",
                                                                              items=refresh_midi_in_devices,
                                                                              update=update_midi_in)
    bpy.types.WindowManager.addroutes_midi_out_enum = bpy.props.EnumProperty(name="MIDI Out Ports",
                                                                               items=refresh_midi_out_devices,
                                                                               update=update_midi_out)
    bpy.types.WindowManager.addroutes_sys_midi_in_enum = bpy.props.EnumProperty(name="MIDI In Ports",
                                                                            items=refresh_sys_midi_in_devices,
                                                                            update=update_midi_in)
    bpy.types.WindowManager.addroutes_sys_midi_out_enum = bpy.props.EnumProperty(name="MIDI Out Ports",
                                                                             items=refresh_sys_midi_out_devices,
                                                                             update=update_midi_out)

    bpy.types.WindowManager.addroutes_midi_in_alert = bpy.props.BoolProperty()
    bpy.types.WindowManager.addroutes_midi_out_alert = bpy.props.BoolProperty()
    bpy.types.WindowManager.addroutes_midi_debug = bpy.props.BoolProperty(
        description='Debug in/out MIDI messages. Warning : Can be slow !',
        update=g_vars.debugcopy
    )

    for c in cls:
        register_class(c)


def unregister():
    del bpy.types.WindowManager.addroutes_midi_debug
    del bpy.types.WindowManager.addroutes_midi_in_alert
    del bpy.types.WindowManager.addroutes_midi_out_alert
    del bpy.types.WindowManager.addroutes_midi_out_device
    del bpy.types.WindowManager.addroutes_midi_in_device
    del bpy.types.WindowManager.addroutes_midi_settings
    del bpy.types.WindowManager.addroutes_sys_midi_in_enum
    del bpy.types.WindowManager.addroutes_sys_midi_out_enum
    del bpy.types.WindowManager.addroutes_midi_in_enum
    del bpy.types.WindowManager.addroutes_midi_out_enum

    for c in cls:
        unregister_class(c)


if __name__ == "__main__":
    register()
