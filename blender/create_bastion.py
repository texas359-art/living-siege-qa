"""Original Bastion assets. No imported models. Blender 3.x bpy, CPU rendering."""
import bpy, math, json, random
from mathutils import Vector, Quaternion
from pathlib import Path
ROOT=Path('model-results');ROOT.mkdir(exist_ok=True)
random.seed(359)

def material(name,color,metal=.0,rough=.4):
    m=bpy.data.materials.new(name);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    im=bpy.data.images.new(name+'_surface',width=64,height=64)
    pix=[]
    for i in range(64*64):
        f=random.uniform(.965,1.035);pix.extend([min(1,c*f) for c in color]+[1])
    im.pixels=pix;im.pack()
    tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    return m

def mesh(name,verts,faces,mat,bone,bevel=.025):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(mat)
    bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    if bevel:
        mod=ob.modifiers.new('Forged edge radii','BEVEL');mod.width=bevel;mod.segments=3
        if hasattr(mod,'affect'):mod.affect='EDGES'
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for poly in ob.data.polygons:poly.use_smooth=True
    wn=ob.modifiers.new('Plate normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=50
    bpy.ops.object.modifier_apply(modifier=wn.name)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
    if bone:
        vg=ob.vertex_groups.new(name=bone);vg.add(list(range(len(ob.data.vertices))),1,'REPLACE')
    ob.select_set(False);PARTS.append(ob);return ob

def loft(name,rings,mat,bone,n=16,exponent=.65,bevel=.02):
    # rings are (center x,y,z, halfwidth, halfdepth); custom nonprimitive shell.
    verts=[]
    for x,y,z,w,dep in rings:
        for i in range(n):
            a=2*math.pi*i/n;c=math.cos(a);s=math.sin(a)
            verts.append((x+w*math.copysign(abs(c)**exponent,c),y+dep*math.copysign(abs(s)**exponent,s),z))
    faces=[tuple(reversed(range(n)))]
    for j in range(len(rings)-1):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces.append(tuple((len(rings)-1)*n+i for i in range(n)))
    return mesh(name,verts,faces,mat,bone,bevel)

def plate(name,outline,y,depth,mat,bone,curve=.0,bevel=.025):
    # Sculpted extruded x,z polygon, bowed outward at its centre.
    v=[];mx=max(abs(x) for x,z in outline) or 1
    for side in [0,1]:
        for x,z in outline:v.append((x,y+side*depth+curve*(x/mx)**2,z))
    n=len(outline);faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return mesh(name,v,faces,mat,bone,bevel)

def strip(name,pts,width,y,dep,mat,bone):
    # Beveled decorative ribbon in x,z; supplies original shield insignia.
    for k,((x,z),(x2,z2)) in enumerate(zip(pts,pts[1:])):
        dx=x2-x;dz=z2-z;l=math.hypot(dx,dz);ox=-dz/l*width/2;oz=dx/l*width/2
        plate(name+str(k),[(x+ox,z+oz),(x2+ox,z2+oz),(x2-ox,z2-oz),(x-ox,z-oz)],y,dep,mat,bone,bevel=min(width/3,.012))

def rivet(name,x,y,z,mat,bone):
    # Octagonal countersunk fastener instead of spherical ornament.
    pts=[(x+.033*math.cos(i*math.pi/4),z+.033*math.sin(i*math.pi/4)) for i in range(8)]
    plate(name,pts,y,.025,mat,bone,bevel=.007)

def build(variant,enemy=False):
    global PARTS
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);PARTS=[]
    for action in list(bpy.data.actions):bpy.data.actions.remove(action)
    steel=material('Blue tempered armour',(.075,.17,.24),.72,.3)
    edge=material('Brushed pale alloy',(.46,.61,.65),.78,.3)
    brass=material('Warm brass inlay',(.65,.37,.115),.7,.34)
    accent=material('Ember enamel',(.88,.21,.055),.18,.32)
    dark=material('Recesses',(.015,.026,.039),.15,.55)
    cloth=material('Carbon weave',(.028,.038,.045),.0,.78)
    glow=material('Warm visor',(.98,.56,.16),.1,.26)
    if enemy:steel=material('Raider copper armour',(.45,.055,.025),.63,.37)
    width={'tower':1,'forge':1.13,'sentinel':.91}[variant]
    # Purpose-built armour torso with six changing cross sections.
    loft('Underarm flexible torso',[(0,0,1.16,.36,.26),(0,0,1.45,.49,.30),(0,0,1.88,.55,.30),(0,0,2.04,.48,.27)],cloth,'spine')
    loft('Forged breast shell',[(0,0,1.35,.42*width,.31),(0,0,1.52,.57*width,.38),(0,.015,1.91,.68*width,.42),(0,.035,2.12,.58*width,.33),(0,.04,2.18,.44*width,.28)],steel,'spine',n=20)
    # Framed chest panel, a designed shield shape with inward waist taper.
    outline=[(-.5*width,2.05),(.5*width,2.05),(.56*width,1.89),(.34*width,1.48),(0,1.39),(-.34*width,1.48),(-.56*width,1.89)]
    plate('Chest perimeter',outline,-.432,.065,edge,'spine',curve=.035)
    outline2=[(x*.86,(z-1.78)*.88+1.78) for x,z in outline]
    plate('Deep forged chest face',outline2,-.468,.045,steel,'spine',curve=.055)
    strip('Chest split emblem',[(-.12,1.84),(0,1.94),(.12,1.84),(0,1.69),(-.12,1.84)],.045,-.51,.02,brass,'spine')
    for z,w in [(1.37,.45),(1.24,.40),(1.12,.37)]:
        plate('Floating abdominal lames',[(-w,z+.07),(w,z+.07),(w*.94,z-.04),(-w*.94,z-.04)],-.32,.13,steel if z!=1.24 else edge,'pelvis')
    loft('Pelvis belt',[(0,0,1.04,.45,.30),(0,0,1.17,.48,.33)],dark,'pelvis')
    plate('Central belt clasp',[(-.12,1.17),(.12,1.17),(.13,1.04),(-.13,1.04)],-.38,.07,brass,'pelvis')
    # Broad articulated tassets, layered rather than a single box.
    for sign,side in [(-1,'l'),(1,'r')]:
        for j in range(3):
            z=1.04-j*.115;x=sign*.38;w=.24
            plate('Hip overlapping plate',[(x-w,z+.04),(x+w,z+.04),(x+w*.95,z-.10),(x-w*.95,z-.10)],-.29-j*.01,.095,steel if j!=1 else edge,'thigh'+side)
        x=sign*.38
        loft('Thigh flexible joint',[(x,0,.55,.20,.20),(x,0,.98,.24,.24)],cloth,'thigh'+side)
        loft('Thigh armour',[(x,.025,.69,.22,.23),(x,.02,.98,.28,.28),(x,0,1.02,.26,.25)],steel,'thigh'+side)
        plate('Knee layered guard',[(x-.21,.72),(x,.80),(x+.21,.72),(x+.16,.52),(x,.48),(x-.16,.52)],-.29,.11,edge,'shin'+side)
        loft('Shin shaped greave',[(x,.02,.20,.19,.18),(x,.04,.44,.23,.22),(x,.035,.58,.22,.22)],steel,'shin'+side)
        strip('Shin inlay',[(x,.24),(x,.49)],.055,-.205,.025,brass,'shin'+side)
        # Boots have custom swept toe, shaped ankle and layered sole.
        loft('Boot reinforced sole',[(x,-.14,.035,.29,.39),(x,-.14,.12,.30,.41),(x,-.10,.16,.27,.37)],dark,'foot'+side,n=20)
        loft('Boot sculpted toe',[(x,-.15,.13,.28,.38),(x,-.14,.22,.29,.39),(x,-.035,.34,.24,.26)],steel,'foot'+side,n=20)
        for j in range(2):
            plate('Toe overlapping armour',[(x-.22,.20+j*.04),(x+.22,.20+j*.04),(x+.20,.14+j*.04),(x-.20,.14+j*.04)],-.53+j*.09,.08,edge if j==0 else steel,'foot'+side)
    # Upper arms, elbows, gauntlets and independently rigged hands.
    for sign,side in [(-1,'l'),(1,'r')]:
        x=sign*.88
        loft('Upperarm underlayer',[(x,.0,1.56,.18,.19),(x,0,2.03,.22,.23)],cloth,'upperarm'+side)
        for j in range(3 if variant!='sentinel' else 2):
            z=2.02-j*.13;w=(.37 if side=='l' else .29)*width
            # asymmetrical large stepped pauldron, five points per side.
            outline=[(x-w,z+.04),(x-w*.65,z+.20),(x+w*.62,z+.20),(x+w,z+.03),(x+w*.94,z-.12),(x-w*.94,z-.12)]
            plate('Stepped shoulder outer bevel',outline,-.24-j*.015,.44,edge if j==0 else steel,'upperarm'+side,bevel=.04)
            plate('Shoulder enamel insert',[(a*.92+x*.08,(b-z)*.78+z) for a,b in outline],-.27-j*.015,.035,steel if j==0 else accent if j==2 else steel,'upperarm'+side)
        if variant=='forge':
            for k in [-1,0,1]:
                plate('Forge shoulder raised fin',[(x+k*.13-.045,2.09),(x+k*.13+.045,2.09),(x+k*.13+.03,2.38),(x+k*.13-.03,2.33)],-.015,.18,brass,'upperarm'+side)
        loft('Elbow articulated seal',[(x,0,1.44,.19,.20),(x,0,1.58,.21,.22)],dark,'forearm'+side)
        loft('Forearm tapered forged cuff',[(sign*.94,-.035,1.10,.23,.22),(sign*.92,-.015,1.24,.29,.26),(x,0,1.47,.23,.22)],steel,'forearm'+side)
        for j in [0,1]:
            plate('Forearm split face',[(sign*.94-.19,1.15+j*.12),(sign*.94+.19,1.15+j*.12),(sign*.94+.18,1.24+j*.12),(sign*.94-.18,1.24+j*.12)],-.285,.07,edge if j==0 else steel,'forearm'+side)
        loft('Gauntlet palm',[(sign*.94,-.06,.93,.19,.19),(sign*.94,-.055,1.11,.21,.21)],dark,'hand'+side)
        for finger in range(4):
            xf=sign*.94+(finger-1.5)*.087
            loft('Finger plated segment',[(xf,-.13,.89,.045,.085),(xf,-.18,.96,.05,.09),(xf,-.14,1.04,.046,.085)],edge if finger in [0,3] else steel,'hand'+side,n=8,bevel=.009)
    # Designed helmet, different shell profile for each candidate.
    loft('Armoured gorget',[(0,0,2.08,.33,.27),(0,.015,2.28,.35,.30)],edge,'head',n=20)
    helmetProfiles={
        'tower':[(0,.01,2.23,.37,.30),(0,.015,2.39,.43,.38),(0,.05,2.70,.41,.37),(0,.06,2.84,.31,.28),(0,.05,2.88,.13,.18)],
        'forge':[(0,0,2.23,.40,.34),(0,0,2.38,.47,.40),(0,.02,2.63,.46,.40),(0,.035,2.77,.40,.34),(0,.035,2.80,.33,.30)],
        'sentinel':[(0,0,2.23,.32,.29),(0,.02,2.40,.37,.36),(0,.06,2.69,.33,.31),(0,.08,2.84,.18,.23),(0,.10,2.95,.03,.08)]}
    loft('Original helmet forged shell',helmetProfiles[variant],steel,'head',n=24,bevel=.025)
    plate('Visor recessed opening',[(-.33,2.58),(.33,2.58),(.32,2.42),(-.32,2.42)],-.379,.035,dark,'head',curve=.05,bevel=.015)
    for sign in [-1,1]:
        plate('Narrow visor light',[(sign*.045,2.49),(sign*.29,2.52),(sign*.285,2.46),(sign*.045,2.455)],-.406,.018,glow,'head',bevel=.007)
        plate('Cheek defensive plate',[(sign*.08,2.44),(sign*.35,2.45),(sign*.29,2.25),(sign*.10,2.23)],-.405,.07,edge,'head',curve=.02)
    plate('Brow single bridge',[(-.4,2.63),(0,2.71),(.4,2.63),(.35,2.55),(0,2.60),(-.35,2.55)],-.41,.075,edge,'head',curve=.035)
    plate('Nasal central wedge',[(-.055,2.63),(.055,2.63),(.07,2.30),(0,2.24),(-.07,2.30)],-.455,.04,brass,'head',bevel=.012)
    for sign in [-1,1]:
        for j in range(2):rivet('Helmet hinge',sign*.35,-.33,2.30+j*.11,brass,'head')
    if variant=='tower':
        strip('Helmet keystone crest',[(0,2.77),(0,2.93)],.075,-.12,.26,brass,'head')
    if variant=='sentinel':
        plate('Long rear helmet crest',[(-.06,2.71),(.06,2.71),(.045,3.08),(-.045,3.03)],.02,.34,brass,'head')
    # Oversized shield uses nested authored polygon surfaces and a raised emblem.
    if not enemy:
        sx=-.98;sz=1.17
        shapes={
            'tower':[(-.62,.78),(-.37,.94),(.37,.94),(.62,.78),(.57,-.68),(.33,-.90),(-.33,-.90),(-.57,-.68)],
            'forge':[(-.73,.40),(-.45,.78),(.45,.78),(.73,.40),(.73,-.40),(.43,-.78),(-.43,-.78),(-.73,-.40)],
            'sentinel':[(-.54,.77),(0,.97),(.54,.77),(.62,.22),(.38,-.51),(0,-.99),(-.38,-.51),(-.62,.22)]}
        poly=shapes[variant];out=[(sx+x,sz+z) for x,z in poly]
        plate('Shield deep rear chassis',out,-.52,.21,dark,'handl',curve=.055,bevel=.035)
        plate('Shield forged alloy perimeter',out,-.64,.12,edge,'handl',curve=.025,bevel=.04)
        inset=[(sx+x*.87,sz+z*.89) for x,z in poly]
        plate('Shield blue convex face',inset,-.69,.07,steel,'handl',curve=.018,bevel=.025)
        # Original gate emblem: two piers and a stepped broken crown.
        for sign in [-1,1]:
            strip('Shield gate pier',[(sx+sign*.26,sz-.43),(sx+sign*.26,sz+.30),(sx+sign*.14,sz+.45)],.095,-.78,.045,brass,'handl')
        strip('Shield central split',[(sx-.11,sz+.28),(sx,sz+.13),(sx-.075,sz-.03),(sx+.045,sz-.22)],.085,-.80,.045,edge,'handl')
        for k,(x,z) in enumerate(poly):
            rivet('Shield perimeter fastening',sx+x*.93,-.745,sz+z*.94,brass,'handl')
        for sign in [-1,1]:
            plate('Shield bottom bumper',[(sx+sign*.34-.105,sz-.78),(sx+sign*.34+.105,sz-.78),(sx+sign*.34+.09,sz-.65),(sx+sign*.34-.09,sz-.65)],-.785,.13,accent,'handl')
        plate('Shield rear grip',[(-1.13,1.36),(-.83,1.36),(-.83,1.10),(-1.13,1.10)],-.34,.08,dark,'handl')
    else:
        # Distinct enemy weapon, skin and proportion differ at construction time.
        plate('Raider falchion',[ (.86,1.04),(1.01,1.08),(1.08,1.82),(.96,1.91),(.89,1.50)],-.34,.07,edge,'handr',bevel=.02)
        plate('Falchion guard',[(.76,1.09),(1.12,1.09),(1.10,1.02),(.78,1.02)],-.36,.08,brass,'handr')
    # Rig with explicit independent limb segments. All armour is deform-weighted.
    arm=bpy.data.armatures.new('Bastion articulated rig');rig=bpy.data.objects.new('BastionRig',arm);bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    defs=[('root',(0,0,0),(0,0,.25),None),('pelvis',(0,0,1.08),(0,0,1.34),'root'),('spine',(0,0,1.34),(0,0,2.13),'pelvis'),('head',(0,0,2.13),(0,0,2.85),'spine')]
    for sign,side in [(-1,'l'),(1,'r')]:
        defs.extend([('upperarm'+side,(sign*.78,0,2.02),(sign*.88,0,1.53),'spine'),('forearm'+side,(sign*.88,0,1.53),(sign*.94,-.035,1.11),'upperarm'+side),('hand'+side,(sign*.94,-.035,1.11),(sign*.94,-.09,.90),'forearm'+side),('thigh'+side,(sign*.38,0,1.08),(sign*.38,.025,.61),'pelvis'),('shin'+side,(sign*.38,.025,.61),(sign*.38,0,.19),'thigh'+side),('foot'+side,(sign*.38,0,.19),(sign*.38,-.35,.12),'shin'+side)])
    for name,head,tail,parent in defs:
        bo=arm.edit_bones.new(name);bo.head=head;bo.tail=tail
        if parent:bo.parent=arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in PARTS:ob.select_set(True)
    bpy.context.view_layer.objects.active=PARTS[0];bpy.ops.object.join();body=bpy.context.object;body.name='Bastion_'+variant if not enemy else 'CrimsonRaider'
    body.parent=rig;mod=body.modifiers.new('Independent skeletal deformation','ARMATURE');mod.object=rig
    # Original raider has a taller narrower silhouette; applies equally to rig and mesh.
    if enemy:rig.scale=(.70,.78,1.03)
    create_actions(rig,enemy)
    return rig,body

