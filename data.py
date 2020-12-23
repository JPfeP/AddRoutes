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
import copy
from bpy.app.handlers import persistent
from bpy.utils import register_class, unregister_class
from numpy import radians, degrees
import numpy as np

import sys
import json

from . import g_vars

addroutes_blemote_pre = {}


def n_to_enum(bl_item, item, arg):
    ref = item['ref']
    prop = item['prop']
    idx = int(arg)
    ref_rna = ref.bl_rna.properties[prop].enum_items
    max_idx = len(ref_rna)-1
    if idx < 0:
        idx = 0
    if idx >= max_idx:
        idx = max_idx
    return ref_rna[idx].identifier


def enum_to_n (bl_item, item, arg):
    ref = item['ref']
    prop = item['prop']
    ref_rna = ref.bl_rna.properties[prop].enum_items
    return ref_rna[arg].value


def radeg(bl_item, item, arg):
    return radians(arg)


def degra(bl_item, item, arg):
    return degrees(arg)


def nothing(bl_item, item, arg):
    return arg


# post function (SET/ADD/SUB/MULT/DIVIDE/EXPR)
def post_set(current, result, bl_item):
    out = result
    return out


def post_add(current, result, bl_item):
    out = current + result
    return out


def post_sub(current, result, bl_item):
    out = current - result
    return out


def post_mul(current, result, bl_item):
    out = current * result
    return out


def post_div(current, result, bl_item):
    out = current / result
    return out


def post_expr(PROP, IN, bl_item):
    out = eval(bl_item.eval_expr)
    return out


def parse_route(item, k=0):
    # FUNCTIONS
    # for general case
    func = {'midi_in_func': nothing,
            'midi_out_func': nothing,
            'osc_in_func': nothing,
            'osc_out_func': nothing,
            'blemote_func': nothing
            }

    if item.is_str2eval is False:

        val = item.offset + k

        if item.is_multi and (item.VAR_use == 'name'):
            if item.name_var == 'VAR':
                index = str(val)
                id = eval('bpy.data.'+item.id_type+'['+index+']')
            else:
                name = item.name_var.replace('VAR', str(val))
                id = eval('bpy.data.' + item.id_type + '["' + name + '"]')
        else:
            id = item.id[item.id_type]

        # Replace VAR in data-path
        dp = item.data_path
        if item.is_multi and (item.VAR_use == 'dp'):
            dp = dp.replace('VAR', str(val))

        # getting a ref
        dp_split = dp.split('.')
        if len(dp_split) > 1:
            ref = eval(repr(id) + '.' + '.'.join(dp_split[0:-1]))
        else:
            ref = id

        prop = dp_split[-1]

        # setting item array and size
        if hasattr(ref.bl_rna.properties[prop], 'is_array'):
            item.is_array = ref.bl_rna.properties[prop].is_array
            item.len = ref.bl_rna.properties[prop].array_length
        else:
            item.is_array = False
            item.len = 0

        if item.is_array and (item.use_array is False or item.engine != 'OSC'):
            value = getattr(ref, prop)[item.array]
        else:
            value = getattr(ref, prop)

         # this a workaround to avoid "Vector" or "Color" prefix or things like that
        try:
            l = len(value)
            value = list(value)
        except:
            pass


        # for enum
        if ref.bl_rna.properties[prop].type == 'ENUM':
            #l = []
            #for item in ref.bl_rna.properties[prop].enum_items:
            #    l.append(item.identifier)
            func = {'midi_in_func': n_to_enum,
                    'midi_out_func': enum_to_n,
                    'osc_in_func': nothing,
                    'osc_out_func': nothing,
                    'blemote_func': n_to_enum,
                    }

        # for angles
        #if hasattr(ref.bl_rna.properties[prop], 'unit'):
        if ref.bl_rna.properties[prop].unit == 'ROTATION':
            item.is_angle = True
        else:
            item.is_angle = False

    #for str2eval prop
    else:
        value, id, ref, prop, dp = None, None, None, None, None

    if item.rad2deg is True and item.is_angle is True:
        func = {'midi_in_func': radeg,
                'midi_out_func': degra,
                'osc_in_func': radeg,
                'osc_out_func': degra,
                'blemote_func': radeg
                }

    # POST FUNCTIONS (SET/ADD/DEL/MUL/DIV/EXPR..)
    post_func = None
    if item.eval_mode == 'replace':
        post_func = post_set
    elif item.eval_mode == 'add':
        post_func = post_add
    elif item.eval_mode == 'subtract':
        post_func = post_sub
    elif item.eval_mode == 'multiply':
        post_func = post_mul
    elif item.eval_mode == 'divide':
        post_func = post_div
    elif item.eval_mode == 'expr':
        post_func = post_expr


    # options for keyframe insertion
    ks_options = set()
    if item.kf_needed:
        ks_options.add('INSERTKEY_NEEDED')
    if item.kf_visual:
        ks_options.add('INSERTKEY_VISUAL')
    if item.kf_rgb:
        ks_options.add('INSERTKEY_XYZ_TO_RGB')
    if item.kf_replace:
        ks_options.add('INSERTKEY_REPLACE')
    if item.kf_available:
        ks_options.add('INSERTKEY_AVAILABLE')
    if item.kf_cycle:
        ks_options.add('INSERTKEY_CYCLE_AWARE')


    if item.kf_group is not '':
        ks_params = {'options': ks_options, 'group': item.kf_group}
    else:
        ks_params = {'options': ks_options}

    return value, id, ref, prop, dp, ks_params, func, post_func


