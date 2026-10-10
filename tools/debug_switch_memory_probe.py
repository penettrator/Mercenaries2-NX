"""Bounded GDB remote inspection of the owned, project-local memory probe."""
import argparse
import hashlib
import json
import re
import struct
import shutil
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMU = ROOT / "tools/bin/eden-0.2.1"
CONFIG = EMU / "user/config/sdl2-config.ini"
parser = argparse.ArgumentParser()
parser.add_argument("--label", default="memory-probe-gdb")
parser.add_argument("--nro", type=Path, default=ROOT / "out/memory-probe/memory-probe.nro")
parser.add_argument("--resume-seconds", type=int, default=8)
parser.add_argument("--second-sample", action="store_true")
parser.add_argument("--wait-for-stop", action="store_true", help="Capture the first asynchronous debugger stop, bounded by resume-seconds")
parser.add_argument("--capture-submissions", action="store_true")
parser.add_argument("--inspect-thread", help="Confirmed PPC thread ID in hexadecimal")
parser.add_argument("--interpret-macros", action="store_true")
parser.add_argument("--game-startup-diagnostic", action="store_true")
args = parser.parse_args()
if not 1 <= args.resume_seconds <= 60:
    parser.error("Resume duration must be in 1..60 seconds")
if not args.label.replace("-", "").replace("_", "").isalnum():
    parser.error("Invalid label")
REPORT = ROOT / "out/emulator-check" / args.label
REPORT.mkdir(exist_ok=False)
original = CONFIG.read_bytes()
text = original.decode().replace("use_gdbstub=false", "use_gdbstub=true").replace("use_gdbstub\\default=true", "use_gdbstub\\default=false")
if args.interpret_macros:
    for key in ["disable_macro_jit", "disable_macro_hle"]:
        text = text.replace(key+"=false", key+"=true").replace(key+"\\default=true", key+"\\default=false")
shader_flag = EMU / "user/sdmc/switch/Mercenaries2/emulator_shader_test.flag"
old_shader_flag = shader_flag.read_bytes() if shader_flag.exists() else None
if args.game_startup_diagnostic:
    if args.nro.name != "mercenaries2.nro": parser.error("Game startup diagnostics require mercenaries2.nro")
    for key, value in [("disable_macro_jit","true"),("sync_memory_operations","true"),("enable_compute_pipelines","true"),("gpu_accuracy","2")]:
        text, count = re.subn(r"(?m)^"+key+r"=(true|false|[0-9]+)", key+"="+value, text)
        if count != 1: raise RuntimeError("Unexpected configuration for "+key)
        text = text.replace(key+"\\default=true", key+"\\default=false")
