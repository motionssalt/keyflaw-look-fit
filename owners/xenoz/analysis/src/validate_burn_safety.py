#!/usr/bin/env python3
"""Reproduce v1.1.1 safety checks. Requires numpy, OpenCV, scikit-image, moderngl/EGL.
Run from any directory. Baseline is read from git commit 3fb65ad (no input changes).
Software OpenGL is a numerical shader check, NOT a Keyflaw device test.
"""
from pathlib import Path
import json,sys,subprocess,re,itertools,hashlib
import numpy as np,cv2,moderngl
from skimage.color import rgb2lab,deltaE_ciede2000
from skimage.metrics import structural_similarity
O=Path(__file__).resolve().parents[2];R=O.parents[1];S=O/'spec';D=O/'analysis/outputs/burn_safety_v1.1.1';D.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(S));import look_apply as ref
P=json.loads((S/'look_params.json').read_text())
def baseline(path): return subprocess.check_output(['git','show','3fb65ad:'+path],cwd=R).decode()
old_shader=baseline('pack/effects/MS_xenoz_cc/shader.glsl');new_shader=(R/'pack/effects/MS_xenoz_cc/shader.glsl').read_text()
oldns={'__name__':'baseline'};exec(baseline('owners/xenoz/spec/look_apply.py'),oldns)
rawns={'__name__':'raw'};exec(baseline('owners/xenoz/spec/look_apply.py').replace('return np.clip(out, 0.0, 1.0).reshape(orig_shape)','return out.reshape(orig_shape)'),rawns)
oldp=json.loads(baseline('owners/xenoz/spec/look_params.json'))
ctx=moderngl.create_standalone_context(backend='egl');print('Offscreen renderer:',ctx.info['GL_RENDERER'])
VS='#version 330\nin vec2 pos; out vec2 vTex; void main(){vTex=pos*0.5+0.5;gl_Position=vec4(pos,0.0,1.0);}'
def program(src):
 src=re.sub(r'#ifdef GL_FRAGMENT_PRECISION_HIGH.*?#endif','',src,count=1,flags=re.S)
 src='#version 330\nout vec4 fragColor;\n'+src.replace('varying vec2 vTex;','in vec2 vTex;').replace('texture2D(','texture(').replace('gl_FragColor','fragColor')
 return ctx.program(vertex_shader=VS,fragment_shader=src)
progs={'before':program(old_shader),'after':program(new_shader)}
vbo=ctx.buffer(np.array([-1,-1,1,-1,-1,1,1,1],np.float32).tobytes())
def render(x,which='after',cc=1,quality=1,flare=1,intensity=1):
 h,w=x.shape[:2]
 if x.shape[-1]==3:x=np.concatenate([x,np.ones((h,w,1))],axis=-1)
 tex=ctx.texture((w,h),4,np.ascontiguousarray(x[::-1],dtype=np.float32).tobytes(),dtype='f4');tex.filter=(moderngl.LINEAR,moderngl.LINEAR);tex.repeat_x=False;tex.repeat_y=False;tex.use(0)
 target=ctx.texture((w,h),4,dtype='f4');fbo=ctx.framebuffer([target]);fbo.use();ctx.viewport=(0,0,w,h)
 prog=progs[which]
 for key,val in {'uTexture':0,'uTexelSize':(1/w,1/h),'uCc':cc,'uQuality':quality,'uFlare':flare,'uIntensity':intensity}.items():
  if key in prog:prog[key].value=val
 vao=ctx.vertex_array(prog,[(vbo,'2f','pos')]);vao.render(moderngl.TRIANGLE_STRIP)
 out=np.frombuffer(fbo.read(components=4,dtype='f4'),np.float32).reshape(h,w,4)[::-1].copy()
 vao.release();fbo.release();target.release();tex.release();return out

