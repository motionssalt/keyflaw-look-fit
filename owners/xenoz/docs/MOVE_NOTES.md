# Move Notes: STRAY_REPO to REAL_REPO

## Migration Details
- Source (STRAY_REPO): motionssalt/keyflaw-look-fit-xenoz
- Destination (REAL_REPO): motionssalt/keyflaw-look-fit
- Owner directory: owners/xenoz/
- Owner slug: xenoz
- Timestamp: 2026-11-02

## What Was Moved
1. BUILD_STATE.json -> owners/xenoz/BUILD_STATE.json (updated repo to motionssalt/keyflaw-look-fit and project to keyflaw-look-fit/xenoz).
2. docs/BUILD_PROMPT.md -> owners/xenoz/docs/BUILD_PROMPT.md and prompts/LOOK_FIT_BRIEF.md.
3. docs/manifest.md -> owners/xenoz/docs/manifest.md.
4. README.md -> owners/xenoz/README.md.
5. inputs/ (.gitkeep) -> owners/xenoz/inputs/.gitkeep.
6. masks/ (.gitkeep) -> owners/xenoz/masks/.gitkeep.
7. analysis/src/*.py -> owners/xenoz/analysis/src/ (11 analytical scripts, paths re-anchored to OWNER_DIR).
8. spec/ (LOOK_SPEC.md, look_params.json, look_apply.py, look.cube) -> owners/xenoz/spec/.

## Clashes & Collisions
- No existing files in REAL_REPO collided with owners/xenoz/.
- Other owners (owners/floby/) were left untouched.