def create_actions(rig,enemy=False):
    rig.animation_data_create()
    durations={'Idle':60,'Walk':42,'Attack':32,'Hit':22,'Death':48,'Spawn':18}
    for name,last in durations.items():
        action=bpy.data.actions.new(name);rig.animation_data.action=action
        for frame in range(last+1):
            t=frame/last
            for pb in rig.pose.bones:pb.rotation_mode='QUATERNION';pb.rotation_quaternion=(1,0,0,0);pb.location=(0,0,0)
            def rot(b,x=0,y=0,z=0):
                # Apply desired world-axis rotations in the bone's rest orientation.
                pb=rig.pose.bones[b];basis=pb.bone.matrix_local.to_quaternion()
                q=Quaternion((1,0,0),x)@Quaternion((0,1,0),y)@Quaternion((0,0,1),z)
                pb.rotation_quaternion=basis.inverted()@q@basis
            def root(x=0,y=0,z=0):rig.pose.bones['root'].location=(x,z,-y)
            # Resting defensive pose: shoulders draw shield forward, free hand balances.
            rot('upperarml',-.13,0,-.10);rot('forearml',-.14);rot('upperarmr',-.09,0,.08);rot('forearmr',-.12)
            if name=='Idle':
                a=2*math.pi*t;root(z=.012*math.sin(a));rot('spine',.02*math.sin(a),.025*math.sin(a),.01*math.sin(a));rot('head',-.02*math.sin(a),0,-.015*math.sin(a));rot('upperarml',-.13+.025*math.sin(a-.6),0,-.10)
            elif name=='Walk':
                a=2*math.pi*t
                root(x=.035*math.sin(a),z=.016*(1-math.cos(2*a)))
                rot('pelvis',.018,.045*math.sin(a),.025*math.sin(a));rot('spine',.04,-.025*math.sin(a),-.02*math.sin(a))
                for sign,side in [(-1,'l'),(1,'r')]:
                    s=math.sin(a+(0 if side=='l' else math.pi));lift=max(0,s)
                    rot('thigh'+side,.30*s);rot('shin'+side,-.36*lift);rot('foot'+side,.12*lift-.07*s)
                    rot('upperarm'+side,-.12-.12*s,0,sign*.09);rot('forearm'+side,-.14-.08*lift)
                rot('head',-.02,0,.015*math.sin(a))
            elif name=='Attack':
                # contact is frame 13 at 30 fps: anticipation, thrust, recoil, recover.
                keys=[(0,0),(.28,-1),(.40625,1),(.48,1),(.67,.25),(1,0)]
                v=0
                for (ta,va),(tb,vb) in zip(keys,keys[1:]):
                    if ta<=t<=tb:
                        u=(t-ta)/(tb-ta);u=u*u*(3-2*u);v=va+(vb-va)*u;break
                root(y=-.17*max(v,0),z=-.035*abs(v));rot('pelvis',-.07*v,0,.10*v);rot('spine',.12*v,0,-.19*v)
                rot('upperarml',-.13-.56*v,0,-.12-.12*v);rot('forearml',-.14+.18*v);rot('handl',-.06*v,0,.10*v)
                rot('upperarmr',.25*v,0,.10+.12*abs(v));rot('forearmr',-.15-.20*abs(v));rot('head',-.04*v,0,.08*v)
                rot('thighr',-.09*v);rot('shinr',-.12*abs(v));rot('thighl',.10*v);rot('shinl',-.10*abs(v))
                if enemy:rot('upperarmr',-.1-.85*v);rot('forearmr',-.1+.3*v)
            elif name=='Hit':
                v=math.sin(min(1,t*1.7)*math.pi)*math.exp(-t*.7);root(y=.11*v,z=-.06*v);rot('spine',-.22*v,0,.08*v);rot('head',-.18*v);rot('upperarml',-.13+.25*v);rot('upperarmr',.18*v,0,.16*v);rot('thighr',-.13*v);rot('shinr',-.2*v)
            elif name=='Death':
                u=max(0,min(1,(t-.08)/.62));u=u*u*(3-2*u)
                root(y=.40*u,z=-.92*u);rot('pelvis',-1.32*u,0,.15*u);rot('spine',-.20*math.sin(t*math.pi));rot('head',-.20*u)
                rot('upperarml',-.13-.44*u,0,-.5*u);rot('upperarmr',-.48*u,0,.65*u);rot('forearmr',-.4*u);rot('thighl',.40*u);rot('thighr',.22*u);rot('shinl',-.55*u);rot('shinr',-.35*u)
            elif name=='Spawn':
                v=(1-t)**2;root(z=.20*v);rot('spine',.08*math.sin(t*math.pi));rot('shinl',-.12*math.sin(t*math.pi));rot('shinr',-.12*math.sin(t*math.pi))
            for pb in rig.pose.bones:
                pb.keyframe_insert('rotation_quaternion',frame=frame);pb.keyframe_insert('location',frame=frame)
        for fc in action.fcurves:
            for k in fc.keyframe_points:k.interpolation='LINEAR'
        track=rig.animation_data.nla_tracks.new();track.name=name;strip=track.strips.new(name,1,action);strip.action_frame_start=0;strip.action_frame_end=last;track.mute=True
    rig.animation_data.action=None
    for track in rig.animation_data.nla_tracks:track.mute=False
    bpy.context.scene.frame_set(0)