def encode(chan, cont_type):
    chan -= 1
    # return channel byte, number of param, quantification
    if cont_type == 'AT_mono':
        return 13 * 16 + chan, 1, 127
    if cont_type == 'AT_poly':
        return 10 * 16 + chan, 2, 127
    if cont_type == 'pitchbend':
        return 14 * 16 + chan, 2, 16383
    if cont_type == 'pgm':
        return 12 * 16 + chan, 1, 127
    if cont_type == 'cc7':
        return 11 * 16 + chan, 2, 127
    if cont_type == 'rpn' or cont_type == 'nrpn':
        return 11 * 16 + chan, 2, 127
    if cont_type == 'rpn14' or cont_type == 'nrpn14':
        return 11 * 16 + chan, 2, 16383

    # workaround for the other note types, to be removed
    return 11 * 16 + chan, 2, 127


def yield_all_routes():
    n = 0
    prefs = bpy.context.preferences.addons['AddRoutes'].preferences

    len1 = len(bpy.context.scene.MOM_Items)
    len2 = len(prefs.AddR_System_Routes)
    len_t = len1+len2

    while n < len_t:
        if n < len1 :
            route_p = n, bpy.context.scene.MOM_Items[n]
        else:
            m = n-len1
            route_p = m, prefs.AddR_System_Routes[m]
        n = n + 1
        yield route_p


