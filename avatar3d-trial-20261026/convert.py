"""Convert the licensed rig, materials and compatible motion captures to GLB."""
import bpy,sys,json,re,math
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:];asset,out=map(Path,args)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(asset/'Export/Business_Male_03_facial.fbx'),use_anim=False)
rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert rigs,'Character has no skeleton'
rig=max(rigs,key=lambda o:len(o.data.bones));originals=set(bpy.data.objects)
for ob in list(bpy.context.scene.objects):
 if ob.type=='MESH' and re.search(r'(?:midpoly|ultralowpoly|(?<!hi)lowpoly)',ob.name,re.I):bpy.data.objects.remove(ob,do_unlink=True)
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert meshes
for mat in bpy.data.materials:
 label=mat.name.lower();part='opacity' if any(x in label for x in ['opacity','hair','eyelash']) else 'head' if any(x in label for x in ['head','eye','teeth','tongue']) else 'body'
 color=asset/f'Textures/m020_{part}_color.tga'
 if not color.exists():color=asset/'Textures/m020_head_color.tga'
 mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();p=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(p.outputs['BSDF'],output.inputs['Surface'])
 p.inputs['Metallic'].default_value=0;p.inputs['Roughness'].default_value=.72 if part=='body' else .58
 if 'Specular' in p.inputs:p.inputs['Specular'].default_value=.25
 image=bpy.data.images.load(str(color),check_existing=True);image.scale(min(image.size[0],2048),min(image.size[1],2048));image.file_format='PNG';image.filepath_raw=str(out/(part+'-color.png'));image.save()
 tex=nodes.new('ShaderNodeTexImage');tex.image=image;mat.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
 if part=='opacity':
  mat.node_tree.links.new(tex.outputs['Alpha'],p.inputs['Alpha']);mat.blend_method='HASHED';mat.use_backface_culling=False
 normal=asset/f'Textures/m020_{part}_normal.tga'
 if normal.exists():
  im=bpy.data.images.load(str(normal),check_existing=True);im.scale(min(im.size[0],1024),min(im.size[1],1024));im.colorspace_settings.name='Non-Color';im.file_format='PNG';im.filepath_raw=str(out/(part+'-normal.png'));im.save()
  nt=nodes.new('ShaderNodeTexImage');nt.image=im;nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.35;mat.node_tree.links.new(nt.outputs['Color'],nm.inputs['Color']);mat.node_tree.links.new(nm.outputs['Normal'],p.inputs['Normal'])
motions=[]
for filename,label in [('m_gestic_talk_neutral_01.max.fbx','lecture_talk'),('m_gestic_presentation_right_01.max.fbx','lecture_explain')]:
 before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(asset/filename),use_anim=True)
 imported=list(set(bpy.data.objects)-before);arms=[o for o in imported if o.type=='ARMATURE' and o.animation_data and o.animation_data.action]
 if arms:
  arm=max(arms,key=lambda o:len(o.data.bones));action=arm.animation_data.action;action.name=label
  target={b.name for b in rig.data.bones};source={b.name for b in arm.data.bones};shared=target&source
  if len(shared)>=15:
   for fc in list(action.fcurves):
    if 'pose.bones[' not in fc.data_path or '.location' in fc.data_path:action.fcurves.remove(fc)
   rig.animation_data_create();track=rig.animation_data.nla_tracks.new();track.name=label;strip=track.strips.new(label,1,action);strip.action_frame_start=action.frame_range[0];strip.action_frame_end=action.frame_range[1]
   motions.append({'name':label,'frames':list(action.frame_range),'sharedBones':len(shared)})
 for ob in imported:bpy.data.objects.remove(ob,do_unlink=True)
rig.animation_data_create();rig.animation_data.action=None
bpy.context.scene.frame_set(1)
metadata={'meshes':[{'name':o.name,'vertices':len(o.data.vertices),'materials':[m.name if m else None for m in o.data.materials],'shapeKeys':[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else []} for o in meshes],'bones':[b.name for b in rig.data.bones],'motions':motions,'objects':[o.name for o in bpy.context.scene.objects]}
(out/'model-report.json').write_text(json.dumps(metadata,indent=2))
bpy.ops.object.select_all(action='DESELECT')
for ob in list(bpy.context.scene.objects):
 if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
options={'filepath':str(out/'professor.glb'),'export_format':'GLB','use_selection':True,'export_animations':True,'export_nla_strips':True,'export_force_sampling':True,'export_morph':True,'export_skins':True,'export_yup':True,'export_apply':False}
supported=bpy.ops.export_scene.gltf.get_rna_type().properties.keys();options={k:v for k,v in options.items() if k in supported}
bpy.ops.export_scene.gltf(**options)
assert (out/'professor.glb').stat().st_size>100000
print(json.dumps({'meshes':len(meshes),'bones':len(metadata['bones']),'motions':motions,'glbBytes':(out/'professor.glb').stat().st_size}))
