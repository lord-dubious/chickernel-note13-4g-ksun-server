#!/usr/bin/env python3
"""Compare a module's imported symbol CRCs without loading it (requires kmod).

Exit 0: all imported CRCs match supplied export tables; 1: mismatch;
2: incomplete evidence or an input error. Matching CRCs alone do not establish
signature, CFI, vermagic, complete ABI or hardware compatibility.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def compare(exports, imports):
    return {
        'mismatches': {name: {'module': hex(crc), 'export': hex(exports[name])}
                       for name, crc in imports.items() if name in exports and exports[name] != crc},
        'unresolved': sorted(name for name in imports if name not in exports),
        'import_count': len(imports),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symvers', type=Path, action='append', required=True,
                        help='Kernel or matching provider-module symbol table; repeat as needed')
    parser.add_argument('modules', type=Path, nargs='+')
    args = parser.parse_args()
    exports = {}
    for table in args.symvers:
        for line in table.read_text().splitlines():
            fields = line.split()
            if len(fields) < 2:
                continue
            crc, name = int(fields[0], 16), fields[1]
            if name in exports and exports[name] != crc:
                raise ValueError(f'Conflicting export tables for {name}')
            exports[name] = crc
    if not exports:
        raise ValueError('No exported symbol versions found')
    results = {}
    for module in args.modules:
        output = subprocess.run(['modprobe', '--show-modversions', str(module.resolve())],
                                text=True, check=True, stdout=subprocess.PIPE).stdout
        imports = {}
        for line in output.splitlines():
            crc, name = line.split()
            imports[name] = int(crc, 16)
        if not imports:
            raise ValueError(f'{module}: no imported versions; compatibility is not established')
        results[str(module)] = compare(exports, imports)
    print(json.dumps({'modules': results,
                      'scope': 'Imported CRCs only. No module is loaded; device compatibility remains untested.'},
                     indent=2))
    if any(item['mismatches'] for item in results.values()):
        return 1
    return 2 if any(item['unresolved'] for item in results.values()) else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(2)
