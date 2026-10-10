#!/usr/bin/env bash
# 39-bit full-application NSP forwarder (HOME menu icon) for sdmc:/switch/Mercenaries2/mercenaries2.nro.
# Adapted from reference/masseffect-nx/tools/build_nsp.sh (Forwarder-Mod + hacBrewPack, pinned commits).
# Usage: SWITCH_PROD_KEYS=/path/prod.keys tools/build_forwarder.sh <release.nro> <output-dir>
# The icon and NACP are taken from the NRO (see HANDOFF B:135 for how the release NRO got them).
set -euo pipefail
NRO="$1"; OUT="$2"
KEYS="${SWITCH_PROD_KEYS:?set SWITCH_PROD_KEYS to your own prod.keys}"
TITLE_ID="${TITLE_ID:-014d455243530000}"   # 01 + "MERCS" in hex
NRO_SD_PATH="sdmc:/switch/Mercenaries2/mercenaries2.nro"
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
cp "$NRO" "$WORK/app.nro"
git clone -q https://github.com/Skywalker25/Forwarder-Mod.git "$WORK/loader"
git -C "$WORK/loader" checkout -q 9853bd9167d5a7f0c5fdf935864245c1fbcf8282
git clone -q https://github.com/rlaphoenix/hacBrewPack.git "$WORK/packer"
git -C "$WORK/packer" checkout -q 745b16ecfc9ce055743067d200572204cb2aac6c
KEYS="$(cd "$(dirname "$KEYS")" && pwd)/$(basename "$KEYS")"
w() { if command -v cygpath >/dev/null; then cygpath -w "$1"; else echo "$1"; fi; }
MSYS_NO_PATHCONV=1 docker run --rm -v "$(w "$WORK"):/work" -v "$(w "$OUT"):/output" \
  -v "$(w "$KEYS"):/run/keys/prod.keys:ro" -e TITLE_ID="$TITLE_ID" -e NRO_SD_PATH="$NRO_SD_PATH" \
  -w /work "${DEVKITA64_IMAGE:-devkitpro/devkita64:latest}" bash -euo pipefail -c '
    python3 - <<"PY"
import json, os, pathlib, struct
root = pathlib.Path("/work")
keys = {}
for line in pathlib.Path("/run/keys/prod.keys").read_text().splitlines():
    if "=" in line:
        name, value = (part.strip() for part in line.split("=", 1))
        if name in ("header_key", "key_area_key_application_00"):
            keys[name] = value
if len(keys) != 2:
    raise SystemExit("Missing header_key or key_area_key_application_00")
(root / "packing.keys").write_text("".join(n + " = " + v + "\n" for n, v in keys.items()))
(root / "packing.keys").chmod(0o600)
nro = (root / "app.nro").read_bytes()
base = struct.unpack_from("<I", nro, 0x18)[0]
if nro[base:base+4] != b"ASET":
    raise SystemExit("NRO must contain an icon and NACP")
control = root / "control"; control.mkdir()
for name, pos in (("icon_AmericanEnglish.dat", 8), ("control.nacp", 24)):
    off, size = struct.unpack_from("<QQ", nro, base + pos)
    (control / name).write_bytes(nro[base+off:base+off+size])
nacp = bytearray((control / "control.nacp").read_bytes())
assert len(nacp) == 0x4000
nacp[0x3025] = 0  # StartupUserAccount: None (saves are files on SD)
nacp[0x3034] = 0  # screenshots enabled
nacp[0x3035] = 2  # video capture enabled
nacp[0x3080:0x3090] = bytes(16)
(control / "control.nacp").write_bytes(nacp)
p = root / "loader/hbl.json"; j = json.loads(p.read_text())
j["name"] = "Mercenaries 2"
tid = "0x" + os.environ["TITLE_ID"]
for k in ("title_id", "title_id_range_min", "title_id_range_max"):
    j[k] = tid
for old, new in (("title_id", "program_id"), ("title_id_range_min", "program_id_range_min"),
                 ("title_id_range_max", "program_id_range_max")):
    j[new] = j[old]
for c in j["kernel_capabilities"]:
    if c["type"] == "debug_flags":
        c["value"] = {"allow_debug": False, "force_debug": True, "force_debug_prod": False}
j["address_space_type"] = 3  # 39-bit; type 1 is only 36 bits
p.write_text(json.dumps(j, indent=2))
src = root / "loader/source/main.c"
src.write_text(src.read_text().replace("void NORETURN ", "void __attribute__((noreturn)) "))
romfs = root / "romfs"; romfs.mkdir()
for n in ("nextNroPath", "nextArgv"):
    (romfs / n).write_text(os.environ["NRO_SD_PATH"])
PY
    make -C loader -j4 RELEASE=1 ROMFS= >/work/loader.log 2>&1 || { tail -30 /work/loader.log; exit 1; }
    mkdir -p exefs
    elf2nso loader/hbl.elf exefs/main
    npdmtool loader/hbl.json exefs/main.npdm
    cp packer/config.mk.template packer/config.mk
    make -C packer -j4 >/work/packer.log 2>&1 || { tail -30 /work/packer.log; exit 1; }
    # Packer output stays out of the console (it reads console keys).
    if ! packer/hacbrewpack --titleid "$TITLE_ID" -k /work/packing.keys --nologo --keygeneration 1 \
        --nspdir /output > /work/pack.log 2> /work/pack.err; then
      echo "error: hacBrewPack failed; check header_key and key_area_key_application_00" >&2; exit 1
    fi
    test -s "/output/$TITLE_ID.nsp"
    mv "/output/$TITLE_ID.nsp" /output/Mercenaries2-forwarder.nsp
    chmod a+r /output/Mercenaries2-forwarder.nsp
  '
echo "Built $OUT/Mercenaries2-forwarder.nsp (39-bit, title ID $TITLE_ID)"
