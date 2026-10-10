"""Run a bounded NRO startup check in the project-local portable Eden."""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, subprocess, time
from contextlib import contextmanager
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--label", required=True)
parser.add_argument("--probe-compat", action="store_true")
parser.add_argument("--game-shader-compat", action="store_true")
parser.add_argument("--probe-case", choices=["add", "multiply", "both", "high-unsigned", "high-signed", "byte-mix", "signed-byte", "byte-mask", "byte-sign-shift", "byte-mix-masks", "high-unsigned-compile", "high-submit-only", "high-unsigned-once"])
parser.add_argument("--nro", type=Path, default=ROOT / "out/nx/mercenaries2.nro")
parser.add_argument("--seconds", type=int, default=45)
parser.add_argument("--gpu-accuracy", choices=["normal", "high", "extreme"])
parser.add_argument("--backend", choices=["vulkan", "opengl"])
parser.add_argument("--no-sync-memory", action="store_true")
parser.add_argument("--sync-memory", action="store_true")
parser.add_argument("--enable-compute-pipelines", action="store_true")
parser.add_argument("--interpret-macros", action="store_true")
parser.add_argument("--disable-macro-jit", action="store_true")
parser.add_argument("--disable-macro-hle", action="store_true")
args = parser.parse_args()
if args.sync_memory and args.no_sync_memory: parser.error("Memory sync overrides are mutually exclusive")
if not args.label.replace("-", "").replace("_", "").isalnum():
    parser.error("label must contain only letters, digits, hyphens or underscores")
if not 1 <= args.seconds <= 120:
    parser.error("seconds must be in 1..120")
root = ROOT / "tools/bin/eden-0.2.1"
user = root / "user"
source = ROOT / "assets/game_root"
dest = user / "sdmc/switch/Mercenaries2"
reportdir = ROOT / "out/emulator-check" / args.label
reportdir.mkdir(parents=True, exist_ok=False)
for name in ["log", "nand", "cache", "keys", "config", "load", "dump"]:
    (user / name).mkdir(parents=True, exist_ok=True)
for p in source.rglob("*"):
    if p.is_file():
        target = dest / "game_root" / p.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            os.link(p, target)
nro = args.nro.resolve()
if not nro.is_relative_to(ROOT) or not nro.is_file():
    parser.error("NRO must be an existing file inside this project")
target = dest / nro.name
# An earlier package may have used a hard link: detach it before writing.
if target.exists() and target.stat().st_nlink > 1:
    target.unlink()
shutil.copy2(nro, target)
si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
si.wShowWindow = 0
started_wall = time.time()
@contextmanager
def renderer_override():
    config = user / "config/sdl2-config.ini"
    if not args.backend and not args.no_sync_memory and not args.interpret_macros and not args.disable_macro_jit and not args.disable_macro_hle and not args.sync_memory and not args.enable_compute_pipelines and not args.gpu_accuracy:
        yield
        return
    original = config.read_bytes()
    text = original.decode()
    if args.backend:
        value = 1 if args.backend == "vulkan" else 0
        text, count = re.subn(r"(?m)^backend=\d+", "backend=" + str(value), text)
        if count != 1:
            raise RuntimeError("Unexpected renderer configuration")
        text = re.sub(r"(?m)^backend\\default=true", r"backend\\default=false", text)
    if args.gpu_accuracy:
        value = {"normal":0,"high":1,"extreme":2}[args.gpu_accuracy]
        text, count = re.subn(r"(?m)^gpu_accuracy=\d+", "gpu_accuracy="+str(value), text)
        if count != 1: raise RuntimeError("Unexpected GPU accuracy configuration")
        text = re.sub(r"(?m)^gpu_accuracy\\default=true", r"gpu_accuracy\\default=false", text)
    if args.no_sync_memory:
        text, count = re.subn(r"(?m)^sync_memory_operations=(true|false)", "sync_memory_operations=false", text)
        if count != 1: raise RuntimeError("Unexpected memory sync configuration")
        text = re.sub(r"(?m)^sync_memory_operations\\default=true", r"sync_memory_operations\\default=false", text)
    for key, enabled in [("sync_memory_operations", args.sync_memory), ("enable_compute_pipelines", args.enable_compute_pipelines)]:
        if enabled:
            text, count = re.subn(r"(?m)^" + key + "=(true|false)", key + "=true", text)
            if count != 1: raise RuntimeError("Unexpected renderer configuration for " + key)
            text = re.sub(r"(?m)^" + key + r"\\default=true", key + r"\\default=false", text)
    if args.interpret_macros or args.disable_macro_jit or args.disable_macro_hle:
        keys = [key for key, disable in [("disable_macro_jit", args.interpret_macros or args.disable_macro_jit), ("disable_macro_hle", args.interpret_macros or args.disable_macro_hle)] if disable]
        for key in keys:
            text, count = re.subn(r"(?m)^" + key + "=(true|false)", key + "=true", text)
            if count != 1: raise RuntimeError("Unexpected macro configuration")
            text = re.sub(r"(?m)^" + key + r"\\default=true", key + r"\\default=false", text)
    try:
        config.write_text(text)
        yield
    finally:
        config.write_bytes(original)