CONFIG.write_text(text)
si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
si.wShowWindow = 0
process = None
connection = None
report = {}
try:
    if args.game_startup_diagnostic: shader_flag.write_text("1")
    with (REPORT / "cli.log").open("w") as output:
        process = subprocess.Popen([str(EMU / "eden-cli.exe"), str(args.nro.resolve())], cwd=EMU, stdout=output, stderr=subprocess.STDOUT, startupinfo=si)
        deadline = time.monotonic() + 10
        while connection is None:
            try:
                connection = socket.create_connection(("127.0.0.1", 6543), timeout=1)
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Owned probe GDB stub did not become available")
                time.sleep(0.2)
        connection.settimeout(5)
        def send(command):
            data = command.encode()
            connection.sendall(b"$" + data + b"#" + f"{sum(data) & 255:02x}".encode())
        def receive():
            while True:
                byte = connection.recv(1)
                if not byte:
                    raise EOFError("GDB connection closed before packet")
                if byte == b"$":
                    break
            data = bytearray()
            while True:
                byte = connection.recv(1)
                if byte == b"#":
                    break
                if not byte:
                    raise EOFError("GDB connection closed")
                data.extend(byte)
            checksum = connection.recv(2)
            connection.sendall(b"+")
            if int(checksum, 16) != (sum(data) & 255):
                raise RuntimeError("GDB checksum mismatch")
            return data.decode()
        def request(command):
            send(command)
            response = receive()
            # Eden may deliver an additional asynchronous stop notification.
            # Keep it from being mistaken for an XML or thread-list reply.
            while command != "?" and response.startswith(("T", "S")):
                report.setdefault("additional_stops", []).append(response)
                response = receive()
            return response
        report["initial_stop"] = request("?")
        report["features"] = request("qSupported")
        send("c")
        if args.wait_for_stop:
            # A lone RSP acknowledgment is readable but is not a stop packet.
            connection.settimeout(args.resume_seconds)
            try:
                report["sample_stop"] = receive()
                report["asynchronous_stop_received"] = True
            except socket.timeout:
                report["asynchronous_stop_received"] = False
                connection.settimeout(5)
                connection.sendall(b"\x03")
                report["sample_stop"] = receive()
            finally:
                connection.settimeout(5)
        else:
            time.sleep(args.resume_seconds)
            connection.sendall(b"\x03")
            report["sample_stop"] = receive()
        report["libraries"] = request("qXfer:libraries:read::0,fff")
        threads = request("qfThreadInfo")
        report["threads_response"] = threads
        report["threads"] = []
        if threads.startswith("m"):
            for thread in threads[1:].split(","):
                entry = {"id": thread, "select": request("Hg" + thread)}
                for name, number in [("pc", "20"), ("sp", "1f"), ("lr", "1e")]:
                    value = request("p" + number)
                    entry[name + "_raw"] = value
                    if value and not (len(value) == 3 and value.startswith("E")):
                        entry[name] = hex(int.from_bytes(bytes.fromhex(value), "little"))
                registers = request("g")
                if len(registers) >= 31 * 16 and not (len(registers) == 3 and registers.startswith("E")):
                    raw = bytes.fromhex(registers)
                    entry["x_registers"] = {
                        "x" + str(i): hex(int.from_bytes(raw[i*8:(i+1)*8], "little"))
                        for i in range(31)
                    }
                if "x_registers" in entry and (("thread:" + thread + ";") in report["sample_stop"] or thread == args.inspect_thread):
                    address = entry["x_registers"]["x19"][2:]
                    context = request("m" + address + ",130")
                    entry["possible_ppc_context_x19"] = context
                    if len(context) == 0x130 * 2:
                        raw_context = bytes.fromhex(context)
                        offsets = {"r3": 0, "r0": 8, "r1": 16, "r2": 24}
                        offsets.update({"r"+str(i): i*8 for i in range(4, 32)})
                        offsets.update({"lr": 256, "ctr": 264})
                        entry["possible_ppc_registers"] = {name: hex(int.from_bytes(raw_context[offset:offset+8], "little")) for name, offset in offsets.items()}
                        obj = int(entry["possible_ppc_registers"]["r3"], 16)
                        if 0xA0000000 <= obj <= 0xE0000000:
                            guest_base = int(entry["x_registers"]["x20"], 16)
                            entry["possible_device_header"] = request("m" + hex(guest_base+obj)[2:] + ",40")
                if "pc" in entry:
                    entry["pc_instruction_bytes"] = request("m"+entry["pc"][2:]+",20")
                if "lr" in entry:
                    entry["lr_instruction_bytes"] = request("m"+entry["lr"][2:]+",20")
                if "sp" in entry:
                    entry["stack"] = request("m" + entry["sp"][2:] + ",100")
                if "x_registers" in entry and ("thread:" + thread + ";") in report["sample_stop"]:
                    # Preserve actual frame records; saved registers are candidates,
                    # not automatically a PPC context.
                    fp = int(entry["x_registers"]["x29"],16)
                    entry["frame_records"] = []
                    for frame_number in range(6):
                        frame_raw = request(f"m{fp:x},60")
                        if len(frame_raw) != 0xc0: break
                        data = bytes.fromhex(frame_raw)
                        words = [int.from_bytes(data[i:i+8],"little") for i in range(0,len(data),8)]
                        record = {"fp":hex(fp),"words":[hex(v) for v in words]}
                        # x19/x20 saves in these generated helper prologues.
                        candidate = words[2]
                        record["saved_x19_candidate_bytes"] = request(f"m{candidate:x},130")
                        entry["frame_records"].append(record)
                        next_fp = words[0]
                        if next_fp <= fp or next_fp-fp > 0x10000: break
                        fp = next_fp

                report["threads"].append(entry)
        if args.capture_submissions:
            # Resolve GPU VA using this run's nvmap allocation/map diagnostics.
            eden = (EMU / "user/log/eden_log.txt").read_text(errors="replace")
            allocations, mappings, allocation_sizes, mapping_sizes = {}, {}, {}, {}
            handle = None
            for line in eden.splitlines():
                created = re.search(r"IocCreate: handle: (\d+), size: 0X([0-9A-Fa-f]+)", line)
                if created:
                    handle = int(created[1])
                    allocation_sizes[handle] = int(created[2],16)
                allocated = re.search(r"IocAlloc: called, addr=([0-9A-Fa-f]+)", line)
                if allocated and handle is not None: allocations[handle] = int(allocated[1],16)
                mapped = re.search(r"MapBufferEx: called, flags=5, nvmap_handle=([0-9A-Fa-f]+).*offset=0X([0-9A-Fa-f]+)", line)
                if mapped and int(mapped[1],16) in allocations:
                    gpu_base = int(mapped[2],16); map_handle = int(mapped[1],16)
                    bounds = re.search(r"buffer_offset=(\d+), mapping_size=(\d+)",line)
                    buffer_offset = int(bounds[1]) if bounds else 0
                    map_size = int(bounds[2]) if bounds and int(bounds[2]) else allocation_sizes[map_handle] - buffer_offset
                    mappings[gpu_base] = allocations[map_handle] + buffer_offset
                    mapping_sizes[gpu_base] = map_size
            trace = EMU / "user/sdmc/switch/Mercenaries2/nvk-submit.log"
            lines = trace.read_text().splitlines()
            start = max(i for i,line in enumerate(lines) if line.startswith("entry=0 "))
            report["submission_captures"] = []
            for line in lines[start:]:
                entry = re.search(r"entry=(\d+).*addr=([0-9A-Fa-f]+) words=(\d+)",line)
                if not entry: continue
                gpu, count = int(entry[2],16), int(entry[3]) * 4
                if gpu not in mappings or count > min(0x100000, mapping_sizes[gpu]): continue
                cpu = mappings[gpu]
                chunks = []
                for offset in range(0,count,0x400):
                    response = request(f"m{cpu+offset:x},{min(0x400,count-offset):x}")
                    if response.startswith("E"):
                        chunks = []
                        break
                    chunks.append(bytes.fromhex(response))
                if chunks:
                    name = f"nvk-command-{int(entry[1]):03}-{gpu:X}.bin"
                    (REPORT / name).write_bytes(b"".join(chunks))
                    report["submission_captures"].append({"entry":int(entry[1]),"gpu":hex(gpu),"cpu":hex(cpu),"bytes":count,"file":name})
            # Capture QMD descriptors referenced by real compute launch packets.
            report["qmd_captures"] = []
            for capture in report["submission_captures"]:
                data = (REPORT / capture["file"]).read_bytes()
                words = struct.unpack("<" + "I"*(len(data)//4), data)
                i = 0
                while i < len(words):
                    h = words[i]; i += 1
                    mode, method, sub, count = h>>29, h&0x1fff, (h>>13)&7, (h>>16)&0x1fff
                    if mode == 4: values = [count]
                    elif mode in (1,3,5): values = words[i:i+count]; i += count
                    else: continue
                    if sub != 1 or method != 0xad or len(values) != 1: continue
                    gpu = values[0] << 8
                    candidates = [base for base in mappings if 0 <= gpu-base <= mapping_sizes[base]-0x100]
                    if not candidates: continue
                    base = max(candidates); cpu = mappings[base] + gpu-base
                    response = request(f"m{cpu:x},100")
                    if len(response) != 0x200: continue
                    name = f"nvk-qmd-{gpu:X}.bin"
                    (REPORT / name).write_bytes(bytes.fromhex(response))
                    report["qmd_captures"].append({"gpu":hex(gpu),"file":name})
            # Inspect actual graphics shader headers and instruction bytes.
            # Maxwell binds an offset into the contiguous shader heap region.
            region_hi = region_lo = None
            shader_addresses = set()
            for capture in report["submission_captures"]:
                data = (REPORT / capture["file"]).read_bytes()
                words = struct.unpack("<" + "I"*(len(data)//4), data)
                i = 0
                while i < len(words):
                    h = words[i]; i += 1
                    mode, method, sub, count = h>>29, h&0x1fff, (h>>13)&7, (h>>16)&0x1fff
                    if mode == 4: values = [count]
                    elif mode in (1,3,5): values = words[i:i+count]; i += count
                    else: continue
                    if sub != 0: continue
                    for k, value in enumerate(values):
                        m = method + (k if mode == 1 else min(k,1) if mode == 5 else 0)
                        if m == 0x582: region_hi = value
                        if m == 0x583: region_lo = value
                        if m in [0x801+j*16 for j in range(6)] and region_hi is not None and region_lo is not None:
                            shader_addresses.add(((region_hi << 32) | region_lo) + value)
            report["graphics_shader_captures"] = []
            for gpu in sorted(shader_addresses)[:32]:
                candidates = [base for base in mappings if 0 <= gpu-base <= mapping_sizes[base]-0x200]
                if not candidates: continue
                base = max(candidates); cpu = mappings[base] + gpu-base
                response = request(f"m{cpu:x},200")
                if len(response) != 0x400: continue
                name = f"nvk-shader-{gpu:X}.bin"
                (REPORT / name).write_bytes(bytes.fromhex(response))
                report["graphics_shader_captures"].append({"gpu":hex(gpu),"cpu":hex(cpu),"header_bytes":80,"file":name})
        if args.second_sample:
            request("Hg" + threads[1:].split(",")[0])
            send("c")
            time.sleep(8)
            connection.sendall(b"\x03")
            report["second_stop"] = receive()
            report["second_main_pc_raw"] = request("p20")
        print(json.dumps({k:v for k,v in report.items() if k != "threads"}, indent=2))
except Exception as error:
    report["error"] = str(error)
    print(json.dumps(report, indent=2))
finally:
    if connection:
        connection.close()
    if process and process.poll() is None:
        process.terminate()
        process.wait(timeout=5)
    CONFIG.write_bytes(original)
    if args.game_startup_diagnostic:
        if old_shader_flag is None:
            shader_flag.unlink(missing_ok=True)
        else:
            shader_flag.write_bytes(old_shader_flag)
    report["owned_emulator_exit_code"] = process.returncode if process else None
    report["nro"] = str(args.nro.resolve())
    report["nro_sha256"] = hashlib.sha256(args.nro.read_bytes()).hexdigest()
    report["game_startup_diagnostic"] = args.game_startup_diagnostic
    (REPORT / "result.json").write_text(json.dumps(report, indent=2))
    sources = [(EMU / "user/log/eden_log.txt", "eden.log")]
    if args.nro.name == "memory-probe.nro":
        sources.append((EMU / "user/sdmc/switch/Mercenaries2/memory-probe-v3.log", "guest.log"))
    for source, name in sources:
        if source.exists():
            shutil.copy2(source, REPORT / name)
