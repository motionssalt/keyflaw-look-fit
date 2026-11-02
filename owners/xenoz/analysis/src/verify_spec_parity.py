#!/usr/bin/env python3
"""Verify current Xenoz spec tables, shader, JSON and LUT (v1.1.1).
The historical verifier referred to obsolete function names and fit constants.
Run validate_burn_safety.py separately for independent shader execution.
"""
from pathlib import Path
import sys,json,re,ast
import numpy as np
O=Path(__file__).resolve().parents[2];R=O.parents[1];S=O/'spec'
sys.path.insert(0,str(S));import look_apply as ref
p=json.loads((S/'look_params.json').read_text());spec=(S/'LOOK_SPEC.md').read_text()
shader=re.search(r'```glsl\n(.*?)```',spec,re.S).group(1)
assert shader==(R/'pack/effects/MS_xenoz_cc/shader.glsl').read_text()
for path in [O/'pack/MS_xenoz_cc/shader.glsl',O/'pack/effects/MS_xenoz_cc/shader.glsl']:assert path.read_text()==shader
for name in ['LOOK_SPEC.md','look_apply.py','look_params.json','look.cube']:assert (S/name).read_bytes()==(O/'reports'/name).read_bytes()
# Parse the actual specification tables, not a copy generated at verification time.
sec=spec.split('### 6.1 Colour stage')[1].split('### 6.2')[0]
rows=re.findall(r'\| `([^`]+)` \| `([^`]+)` \|',sec);assert len(rows)>=24
for a,b in rows:
 x=np.array(ast.literal_eval(a));y=np.array(ast.literal_eval(b));actual=ref.stage1_colour_correction(x[None,:],p['colour_correction'])[0]
 assert np.max(abs(actual-y))<2e-8,(a,actual,y)
sec=spec.split('### 6.2 Vertical gradient')[1].split('### 6.3')[0]
rows=re.findall(r'\| `([^`]+)` \| `([^`]+)` \|',sec);assert len(rows)>=6
for a,b in rows:
 t=ref.smoothstep_np(p['gradient']['y0_norm'],p['gradient']['y1_norm'],float(a));actual=1-t*np.array(p['gradient']['strength_rgb'])
 assert np.max(abs(actual-np.array(ast.literal_eval(b))))<2e-9
sec=spec.split('### 6.3 Flare')[1].split('### 6.4')[0]
rows=re.findall(r'\| `([^`]+)` \| `([^`]+)` \| `([^`]+)` \|',sec);assert len(rows)>=6
fp=p['flare']['canonical_default_params']
for a,b,c in rows:
 x,y=ast.literal_eval(a);w=np.exp(-.5*(((x-fp['cx'])*(1280/720)/fp['rx_frac_h'])**2+((y-fp['cy'])/fp['ry_frac_h'])**2))
 f=fp['intensity']*w*np.array(fp['colour_rgb']);actual=.5+.5*f
 assert np.max(abs(f-np.array(ast.literal_eval(b))))<2e-9
 assert np.max(abs(actual-np.array(ast.literal_eval(c))))<2e-9
sec=spec.split('### 6.4 Isolated anti-halo')[1].split('## 7.')[0]
rows=re.findall(r'\| `(\d+)` \| `([0-9.]+)` \| `([0-9.]+)` \|',sec);assert len(rows)==21
step=np.array([float(b) for a,b,c in rows]);image=np.broadcast_to(step[None,:,None],(720,21,3)).copy()
y=ref.stage3_unsharp_mask(image,p['unsharp'])[360,:,0]
assert np.max(abs(y-np.array([float(c) for a,b,c in rows])))<2e-9
# Verify every numeric JSON parameter is represented verbatim in the spec table.
def flatten(obj,prefix=''):
 for key,value in obj.items():
  name=prefix+'.'+key if prefix else key
  if isinstance(value,dict):yield from flatten(value,name)
  elif isinstance(value,(int,float,list)):yield name,value
for name,value in flatten({k:p[k] for k in ['colour_correction','gradient','unsharp','flare']}):
 assert '| `'+name+'` | `'+json.dumps(value,separators=(', ', ': '))+'` |' in spec,name
b,g,r=np.meshgrid(*([np.linspace(0,1,33)]*3),indexing='ij');grid=np.stack([r,g,b],-1).reshape(-1,3)
expected=ref.stage1_colour_correction(grid,p['colour_correction']);cube=np.loadtxt(S/'look.cube',skiprows=4)
assert cube.shape==(33**3,3) and np.max(abs(expected-cube))<1e-8
print('PASS: packaged/owner/spec GLSL identical; all numeric parameters, 26 colour, 6 gradient, 6 flare, 21 step samples, reference copies and 33^3 LUT agree.')