def generate_dict(self, context):
    exed_item = {
        'key_on': [],
        'key_off': [],
        'cc7': [],
        'pgm': [],
        'AT_mono': [],
        'AT_poly': [],
        'pitchbend': [],
        'rpn': [],
        'rpn14': [],
        'nrpn': [],
        'nrpn14': []
        }

    g_vars.addroutes_in = {
        '1': copy.deepcopy(exed_item),
        '2': copy.deepcopy(exed_item),
        '3': copy.deepcopy(exed_item),
        '4': copy.deepcopy(exed_item),
        '5': copy.deepcopy(exed_item),
        '6': copy.deepcopy(exed_item),
        '7': copy.deepcopy(exed_item),
        '8': copy.deepcopy(exed_item),
        '9': copy.deepcopy(exed_item),
        '10': copy.deepcopy(exed_item),
        '11': copy.deepcopy(exed_item),
        '12': copy.deepcopy(exed_item),
        '13': copy.deepcopy(exed_item),
        '14': copy.deepcopy(exed_item),
        '15': copy.deepcopy(exed_item),
        '16': copy.deepcopy(exed_item),
        'pass': None
        }

    g_vars.addroutes_out = []
    g_vars.addroutes_osc_in = {}
    g_vars.addroutes_osc_out = []

    addroutes_blemote_pre = {}

    for i, item in yield_all_routes():
        if item.is_multi:
            j = item.number
        else:
            j = 1

        # first pass to test if creating a route is possible
        try:
            for k in range(j):
                # val = k + item.offset
                value, id, ref, prop, dp, ks_params, func, post_func = parse_route(item, k)
        except:
            item.alert = True
            break
        item.alert = False

        # some common variables for MIDI receiving/sending
        cont = item.cont_type
        chan = item.channel
        midi, lenx, quant = encode(chan, cont)

        # add an option for treating velocity later
        num = item['cont_type']
        option = g_vars.Cont_types[num][2]

        # set filter flag to various events
        # MIDI : "option" is useful only for receiving, but f_show and f_filter serve for the GUI too (send/receive)
        if item.engine == 'MIDI':
            if option == '':
                item.f_show = False
                item.filter = False
            if option == 'f_forced':
                item.filter = True
                item.f_show = False
            if option == 'f_opt':
                item.f_show = True

        if item.mode == 'Receive' or item.mode == 'Both':
            dico = {}

            # actually create route for MIDI
            if item.engine == 'MIDI':
                rescale = item.rescale_outside_high - item.rescale_outside_low
                for k in range(j):
                    value, id, ref, prop, dp, ks_params, func, post_func = parse_route(item, k)
                    filt = str(k + item.controller)
                    dico[filt] = {
                        'ref': ref,
                        'prop': prop,
                        'option': option,
                        'quant': quant,
                        'rescale_out': rescale,
                        'func': func['midi_in_func'],
                        'post_func': post_func,
                        'ks_params': ks_params
                     }

                g_vars.addroutes_in[str(chan)][cont].append((i, item, dico))

            # for OSC
            elif item.engine == 'OSC':
                if g_vars.addroutes_osc_in.get(item.osc_address) is None:
                    g_vars.addroutes_osc_in[item.osc_address] = []

                for k in range(j):
                    value, id, ref, prop, dp, ks_params, func, post_func = parse_route(item, k)
                    filt = str(k)

                    dico[filt] = {
                        'ref': ref,
                        'prop': prop,
                        'func': func['osc_in_func'],
                        'post_func': post_func,
                        'ks_params': ks_params
                     }

                g_vars.addroutes_osc_in[item.osc_address].append((i, item, dico))

        if item.mode == 'Send' or item.mode == 'Both':
            # for MIDI engine
            if item.engine == 'MIDI':
                rescale = item.rescale_blender_high - item.rescale_blender_low

                # for single and multi routes
                for k in range(j):
                    value, id, ref, prop, dp, ks_params, func, post_func = parse_route(item, k)
                    filt = k + item.controller
                    LSB = str(filt % 128)
                    MSB = str(int(filt / 128))

                    if item.cont_type == 'rpn':
                        reg = [(101, MSB), (100, LSB), (6, 'val2')]
                    elif item.cont_type == 'rpn14':
                        reg = [(101, MSB), (100, LSB), (6, 'MSB'), (38, 'LSB')]
                    elif item.cont_type == 'nrpn':
                        reg = [(99, MSB), (98, LSB), (6, 'val2')]
                    elif item.cont_type == 'nrpn14':
                        reg = [(99, MSB), (98, LSB), (6, 'MSB'), (38, 'LSB')]
                    else:
                        reg = None

                    dico = {
                        'chan': chan,
                        'cont': cont,
                        'ref': ref,
                        'prop': prop,
                        'ID': id,
                        'filter': filt,
                        'midi': midi,
                        'val': None,
                        'rescale_bl': rescale,
                        'quant': quant,
                        'lenx': lenx,
                        'reg': reg,
                        'func': func['midi_out_func'],
                        'parent': item,
                        'n': i}

                    g_vars.addroutes_out.append((item, dico))


            # for OSC
            else:
                # for single and multi routes
                for k in range(j):
                    value, id, ref, prop, dp, ks_params, func, post_func = parse_route(item, k)

                    dico= {'address': item.osc_address,
                         'ref': ref,
                         'prop': prop,
                         'ID': id,
                         'val': None,
                         'func': func['osc_out_func'],
                         'n': i,
                         'idx': k
                         }

                    g_vars.addroutes_osc_out.append((item, dico))

        # A special case is Blemote (no receive/send thing)
        if item.engine == 'Blemote':
            value, id, ref, prop, dp, ks_params, func, post_func = parse_route(item)
            addroutes_blemote_pre[item.perma_rank] = {
                'ref': ref,
                'prop': prop,
                'ID': id,
                'parent': item,
                'func': func['blemote_func'],
                'post_func': post_func,
                'ks_params': ks_params
            }

    # this to avoid some errors when changing scene
    g_vars.scene = context.scene
    #generate_dict(None, context)
    #print(g_vars.addroutes_in, "\n")
    #print(g_vars.addroutes_out, "\n")

    #print(g_vars.addroutes_osc_in, "\n")
    #print(g_vars.addroutes_osc_out, "\n")

    # for the blemotization and the real blemote routes
    g_vars.addroutes_blemote = {}
    for i, item in yield_all_routes():
        trigger = None
        if item.blem_switch and item.engine == 'MIDI':
            trigger = {
                      'channel': item.channel,
                      'cont_type': item.cont_type,
                      'controller': item.controller
            }
        elif item.blem_switch and item.engine == 'OSC':
            trigger = item.osc_address

        elif item.engine == 'Blemote':
            trigger = addroutes_blemote_pre.get(item.perma_rank)

        if trigger is not None:
            dico = {
                'engine': item.engine,
                'trigger': trigger,
                'min': item.blem_min,
                'max': item.blem_max,
                'step': item.blem_step,
                'category': item.category
            }
            g_vars.addroutes_blemote[str(item.perma_rank)] = (item, i, dico)
        else:
            pass
            #print('fail')
    #print(g_vars.addroutes_blemote)


