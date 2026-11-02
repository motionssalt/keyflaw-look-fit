# Maintenance override — 2026-11-02

Victor's newer instruction overrides the older unversioned release filename below. Every new `.kfpack` must use `releases/MotionSalt_CC_v<VERSION>.kfpack` and a separate versioned GitHub Release/tag. Never overwrite/delete an existing release, asset or pack. `tools/release_pack.py` enforces unused versions. The old unversioned file is frozen. Current safety implementation and limitations are in `spec/LOOK_SPEC.md` and `reports/BURN_SAFETY_v1.1.1.md`; do not regenerate the obsolete unconstrained grade from historical build scripts. No credentials belong in prompts, state or commits.

---

# LOOK-FIT: Recover an editor's colour grade and "quality" look from frame pairs

An analysis job for MOTIONSALT. Read this whole file first. It is self-contained: assume nothing from any earlier conversation. The same brief is reused for different CC owners; everything specific to this run is in STEP 0.

## STEP 0: FILL-IN FIELDS
```
GITHUB_PAT = <REDACTED_IN_REPO>
CC_OWNER = Xenoz
EXTRA_EFFECTS = none
```
- CC_OWNER is the person whose CC is being copied ("Xenoz").
- EXTRA_EFFECTS is optional: none.
