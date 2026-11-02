# Keyflaw look-fit repository

This private repository contains MOTIONSALT’s recovered Keyflaw colour-correction work, organized by owner.

| Owner | Status | Release | Repository source |
|---|---|---|---|
| [Floby](owners/floby/README.md) | Complete analysis and look deliverables | [Floby’s CC v1.0](https://github.com/motionssalt/keyflaw-look-fit/releases/tag/floby-cc-v1.0) | [owners/floby/](owners/floby/) |
| [Xenoz](owners/xenoz/README.md) | Complete analysis and look deliverables | [Xenoz’s CC v1.0](https://github.com/motionssalt/keyflaw-look-fit/releases/tag/xenoz-cc-v1.0) | [owners/xenoz/](owners/xenoz/) |

## Layout
`docs/` contains the build prompt, manifest, and tidy notes. `owners/<owner>/inputs/` contains the matched frame pairs, while `masks/` contains masks and overlay previews. `owners/<owner>/analysis/` contains fit scripts, aligned intermediates, scratch work, and diagnostic outputs. `owners/<owner>/reports/` contains the owner’s quantitative report. `owners/<owner>/spec/` contains the source-of-truth look specification, parameters, reference implementation, and LUT. `BUILD_STATE.json` records resumable work and decisions.

The suite pack source is organized in `pack/` (`pack/suite.json` and `pack/effects/`), with installable packs in `releases/MotionSalt_CC.kfpack`. The shared pack includes both Floby’s CC (`MS_floby_cc`) and Xenoz’s CC (`MS_xenoz_cc`).
