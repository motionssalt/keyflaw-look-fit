"""CLI entry point: `python -m lookfit.run --owner <slug|all>`."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from lookfit.core.io import list_owners, verify_inputs_untouched
from lookfit.export.kfpack import build_motionsalt_kfpack
from lookfit.export.report_builder import export_owner_results
from lookfit.planner import analyze_owner_pairs, detect_and_plan
from lookfit.plugins import create_all_plugins
from lookfit.tuner import tune_owner_stack


def _update_owner_build_state(
    repo_root: Path,
    owner_slug: str,
    look_doc: Dict[str, Any],
    elapsed_sec: float,
    iteration_tag: str,
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    owner_bs_path = repo_root / "owners" / owner_slug / "BUILD_STATE.json"
    if owner_bs_path.exists():
        obs = json.loads(owner_bs_path.read_text(encoding="utf-8"))
    else:
        obs = {"owner": owner_slug}

    agg0 = look_doc["metrics_before"]["aggregate"]
    agg1 = look_doc["metrics_after"]["aggregate"]
    entry = {
        "iteration": iteration_tag,
        "timestamp": now_iso,
        "elapsed_sec": round(elapsed_sec, 2),
        "accepted_layers": look_doc["accepted_order"],
        "ciede2000_median_before": agg0["ciede2000_median"],
        "ciede2000_median_after": agg1["ciede2000_median"],
        "ciede2000_p90_before": agg0["ciede2000_p90"],
        "ciede2000_p90_after": agg1["ciede2000_p90"],
        "mae_mean_255_before": agg0["mae_mean_255"],
        "mae_mean_255_after": agg1["mae_mean_255"],
        "edge_halo_rmse_255_before": agg0["edge_halo_rmse_255"],
        "edge_halo_rmse_255_after": agg1["edge_halo_rmse_255"],
        "ssim_before": agg0["ssim"],
        "ssim_after": agg1["ssim"],
        "joint_loss_after": agg1["joint_loss"],
        "shader_taps": look_doc["shader_validation"]["total_texture_taps"],
        "shader_parity": look_doc["shader_validation"]["numpy_vs_python_parity"],
    }
    obs["status"] = "tuned"
    obs["last_updated"] = now_iso
    obs["accepted_layers"] = look_doc["accepted_order"]
    obs["latest_metrics"] = entry
    obs.setdefault("history", []).append(entry)
    owner_bs_path.write_text(json.dumps(obs, indent=2) + "\n", encoding="utf-8")

    # Also update root BUILD_STATE.json if running single-process (or merge safely)
    root_bs_path = repo_root / "BUILD_STATE.json"
    if root_bs_path.exists():
        rbs = json.loads(root_bs_path.read_text(encoding="utf-8"))
        rbs.setdefault("owner_status", {})[owner_slug] = {
            "status": "tuned",
            "pairs": list(look_doc["metrics_after"]["per_pair"].keys()),
            "accepted_layers": look_doc["accepted_order"],
        }
        rbs.setdefault("results", {}).setdefault(owner_slug, []).append(entry)
        rbs["last_updated"] = now_iso
        root_bs_path.write_text(json.dumps(rbs, indent=2) + "\n", encoding="utf-8")


def run_for_owner(
    repo_root: Path,
    owner_slug: str,
    artifacts_root: Path | None = None,
    iteration_tag: str = "iter1",
    update_root_state: bool = True,
) -> Dict[str, Any]:
    t0 = time.time()
    print(f"[{owner_slug}] P0: Aligning pairs and building masks...", flush=True)
    bundles = analyze_owner_pairs(repo_root, owner_slug)
    plugins = create_all_plugins()

    results_dir = repo_root / "owners" / owner_slug / "results"
    visuals_dir = results_dir / "visuals"
    art_dir = (artifacts_root / owner_slug) if artifacts_root is not None else None

    print(f"[{owner_slug}] P1 & P2: Detecting effects and planning stack...", flush=True)
    plan = detect_and_plan(bundles, plugins, diag_dir=visuals_dir)
    # Copy evidence.json to results_dir root as well for easy access
    if (visuals_dir / "evidence.json").exists():
        (results_dir / "evidence.json").write_text(
            (visuals_dir / "evidence.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (visuals_dir / "evidence.json").unlink()
    print(f"[{owner_slug}] Planned stack: {plan.planned_order}", flush=True)

    print(f"[{owner_slug}] P3 & P4: Layer-by-layer tuning + joint refinement...", flush=True)
    tune_res = tune_owner_stack(bundles, plan, plugins, artifacts_dir=art_dir)
    print(
        f"[{owner_slug}] Accepted stack: {[lr.plugin_name for lr in tune_res.accepted_layers]}",
        flush=True,
    )

    print(f"[{owner_slug}] P5 & P6: Exporting look.json, look.cube, GLSL, visuals, and REPORT.md...", flush=True)
    exported = export_owner_results(owner_slug, bundles, plan, tune_res, plugins, results_dir)
    elapsed = time.time() - t0

    if update_root_state:
        _update_owner_build_state(repo_root, owner_slug, exported["look_doc"], elapsed, iteration_tag)
    else:
        # Matrix worker mode: write owner BUILD_STATE.json only to avoid git merge conflicts on root BUILD_STATE.json
        now_iso = datetime.now(timezone.utc).isoformat()
        owner_bs_path = repo_root / "owners" / owner_slug / "BUILD_STATE.json"
        obs = json.loads(owner_bs_path.read_text(encoding="utf-8")) if owner_bs_path.exists() else {"owner": owner_slug}
        obs["status"] = "tuned"
        obs["last_updated"] = now_iso
        obs["accepted_layers"] = exported["look_doc"]["accepted_order"]
        obs["latest_metrics"] = exported["look_doc"]["metrics_after"]["aggregate"]
        owner_bs_path.write_text(json.dumps(obs, indent=2) + "\n", encoding="utf-8")

    verify_inputs_untouched(repo_root)
    agg0 = exported["look_doc"]["metrics_before"]["aggregate"]
    agg1 = exported["look_doc"]["metrics_after"]["aggregate"]
    print(
        f"[{owner_slug}] DONE in {elapsed:.1f}s | Med DE00: {agg0['ciede2000_median']:.2f} -> {agg1['ciede2000_median']:.2f} | "
        f"MAE: {agg0['mae_mean_255']:.2f} -> {agg1['mae_mean_255']:.2f} | "
        f"Halo RMSE: {agg0['edge_halo_rmse_255']:.2f} -> {agg1['edge_halo_rmse_255']:.2f} | "
        f"Taps: {exported['shader_meta']['total_texture_taps']}",
        flush=True,
    )
    return exported


def main() -> None:
    parser = argparse.ArgumentParser(description="Run plugin-based look-fit pipeline per owner.")
    parser.add_argument("--owner", required=True, help="Owner slug (e.g. floby, gojo, xenoz) or 'all'")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--artifacts-dir", default="artifacts", help="Directory for full intermediate renders")
    parser.add_argument("--iteration-tag", default="run", help="Tag recorded in BUILD_STATE.json")
    parser.add_argument("--no-root-state", action="store_true", help="Only update owners/<owner>/BUILD_STATE.json (for CI matrix)")
    parser.add_argument("--build-pack", action="store_true", help="Also build pack/ and releases/MotionSalt_CC.kfpack")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    verify_inputs_untouched(repo_root)

    all_owners = list_owners(repo_root)
    if args.owner.strip().lower() == "all":
        selected = all_owners
    else:
        selected = [s.strip() for s in args.owner.split(",") if s.strip()]
        for s in selected:
            if s not in all_owners:
                raise ValueError(f"Unknown owner '{s}'. Available owners: {all_owners}")

    art_root = Path(args.artifacts_dir).resolve() if args.artifacts_dir else None
    owner_shaders = {}
    for slug in selected:
        exp = run_for_owner(
            repo_root=repo_root,
            owner_slug=slug,
            artifacts_root=art_root,
            iteration_tag=args.iteration_tag,
            update_root_state=(not args.no_root_state),
        )
        owner_shaders[slug] = (exp["shader_src"], exp["shader_meta"])

    if args.build_pack:
        # Also load any other already-tuned owners from owners/*/results/look.json + shader.glsl so the suite is complete
        for slug in all_owners:
            if slug not in owner_shaders:
                sh_p = repo_root / "owners" / slug / "results" / "shader.glsl"
                lk_p = repo_root / "owners" / slug / "results" / "look.json"
                if sh_p.exists() and lk_p.exists():
                    lk = json.loads(lk_p.read_text(encoding="utf-8"))
                    owner_shaders[slug] = (
                        sh_p.read_text(encoding="utf-8"),
                        {"has_haze_flare_switch": lk["shader_validation"]["has_haze_flare_switch"]},
                    )
        pack_res = build_motionsalt_kfpack(repo_root, owner_shaders, version="2.0.0")
        print(f"[pack] Built and validated {pack_res['kfpack_path']} ({len(pack_res['zip_entries'])} entries).", flush=True)


if __name__ == "__main__":
    main()
