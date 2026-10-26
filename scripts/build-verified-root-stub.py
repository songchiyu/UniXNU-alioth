#!/usr/bin/env python3
"""First-pass stub for the owner-verified root probe archive (libVerifiedRootProbe.a).

The real build-verified-root-probe.py needs the fully verified original OS image's
signed hash table and its XNU crypto bridge; a new device tree does not have those
assets yet. This archives a no-op native_verified_root_probe so the kernel links,
mirroring the first-pass pattern of build-platform-power.py. Replace it with the
real archive once the verified-root assets exist.

The kernel link (scripts/build-xnu-4k-baseline.sh) force-loads
$ROOT/build/verified-root-xnu/libVerifiedRootProbe.a when CONFIG_XNU_VERIFIED_ROOT_PROBE=1.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / 'build/verified-root-xnu'
out.mkdir(parents=True, exist_ok=True)
stub = out / 'FirstPassStub.c'
stub.write_text('// No verified original OS image yet: the probe needs one, so the first kernel links without it.\n'
                'void native_verified_root_probe(void);\nvoid native_verified_root_probe(void)\n{\n}\n')
obj, archive = out / 'FirstPassStub.o', out / 'libVerifiedRootProbe.a'
subprocess.run(['xcrun', '--sdk', 'iphoneos', 'clang', '-arch', 'arm64', '-mkernel',
                '-miphoneos-version-min=17.0', '-Os', '-Wall', '-Werror', '-c', stub, '-o', obj], check=True)
archive.unlink(missing_ok=True)
subprocess.run(['xcrun', 'ar', 'rcs', archive, obj], check=True)
print(archive)