def dynamic_cat(self, context):
    list_items = [("Default", "Default", "", 0)]
    for item in context.scene.MOM_categories:
        new = (item.name, item.name, item.name, item.rank)
        list_items.append(new)
    return list_items


class MOM_categories_PG(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name='New Category')
    rank: bpy.props.IntProperty()


class AddRoutes_ID_PG(bpy.types.PropertyGroup):
    actions:        bpy.props.PointerProperty(name="ID_act", type=bpy.types.Action, update=generate_dict)
    armatures:      bpy.props.PointerProperty(name="ID_arm", type=bpy.types.Armature, update=generate_dict)
    brushes:        bpy.props.PointerProperty(name="ID_bru", type=bpy.types.Brush, update=generate_dict)
    cache_files:    bpy.props.PointerProperty(name="ID_cac", type=bpy.types.CacheFile, update=generate_dict)
    cameras:        bpy.props.PointerProperty(name="ID_cam", type=bpy.types.Camera, update=generate_dict)
    collections:    bpy.props.PointerProperty(name="ID_col", type=bpy.types.Collection, update=generate_dict)
    curves:         bpy.props.PointerProperty(name="ID_cur", type=bpy.types.Curve, update=generate_dict)
    grease_pencils: bpy.props.PointerProperty(name="ID_gre", type=bpy.types.GreasePencil, update=generate_dict)
    images:         bpy.props.PointerProperty(name="ID_ima", type=bpy.types.Image, update=generate_dict)
    shape_keys:     bpy.props.PointerProperty(name="ID_sha", type=bpy.types.Key, update=generate_dict)                     #Warning shape_keys or keys ???
    lattices:       bpy.props.PointerProperty(name="ID_lat", type=bpy.types.Lattice, update=generate_dict)
    libraries:      bpy.props.PointerProperty(name="ID_lib", type=bpy.types.Library, update=generate_dict)
    lights:         bpy.props.PointerProperty(name="ID_lig", type=bpy.types.Light, update=generate_dict)
    lightprobes:    bpy.props.PointerProperty(name="ID_lip", type=bpy.types.LightProbe, update=generate_dict)
    linestyles:     bpy.props.PointerProperty(name="ID_lin", type=bpy.types.FreestyleLineStyle, update=generate_dict)
    masks:          bpy.props.PointerProperty(name="ID_mas", type=bpy.types.Mask, update=generate_dict)
    materials:      bpy.props.PointerProperty(name="ID_mat", type=bpy.types.Material, update=generate_dict)
    meshes:         bpy.props.PointerProperty(name="ID_mes", type=bpy.types.Mesh, update=generate_dict)
    metaballs:      bpy.props.PointerProperty(name="ID_met", type=bpy.types.MetaBall, update=generate_dict)
    movieclips:     bpy.props.PointerProperty(name="ID_mov", type=bpy.types.MovieClip, update=generate_dict)
    node_groups:    bpy.props.PointerProperty(name="ID_nod", type=bpy.types.NodeTree, update=generate_dict)
    objects:        bpy.props.PointerProperty(name="ID_obj", type=bpy.types.Object, update=generate_dict)
    paint_curves:   bpy.props.PointerProperty(name="ID_pai", type=bpy.types.PaintCurve, update=generate_dict)
    palettes:       bpy.props.PointerProperty(name="ID_pal", type=bpy.types.Palette, update=generate_dict)
    particles:      bpy.props.PointerProperty(name="ID_par", type=bpy.types.ParticleSettings, update=generate_dict)
    scenes:         bpy.props.PointerProperty(name="ID_sce", type=bpy.types.Scene, update=generate_dict)
    sounds:         bpy.props.PointerProperty(name="ID_sou", type=bpy.types.Sound, update=generate_dict)
    speakers:       bpy.props.PointerProperty(name="ID_spe", type=bpy.types.Speaker, update=generate_dict)
    texts:          bpy.props.PointerProperty(name="ID_tex", type=bpy.types.Text, update=generate_dict)
    textures:       bpy.props.PointerProperty(name="ID_tur", type=bpy.types.Texture, update=generate_dict)
    fonts:          bpy.props.PointerProperty(name="ID_fon", type=bpy.types.VectorFont, update=generate_dict)
    window_managers:bpy.props.PointerProperty(name="ID_win", type=bpy.types.WindowManager, update=generate_dict)
    workspaces:     bpy.props.PointerProperty(name="ID_wor", type=bpy.types.WorkSpace, update=generate_dict)
    worlds:         bpy.props.PointerProperty(name="ID_wod", type=bpy.types.World, update=generate_dict)


