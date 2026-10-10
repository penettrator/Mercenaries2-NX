"""Bounded Windows integration test with opt-in guest render-target captures."""
from pathlib import Path
import argparse, json, os, subprocess, time
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
parser.add_argument('--seconds', type=int, default=65)
parser.add_argument('--capture-seconds', default='10,30,55,90,110')
parser.add_argument('--scripted-input', action='store_true')
parser.add_argument('--input-script', type=Path)
parser.add_argument('--live-input-file', type=Path)
parser.add_argument('--headless-dialogs', action='store_true')
parser.add_argument('--kernel-trace', action='store_true')
parser.add_argument('--dump-rdata', action='store_true')
parser.add_argument('--runtime-arg', action='append', default=[], help='Additional runtime option, use --runtime-arg=--name=value')
parser.add_argument('--log-level', choices=['info', 'debug', 'trace'], default='info')
args = parser.parse_args()
if not args.label.replace('-', '').replace('_', '').isalnum() or not 1 <= args.seconds <= 1800:
    parser.error('Invalid label or duration')
folder = ROOT / 'out/runtime-windows' / args.label
folder.mkdir(exist_ok=False)
log = folder / 'runtime.log'
env = os.environ.copy()
env['MERCENARIES2_TEST_FRAME_DIR'] = str(folder)
capture_seconds = [int(value) for value in args.capture_seconds.split(',')]
if capture_seconds != sorted(set(capture_seconds)) or any(not 1 <= value <= 1800 for value in capture_seconds):
    parser.error('Capture times must be increasing unique seconds in 1..1800')
env['MERCENARIES2_TEST_CAPTURE_SECONDS'] = ' '.join(map(str, capture_seconds))
if args.live_input_file:
    env['MERCENARIES2_TEST_LIVE_INPUT_FILE'] = str(args.live_input_file.resolve())
if args.dump_rdata:
    env['MERCENARIES2_TEST_DUMP_IMAGE'] = '1'
if args.kernel_trace:
    env['MERCENARIES2_TEST_KERNEL_TRACE'] = '1'
if args.input_script:
    import shutil
    shutil.copy2(args.input_script, folder / 'input-script.txt')
    env['MERCENARIES2_TEST_INPUT_FILE'] = str(folder / 'input-script.txt')
if args.scripted_input:
    env['MERCENARIES2_TEST_SCRIPTED_INPUT'] = '1'
else:
    env.pop('MERCENARIES2_TEST_SCRIPTED_INPUT', None)
si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
si.wShowWindow = 0
command = [str(ROOT / 'out/windows/mercenaries2.exe'),
    f'--game_data_root={ROOT / "assets/game_root"}',
    f'--user_data_root={folder / "user"}',
    f'--cache_root={ROOT / "out/runtime-windows/cache"}',
    f'--log_file={log}', f'--log_level={args.log_level}', '--log_flush_interval=1']
if args.headless_dialogs:
    command.append('--headless=true')
command.extend(args.runtime_arg)
process = subprocess.Popen(command, cwd=ROOT / 'out/windows', env=env, startupinfo=si)
started = time.monotonic()
timed_out = False
try:
    process.wait(timeout=args.seconds)
except subprocess.TimeoutExpired:
    timed_out = True
    process.terminate()
    process.wait(timeout=10)
report = {'exit_code': process.returncode, 'seconds': round(time.monotonic()-started, 2),
    'terminated_after_timeout': timed_out, 'scripted_input': args.scripted_input, 'headless_dialogs': args.headless_dialogs,
    'frame_reports': [p.read_text() for p in sorted(folder.glob('frame-*.txt'))],
    'visual_review_required': True, 'runtime_args': args.runtime_arg}
if log.exists():
    lines = log.read_text(errors='replace').splitlines()
    report['fatal_errors'] = []
    for part in sorted(folder.glob('runtime*.log')):
        with part.open(errors='replace') as stream:
            for line in stream:
                if '[FATAL]' in line or '[critical]' in line:
                    report['fatal_errors'].append(line[:1000].rstrip())
    print('\n'.join(s[:500] for s in lines[-12:]))
(folder / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
