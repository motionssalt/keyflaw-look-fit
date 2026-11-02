#!/usr/bin/env python3
"""Validate a Keyflaw suite folder and zip it into a .kfpack (Keyflaw 1.4.9+ aware).

Usage:  python3 kfpack_build.py <suite_folder> [output.kfpack]

<suite_folder> must contain suite.json and effects/<id>/effect.json plus either
shader.glsl (single pass) or the files listed in effect.json "passes" (multi-pass).
Exit code 1 if any ERROR is found (no file is written). WARN lines never block.
"""
import json, re, sys, zipfile
from pathlib import Path

PARAM_TYPES = {"SCALAR", "BOOL", "CHOICE", "COLOR"}
CATEGORIES = {"Distorsi", "Stilisasi", "Blur", "Warna", "Gerak", "Simulasi", "Generator",
              "Transisi", "Keying", "Perspective", "Custom"}
BUILTIN = {"uTexture", "uTime", "uTexelSize"}
NEW_FEATURES = ("passes", "expandBounds", "usesNativeMotionBlur")
errors, warns = [], []
E = lambda m: errors.append(m)
W = lambda m: warns.append(m)


def ver(s):
    try:
        return tuple(int(x) for x in str(s).split("."))
    except ValueError:
        return (0,)


def uname(k):
    return "u" + k[0].upper() + k[1:]


def check_shader(fid, fname, src):
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
        W(f"{tag}: no texture2D call (fine only for Generator effects)")
    if not re.search(r"uniform\s+sampler2D\s+uTexture\s*;", src):
        E(f"{tag}: missing 'uniform sampler2D uTexture;'")
    if not re.search(r"varying\s+vec2\s+vTex\s*;", src):
        E(f"{tag}: missing 'varying vec2 vTex;'")
    consts = set(re.findall(r"const\s+int\s+(\w+)\s*=\s*\d+\s*;", src))
    for m in re.finditer(r"\bfor\s*\(([^;]*);([^;]*);", src):
        cond = m.group(2).strip()
        ok = re.search(r"[<>]=?\s*\d+\s*$", cond) or any(re.search(r"[<>]=?\s*" + c + r"\s*$", cond) for c in consts)
        if not ok:
            E(f"{tag}: for-loop bound must be a literal or a 'const int' constant: for(...;{cond};...)")
    if re.search(r"1080\.0|1920\.0", src):
        W(f"{tag}: hard-coded 1080/1920 resolution; use uTexelSize instead")
    decl_all = set(re.findall(r"uniform\s+(?:float|vec2|vec3)\s+(u\w+)\s*;", src))
    if "uTexelSize" in src and "uTexelSize" not in decl_all:
        E(f"{tag}: uses uTexelSize without declaring 'uniform vec2 uTexelSize;'")
    code = re.sub(r"//[^\n]*|/\*.*?\*/", "", src, flags=re.S)
    if code.count("{") != code.count("}") or code.count("(") != code.count(")"):
        E(f"{tag}: unbalanced braces/parentheses")
    if re.search(r"/\s*(?:u[A-Z]\w*|dot\([^)]*\)|length\([^)]*\))(?!\s*[\w(])", src) and "max(" not in src:
        W(f"{tag}: division by a uniform/length with no max(...,0.0001) anywhere")
    return {n: t for t, n in re.findall(r"uniform\s+(float|vec2|vec3)\s+(u\w+)\s*;", src)}


