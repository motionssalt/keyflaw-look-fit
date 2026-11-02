#!/usr/bin/env python3
"""Validate/build one immutable versioned suite pack; never overwrite any release.
Usage: python tools/release_pack.py
Version is read from pack/suite.json. Bump it before each new build.
Does not publish to GitHub or alter releases/MotionSalt_CC.kfpack (legacy).
"""
from pathlib import Path
import json,re,subprocess,sys,hashlib
R=Path(__file__).resolve().parents[1]
suite=json.loads((R/'pack/suite.json').read_text())
v=suite['version']
if not re.fullmatch(r'\d+\.\d+\.\d+',v):sys.exit('ERROR: semantic version X.Y.Z required')
out=R/f'releases/MotionSalt_CC_v{v}.kfpack'
sha=out.with_suffix(out.suffix+'.sha256')
if out.exists() or sha.exists():sys.exit(f'ERROR: {out.name} already exists. Never overwrite a release; bump pack/suite.json version.')
out.parent.mkdir(exist_ok=True)
subprocess.run([sys.executable,str(R/'owners/xenoz/analysis/src/kfpack_build.py'),str(R/'pack'),str(out)],check=True)
digest=hashlib.sha256(out.read_bytes()).hexdigest()
with sha.open('x') as f:f.write(f'{digest}  {out.name}\n')
print('Immutable release built:',out.name)
