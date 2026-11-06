"""Validate this port's native prewarm and NVK cache without modifying them."""
import argparse
import ctypes
import ctypes.util
import hashlib
import json
import struct
from pathlib import Path


def audit(folder, library=None):
    library = library or ctypes.util.find_library('xxhash')
    if not library:
        raise RuntimeError('Provide --hash-library with a host xxHash library')
    lib = ctypes.CDLL(str(library))
    hash64 = getattr(lib, 'XXH3_64bits', None) or lib.merc_shader_hash
    hash64.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    hash64.restype = ctypes.c_uint64
    p = folder / 'native-prewarm-45410828.bin'
    data = p.read_bytes()
    magic, version, key_size, count, keys_count, checksum = struct.unpack_from('<QIIIIQ', data)
    assert magic == 0x314D5257504E324D and version == 1 and key_size == 200
    assert keys_count <= 8192 and hash64(data[32:], len(data) - 32) == checksum
    offset, shaders = 32, {}
    for _ in range(count):
        identity, stage, dwords = struct.unpack_from('<QII', data, offset)
        offset += 16
        assert stage <= 1 and dwords and offset + dwords * 4 <= len(data)
        assert identity not in shaders
        shaders[identity] = stage
        offset += dwords * 4
    assert offset + keys_count * key_size == len(data)
    keys = {data[i:i + key_size] for i in range(offset, len(data), key_size)}
    assert len(keys) == keys_count
    for key in keys:
        vs, _, ps, _ = struct.unpack_from('<QQQQ', key)
        assert vs in shaders and shaders[vs] == 0
        assert not ps or ps in shaders and shaders[ps] == 1
    files = {p.name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}}
    drivers = []
    for path in sorted(folder.glob('native-45410828-*.cache')):
        packed = path.read_bytes()
        magic, size, checksum = struct.unpack_from('<QQQ', packed)
        raw = packed[24:]
        assert magic == 0x3148434E54414E52 and size == len(raw)
        assert hash64(raw, len(raw)) == checksum
        length, version, vendor, device = struct.unpack_from('<IIII', raw)
        assert 32 <= length <= len(raw) and version == 1 and vendor == 0x10DE and device == 0xFE0
        drivers.append({'file': path.name, 'vendor': vendor, 'device': device, 'uuid': raw[16:32].hex()})
        files[path.name] = {'bytes': len(packed), 'sha256': hashlib.sha256(packed).hexdigest()}
    assert drivers, 'No native driver cache found'
    return {'shaders': count, 'pipeline_keys': keys_count, 'payload_checksum_valid': True,
            'all_shader_references_valid': True, 'driver_headers_valid': True,
            'drivers': drivers, 'files': files,
            'scope': 'Known recorded variants only; not proof of full game coverage or device execution'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir', type=Path, required=True)
    parser.add_argument('--hash-library', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.cache_dir, args.hash_library)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(report, indent=2) + '\n').encode())
    print(json.dumps({k: report[k] for k in ['shaders', 'pipeline_keys', 'payload_checksum_valid', 'all_shader_references_valid']}))
