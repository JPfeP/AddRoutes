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


bl_info = {
    "name": "AddRoutes",
    "author": "JPfeP",
    "version": (0, 32),
    "blender": (2, 80, 0),
    "location": "",
    "description": "Realtime interactions with Blender (MIDI, OSC, smartphone App)",
    "warning": "Better, but still a W.I.P",
    "wiki_url": "http://www.jpfep.net/pages/addons/addroutes/",
    "tracker_url": "",
    "category": "System"}


import sys
import os
script_file = os.path.realpath(__file__)
directory = os.path.dirname(script_file)

if directory not in sys.path:
   sys.path.append(directory)

if "bpy" in locals():
    import importlib
    importlib.reload(data)
    importlib.reload(load_save)
    importlib.reload(ui)
    importlib.reload(midi_devices)
    importlib.reload(midi)
    importlib.reload(osc_devices)
    importlib.reload(osc)
    importlib.reload(blemote)
    importlib.reload(blemote_devices)

else:
    from . import data
    from . import load_save
    from . import ui
    from . import midi_devices
    from . import midi
    from . import osc_devices
    from . import osc
    from . import blemote
    from . import blemote_devices


import bpy
from bpy.utils import register_class, unregister_class
from bpy.types import AddonPreferences, PropertyGroup, Collection
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty, PointerProperty, CollectionProperty

from . import g_vars
from .data import generate_dict
from .osc_devices import update_osc_in, update_osc_out, update_osc_in_enable, update_osc_out_enable
#from .midi_devices import update_midi_mode