def check_effect(folder: Path, suite_min):
    fid = folder.name
    try:
        meta = json.loads((folder / "effect.json").read_text(encoding="utf-8"))
    except Exception as ex:
        return E(f"{fid}: effect.json missing/invalid JSON ({ex}) (comments are NOT allowed in JSON)")

    for k in ("id", "name", "category", "parameters"):
        if k not in meta:
            E(f"{fid}: effect.json missing '{k}'")
    if meta.get("id") != fid:
        E(f"{fid}: effect.json id '{meta.get('id')}' must equal folder name")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", fid):
        E(f"{fid}: id must be letters/digits/underscore, starting with a letter")
    if meta.get("category") not in CATEGORIES:
        W(f"{fid}: category '{meta.get('category')}' is not one of {sorted(CATEGORIES)} "
          "(a custom category worked in the Amethyst pack, but is untested elsewhere)")

    # ---- 1.4.9 fields ----
    files = ["shader.glsl"]
    if "passes" in meta:
        ps = meta["passes"]
        if not (isinstance(ps, list) and len(ps) >= 2 and all(isinstance(x, str) and x.endswith(".glsl") for x in ps)):
            E(f"{fid}: 'passes' must be a list of 2+ .glsl file names")
        else:
            files = ps
            if len(set(ps)) != len(ps):
                E(f"{fid}: 'passes' lists the same file twice")
            if (folder / "shader.glsl").exists():
                W(f"{fid}: shader.glsl exists but 'passes' is set; shader.glsl is ignored (and not packed)")
    if "expandBounds" in meta:
        eb = meta["expandBounds"]
        if isinstance(eb, bool) or not isinstance(eb, (int, float)) or eb < 0:
            E(f"{fid}: expandBounds must be a number >= 0 (0.3 = 30% padding)")
        elif eb > 1:
            W(f"{fid}: expandBounds {eb} is over 1.0 (100% padding); expensive and rarely needed")
    if "usesNativeMotionBlur" in meta and not isinstance(meta["usesNativeMotionBlur"], bool):
        E(f"{fid}: usesNativeMotionBlur must be true or false")
    if any(f in meta for f in NEW_FEATURES) and suite_min is not None and ver(suite_min) < (1, 4, 9):
        W(f"{fid}: uses 1.4.9 fields but suite minAppVersion is {suite_min}; set it to '1.4.9'")

    # ---- parameters ----
    keys, ptypes = [], {}
    for p in meta.get("parameters", []):
        k = p.get("key", "")
        keys.append(k)
        ptype = p.get("type", "SCALAR")
        ptypes[k] = ptype
        need = ("key", "label", "default") if ptype == "COLOR" else ("key", "label", "default", "min", "max", "step")
        for f in need:
            if f not in p:
                E(f"{fid}: param '{k}' missing '{f}'")
        if not re.fullmatch(r"[a-z][A-Za-z0-9]*", k):
            E(f"{fid}: param key '{k}' must be camelCase starting lowercase")
        if ptype not in PARAM_TYPES:
            W(f"{fid}: param '{k}' has unseen type '{ptype}' (seen types: {sorted(PARAM_TYPES)})")
        if len(str(p.get("label", ""))) > 40:
            W(f"{fid}: label of '{k}' is over 40 chars; the app may cut it off")
        if "group" in p and not isinstance(p["group"], str):
            E(f"{fid}: param '{k}' group must be a string")
        if ptype == "COLOR":
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(p.get("default", ""))):
                E(f"{fid}: COLOR '{k}' default must be a '#RRGGBB' string")
            continue
        if ptype == "CHOICE":
            opts = p.get("options")
            if not (isinstance(opts, list) and len(opts) >= 2 and all(isinstance(o, str) for o in opts)):
                E(f"{fid}: CHOICE param '{k}' needs an 'options' list of 2+ strings")
            elif not (p.get("min") == 0 and p.get("max") == len(opts) - 1 and p.get("step") == 1
                      and p.get("default") == int(p.get("default", 0))):
                E(f"{fid}: CHOICE '{k}' needs min 0, max {len(opts) - 1}, step 1, whole-number default")
        elif "options" in p:
            E(f"{fid}: only CHOICE params take 'options'")
        if ptype == "BOOL":
            if not (p.get("min") == 0 and p.get("max") == 1 and p.get("default") in (0, 1)):
                E(f"{fid}: BOOL '{k}' needs min 0, max 1, default 0 or 1")
            elif p.get("step") != 1:
                W(f"{fid}: BOOL '{k}' step should be 1 (one reference pack used 0.01)")
        try:
            if not (p["min"] < p["max"]):
                E(f"{fid}: param '{k}' min must be < max")
            if not (p["min"] <= p["default"] <= p["max"]):
                E(f"{fid}: param '{k}' default outside min..max")
            if p["step"] <= 0:
                E(f"{fid}: param '{k}' step must be > 0")
            if any(isinstance(p[f], bool) or not isinstance(p[f], (int, float))
                   for f in ("default", "min", "max", "step")):
                E(f"{fid}: param '{k}' default/min/max/step must be plain numbers")
        except KeyError:
            pass
    if len(keys) != len(set(keys)):
        E(f"{fid}: duplicate parameter keys")

    if meta.get("usesNativeMotionBlur") is True and not {"motionBlur", "trailLength"} <= set(keys):
        W(f"{fid}: usesNativeMotionBlur is true; the official pattern also has 'motionBlur' (BOOL) and 'trailLength' sliders")

    # ---- shaders ----
    declared_union = {}
    for fn in files:
        path = folder / fn
        if not path.exists():
            E(f"{fid}: {fn} missing")
            continue
        decl = check_shader(fid, fn, path.read_text(encoding="utf-8"))
        wanted = {uname(k): ("vec3" if ptypes.get(k) == "COLOR" else "float") for k in keys if k}
        for u, t in sorted(decl.items()):
            if u in BUILTIN:
                continue
            if u not in wanted:
                E(f"{fid}/{fn}: shader declares {u} but no matching parameter key")
            elif wanted[u] != t:
                E(f"{fid}/{fn}: {u} must be 'uniform {wanted[u]}', found {t}")
        declared_union.update(decl)
    if all((folder / fn).exists() for fn in files):
        for k in keys:
            if k and uname(k) not in declared_union:
                E(f"{fid}: parameter '{k}' needs 'uniform {'vec3' if ptypes.get(k) == 'COLOR' else 'float'} {uname(k)};' "
                  f"in {'at least one pass' if len(files) > 1 else 'the shader'}")
    return files


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = Path(sys.argv[1]).resolve()
    suite_path = root / "suite.json"
    if not suite_path.exists():
        sys.exit(f"ERROR: {suite_path} missing (suite.json must be at the ROOT of the pack)")
    try:
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
    except Exception as ex:
        sys.exit(f"ERROR: suite.json invalid JSON: {ex}")
    for k in ("id", "name", "author", "version", "description"):
        if k not in suite:
            E(f"suite.json missing '{k}'")

    eff_dirs = sorted(p for p in (root / "effects").glob("*") if p.is_dir())
    if not eff_dirs:
        E("no effects/<id>/ folders found")
    if "effects" in suite:
        listed, found = list(suite["effects"]), [d.name for d in eff_dirs]
        for n in sorted(set(listed) - set(found)):
            E(f"suite.json effects lists '{n}' but effects/{n}/ does not exist")
        for n in sorted(set(found) - set(listed)):
            E(f"effects/{n}/ exists but is missing from suite.json 'effects' list")
    typed = False
    for d in eff_dirs:
        if (d / "effect.json").exists():
            try:
                typed |= any("type" in p for p in json.loads((d / "effect.json").read_text(encoding="utf-8")).get("parameters", []))
            except Exception:
                pass
    if typed and "minAppVersion" not in suite:
        W("typed params (BOOL/CHOICE/COLOR/group) are used; set suite.json minAppVersion (1.2.4 for typed, 1.4.9 for passes/expandBounds/usesNativeMotionBlur)")

    packed = {}
    for d in eff_dirs:
        packed[d.name] = check_effect(d, suite.get("minAppVersion")) or ["shader.glsl"]

    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    if errors:
        sys.exit(f"\n{len(errors)} error(s). Pack NOT written. Fix and re-run.")

    out = Path(sys.argv[2]) if len(sys.argv) > 2 else root.parent / f"{suite['id']}.kfpack"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(suite_path, "suite.json")
        order = suite.get("effects") or [d.name for d in eff_dirs]
        for d in sorted(eff_dirs, key=lambda x: order.index(x.name) if x.name in order else 999):
            for name in ["effect.json"] + packed[d.name]:
                z.write(d / name, f"effects/{d.name}/{name}")  # forward slashes always
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        print("\nOK. Wrote", out)
        for n in z.namelist():
            print("  ", n)


if __name__ == "__main__":
    main()
