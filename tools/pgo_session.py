"""Freeze GEN identity and reject missing/mixed profiles before a USE build."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(1 << 20), b''):
            h.update(data)
    return h.hexdigest()


def sources():
    paths = set()
    for folder in ['app/src', 'app/generated/default',
                   'reference/masseffect-nx/sdk/include', 'reference/masseffect-nx/sdk/src']:
        paths.update(p for p in (ROOT / folder).rglob('*')
                     if p.is_file() and p.suffix in {'.h', '.hpp', '.cpp', '.c', '.inc'})
    for name in ['app/CMakeLists.txt', 'tools/build_switch.ps1',
                 'tools/switch/cmake/switch-devkitA64.cmake']:
        paths.add(ROOT / name)
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(paths)}


def validate_data(manifest, data):
    expected = manifest.get('expected_gcda')
    if not expected:
        raise RuntimeError('GEN artifact has not been finalized')
    for name, info in expected.items():
        path = data / name
        if not path.is_file():
            raise RuntimeError(f'Missing profile: {name}')
        header = path.read_bytes()[:16]
        if len(header) != 16 or header[:4] != b'adcg':
            raise RuntimeError(f'Invalid gcda header: {name}')
        if header[4:8].hex() != info['version'] or header[8:12].hex() != info['stamp']:
            raise RuntimeError(f'Compiler/GEN stamp mismatch: {name}')
    return len(expected)


def audit_data(manifest, data, executable='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcov-dump'):
    """Use the matching GCC reader, including record/truncation diagnostics."""
    log = data / 'gcov-audit.log'
    functions = 0
    with log.open('w') as output:
        for name in manifest['expected_gcda']:
            run = subprocess.run([executable, str(data / name)], capture_output=True, text=True)
            output.write(run.stdout + run.stderr)
            text = run.stdout + run.stderr
            if (run.returncode or 'FUNCTION' not in text or 'COUNTERS arcs' not in text or
                    re.search(r'warning:|error:|unexpected|record size mismatch|corrupt', text, re.I)):
                raise RuntimeError(f'GCC profile record audit failed: {name}; see {log}')
            functions += text.count(':FUNCTION ')
    print(f'GCC profile records PASS: {len(manifest["expected_gcda"])} files, {functions} function records')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'finalize', 'import', 'audit'])
    parser.add_argument('--session', required=True)
    parser.add_argument('--data-session')
    parser.add_argument('--lookup-frame-csv', type=int, choices=[0,1], default=0)
    parser.add_argument('--native-table-lookup', type=int, choices=[0,1], default=0)
    parser.add_argument('--skip-renderer-profile', type=int, choices=[0,1], default=0)
    parser.add_argument('--skip-native-system-profile', type=int, choices=[0,1], default=0)
    parser.add_argument('--retention-ring-features', choices=['00','01','10','11'], default='00')
    parser.add_argument('--stage', choices=['GEN', 'USE'])
    parser.add_argument('--image')
    parser.add_argument('--build')
    parser.add_argument('--features')
    parser.add_argument('--skip-texture-profile', type=int, choices=[0,1], default=0)
    parser.add_argument('--texture-features', choices=['00','01','10','11'], default='00')
    parser.add_argument('--source-epoch', type=int, choices=[0, 1], default=0)
    parser.add_argument('--elf', type=Path)
    parser.add_argument('--compiler', type=Path)
    parser.add_argument('--from-dir', type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.session):
        raise RuntimeError('Unsafe session name')
    if args.data_session and not re.fullmatch(r'[A-Za-z0-9_-]+', args.data_session):
        raise RuntimeError('Unsafe data session name')
    if args.stage == 'GEN' and args.data_session not in (None, args.session):
        raise RuntimeError('GEN cannot overwrite a referenced profile cohort')
    folder = ROOT / 'out/pgo-sessions' / args.session
    path = folder / 'session.json'
    if args.action == 'prepare':
        if not re.fullmatch(r'[01]{8}', args.features or ''):
            raise RuntimeError('Expected all eight explicit feature bits')
        identity = {'session': args.session, 'image': args.image, 'build': args.build,
                    'features': args.features, 'source_epoch': args.source_epoch, 'texture_features': args.texture_features, 'skip_texture_profile': args.skip_texture_profile, 'skip_native_system_profile': args.skip_native_system_profile, 'skip_renderer_profile': args.skip_renderer_profile, 'native_table_lookup': args.native_table_lookup, 'lookup_frame_csv': args.lookup_frame_csv, 'retention_ring_features': args.retention_ring_features, 'data_session': args.data_session or args.session, 'sources': sources()}
        if path.exists():
            manifest = json.loads(path.read_text())
            for key, value in identity.items():
                if manifest.get(key, 0 if key in ('source_epoch', 'skip_texture_profile', 'skip_native_system_profile', 'skip_renderer_profile', 'native_table_lookup', 'lookup_frame_csv') else '00' if key in ('texture_features', 'retention_ring_features') else manifest['session'] if key == 'data_session' else None) != value:
                    raise RuntimeError(f'PGO identity changed: {key}; keep old data, use a new session')
        elif args.stage == 'GEN':
            folder.mkdir(parents=True, exist_ok=True)
            manifest = dict(identity, device_dir=f'sdmc:/switch/Mercenaries2/pgo/{args.session}')
            path.write_text(json.dumps(manifest, indent=2) + '\n')
        else:
            raise RuntimeError('USE requires a matching finalized GEN session')
        if args.stage == 'USE':
            count = validate_data(manifest, ROOT / 'out/pgo-data' / manifest.get('data_session', args.session))
            # The host is Windows; validate records once inside the same immutable
            # toolchain image before attempting the optimized compilation.
            subprocess.run(['docker', 'run', '--rm', '--mount',
                            f'type=bind,source={ROOT},target=/work', '-w', '/work', manifest['image'],
                            'python3', 'tools/pgo_session.py', 'audit', '--session', args.session], check=True)
            print(f'USE identity/profile headers PASS: {count} files')
        else:
            print(f'GEN identity frozen: {len(identity["sources"])} source files')
    elif args.action == 'finalize':
        manifest = json.loads(path.read_text())
        if sources() != manifest['sources']:
            raise RuntimeError('Sources changed during GEN build')
        build = ROOT / manifest['build']
        binary = args.elf.read_bytes()
        prefix = re.escape(manifest['device_dir'].encode() + b'/')
        names = sorted(set(m.decode() for m in re.findall(prefix + rb'([^\x00]+\.gcda)\x00', binary)))
        if not names:
            raise RuntimeError('No session-specific gcda paths in GEN ELF')
        expected = {}
        for name in names:
            if '/' in name or '\\' in name:
                raise RuntimeError(f'Unexpected non-flat profile name: {name}')
            notes = build / (name.replace('#', '/').lstrip('/')[:-5] + '.gcno')
            if not notes.is_file():
                raise RuntimeError(f'No matching gcno graph: {name} -> {notes}')
            header = notes.read_bytes()[:16]
            if header[:4] != b'oncg':
                raise RuntimeError(f'Invalid graph header: {notes}')
            expected[name] = {'version': header[4:8].hex(), 'stamp': header[8:12].hex(),
                              'gcno': notes.relative_to(ROOT).as_posix(), 'gcno_sha256': digest(notes)}
        manifest.update(expected_gcda=expected, compiler=json.loads(args.compiler.read_text()),
                        gen_elf_sha256=digest(args.elf))
        path.write_text(json.dumps(manifest, indent=2) + '\n')
        print(f'GEN finalized: {len(expected)} expected profiles/graphs')
    elif args.action == 'audit':
        manifest = json.loads(path.read_text())
        data = ROOT / 'out/pgo-data' / manifest.get('data_session', args.session)
        validate_data(manifest, data)
        audit_data(manifest, data)
    else:
        manifest = json.loads(path.read_text())
        if manifest.get('data_session', args.session) != args.session:
            raise RuntimeError('Import into a referenced cohort is forbidden')
        count = validate_data(manifest, args.from_dir)
        destination = ROOT / 'out/pgo-data' / manifest.get('data_session', args.session)
        destination.mkdir(parents=True, exist_ok=True)
        for name in manifest['expected_gcda']:
            target = destination / name
            source = args.from_dir / name
            if target.exists() and digest(target) != digest(source):
                raise RuntimeError(f'Refusing to overwrite earlier imported profile: {name}')
            shutil.copy2(source, target)
        print(f'Imported {count} profiles; source results preserved')


if __name__ == '__main__':
    main()
