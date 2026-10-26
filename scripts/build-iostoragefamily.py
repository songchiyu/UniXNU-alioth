#!/usr/bin/env python3
"""Compile the IOStorageFamily classes the built-in block drivers subclass.

NativeUfsBlock inherits IOBlockStorageDevice and publishes an IOMedia for the root
window, so the kernel link needs those implementations, not only their headers.
prepare-storage-headers.py copies the public headers and stops there; nothing ever
compiled the sources, which is why the link ends up with "vtable for
IOBlockStorageDevice", its member functions and "IOMedia::metaClass" undefined.

The upstream tree is the unchanged Apple open source the feed pins
(refer/IOStorageFamily), and these classes are ordinary IOKit C++: IOService plus
IOLib, IOUserClient and the storage headers. Build them with the same kernel recipe
the platform expert uses, so the objects keep the exact kernel ABI, target and
deployment the rest of the kernel has.

Only the transport-independent storage core is built here. The partition, label and
BSD-client schemes stay out: nothing on this board references them yet, and they pull
the BSD side of the driver in with them.
"""
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'refer/IOStorageFamily'
REVISION = 'e45fbe30a7879e0b16e26dddb78538f1b00e0bff'
OUT = ROOT / 'build/iostoragefamily'

# Dependency closure of IOBlockStorageDevice and IOMedia, leaves first.
SOURCES = (
    'IOStorage.cpp',
    'IOBlockStorageDevice.cpp',
    'IOMedia.cpp',
    'IOFilterScheme.cpp',
    'IOPartitionScheme.cpp',
    'IORequest.cpp',
    'IORequestsPool.cpp',
    'IOBlockStorageDriver.cpp',
)

if not (SOURCE / '.git').is_dir():
    raise SystemExit(f'Missing {SOURCE}; run "unixnu fetch IOStorageFamily" first')
revision = subprocess.check_output(['git', '-C', SOURCE, 'rev-parse', 'HEAD'], text=True).strip()
if revision != REVISION:
    raise SystemExit(f'Unexpected public IOStorageFamily revision: {revision}')

recipe = ROOT / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'
record = json.loads(recipe.read_text().strip().rstrip(','))
OUT.mkdir(parents=True, exist_ok=True)
includes = ['-I', str(ROOT / 'build/storage-abi/include'), '-I', str(SOURCE)]

objects = []
for name in SOURCES:
    source = SOURCE / name
    if not source.is_file():
        raise SystemExit(f'Missing upstream source {source}')
    destination = OUT / (source.stem + '.o')
    arguments = record['arguments']
    command = []
    index = 0
    while index < len(arguments):
        value = arguments[index]
        if value == record['file']:
            command.append(str(source))
        elif value == '-o':
            command.extend(['-o', str(destination)])
            index += 1
        elif value in ('-MF', '-MJ'):
            index += 1
        elif value not in ('-MD', '-MP'):
            command.append(value)
        index += 1
    command += includes
    result = subprocess.run(command, cwd=record['directory'], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    (OUT / (source.stem + '.log')).write_text(result.stdout)
    if result.returncode:
        raise SystemExit(f'{name}: compile failed\n{result.stdout[-3500:]}')

    data = destination.read_bytes()
    if struct.unpack_from('<4I', data) != (0xfeedfacf, 0x100000c, 0, 1):
        raise SystemExit(f'{name}: expected ordinary ARM64 output')
    offset, deployment = 32, None
    for _ in range(struct.unpack_from('<I', data, 16)[0]):
        cmd, length = struct.unpack_from('<II', data, offset)
        if cmd == 0x32:
            deployment = struct.unpack_from('<II', data, offset + 8)
        offset += length
    if deployment != (2, 0x110000):
        raise SystemExit(f'{name}: unexpected deployment {deployment}')
    objects.append(destination)

archive = OUT / 'libIOStorageFamily.a'
archive.unlink(missing_ok=True)
subprocess.run(['xcrun', 'ar', 'rcs', archive, *objects], check=True)
(OUT / 'build-report.json').write_text(json.dumps({
    'source_revision': revision,
    'sources': list(SOURCES),
    'objects': [str(o) for o in objects],
}, indent=2) + '\n')
print(f'{len(objects)} IOStorageFamily sources compiled (ordinary ARM64 / iOS 17 audited)')