g_vars.ID_types = [
                    ('actions', 'Action', 'Action', 'ACTION', 0),
                    ('armatures', 'Armature', 'Armature', 'ARMATURE_DATA', 1),
                    ('brushes', 'Brush', 'Brush', 'BRUSH_DATA', 2),
                    ('cache_files', 'CacheFile', 'CacheFile', 'FILE', 3),
                    ('cameras', 'Camera', 'Camera', 'CAMERA_DATA', 4),
                    ('collections', 'Collection', 'Collection', 'GROUP', 5),
                    ('curves', 'Curve', 'Curve', 'CURVE_DATA', 6),
                    ('grease_pencils', 'Grease Pencil', 'Grease Pencil', 'GREASEPENCIL', 7),
                    ('images', 'Image', 'Image', 'IMAGE_DATA', 8),
                    ('shape_keys', 'Key', 'Key', 'SHAPEKEY_DATA', 9),
                    ('lattices', 'Lattice', 'Lattice', 'LATTICE_DATA', 10),
                    ('libraries', 'Library', 'Library', 'LIBRARY_DATA_DIRECT', 11),
                    ('lights', 'Light', 'Light', 'LIGHT_DATA', 12),
                    ('lightprobes', 'LightProbe', 'LightProbe', 'LIGHTPROBE_CUBEMAP', 13),
                    ('linestyles', 'Line Style', 'Line Style', 'LINE_DATA', 14),
                    ('masks', 'Mask', 'Mask', 'MOD_MASK', 15),
                    ('materials', 'Material', 'Material', 'MATERIAL_DATA', 16),
                    ('meshes', 'Mesh', 'Mesh', 'MESH_DATA', 17),
                    ('metaballs', 'Metaball', 'Metaball', 'META_DATA', 18),
                    ('movieclips', 'Movie Clip', 'Movie Clip', 'SEQUENCE', 19),
                    ('node_groups', 'Node Tree', 'Node Tree', 'NODETREE', 20),
                    ('objects', 'Object', 'Object', 'OBJECT_DATA', 21),
                    ('paint_curves', 'Paint Curve', 'Paint Curve', 'CURVE_BEZCURVE', 22),
                    ('palettes', 'Palette', 'Palette', 'RESTRICT_COLOR_ON', 23),
                    ('particles', 'Particle', 'Particle', 'PARTICLE_DATA', 24),
                    ('scenes', 'Scene', 'Scene', 'SCENE_DATA', 25),
                    # ('screens', 'Screen', 'Screen', 'SCREEN', 25),                                                       #No screen exposed ?
                    ('sounds', 'Sound', 'Sound', 'SOUND', 26),
                    ('speakers', 'Speaker', 'Speaker', 'SPEAKER', 27),
                    ('texts', 'Text', 'Text', 'TEXT', 28),
                    ('textures', 'Texture', 'Texture', 'TEXTURE_DATA', 29),
                    ('fonts', 'Font', 'Font', 'FONT_DATA', 30),
                    ('window_managers', 'Window Manager', 'Window Manager', 'WINDOW', 31),
                    ('workspaces', 'Workspace', 'Workspace', 'WORKSPACE', 32),
                    ('worlds', 'World', 'World', 'WORLD_DATA', 33)
            ]


