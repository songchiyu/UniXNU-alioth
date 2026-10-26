#!/usr/bin/env python3
"""First-pass stub for the owner-verified root probe archive (libVerifiedRootProbe.a).

The real build-verified-root-probe.py needs the fully verified original OS image's
signed hash table and its XNU crypto bridge; a new device tree does not have those
assets yet. This defines every symbol the kernel and ShengUfs reference but leaves
them inert: the policy table is empty and the vr_* calls report failure, so the
block verifier rejects rather than trusts. Replace it with the real archive once the
verified-root assets exist.

The kernel link (scripts/build-xnu-4k-baseline.sh) force-loads
$ROOT/build/verified-root-xnu/libVerifiedRootProbe.a when CONFIG_XNU_VERIFIED_ROOT_PROBE=1.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / 'build/verified-root-xnu'
out.mkdir(parents=True, exist_ok=True)
stub = out / 'FirstPassStub.c'
stub.write_text(
    '/* First-pass verified-root probe stub: no original OS image yet, so there is\n'
    ' * no signed hash table. Every symbol NativeUfsBlock::configureVerification()\n'
    ' * references stays defined but inert: the policy table is empty and vr_*\n'
    ' * report failure, so the block verifier rejects rather than trusts. */\n'
    'const unsigned char verified_root_key[1] = {0};\n'
    'const unsigned long verified_root_policies[2] = {0, 0};\n'
    'const unsigned long verified_root_policy_count = 0;\n'
    'int vr_open(void) { return -1; }\n'
    'int vr_verify_block(void) { return -1; }\n'
    'int vr_xnu_crypto(void) { return -1; }\n'
    'void native_verified_root_probe(void) {}\n')
obj, archive = out / 'FirstPassStub.o', out / 'libVerifiedRootProbe.a'
subprocess.run(['xcrun', '--sdk', 'iphoneos', 'clang', '-arch', 'arm64', '-mkernel',
                '-miphoneos-version-min=17.0', '-Os', '-Wall', '-Werror', '-c', stub, '-o', obj], check=True)
archive.unlink(missing_ok=True)
subprocess.run(['xcrun', 'ar', 'rcs', archive, obj], check=True)
print(archive)
