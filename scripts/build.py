#!/usr/bin/env python3
"""Build the pinned kernel without rewriting its source defconfig. Linux/WSL only."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

from verify_kernel import verify

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / 'source-lock.json').read_text())


def run(*args, cwd=None, env=None, capture=False, input=None):
    print('+', ' '.join(str(a) for a in args), flush=True)
    return subprocess.run([str(a) for a in args], cwd=cwd, env=env, check=True,
                          text=True, input=input, stdout=subprocess.PIPE if capture else None).stdout


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_source(source):
    """Permit only the exact patch set computed against the pinned source tree."""
    run('git', 'diff', '--cached', '--quiet', 'HEAD', cwd=source)
    if run('git', 'ls-files', '--others', '--exclude-standard', cwd=source, capture=True).strip():
        raise ValueError('Remove unrelated untracked source files before building')
    with tempfile.TemporaryDirectory(prefix='chickernel-index-') as temp:
        patch_env = os.environ | {'GIT_INDEX_FILE': str(Path(temp) / 'index')}
        run('git', 'read-tree', 'HEAD', cwd=source, env=patch_env)
        patches = []
        for relative, checksum in LOCK.get('patches', {}).items():
            patch = (ROOT / relative).resolve()
            if ROOT not in patch.parents or digest(patch) != checksum:
                raise ValueError(f'Patch identity mismatch: {relative}')
            run('git', 'apply', '--cached', '--check', patch, cwd=source, env=patch_env)
            run('git', 'apply', '--cached', patch, cwd=source, env=patch_env)
            patches.append(patch)
        expected = run('git', 'diff', '--cached', '--binary', 'HEAD', cwd=source,
                       env=patch_env, capture=True)
        actual = run('git', 'diff', '--binary', 'HEAD', cwd=source, capture=True)
        if actual and actual != expected:
            raise ValueError('Source contains changes outside the locked patch set')
        if not actual:
            for patch in patches:
                run('git', 'apply', '--check', patch, cwd=source)
                run('git', 'apply', patch, cwd=source)
        if run('git', 'diff', '--binary', 'HEAD', cwd=source, capture=True) != expected:
            raise ValueError('Prepared source does not match the locked patch set')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--dist', type=Path)
    parser.add_argument('--toolchain', type=Path, help='AOSP clang directory containing bin/clang')
    parser.add_argument('--config-only', action='store_true')
    parser.add_argument('--template', type=Path, help='Audited stable-7 AnyKernel3 ZIP')
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Run inside Linux or WSL')
    source, out = args.source.resolve(), args.out.resolve()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    if out == source or source in out.parents:
        parser.error('--out must be outside the kernel source tree')
    if not args.config_only and (not args.toolchain or not args.dist):
        parser.error('Full builds require --toolchain and --dist')
    if args.toolchain and not (args.toolchain / 'bin/clang').is_file():
        parser.error('--toolchain must contain bin/clang; refusing a PATH fallback')
    dist = args.dist.resolve() if args.dist else None
    if dist:
        if dist == source or source in dist.parents or dist == out or out in dist.parents:
            parser.error('--dist must be separate from source and build output')
        if dist.exists() and any(dist.iterdir()):
            parser.error('--dist must be empty to avoid replacing previous artifacts')
    if args.template:
        if digest(args.template) != '988ba55f5376b7197c66249229b662bdfceee899fd36012fd356c124df039049':
            parser.error('Template hash does not match the audited stable-7 ZIP')
        with zipfile.ZipFile(args.template) as template:
            if template.namelist().count('Image.gz') != 1 or 'Image' in template.namelist():
                parser.error('Unexpected template kernel entries')
    head = run('git', 'rev-parse', 'HEAD', cwd=source, capture=True).strip()
    if head != LOCK['commit']:
        parser.error(f'Kernel HEAD must be pinned to {LOCK["commit"]}, got {head}')
    for name, sha in LOCK['submodules'].items():
        if run('git', '-C', source / name, 'rev-parse', 'HEAD', capture=True).strip() != sha:
            parser.error(f'Initialize pinned submodule {name}: git submodule update --init')
        if run('git', '-C', source / name, 'status', '--porcelain', capture=True).strip():
            parser.error(f'Pinned submodule {name} must be clean')
    prepare_source(source)
    env = os.environ.copy()
    env.pop('KCONFIG_CONFIG', None)
    env.pop('KCONFIG_ALLCONFIG', None)
    env.pop('LOCALVERSION', None)
    if args.toolchain:
        env['PATH'] = str(args.toolchain.resolve() / 'bin') + os.pathsep + env['PATH']
    if not args.config_only:
        # make computes PAHOLE_FLAGS when it starts; installing the tool after
        # compilation begins can leave required BTF compatibility flags empty.
        if not shutil.which('pahole', path=env['PATH']):
            parser.error('Full builds require pahole before make starts (install pahole/dwarves)')
        # Test a real optimizer invocation: distro clang can advertise the option
        # yet fail because it lacks the release ML model required by this tree.
        run('clang', '--target=aarch64-linux-gnu', '-O2', '-mllvm',
            '-regalloc-enable-advisor=release', '-mllvm', '-polly', '-x', 'c',
            '-c', '-o', '/dev/null', '-', env=env, input='int f(int x) { return x + 1; }\n')
    out.mkdir(parents=True, exist_ok=True)
    fragments = [source / 'arch/arm64/configs/chickernel-variants/ksun.config']
    fragments += [ROOT / 'reference-source' / name for name in
                  ('server.config', 'native-sapphire.config', 'thin-lto.config')]
    merged = out / 'requested.config'
    merge_env = env | {'KCONFIG_CONFIG': str(merged)}
    run('bash', source / 'scripts/kconfig/merge_config.sh', '-m',
        source / 'arch/arm64/configs/chickernel_defconfig', *fragments,
        cwd=out, env=merge_env)
    make = ['make', '-C', source, f'O={out}', 'ARCH=arm64', 'LLVM=1',
            'HOSTCC=gcc', 'HOSTCXX=g++', 'HOSTLD=g++', 'LOCALVERSION=']
    run(*make, f'KCONFIG_ALLCONFIG={merged}', 'alldefconfig', env=env)
    config_receipt = verify(out / '.config', 'config', fragments)
    print(json.dumps(config_receipt, indent=2))
    if args.config_only:
        return
    # Check the input to .incbin before the expensive whole-kernel link. The
    # pinned upstream rule used a hardcoded stock defconfig until patched.
    run(*make, 'kernel/configs.o', env=env)
    print(json.dumps(verify(out / 'kernel/config_data.gz', 'gzip-config', fragments,
                            out / '.config'), indent=2))
    run(*make, f'-j{args.jobs}', 'Image', env=env)
    image = out / 'arch/arm64/boot/Image'
    receipt = verify(image, 'image', fragments, out / '.config')
    dist.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image, dist / 'Image')
    shutil.copyfile(out / '.config', dist / 'kernel.config')
    shutil.copyfile(out / 'vmlinux.symvers', dist / 'vmlinux.symvers')
    if args.template:
        # Only the audited historical stable-7 layout is supported. Its old
        # Image is untrusted and always replaced; other installer bytes persist.
        package = dist / 'chickernel-stable-7-ksun-server.zip'
        with zipfile.ZipFile(args.template) as old, zipfile.ZipFile(package, 'w') as new:
            if old.namelist().count('Image.gz') != 1 or 'Image' in old.namelist():
                parser.error('Unexpected template kernel entries')
            for info in old.infolist():
                data = gzip.compress(image.read_bytes(), mtime=0) if info.filename == 'Image.gz' else old.read(info)
                new.writestr(info, data)
        verify(package, 'zip', fragments, out / '.config')
    provenance = {'kernel_source': LOCK, 'reference_repo_commit':
                  run('git', '-C', ROOT, 'rev-parse', 'HEAD', capture=True).strip(),
                  'reference_repo_dirty': bool(run('git', '-C', ROOT, 'status', '--porcelain',
                                                   capture=True).strip()),
                  'compiler': run('clang', '--version', env=env, capture=True),
                  'tool_executables_sha256': {
                      name: digest(Path(shutil.which(name, path=env['PATH'])).resolve())
                      for name in ('clang', 'clang.real', 'ld.lld', 'llvm-ar')
                      if shutil.which(name, path=env['PATH'])},
                  'kernel_source_diff': run('git', 'diff', '--binary', cwd=source, capture=True),
                  'template_sha256': digest(args.template) if args.template else None,
                  'fragments_sha256': {str(p.relative_to(ROOT)) if ROOT in p.parents else str(p):
                                       digest(p) for p in fragments},
                  'image_verification': receipt,
                  'module_compatibility': 'NOT VERIFIED against the connected device; compare its actual modules with vmlinux.symvers',
                  'hardware_validation': 'NOT RUN; no flash authorization is inferred by this script'}
    (dist / 'build-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    files = sorted(p for p in dist.iterdir() if p.is_file())
    (dist / 'SHA256SUMS.txt').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in files))
    print(f'Built and config-verified outputs: {dist}. Device compatibility remains untested.')


if __name__ == '__main__':
    try:
        main()
    except (subprocess.CalledProcessError, ValueError, OSError, zipfile.BadZipFile) as error:
        sys.exit(f'ERROR: {error}')
