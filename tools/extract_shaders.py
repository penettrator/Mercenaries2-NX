"""Extract Mercenaries 2 shaders.bin's big-endian ID/offset table.

These are original Xenos containers, not translated SPIR-V. Nothing here
assumes Mass Effect's Unreal packages or changes guest shader instructions.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import struct

def parse(data):
    def u32(offset):
        return struct.unpack_from('>I', data, offset)[0]
    if len(data) < 4:
        raise ValueError('Truncated table')
    count = u32(0)
    table_end = 4 + count * 8
    if not 0 < count <= 4096 or table_end > len(data):
        raise ValueError('Invalid count')
    records = [struct.unpack_from('>II', data, 4 + i*8) for i in range(count)]
    offsets = [offset for _, offset in records]
    if offsets != sorted(set(offsets)) or offsets[0] < table_end:
        raise ValueError('Offsets must be ordered, unique and after the table')
    result = []
    for i, (shader_id, offset) in enumerate(records):
        end = offsets[i+1] if i+1 < count else len(data)
        if offset % 16 or offset + 28 > end or end > len(data):
            raise ValueError(f'Invalid span {i}')
        signature, virtual, physical = struct.unpack_from('>III', data, offset)
        if signature not in (0x102A1100, 0x102A1101):
            raise ValueError(f'Unexpected signature {signature:08x} in entry {i}')
        length = virtual + physical
        if virtual < 28 or physical == 0 or offset + length > end:
            raise ValueError(f'Invalid container length in entry {i}')
        header = u32(offset+24)
        if header < 28 or header + 8 > virtual:
            raise ValueError(f'Invalid code header in entry {i}')
        code_offset, code_size = struct.unpack_from('>II', data, offset+header)
        if code_size == 0 or code_size % 12 or code_offset + code_size > physical:
            raise ValueError(f'Invalid microcode bounds in entry {i}')
        blob = data[offset:offset+length]
        record = {'index': i, 'id': f'{shader_id:08x}', 'offset': offset,
                  'size': length, 'stage': 'vs' if signature & 1 else 'ps',
                  'microcode_size': code_size, 'sha256': hashlib.sha256(blob).hexdigest()}
        result.append((record, blob))
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('-o', '--output', type=Path, default=Path('out/shaders/containers'))
    args = parser.parse_args()
    # Validate the complete table before writing any output.
    records = parse(args.input.read_bytes())
    args.output.mkdir(parents=True, exist_ok=True)
    for record, blob in records:
        record['file'] = f"{record['stage']}_{record['index']:04d}_{record['id']}.bin"
        (args.output / record['file']).write_bytes(blob)
    summary = {'source_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
               'count': len(records), 'stages': dict(collections.Counter(r['stage'] for r, _ in records)),
               'records': [r for r, _ in records]}
    (args.output / 'index.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k != 'records'}, indent=2))

if __name__ == '__main__':
    main()