def metrics(pred,target,flat,valid,edges):
 de=deltaE_ciede2000(rgb2lab(pred),rgb2lab(target));err=(pred-target)*255
 _,ss=structural_similarity(pred@ref.LUMA_W,target@ref.LUMA_W,data_range=1,full=True)
 return {'median_de00':float(np.median(de[flat])),'p90_de00':float(np.percentile(de[flat],90)),'mae_rgb_255':np.mean(abs(err[flat]),axis=0).tolist(),'edge_rmse_255':float(np.sqrt(np.mean(err[edges]**2))),'valid_luma_ssim':float(np.mean(ss[valid])),'valid_any_channel_at_255_pct':float(np.mean(np.any(pred[valid]>=254.5/255,axis=-1))*100)}
summary={'version':'1.1.1','renderer':ctx.info['GL_RENDERER'],'baseline_commit':'3fb65ad','pairs':{},'tests':{}}
for pair in ['A','B']:
 x=cv2.imread(str(O/f'analysis/outputs/aligned/pair{pair}_orig_aligned_720p.png'))[:,:,::-1].astype(np.float64)/255
 target=cv2.imread(str(O/f'inputs/pair{pair}_edited.png'))[:,:,::-1].astype(np.float64)/255
 flat=cv2.imread(str(O/f'masks/pair{pair}_flat_interior.png'),0)>0
 valid=np.ones(x.shape[:2],bool)
 for name in ['bars','caption','invalid_border']:valid &= cv2.imread(str(O/f'masks/pair{pair}_{name}.png'),0)==0
 flat &= valid;edges=(cv2.imread(str(O/f'masks/pair{pair}_line_edges.png'),0)>0)&valid
 raw=rawns['stage1_colour_correction'](x,oldp['colour_correction'])
 before=render(x,'before')[:,:,:3];after=render(x)[:,:,:3]
 expected=ref.apply_look(x,P)
 diff=np.max(abs(expected-after));assert diff<1/255,('full frame shader/reference mismatch',pair,diff)
 colour=ref.stage1_colour_correction(x,P['colour_correction'])
 item={'raw_grade_out_of_gamut_valid_pct':float(np.mean(np.any((raw[valid]<0)|(raw[valid]>1),axis=-1))*100),'before':metrics(before,target,flat,valid,edges),'after':metrics(after,target,flat,valid,edges),'shader_reference_max_error_255':float(diff*255),'safe_grade_above_254_5_pct':float(np.mean(np.any(colour[valid]>=254.5/255,axis=-1))*100)}
 summary['pairs']['pair'+pair]=item
 cv2.imwrite(str(D/f'pair{pair}_after.png'),np.round(after[:,:,::-1]*255).astype(np.uint8))
 cv2.imwrite(str(D/f'pair{pair}_before.png'),np.round(before[:,:,::-1]*255).astype(np.uint8))
 err=np.mean(abs(after-target),axis=-1);heat=cv2.applyColorMap(np.round(np.clip(err*5,0,1)*255).astype(np.uint8),cv2.COLORMAP_INFERNO)
 tiles=[cv2.resize(np.round(z[:,:,::-1]*255).astype(np.uint8),(640,360)) for z in [target,before,after]]
 tiles.append(cv2.resize(heat,(640,360)));board=np.concatenate(tiles,axis=1)
 cv2.imwrite(str(D/f'pair{pair}_comparison.png'),board)
 print(pair,json.dumps(item))