@contextmanager
def probe_case_override():
    game_flag = dest / "emulator_shader_test.flag"
    old_game_flag = game_flag.read_bytes() if game_flag.exists() else None
    if args.game_shader_compat:
        if nro.name != "mercenaries2.nro": raise RuntimeError("Game shader compatibility applies only to Mercenaries 2")
        game_flag.write_text("1")
    compatibility = dest / "nvk-compute-probe-compat.flag"
    old_compatibility = compatibility.read_bytes() if compatibility.exists() else None
    if args.probe_compat:
        if nro.name != "nvk-compute-probe.nro": raise RuntimeError("Probe compatibility applies only to the compute probe")
        compatibility.write_text("1")
    selection = dest / "nvk-compute-probe-case.txt"
    previous = selection.read_bytes() if selection.exists() else None
    if args.probe_case:
        if nro.name != "nvk-compute-probe.nro": raise RuntimeError("Probe case applies only to the compute probe")
        selection.write_text(args.probe_case)
    try:
        yield
    finally:
        if args.game_shader_compat:
            if old_game_flag is None: game_flag.unlink()
            else: game_flag.write_bytes(old_game_flag)
        if args.probe_compat:
            if old_compatibility is None: compatibility.unlink()
            else: compatibility.write_bytes(old_compatibility)
        if args.probe_case:
            if previous is None: selection.unlink()
            else: selection.write_bytes(previous)

with renderer_override(), probe_case_override():
    with (reportdir / "cli.log").open("w", encoding="utf-8") as out:
        process = subprocess.Popen([str(root / "eden-cli.exe"), str(target)],
            cwd=root, stdout=out, stderr=subprocess.STDOUT, startupinfo=si)
        started = time.monotonic()
        timed_out = False
        try:
            process.wait(timeout=args.seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            process.wait(timeout=10)
report = {"emulator": "Eden 0.2.1 MSVC amd64", "renderer_override": args.backend, "gpu_accuracy_override": args.gpu_accuracy, "no_sync_memory_diagnostic": args.no_sync_memory, "sync_memory_diagnostic": args.sync_memory, "compute_pipelines_enabled_diagnostic": args.enable_compute_pipelines, "macro_interpreter_diagnostic": args.interpret_macros, "disable_macro_jit": args.disable_macro_jit, "disable_macro_hle": args.disable_macro_hle, "exit_code": process.returncode,
    "seconds": round(time.monotonic()-started, 2),
    "terminated_after_timeout": timed_out,
    "nro_sha256": hashlib.sha256(nro.read_bytes()).hexdigest(), "nro": str(nro), "probe_case": args.probe_case, "probe_compatibility": args.probe_compat, "game_shader_compatibility": args.game_shader_compat,
    "console_launch_verified": False, "menu_or_gameplay_verified": False}
log = user / "log/eden_log.txt"
if log.exists():
    shutil.copy2(log, reportdir / "eden.log")
    eden_lines = log.read_text(errors="replace").splitlines()
    report["cpu_memory_abort_lines"] = [line for line in eden_lines if "Stopping execution due to unmapped memory access" in line]
    report["cpu_memory_abort_detected"] = bool(report["cpu_memory_abort_lines"])
    decode_errors = [line for line in eden_lines if "assert Invalid insn" in line]
    report["shader_decode_error_count"] = len(decode_errors)
    report["shader_decode_error_lines"] = decode_errors[:40]
    report["graphics_pipeline_count"] = sum("<Info>" in line and "CreateGraphicsPipeline:" in line for line in eden_lines)
    report["pipeline_translation_error_lines"] = [line for line in eden_lines if "<Error>" in line and ("CreateGraphicsPipeline:" in line or "CreateComputePipeline:" in line)]
    report["pipeline_count_meaning"] = "Info-level pipeline translation attempts; successful rendering is not implied"
    report["compute_pipeline_count"] = sum("<Info>" in line and "CreateComputePipeline:" in line for line in eden_lines)
guest_logs = sorted((user / "sdmc/logs").glob("*.log"), key=lambda p: p.stat().st_mtime)
if guest_logs and guest_logs[-1].stat().st_mtime >= started_wall - 2:
    shutil.copy2(guest_logs[-1], reportdir / "rex.log")
    lines = guest_logs[-1].read_text(errors="replace").splitlines()
    report["guest_errors"] = [line for line in lines if "[error]" in line or "[critical]" in line][-20:]
    print("\n".join(lines[-18:]))
# Preserve fresh failed command streams for endian / packet-boundary diagnosis.
for diagnostic in list(dest.glob("bad-indirect-*.bin")) + list(dest.glob("emitter-*.bin")) + list(dest.glob("device-*.bin")) + list(dest.glob("nvk-entry-*.bin")):
    if diagnostic.stat().st_mtime >= started_wall - 2:
        shutil.copy2(diagnostic, reportdir / diagnostic.name)
# Preserve fresh platform diagnostics; stale logs from earlier runs are excluded.
for name in ["gpu-host-memory.log", "zpd-memory.log", "nvk-compute-probe.log", "nvk-probe-compiler.log", "thread_create.log", "rex_profile.log", "encoder-trace.log", "emitter-trace.log", "device-trace.log", "nvk-submit.log"]:
    for diagnostic in (user / "sdmc").rglob(name):
        if diagnostic.stat().st_mtime >= started_wall - 2:
            shutil.copy2(diagnostic, reportdir / name)
probe_log = reportdir / "nvk-compute-probe.log"
if nro.name == "nvk-compute-probe.nro":
    expected_cases = 2 if args.probe_case in (None, "both") else 1
    report["probe_arithmetic_case_verified"] = probe_log.exists() and probe_log.read_text(errors="replace").count("CASE_PASS=1") == expected_cases
    report["probe_execution_verified"] = probe_log.exists() and "ALL_PASS=1" in probe_log.read_text()
(reportdir / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