class MOM_Items_PG(bpy.types.PropertyGroup):
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
    id_type: bpy.props.EnumProperty(
                items=g_vars.ID_types,
                name='ID-Block',
                default='objects',
                update=generate_dict
                )
    id: bpy.props.PointerProperty(name='ID', type=AddRoutes_ID_PG, update=generate_dict)
    data_path: bpy.props.StringProperty(name="Data Path", update=generate_dict)
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
    is_str2eval: bpy.props.BoolProperty(name='python expr', update=generate_dict)
    str2eval : bpy.props.StringProperty(name="To eval", update=generate_dict)
    withctx : bpy.props.StringProperty(name="Context", default='VIEW_3D', update=generate_dict)
    eval_mode: bpy.props.EnumProperty(
        name='Actualization',
        items=[
                    ('replace', 'Replace', 'replace', '', 0),
                    #('add', 'add', 'add', '', 1),
                    #('subtract', 'subtract', 'subtract', '', 2),
                    #('multiply', 'multiply', 'multiply', '', 3),
                    #('divide', 'divide', 'divide', '', 4),
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
    kf_group: bpy.props.StringProperty(name='Group', description='Group name for F-curves (mandatory for MIDI envelope)', update=generate_dict)

    # for Blemote
    blem_switch: bpy.props.BoolProperty(name='Show Blemote options', description='Display this route in Blemote', update=generate_dict)
    blem_min: bpy.props.FloatProperty(name='Min', default=0, update=generate_dict)
    blem_max: bpy.props.FloatProperty(name='Max', default=100, update=generate_dict)
    blem_step: bpy.props.FloatProperty(name='Step', min=0, description='Minimal interval (0 = None)', update=generate_dict)
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
    osc_select_rank: bpy.props.IntProperty(name="From", description="Starting rank to pick data in the incoming payload", update=generate_dict)
    osc_select_n: bpy.props.IntProperty(name="n", min=1, default=1, description="Number of items to pick in the incoming payload", update=generate_dict)

    # for angles
    rad2deg: bpy.props.BoolProperty(name='Deg <-> Rad', default=True, update=generate_dict, description='Convert degrees <-> radians')
    is_angle: bpy.props.BoolProperty(name='Is Angle')

    # for MIDI post processing
    env_auto: bpy.props.BoolProperty(name='Auto', description='Automatically apply envelope after midifile conversion')
    env_attack: bpy.props.IntProperty(name='Pre Attack', description='Pre Attack time in millisecondes', default=50, min=1)
    env_release: bpy.props.IntProperty(name='Release', description='Release time in millisecondes', default=50, min=1)

    # for the categories feature
    category: bpy.props.EnumProperty(
        name='Category',
        items=dynamic_cat,
        update=generate_dict
    )

    # for internal sorting
    perma_rank: bpy.props.IntProperty()

    # gui features
    show_expanded: bpy.props.BoolProperty(default=True)


class AddRoutes_GetCTX(bpy.types.Operator):
    '''Get the Area CTX'''
    bl_idname = "addroutes.getctx"
    bl_label = "AddRoutes Remove Sys Route"

    s: bpy.props.StringProperty()

    def execute(self, context):
        global g_vars
        splitted = self.s.split('.')
        ref = '.'.join(splitted[:-1])
        g_vars.eval_prop = splitted[-1]
        C = context
        D = bpy.data

        try:
            g_vars.eval_ref = eval(ref)
        except:
            print("Error while evaluating string...")
            g_vars.eval_ref = None

        return {'FINISHED'}


cls = ( MOM_categories_PG,
        AddRoutes_GetCTX,
        AddRoutes_ID_PG,
        MOM_Items_PG
        )


def register():
    for c in cls:
        register_class(c)
    bpy.types.Scene.MOM_categories = bpy.props.CollectionProperty(type=MOM_categories_PG)
    bpy.types.Scene.MOM_catenum = bpy.props.EnumProperty(
        name='Category',
        items=dynamic_cat)
    bpy.types.Scene.MOM_Items = bpy.props.CollectionProperty(type=MOM_Items_PG)
    bpy.types.Scene.show_postprocess = bpy.props.BoolProperty(name="Show envelope settings ")
    bpy.types.Scene.show_categories = bpy.props.BoolProperty(name="Show categories")
    bpy.types.Scene.addroutes_show_name_setting = bpy.props.BoolProperty(name="Show name setting")
    bpy.types.Scene.show_routes_number = bpy.props.BoolProperty(name="Show routes number")
    bpy.types.Scene.MOM_sorting = bpy.props.EnumProperty(
        name='Sorting',
        items=[
            ('None', 'None', '', '', 0),
            ('Category', 'Category', '', '', 1)
        ]
    )


def unregister():
    del bpy.types.Scene.MOM_categories
    del bpy.types.Scene.MOM_catenum
    del bpy.types.Scene.MOM_sorting
    del bpy.types.Scene.show_routes_number
    del bpy.types.Scene.show_categories
    del bpy.types.Scene.addroutes_show_name_setting
    del bpy.types.Scene.show_postprocess
    del bpy.types.Scene.MOM_Items
    for c in cls:
        unregister_class(c)


if __name__ == "__main__":
    register()