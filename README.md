# Keyflaw look-fit repository

This private repository contains MOTIONSALT’s recovered Keyflaw colour-correction work, organized by owner. Floby’s completed source-of-truth files and installable deliverables are published in the [Floby’s CC v1.0 GitHub Release](https://github.com/motionssalt/keyflaw-look-fit/releases/tag/floby-cc-v1.0).

| Owner | Status | Release | Repository source |
|---|---|---|---|
| [Floby](owners/floby/README.md) | Complete analysis and look deliverables | [Floby’s CC v1.0](https://github.com/motionssalt/keyflaw-look-fit/releases/tag/floby-cc-v1.0) | [owners/floby/](owners/floby/) |

## Layout

`docs/` contains the build prompt, manifest, and tidy notes. `owners/<owner>/inputs/` contains the matched frame pairs, while `masks/` contains masks and overlay previews. `owners/<owner>/analysis/` contains fit scripts, aligned intermediates, scratch work, and diagnostic outputs. `owners/<owner>/reports/` contains the owner’s quantitative report. `owners/<owner>/spec/` contains the source-of-truth look specification, parameters, reference implementation, and LUT. `BUILD_STATE.json` records resumable work and decisions.

There are currently no reusable cross-owner tools or prompt files in this repository, and no Keyflaw `.kfpack` or pack source was found in the Floby work.
