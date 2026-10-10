"""Check extraction against XDVDFS and record this edition for local port work."""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    source = ROOT / 'reference/masseffect-nx/tools/extract_iso.py'
    spec = importlib.util.spec_from_file_location('xdvdfs', source)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    with args.image.open('rb') as stream:
        base, layout = reader.find_partition(stream)
        sector, size = reader.read_volume_descriptor(stream, base)
        files = [(p, e) for p, e in reader.walk(stream, base, sector, size) if not e['is_dir']]
    errors = []
    inventory = []
    for name, entry in files:
        path = ROOT / 'assets/game_root' / name
        offset = base + entry['sector'] * reader.SECTOR
        if offset + entry['size'] > args.image.stat().st_size:
            errors.append(f'Outside image: {name}')
        if not path.is_file() or path.stat().st_size != entry['size']:
            errors.append(f'Missing or wrong extracted size: {name}')
        inventory.append(dict(path=name, size=entry['size'], iso_offset=offset))
    xex = ROOT / 'assets/game_root/default.xex'
    data = xex.read_bytes()
    if data[:4] != b'XEX2':
        raise ValueError('Not XEX2')
    u32 = lambda off: struct.unpack_from('>I', data, off)[0]
    optional = dict(struct.unpack_from('>II', data, 0x18 + i * 8) for i in range(u32(0x14)))
    execution = struct.unpack_from('>IIII', data, optional[0x40006])
    security = u32(0x10)
    shader_path = ROOT / 'assets/game_root/shaders.bin'
    shaders = shader_path.read_bytes()
    # Signature hits are candidates, not proof that containers are valid/translatable.
    candidates = [i for i in range(len(shaders) - 3) if shaders[i:i + 2] == b'\x10\x2a']
    report = {
        'image': args.image.name, 'image_size': args.image.stat().st_size,
        'partition_base': hex(base), 'layout': layout,
        'files': inventory, 'file_count': len(files),
        'extracted_total_bytes': sum(e['size'] for _, e in files),
        'extraction_errors': errors,
        'xex': {'sha256': digest(xex), 'size': len(data),
                'title_id': f'{execution[3]:08X}', 'media_id': f'{execution[0]:08X}',
                'version_raw': hex(execution[1]), 'image_base': hex(optional[0x10201]),
                'entry_point': hex(optional[0x10100]), 'image_size': u32(security + 4)},
        'shaders': {'size': len(shaders), 'sha256': digest(shader_path),
                    'prefix_hex': shaders[:64].hex(),
                    'signature_candidate_count': len(candidates),
                    'signature_counts': dict(collections.Counter(shaders[i:i+4].hex() for i in candidates)),
                    'first_candidate_offsets': candidates[:16]},
    }
    out = ROOT / 'out/analysis/disc.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
