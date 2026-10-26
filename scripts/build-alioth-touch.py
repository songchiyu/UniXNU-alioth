#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
# alioth (K40, SM8250) FocalTech FT5652 touch bring-up: compiles the board probe
# (FocalTouchProbe.cpp), the FTS5652 protocol core (FocalTouchProtocol.c), the
# GENI SPI engine (GeniSpi.c) and the HID digitizer consumer (NativeHidInput.cpp)
# with the kernel's own flags, then packs them into an archive the prelink stage
# can merge (the same pattern the sm8550 port uses for its touch archive).
#
# Run after `unixnu build kernel`, from the UniXNU tree root (ROOT). The device
# repository (this tree's parent) supplies the kit files; the HID consumer comes
# from the ShengHidInput driver feed.
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # UniXNU tree
DEVICE = Path(os.environ.get("UNIXNU_DEVICE", ROOT.parent))   # device repository checkout
KIT = DEVICE / "kits" / "alioth-touch"
if not KIT.exists():
    sys.exit(f"alioth-touch kit not found (expected {KIT})")
OUT = ROOT / "build" / "alioth-touch"
OUT.mkdir(parents=True, exist_ok=True)

def run(cmd, **kw):
    return subprocess.check_call(cmd, **kw)

def require(cond, msg):
    if not cond:
        sys.exit(msg)

def code(data, macho_):
    return hashlib.sha256(data).hexdigest()

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

# HID consumer: NativeHidInput.cpp from the ShengHidInput driver feed.
hid = ROOT / "drivers" / "ShengHidInput"
require((hid / "NativeHidInput.cpp").exists(),
        "ShengHidInput feed missing: add the UniXNU/ShengHidInput driver source to feeds.toml")

# Compile-command templates from the kernel build (both live under build/xnu/ios-obj).
ios = ROOT / "build" / "xnu" / "ios-obj"
expert = ios / "DEVELOPMENT_ARM64_BCM2837" / "iokit" / "DEVELOPMENT" / "IOPlatformExpert.cpo.json"
startup = ios / "DEVELOPMENT_ARM64_BCM2837" / "osfmk" / "DEVELOPMENT" / "startup.o.json"
require(expert.exists(), "IOPlatformExpert.cpo.json missing: run `unixnu build kernel` first")
require(startup.exists(), "startup.o.json missing: run `unixnu build kernel` first")

def cpp_cmd(source, obj, json_path, extra_inc=None):
    """C++ objects: the IOPlatformExpert compile line with source/object swapped."""
    r = json.loads(json_path.read_text().strip().rstrip(","))
    cmd, i = [], 0
    while i < len(r["arguments"]):
        value = r["arguments"][i]
        if value == r["file"]:
            cmd.append(str(source))
        elif value == "-o":
            cmd += ["-o", str(obj)]
            i += 1
        elif value == "-Xclang" and r["arguments"][i + 1].startswith("-W"):
            i += 1
        elif not value.startswith("-W"):
            cmd.append(value)
        i += 1
    cmd += ["-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
            "-Wno-unnecessary-virtual-specifier", "-Wno-c99-designator", "-Wno-reorder-init-list",
            "-Wno-deprecated-enum-enum-conversion", "-I", str(ROOT / ".cache/xnu-work/osfmk")]
    if extra_inc:
        cmd += ["-I" + str(p) for p in extra_inc]
    return cmd, r["directory"]

def c_cmd(source, obj, json_path, extra_inc=None):
    """C objects: the osfmk startup compile line with source/object swapped."""
    r = json.loads(json_path.read_text().strip().rstrip(","))
    cmd, i = [], 0
    while i < len(r["arguments"]):
        value = r["arguments"][i]
        if value == r["file"]:
            cmd.append(str(source))
        elif value in ("-o", "-MF", "-MT", "-MJ"):
            if value == "-o":
                cmd += ["-o", str(obj)]
            i += 1
        elif value == "-Xclang" and r["arguments"][i + 1].startswith("-W"):
            i += 1
        elif not value.startswith("-W"):
            cmd.append(value)
        i += 1
    cmd += ["-Wall", "-Wextra", "-Werror", "-mgeneral-regs-only",
            "-I", str(ROOT / ".cache/xnu-work/osfmk")]
    if extra_inc:
        cmd += ["-I" + str(p) for p in extra_inc]
    return cmd, r["directory"]

inc = [KIT, ROOT / "drivers" / "QcomGeniSpi", hid]

touch_cpp = KIT / "FocalTouchProbe.cpp"
touch_obj = OUT / "FocalTouchProbe.o"
cmd, cwd = cpp_cmd(touch_cpp, touch_obj, expert, inc)
run(cmd, cwd=cwd)

hid_obj = OUT / "NativeHidInput.o"
cmd, cwd = cpp_cmd(hid / "NativeHidInput.cpp", hid_obj, expert, inc)
run(cmd, cwd=cwd)

c_sources = [KIT / "FocalTouchProtocol.c", ROOT / "drivers" / "QcomGeniSpi" / "GeniSpi.c"]
objs = [touch_obj, hid_obj]
for src in c_sources:
    obj = OUT / (src.stem + ".o")
    objs.append(obj)
    ccmd, ccwd = c_cmd(src, obj, startup, inc)
    run(ccmd, cwd=ccwd)

archive = OUT / "libNativeAliothTouch.a"
archive.unlink(missing_ok=True)
run(["xcrun", "ar", "rcs", archive, *objs])

(OUT / "build-report.json").write_text(json.dumps({
    "archive": str(archive),
    "objects": [str(o) for o in objs],
    "source_sha256": {str(p.relative_to(ROOT.parent if p.is_relative_to(ROOT.parent) else ROOT)): sha(p)
                      for p in [touch_cpp, hid / "NativeHidInput.cpp", *c_sources]},
}, indent=2) + "\n")
print(f"Built {archive} ({len(objs)} objects); merge into the kernel prelink (see kits/alioth-touch/README.md)")