class AddR_Items_PG(bpy.types.PropertyGroup):

    def upd_min(self, context):
        if self.min >= self.max:
            self.min = self.max - 1
        generate_dict(self, context)

    def upd_max(self, context):
        if self.max <= self.min:
            self.max = self.max + 1
        generate_dict(self, context)

    engine: bpy.props.EnumProperty(
        items=[
            ('MIDI', 'MIDI', 'MIDI', '', 0),
            ('OSC', 'OSC', 'OSC', '', 1),
            ('Blemote', 'Blemote', 'Blemote', '', 2)
        ],
        default='MIDI',
        update=generate_dict
    )
    mode: bpy.props.EnumProperty(
        items=[
            ('Receive', 'Receive', 'Receive', '', 0),
            ('Send', 'Send', 'Send', '', 1),
            ('Both', 'Both', 'Both', '', 2),
            ('Off', 'Off', 'Off', '', 3)
        ],
        default='Off',
        update=generate_dict
    )

    record: bpy.props.BoolProperty(name='Record', update=generate_dict)
    '''
    id_type: bpy.props.EnumProperty(
        items=g_vars.ID_types,
        name='ID-Block',
        default='objects',
        update=generate_dict
    )
    id: bpy.props.PointerProperty(name='ID', type=MOM_ID_PG, update=generate_dict)
    data_path: bpy.props.StringProperty(name="Data Path", update=generate_dict)
    '''
    array: bpy.props.IntProperty(name="Index", min=0, update=generate_dict)
    is_array: bpy.props.BoolProperty(name='Is Array')
    len: bpy.props.IntProperty()
    use_array: bpy.props.BoolProperty(name='All')
    channel: bpy.props.IntProperty(name="Channel", min=1, max=16, default=1, update=generate_dict)
    controller: bpy.props.IntProperty(name="Controller number", min=0, max=16384, default=1, update=generate_dict)
    # controller14: bpy.props.IntProperty(name="Controller number", min=1, max=16384, default=1, update=generate_dict)
    use_clip: bpy.props.BoolProperty(name='Clip incoming', update=generate_dict)
    clip_low: bpy.props.FloatProperty(name="Low", default=0, update=generate_dict)
    clip_high: bpy.props.FloatProperty(name="High", default=127, update=generate_dict)
    rescale_mode: bpy.props.EnumProperty(name='Rescale in/out',
                                         items=[
                                             ('Direct', 'Direct', 'Direct', '', 0),
                                             ('Auto', 'Auto', 'Auto', '', 1),
                                             ('Cut', 'Cut', 'Cut', '', 2),
                                             ('Wrap', 'Wrap', 'Wrap', '', 3)
                                         ]
                                         )
    rescale_outside_low: bpy.props.IntProperty(name="Low", default=0, min=0, max=16383, update=generate_dict)
    rescale_outside_high: bpy.props.IntProperty(name="High", default=127, min=0, max=16383, update=generate_dict)
    rescale_blender_low: bpy.props.FloatProperty(name="Low", default=0, update=generate_dict)
    rescale_blender_high: bpy.props.FloatProperty(name="High", default=127, update=generate_dict)
    min: bpy.props.IntProperty(name="Min", default=0, update=generate_dict)
    max: bpy.props.IntProperty(name="Max", default=127, update=generate_dict)
    is_str2eval: bpy.props.BoolProperty(name='python expr', update=generate_dict, default=True)
    str2eval: bpy.props.StringProperty(name="To eval", update=generate_dict)
    withctx: bpy.props.StringProperty(name="Context", default='VIEW_3D', update=generate_dict)
    eval_mode: bpy.props.EnumProperty(
        name='Actualization',
        items=[
            ('replace', 'Replace', 'replace', '', 0),
            # ('add', 'add', 'add', '', 1),
            # ('subtract', 'subtract', 'subtract', '', 2),
            # ('multiply', 'multiply', 'multiply', '', 3),
            # ('divide', 'divide', 'divide', '', 4),
            ('expr', 'Expression', 'expression', '', 5)
        ],
        update=generate_dict)

    eval_expr: bpy.props.StringProperty(name="Evaluate",
                                        description='IN = incoming value (processed)\nPROP = current Blender value',
                                        default='IN',
                                        update=generate_dict)
    osc_address: bpy.props.StringProperty(name="Address", default='/blender', update=generate_dict)
    filter: bpy.props.BoolProperty(name='Filter')
    f_show: bpy.props.BoolProperty(name='Show Filter')
    cont_type: bpy.props.EnumProperty(
        name='Event type',
        items=g_vars.Cont_types,
        update=generate_dict
    )
    alert: bpy.props.BoolProperty(name='Alert')

    # for keying set options
    kf_needed: bpy.props.BoolProperty(name='KF_needed', update=generate_dict)
    kf_visual: bpy.props.BoolProperty(name='KF_visual', update=generate_dict)
    kf_rgb: bpy.props.BoolProperty(name='KF_xyz2rgb', update=generate_dict)
    kf_replace: bpy.props.BoolProperty(name='KF_replace', update=generate_dict)
    kf_available: bpy.props.BoolProperty(name='KF_available', update=generate_dict)
    kf_cycle: bpy.props.BoolProperty(name='KF_cycle', update=generate_dict)
    kf_group: bpy.props.StringProperty(name='Group',
                                       description='Group name for F-curves (mandatory for MIDI envelope)',
                                       update=generate_dict)

    # for Blemote
    blem_switch: bpy.props.BoolProperty(name='Show Blemote options', description='Display this route in Blemote',
                                      update=generate_dict)
    blem_min: bpy.props.FloatProperty(name='Min', default=0, update=generate_dict)
    blem_max: bpy.props.FloatProperty(name='Max', default=100, update=generate_dict)
    blem_step: bpy.props.FloatProperty(name='Step', min=0, description='Minimal interval (0 = None)',
                                       update=generate_dict)
    route_name: bpy.props.StringProperty(name='Route Name', description='Name of the route', update=generate_dict)

    # for multi routes
    is_multi: bpy.props.BoolProperty(name='Multi routing', update=generate_dict)
    number: bpy.props.IntProperty(name="Instances", default=2, min=2, update=generate_dict)
    VAR_use: bpy.props.EnumProperty(
        name='Use VAR',
        items=[
            ('name', 'in name', 'in name', '', 0),
            ('dp', 'in data-path', 'in data-path', '', 1)
        ],
        update=generate_dict) 
    name_var: bpy.props.StringProperty(name='Base name', default='name_VAR', update=generate_dict)
    offset: bpy.props.IntProperty(name="Offset ", default=0, update=generate_dict)

    osc_select_rank: bpy.props.IntProperty(name="From", update=generate_dict)
    osc_select_n: bpy.props.IntProperty(name="n", min=1, default=1, update=generate_dict)

    # for angles
    rad2deg: bpy.props.BoolProperty(name='Deg <-> Rad', default=True, update=generate_dict,
                                    description='Convert degrees <-> radians')
    is_angle: bpy.props.BoolProperty(name='Is Angle', update=generate_dict)                                                          # difference with the normal routes

    # for MIDI post processing
    env_auto: bpy.props.BoolProperty(name='Auto', description='Automatically apply envelope after midifile conversion')
    env_attack: bpy.props.IntProperty(name='Pre Attack', description='Pre Attack time in millisecondes', default=50,
                                      min=1)
    env_release: bpy.props.IntProperty(name='Release', description='Release time in millisecondes', default=50, min=1)

    perma_rank: bpy.props.IntProperty()

    # for the categories feature
    category: bpy.props.StringProperty(default='System')

    # gui features
    show_expanded: bpy.props.BoolProperty(default=True)


