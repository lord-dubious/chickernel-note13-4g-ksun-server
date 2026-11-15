#!/usr/bin/env python3
"""Check requested Kconfig values against a resolved config or embedded IKCONFIG."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile
import zlib


def parse_config(text):
    values = {}
    for line in text.splitlines():
        enabled = re.fullmatch(r'(CONFIG_\w+)=(.*)', line.strip())
        disabled = re.fullmatch(r'# (CONFIG_\w+) is not set', line.strip())
        if enabled:
            values[enabled[1]] = enabled[2]
        elif disabled:
            values[disabled[1]] = 'n'
    return values


def requirements(fragments):
    result = {}
    for fragment in fragments:
        result.update(parse_config(Path(fragment).read_text()))
    if not result:
        raise ValueError('No requested Kconfig assignments found')
    return result


def embedded_config(data):
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    configs = []
    for match in re.finditer(b'IKCFG_ST', data):
        inflater = zlib.decompressobj(31)
        try:
            text = inflater.decompress(data[match.end():]).decode('utf-8')
        except (zlib.error, UnicodeDecodeError):
            continue  # The kernel can also contain the marker as a literal string.
        if inflater.eof and inflater.unused_data.startswith(b'IKCFG_ED'):
            configs.append(text)
    if len(configs) != 1:
        raise ValueError(f'Expected one valid embedded config, found {len(configs)}')
    return configs[0]


def read_config(path, kind):
    path = Path(path)
    if kind == 'config':
        return path.read_text()
    if kind == 'zip':
        with zipfile.ZipFile(path) as archive:
            images = [n for n in archive.namelist() if n in ('Image', 'Image.gz')]
            if len(images) != 1:
                raise ValueError('ZIP must contain exactly one root Image or Image.gz')
            data = archive.read(images[0])
    else:
        data = path.read_bytes()
    return embedded_config(data)


def verify(path, kind, fragments, reference=None):
    actual = parse_config(read_config(path, kind))
    expected = requirements(fragments)
    failures = {key: {'expected': value, 'actual': actual.get(key, 'n')}
                for key, value in expected.items() if actual.get(key, 'n') != value}
    if reference is not None:
        baseline = parse_config(Path(reference).read_text())
        different = [key for key in sorted(actual.keys() | baseline.keys())
                     if actual.get(key, 'n') != baseline.get(key, 'n')]
        if different:
            raise ValueError('Embedded config differs from build .config: ' + ', '.join(different))
    if failures:
        raise ValueError('Unsatisfied configuration: ' + json.dumps(failures, sort_keys=True))
    return {'file': str(Path(path).resolve()), 'kind': kind,
            'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'requested_settings': len(expected)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact', type=Path)
    parser.add_argument('--kind', choices=['config', 'image', 'zip'], required=True)
    parser.add_argument('--fragment', type=Path, action='append', required=True)
    parser.add_argument('--reference-config', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.artifact, args.kind, args.fragment,
                                args.reference_config), indent=2))
    except (ValueError, OSError, zipfile.BadZipFile, EOFError) as error:
        parser.exit(1, f'ERROR: {error}\n')


if __name__ == '__main__':
    main()
