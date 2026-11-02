"""Keyflaw 1.4.8 suite builder and SKILL.md Section 8 validator/packer."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from lookfit.export.glsl_exporter import validate_glsl_es100

PARAM_TYPES = {"SCALAR", "BOOL", "CHOICE", "COLOR"}
CATEGORIES = {
    "Distorsi", "Stilisasi", "Blur", "Warna", "Gerak", "Simulasi", "Generator",
    "Transisi", "Keying", "Perspective", "Custom",
}
BUILTIN = {"uTexture", "uTime", "uTexelSize"}
NEW_FEATURES = ("passes", "expandBounds", "usesNativeMotionBlur")


def _ver(s: Any) -> Tuple[int, ...]:
    try:
        return tuple(int(x) for x in str(s).split("."))
    except ValueError:
        return (0,)


def _uname(k: str) -> str:
    return "u" + k[0].upper() + k[1:]


def validate_and_pack_suite(
    suite_folder: str | Path,
    out_kfpack: str | Path,
) -> Dict[str, Any]:
    """Run exact SKILL.md Section 8 validator + glslangValidator #version 100 check, then write .kfpack."""
    root = Path(suite_folder).resolve()
    out = Path(out_kfpack).resolve()
    errors: List[str] = []
    warns: List[str] = []

    def E(msg: str) -> None:
        errors.append(msg)

    def W(msg: str) -> None:
        warns.append(msg)

    def check_shader(fid: str, fname: str, src: str) -> Dict[str, str]:
        tag = f"{fid}/{fname}"
        if "GL_FRAGMENT_PRECISION_HIGH" not in src or "precision mediump float" not in src:
            E(f"{tag}: missing the 5-line precision header")
        if "#version" in src:
            E(f"{tag}: remove #version (app uses GLSL ES 1.00 style)")
        if re.search(r"\btexture\s*\(", src):
            E(f"{tag}: use texture2D(), not texture()")
        if "gl_FragColor" not in src:
            E(f"{tag}: never writes gl_FragColor")
        if "texture2D" not in src:
            W(f"{tag}: no texture2D call")
        if not re.search(r"uniform\s+sampler2D\s+uTexture\s*;", src):
            E(f"{tag}: missing 'uniform sampler2D uTexture;'")
        if not re.search(r"varying\s+vec2\s+vTex\s*;", src):
            E(f"{tag}: missing 'varying vec2 vTex;'")
        consts = set(re.findall(r"const\s+int\s+(\w+)\s*=\s*\d+\s*;", src))
        for m in re.finditer(r"\bfor\s*\(([^;]*);([^;]*);", src):
            cond = m.group(2).strip()
            ok = re.search(r"[<>]=?\s*\d+\s*$", cond) or any(
                re.search(r"[<>]=?\s*" + c + r"\s*$", cond) for c in consts
            )
            if not ok:
                E(f"{tag}: for-loop bound must be a literal or 'const int': for(...;{cond};...)")
        if re.search(r"1080\.0|1920\.0", src):
            W(f"{tag}: hard-coded 1080/1920 resolution; use uTexelSize instead")
        decl_all = set(re.findall(r"uniform\s+(?:float|vec2|vec3)\s+(u\w+)\s*;", src))
        if "uTexelSize" in src and "uTexelSize" not in decl_all:
            E(f"{tag}: uses uTexelSize without declaring 'uniform vec2 uTexelSize;'")
        if "uTime" in src and "uTime" not in decl_all:
            E(f"{tag}: uses uTime without declaring 'uniform float uTime;'")
        code = re.sub(r"//[^\n]*|/\*.*?\*/", "", src, flags=re.S)
        if code.count("{") != code.count("}") or code.count("(") != code.count(")"):
            E(f"{tag}: unbalanced braces/parentheses")
        ok_glsl, glsl_msg = validate_glsl_es100(src)
        if not ok_glsl:
            E(f"{tag}: glslangValidator (#version 100) failed: {glsl_msg}")
        return {n: t for t, n in re.findall(r"uniform\s+(float|vec2|vec3)\s+(u\w+)\s*;", src)}

    def check_effect(folder: Path, suite_min: Any) -> List[str]:
        fid = folder.name
        try:
            meta = json.loads((folder / "effect.json").read_text(encoding="utf-8"))
        except Exception as ex:
            E(f"{fid}: effect.json missing/invalid JSON ({ex})")
            return ["shader.glsl"]
        for k in ("id", "name", "category", "parameters"):
            if k not in meta:
                E(f"{fid}: effect.json missing '{k}'")
        if meta.get("id") != fid:
            E(f"{fid}: effect.json id '{meta.get('id')}' must equal folder name")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", fid):
            E(f"{fid}: id must be letters/digits/underscore, starting with a letter")
        if meta.get("category") not in CATEGORIES:
            W(f"{fid}: custom category '{meta.get('category')}' (matches Amethyst custom category pattern)")
        for nf in NEW_FEATURES:
            if nf in meta:
                E(f"{fid}: 1.4.9 field '{nf}' forbidden when targeting Keyflaw 1.4.8")

        files = ["shader.glsl"]
        keys: List[str] = []
        ptypes: Dict[str, str] = {}
        for p in meta.get("parameters", []):
            k = p.get("key", "")
            keys.append(k)
            ptype = p.get("type", "SCALAR")
            ptypes[k] = ptype
            if ptype == "COLOR":
                E(f"{fid}: COLOR param '{k}' forbidden on Keyflaw 1.4.8")
            for f in ("key", "label", "default", "min", "max", "step"):
                if f not in p:
                    E(f"{fid}: param '{k}' missing '{f}'")
            if not re.fullmatch(r"[a-z][A-Za-z0-9]*", k):
                E(f"{fid}: param key '{k}' must be camelCase starting lowercase")
            if ptype not in PARAM_TYPES:
                E(f"{fid}: unseen param type '{ptype}'")
            if len(str(p.get("label", ""))) > 40:
                E(f"{fid}: label of '{k}' exceeds 40 chars")
            if ptype == "BOOL":
                if p.get("min") != 0.0 or p.get("max") != 1.0 or p.get("step") != 1.0 or p.get("default") not in (0.0, 1.0):
                    E(f"{fid}: BOOL param '{k}' must have min=0.0, max=1.0, step=1.0, default in {{0.0, 1.0}}")

        declared_union: Dict[str, str] = {}
        for fn in files:
            path = folder / fn
            if not path.exists():
                E(f"{fid}: {fn} missing")
                continue
            src_txt = path.read_text(encoding="utf-8")
            decl = check_shader(fid, fn, src_txt)
            wanted = {_uname(k): "float" for k in keys if k}
            for u, t in sorted(decl.items()):
                if u in BUILTIN:
                    continue
                if u not in wanted:
                    E(f"{fid}/{fn}: shader declares {u} but no matching parameter key")
                elif wanted[u] != t:
                    E(f"{fid}/{fn}: {u} must be 'uniform {wanted[u]}', found {t}")
            declared_union.update(decl)
            # Also verify every parameter uniform is actually used in body
            for k in keys:
                un = _uname(k)
                if len(re.findall(r"\b" + re.escape(un) + r"\b", src_txt)) < 2:
                    E(f"{fid}/{fn}: uniform {un} declared but never used in shader body")
        for k in keys:
            if k and _uname(k) not in declared_union:
                E(f"{fid}: parameter '{k}' needs 'uniform float {_uname(k)};' in shader.glsl")
        return files

    suite_path = root / "suite.json"
    if not suite_path.exists():
        raise FileNotFoundError(f"suite.json missing at {suite_path}")
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    for k in ("id", "name", "author", "version", "description", "category", "minAppVersion", "effects"):
        if k not in suite:
            E(f"suite.json missing '{k}'")

    eff_dirs = sorted(p for p in (root / "effects").glob("*") if p.is_dir())
    if not eff_dirs:
        E("no effects/<id>/ folders found")
    listed = list(suite.get("effects", []))
    found = [d.name for d in eff_dirs]
    for n in sorted(set(listed) - set(found)):
        E(f"suite.json effects lists '{n}' but effects/{n}/ does not exist")
    for n in sorted(set(found) - set(listed)):
        E(f"effects/{n}/ exists but is missing from suite.json 'effects' list")

    packed: Dict[str, List[str]] = {}
    for d in eff_dirs:
        meta_eff = json.loads((d / "effect.json").read_text(encoding="utf-8"))
        if meta_eff.get("category") != suite.get("category"):
            E(f"{d.name}: effect category '{meta_eff.get('category')}' != suite category '{suite.get('category')}'")
        packed[d.name] = check_effect(d, suite.get("minAppVersion"))

    if errors:
        raise ValueError("Keyflaw pack validation failed:\n" + "\n".join(errors))

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(suite_path, "suite.json")
        order = suite.get("effects") or found
        for d in sorted(eff_dirs, key=lambda x: order.index(x.name) if x.name in order else 999):
            for name in ["effect.json"] + packed[d.name]:
                if name.endswith((".png", ".jpg", ".jpeg")):
                    raise ValueError(f"Refusing to pack image asset into .kfpack: {name}")
                z.write(d / name, f"effects/{d.name}/{name}")

    with zipfile.ZipFile(out, "r") as z:
        assert z.testzip() is None
        names = z.namelist()
        assert "suite.json" in names

    return {
        "kfpack_path": str(out),
        "zip_entries": names,
        "errors": errors,
        "warnings": warns,
    }