class AddonPreferences(AddonPreferences):
    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __package__

    blemote_udp_in: StringProperty(
        name="Server",
        default="0.0.0.0"
    )
    blemote_port_in: IntProperty(
        name="port",
        default=10000
    )
    blemote_udp_out: StringProperty(
        name="Output",
        default="127.0.0.1"
    )
    blemote_port_out: IntProperty(
        name="port",
        default=10001
    )
    blemote_enable: BoolProperty(
        name="Enable Blemote",
        default=False,
    )
    blemote_autoconf: BoolProperty(
        name="Automatic output configuration",
        default=True
    )

    refresh: IntProperty(
        name="Refresh rate of engines (ms)",
        default=1,
        min=1,
        max=1000
    )
    overflow: IntProperty(
        name="Maximum events per cycle",
        default=200,
        min=1
    )
    AddR_System_Routes: CollectionProperty(
        name="system_routes",
        type=AddR_Items_PG,
    )
    # MIDI devices
    midi_in_device: StringProperty(
        name="MIDI Input",
        default="None",
    )
    midi_out_device: StringProperty(
        name="MIDI Output",
        default="None",
    )
    # OSC devices
    osc_in_enable: BoolProperty(update=update_osc_in_enable)

    osc_out_enable: BoolProperty(update=update_osc_out_enable)

    osc_udp_in: StringProperty(
        name="OSC Input System Address",
        default='0.0.0.0',
        update=update_osc_in,
        description='The IP of the interface of your Blender machine to listen on, set to 0.0.0.0 for all of them')

    osc_udp_out: StringProperty(
        default="127.0.0.1",
        update=update_osc_out,
        description='The IP of the destination machine to send messages to')

    osc_port_in: IntProperty(
        default=9001,
        min=0,
        max=65535,
        update=update_osc_in,
        description='The input network port (0-65535)'
    )

    osc_port_out: IntProperty(
        default=9002,
        min=0,
        max=65535,
        update=update_osc_out,
        description='The output network port (0-65535)'
    )

    debug_copy: BoolProperty(
        description="Copy debug messages in the text editor (text file name: 'AddRoutes: Debug in/out')"
    )
    debug_timestamp: BoolProperty(
        description="Add a time stamp to each debug message"
    )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="General Settings:")
        col = box.column(align=True)
        col.prop(self, "refresh")
        col.prop(self, "overflow")
        box.label(text="Debug Settings:")
        col = box.column(align=True)
        col.prop(self, "debug_copy", text='Copy all in/out debug messages in the text editor')
        col.prop(self, "debug_timestamp", text='Add time stamp to debug messages')

        box = layout.box()
        box.label(text="Blemote Settings:")
        col = box.column(align=True)
        col.prop(self, "blemote_enable")
        col.prop(self, "blemote_autoconf")

        col = box.column(align=True)
        row = col.row(align=True)
        row.alert = bpy.context.window_manager.addroutes_blemote_alert and self.blemote_enable
        row.prop(self, "blemote_udp_in")
        row.prop(self, "blemote_port_in")

        row = col.row(align=True)
        row.prop(self, "blemote_udp_out")
        row.prop(self, "blemote_port_out")
        row.active = not(self.blemote_autoconf)

        box = layout.box()
        box.label(text="MIDI System Settings:")
        col = box.column(align=True)
        row1 = col.row(align=True)
        row2 = col.row(align=True)
        row1.alert = context.window_manager.addroutes_midi_in_alert
        row2.alert = context.window_manager.addroutes_midi_out_alert
        row1.prop(context.window_manager, "addroutes_sys_midi_in_enum", text="System In")
        row2.prop(context.window_manager, "addroutes_sys_midi_out_enum", text="System Out")
        box.operator("addroutes.refresh_devices", text='Refresh Devices List')

        box = layout.box()
        box.label(text="OSC System Settings:")
        col = box.column(align=True)
        row1 = col.row(align=True)
        row2 = col.row(align=True)
        row1.alert = bpy.context.window_manager.addroutes_osc_in_alert and g_vars.osc_in_enable
        row2.alert = bpy.context.window_manager.addroutes_osc_out_alert and g_vars.osc_out_enable
        row1.prop(self, 'osc_udp_in', text="Listen on ")
        row1.prop(self, 'osc_port_in', text="Input port")
        row1.prop(self, 'osc_in_enable', text="")

        row2.prop(self, 'osc_udp_out', text="Destination address")
        row2.prop(self, 'osc_port_out', text="Output port")
        row2.prop(self, 'osc_out_enable', text="")

cls = (
    AddR_Items_PG,
    AddonPreferences,
)


def register():
    data.register()
    load_save.register()
    ui.register()
    midi_devices.register()
    midi.register()
    osc_devices.register()
    osc.register()
    blemote_devices.register()
    blemote.register()

    for c in cls:
        register_class(c)


def unregister():
    osc.unregister()
    osc_devices.unregister()
    ui.unregister()
    midi.unregister()
    midi_devices.unregister()
    data.unregister()
    load_save.unregister()
    blemote.unregister()
    blemote_devices.unregister()

    for c in cls:
        unregister_class(c)


if __name__ == "__main__":
    register()