# 33^3 cube in standard .cube order: red fastest.
a=np.linspace(0,1,33);b,g,r=np.meshgrid(a,a,a,indexing='ij');grid=np.stack([r,g,b],-1).reshape(-1,3)
raw=rawns['stage1_colour_correction'](grid,oldp['colour_correction']);safe=ref.stage1_colour_correction(grid,P['colour_correction'])
assert np.isfinite(safe).all() and safe.min()>=0 and safe.max()<=1
shader_grid=render(grid.reshape(33,1089,3),quality=0,flare=0)[:,:,:3].reshape(-1,3)
maxerr=float(np.max(abs(shader_grid-safe)));assert maxerr<1/255
summary['tests']['colour_cube']={'count':len(grid),'before_raw_out_of_gamut_pct':float(np.mean(np.any((raw<0)|(raw>1),axis=-1))*100),'shader_reference_max_error_255':maxerr*255,'safe_min':float(safe.min()),'safe_max':float(safe.max())}
with (S/'look.cube').open('w') as f:
 f.write('TITLE "Xenoz CC v1.1.1 gamut-safe colour only"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
 np.savetxt(f,safe,fmt='%.9f')
loaded=np.loadtxt(S/'look.cube',skiprows=4);assert np.max(abs(loaded-safe))<1e-8
# Anti-halo step input and ramps at three heights.
steps={}
for h in [409,720,1080]:
 x=np.broadcast_to(np.r_[np.full(20,.2),np.full(21,.8)][None,:,None],(h,41,3)).copy()
 out=ref.stage3_unsharp_mask(x,P['unsharp']);assert out.min()>=.2-1e-7 and out.max()<=.8+1e-7
 gpu=render(x,cc=0,flare=0)[:,:,:3];cpu=ref.stage2_gradient(out,P['gradient']);assert np.max(abs(cpu-gpu))<1/255
 steps[str(h)]={'min':float(out.min()),'max':float(out.max()),'shader_max_error_255':float(np.max(abs(cpu-gpu))*255)}
summary['tests']['anti_halo_steps']=steps
# Every switch combination plus dry mix; fully premultiplied alpha must survive.
rng=np.random.default_rng(9);x=rng.uniform(.01,.99,(25,31,3))
maxswitch=0
for cc,q,f in itertools.product([0,1],repeat=3):
 gpu=render(x,cc=cc,quality=q,flare=f)[:,:,:3]
 cpu=ref.apply_look(x,P,enable_cc=bool(cc),enable_grad=bool(q),enable_usm=bool(q),enable_flare=bool(f))
 maxswitch=max(maxswitch,float(np.max(abs(gpu-cpu))))
assert maxswitch<1/255
rgba=np.concatenate([x*.35,np.full((25,31,1),.35)],axis=-1);out=render(rgba);assert np.max(abs(out[:,:,3]-.35))<1e-6 and np.max(out[:,:,:3])<=.350001
assert np.max(abs(render(x,intensity=0)[:,:,:3]-x))<1e-5
summary['tests']['switches_and_alpha']={'all_8_combinations':True,'max_error_255':maxswitch*255,'premultiplied_alpha_preserved':True,'zero_intensity_identity':True}
# Machine-checkable vectors used by the spec.
colours=np.array([[k/255]*3 for k in range(0,256,16)]+[[1,1,1],[1,0,0],[0,1,0],[0,0,1],[1,1,0],[0,1,1],[1,0,1],[.93,.899,.848],[.175,.366,.665],[.087,.012,.013]],float)
vectors={'version':'1.1.1','colour':[{'input':c.tolist(),'expected':y.tolist()} for c,y in zip(colours,ref.stage1_colour_correction(colours,P['colour_correction']))],'gradient':[],'flare':[],'unsharp_step':{}}
for y in [0,.2,.4,.6,.8,1]:
 t=ref.smoothstep_np(P['gradient']['y0_norm'],P['gradient']['y1_norm'],np.array(y));vectors['gradient'].append({'y_top':y,'multiplier':(1-t*np.array(P['gradient']['strength_rgb'])).tolist()})
fp=P['flare']['canonical_default_params']
for x,y in [(0.5,.05),(.1,.1),(.9,.1),(.5,.5),(.1,.9),(.9,.9)]:
 w=np.exp(-.5*(((x-.5)*(1280/720)/.45)**2+((y-.05)/.35)**2));fv=.12*w*np.array(fp['colour_rgb']);vectors['flare'].append({'xy_top':[x,y],'input':[.5]*3,'contribution':fv.tolist(),'expected':(.5+.5*fv).tolist()})
step=np.broadcast_to(np.r_[np.full(10,.2),np.full(11,.8)][None,:,None],(720,21,3)).copy();vectors['unsharp_step']={'height':720,'input':step[360,:,0].tolist(),'expected':ref.stage3_unsharp_mask(step,P['unsharp'])[360,:,0].tolist()}
(D/'test_vectors.json').write_text(json.dumps(vectors,indent=2)+'\n')
(D/'validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print('All shader, gamut, anti-halo, switch and alpha assertions passed.')