def build_motionsalt_kfpack(
    repo_root: str | Path,
    owner_shaders: Dict[str, Tuple[str, Dict[str, Any]]],
    version: str = "2.0.0",
) -> Dict[str, Any]:
    """Write `pack/` suite tree from owner_shaders and pack `releases/MotionSalt_CC.kfpack`."""
    root = Path(repo_root)
    pack_dir = root / "pack"
    effects_root = pack_dir / "effects"
    if pack_dir.exists():
        import shutil
        shutil.rmtree(pack_dir)
    effects_root.mkdir(parents=True, exist_ok=True)

    effect_ids: List[str] = []
    for owner_slug in sorted(owner_shaders.keys()):
        shader_src, meta = owner_shaders[owner_slug]
        eff_id = f"MS_{owner_slug}_cc"
        effect_ids.append(eff_id)
        eff_dir = effects_root / eff_id
        eff_dir.mkdir(parents=True, exist_ok=True)

        params = [
            {
                "key": "colourCorrection",
                "label": "Colour Correction",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "step": 1.0,
                "type": "BOOL",
            },
            {
                "key": "quality",
                "label": "Quality",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "step": 1.0,
                "type": "BOOL",
            },
        ]
        if meta.get("has_haze_flare_switch", False):
            params.append(
                {
                    "key": "hazeFlare",
                    "label": "Haze Flare",
                    "default": 1.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 1.0,
                    "type": "BOOL",
                }
            )

        title_owner = owner_slug.capitalize()
        eff_json = {
            "id": eff_id,
            "name": f"{title_owner} CC",
            "category": "MotionSalt CC",
            "parameters": params,
        }
        (eff_dir / "effect.json").write_text(json.dumps(eff_json, indent=2) + "\n", encoding="utf-8")
        (eff_dir / "shader.glsl").write_text(shader_src, encoding="utf-8")

    suite_json = {
        "id": "com.motionsalt.cc",
        "name": "Motion Salt CC",
        "category": "MotionSalt CC",
        "author": "MOTIONSALT",
        "version": version,
        "minAppVersion": "1.2.4",
        "description": "Layer-by-layer fitted colour correction and quality effects for Keyflaw 1.4.8.",
        "effects": effect_ids,
    }
    (pack_dir / "suite.json").write_text(json.dumps(suite_json, indent=2) + "\n", encoding="utf-8")

    out_kfpack = root / "releases" / "MotionSalt_CC.kfpack"
    return validate_and_pack_suite(pack_dir, out_kfpack)