def stage(rig):
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
    sc.render.resolution_x=sc.render.resolution_y=720;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
    sc.view_settings.view_transform='Filmic';sc.view_settings.look='Medium High Contrast';sc.view_settings.exposure=.4
    sc.world.color=(.14,.14,.14)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012));ground=bpy.context.object;ground.name='RenderGround'
    mat=bpy.data.materials.new('Stage matte');mat.diffuse_color=(.08,.105,.13,1);ground.data.materials.append(mat)
    for name,pos,power,size,color in [('Key',(-3,-4,6),950,4,(1,.85,.69)),('Rim',(3,3,5),1300,3,(.47,.72,1)),('Fill',(4,-2,3),500,4,(.72,.88,1))]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
        ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,0,1.3))-ob.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',data);bpy.context.collection.objects.link(cam);sc.camera=cam;data.type='ORTHO';data.ortho_scale=3.8
    return cam

manifest={'author':'Arena Inventors procedural original artwork','license':'Original project asset; no third party model incorporated','blender':bpy.app.version_string,'variants':[],'clips':{'Idle':2,'Walk':1.4,'Attack':32/30,'Hit':22/30,'Death':48/30,'Spawn':.6},'attackContactSeconds':13/30}
for variant,enemy in [('tower',False),('forge',False),('sentinel',False),('sentinel',True)]:
    name='raider' if enemy else variant
    rig,body=build(variant,enemy);sc=bpy.context.scene;sc.render.fps=30;sc.frame_start=0;sc.frame_end=60
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);body.select_set(True);bpy.context.view_layer.objects.active=rig
    glb=ROOT/(name+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=True,export_nla_strips=True,export_force_sampling=True,export_frame_range=False,export_skins=True,export_materials='EXPORT')
    cam=stage(rig)
    # NLA strips off for clean rest-pose review; assets already exported with actions.
    for tr in rig.animation_data.nla_tracks:tr.mute=True
    idle=bpy.data.actions.get('Idle');rig.animation_data.action=idle;sc.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/(name+'.blend')))
    if not enemy:
        for view,pos in [('front',(0,-7,1.5)),('side',(7,0,1.5)),('game',(-4,-6,4.8))]:
            cam.location=pos;cam.rotation_euler=(Vector((-.15,0,1.45))-cam.location).to_track_quat('-Z','Y').to_euler()
            sc.render.filepath=str(ROOT/(name+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
        manifest['variants'].append({'name':name,'vertices':len(body.data.vertices),'polygons':len(body.data.polygons),'bones':len(rig.data.bones),'file':glb.name})
    print('EXPORTED',name,glb.stat().st_size,flush=True)
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('ORIGINAL_BASTION_VARIANTS_READY',flush=True)
