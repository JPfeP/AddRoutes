import json

import bpy
from bpy.app.handlers import persistent
from bpy.utils import register_class, unregister_class

from distutils.util import strtobool

from . import g_vars
from .data import yield_all_routes


def build_idx():
    for i, (j, item) in enumerate(yield_all_routes()):
        item.perma_rank = i
        g_vars.highest_rank = i


def save_settings(self, context):
    if g_vars.save_inh is False:
        text_settings = None
        for text in bpy.data.texts:
            if text.name == '.addroutes_settings':
                text_settings = text

        if text_settings is None:
            bpy.ops.text.new()
            text_settings = bpy.data.texts[-1]
            text_settings.name = '.addroutes_settings'

        props = (
            # MIDI
            'addroutes_midi_in_device',
            'addroutes_midi_out_device',
            'addroutes_midi_settings',
            'addroutes_midi_debug',

            # OSC
            'addroutes_osc_udp_in',
            'addroutes_osc_port_in',
            'addroutes_osc_udp_out',
            'addroutes_osc_port_out',
            'addroutes_osc_in_enable',
            'addroutes_osc_out_enable',
            'addroutes_osc_settings',
            'addroutes_osc_debug',

            # Blemote
            'addroutes_blemote_debug',
            #'bpy.context.window_manager.addroutes_blemote_udp_in',
            #'bpy.context.window_manager.addroutes_blemote_port_in',
            #'bpy.context.window_manager.addroutes_blemote_udp_out',
            #'bpy.context.window_manager.addroutes_blemote_port_out',
        )

        dico_settings = {}
        for prop in props:
            dico_settings[prop] = eval("bpy.context.window_manager."+prop)

        text_settings.clear()
        text_settings.write(json.dumps(dico_settings))
        print("saving settings done")



def convert_old_settings(text):
    g_vars.save_inh = True
    # for midi settings
    try:
        if text.lines[1].body != '':
            bpy.context.window_manager.addroutes_midi_in_device = text.lines[1].body
            bpy.context.window_manager.addroutes_midi_settings = "Project"
    except:
        pass
    try:
        if text.lines[2].body != '':
            bpy.context.window_manager.addroutes_midi_out_device = text.lines[2].body
            bpy.context.window_manager.addroutes_midi_settings = "Project"
    except:
        pass

    # for OSC settings
    try:
        if text.lines[10].body != '':
            bpy.context.window_manager.addroutes_osc_udp_in = text.lines[10].body
    except:
        print("OSC: Using default input IP")
    try:
        bpy.context.window_manager.addroutes_osc_port_in = int(text.lines[11].body)
    except:
        print("OSC: Using default input port")

    try:
        if text.lines[12].body != '':
            bpy.context.window_manager.addroutes_osc_udp_out = text.lines[12].body
    except:
        print("OSC: Using default output IP")
    try:
        bpy.context.window_manager.addroutes_osc_port_out = int(text.lines[13].body)
    except:
        print("OSC: Using default output port")

    try:

        bpy.context.window_manager.addroutes_osc_in_enable = strtobool(text.lines[14].body)
    except:
        pass
    try:
        bpy.context.window_manager.addroutes_osc_out_enable = strtobool(text.lines[15].body)
    except:
        pass

    # for Blemote settings
    try:
        if text.lines[20].body != '':
            bpy.context.window_manager.addroutes_blemote_udp_in = text.lines[20].body
    except:
        print("Blemote: Using default input IP")
    try:
        bpy.context.window_manager.addroutes_blemote_port_in = int(text.lines[21].body)

    except:
        print("Blemote: Using default input port")

    try:
        if text.lines[22].body != '':
            bpy.context.window_manager.addroutes_blemote_udp_out = text.lines[22].body
    except:
        print("Blemote: Using default output IP")
    try:
        bpy.context.window_manager.addroutes_blemote_port_out = int(text.lines[23].body)
    except:
        print("Blemote: Using default output port")
    g_vars.save_inh = False


def restore_project_settings(text):
    g_vars.save_inh = True
    body = text.lines[0].body
    if body != "":
        table = json.loads(body)
        for prop, val in table.items():
            try:
                setattr(bpy.context.window_manager, prop, val)
            except:
                pass
    g_vars.save_inh = False


# Restore saved settings
@persistent
def addroutes_restore_handler(scene):
    g_vars.midi_update_inh = True

    for text in bpy.data.texts:
        if text.name == '.mom_settings':
            convert_old_settings(text)
            bpy.data.texts.remove(text)
            print('AddRoutes: Removing old config file')
        elif text.name == '.addroutes_settings':
            restore_project_settings(text)

    #bpy.ops.addroutes.refresh_devices()

    bcw = bpy.context.window_manager
    prefs = bpy.context.preferences.addons['AddRoutes'].preferences

    # bcw.addroutes_midi_in_enum = bcw.addroutes_midi_in_device
    # bcw.addroutes_midi_out_enum = bcw.addroutes_midi_out_device
    # bcw.addroutes_sys_midi_in_enum = prefs.midi_in_device
    # bcw.addroutes_sys_midi_out_enum = prefs.midi_out_device
    g_vars.midi_update_inh = False

    bpy.ops.addroutes.refresh_devices()

    #bpy.ops.addroutes.start_midi()
    bpy.ops.addroutes.midifile_parse()
    build_idx()


# save settings
@persistent
def addroutes_save_handler(scene):
    save_settings(None, None)


cls = (
        )


def register():
    for c in cls:
        register_class(c)

    bpy.app.handlers.load_post.append(addroutes_restore_handler)
    bpy.app.handlers.save_pre.append(addroutes_save_handler)


def unregister():
    bpy.app.handlers.load_post.remove(addroutes_restore_handler)
    bpy.app.handlers.save_pre.remove(addroutes_save_handler)
    for c in cls:
        unregister_class(c)


if __name__ == "__main__":
    register()