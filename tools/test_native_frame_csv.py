#!/usr/bin/env python3
"""Exercise the actual diagnostic capture code with fake HID/time and real asynchronous CSV IO."""
from pathlib import Path
import csv
import argparse
import subprocess

args_parser=argparse.ArgumentParser();args_parser.add_argument("--ring-only",action="store_true");args=args_parser.parse_args()
root = Path(__file__).resolve().parents[1]
system = (root / 'app/src/native/mercs2_native_system.cpp').read_text()
start = system.index('  struct FrameSample {')
end = system.index('\n#endif\n\n  // A frame longer', start)
capture = system[start:end]
header = (root / 'app/src/native/native_renderer.h').read_text()
start = header.index('struct RendererStats {')
end = header.index('\n};', start) + 3
stats = header[start:end]
out = root / ('out/perf-pass-15/capture-test' if args.ring_only else 'out/perf-pass-1/capture-test')
out.mkdir(parents=True, exist_ok=True)
prefix = r'''
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <string>
#include <thread>
#include <vector>
#define MERCENARIES2_FRAME_CSV 1
#define MERCENARIES2_DESCRIPTOR_BATCH 1
#define MERCENARIES2_LEAN_DRAW_TIMERS 1
using Clock=std::chrono::steady_clock;
static unsigned errors=0;
#define REXLOG_WARN(...) ((void)0)
#define REXLOG_ERROR(...) (++errors)
static uint64_t held=0;
struct HidNpadHandheldState {uint64_t buttons=0;};
using HidNpadFullKeyState=HidNpadHandheldState;
using HidNpadJoyDualState=HidNpadHandheldState;
constexpr unsigned HidNpadIdType_Handheld=0,HidNpadIdType_No1=1;
constexpr uint64_t HidNpadButton_StickL=1,HidNpadButton_StickR=2;
int hidGetNpadStatesHandheld(unsigned,HidNpadHandheldState* s,unsigned){s->buttons=held;return 1;}
int hidGetNpadStatesFullKey(unsigned,HidNpadFullKeyState*,unsigned){return 0;}
int hidGetNpadStatesJoyDual(unsigned,HidNpadJoyDualState*,unsigned){return 0;}
const char* RexSwitchLogDir(){return "out/perf-pass-1/capture-test/";}
'''
if args.ring_only:
    prefix=prefix.replace('#define MERCENARIES2_FRAME_CSV 1','#define MERCENARIES2_FRAME_CSV 0\n#define MERCENARIES2_LOOKUP_FRAME_CSV 1\n#define MERCENARIES2_NATIVE_TABLE_LOOKUP 1').replace('out/perf-pass-1/capture-test/','out/perf-pass-15/capture-test/')
text = prefix + stats + '\nstruct TestCapture {\n' + capture + '\n};\n'
text += r'''
int main(){
 TestCapture test;RendererStats s;const auto now=Clock::now();
 // No chord: no allocation, capture, writer or SD output.
 test.CaptureFrame(now,16,s,1,2,3);assert(!test.frame_capture_ && !test.frame_writer_.joinable());
 for(unsigned pass=0;pass<2;++pass){
  const auto begin=now+std::chrono::seconds(40*pass);
  held=3;test.CaptureFrame(begin,16,s,1,2,3);
  assert(test.frame_capture_ && test.frame_samples_.empty());
  assert(test.frame_capture_index_==pass+1);
  for(unsigned i=1;i<=15;++i){
   held=i==1 ? 3 : 0; // holding the start chord must not start a second capture
   s.draws+=7;
#if MERCENARIES2_FRAME_CSV
   s.descriptor_bind_calls+=1;s.descriptor_bind_calls_unbatched+=4;
#endif
   test.CaptureFrame(begin+std::chrono::seconds(2*i),2000,s,11,12,13);
  }
  assert(!test.frame_capture_ && test.frame_writer_.joinable());
  test.frame_writer_.join();assert(!test.frame_writer_busy_.load());
 }
 test.FinishFrameCapture();assert(!errors);
 std::puts("PASS actual capture: no chord/no writer, edge-trigger, 30 s stop, two scenes, async save and join");
}
'''
cpp = out / 'frame_csv_test.cpp'
cpp.write_text(text)
exe = out / 'frame_csv_test'
before = set(out.glob('perf_*.csv'))
subprocess.run(['g++', '-std=c++20', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', '-pthread', str(cpp), '-o', str(exe)], check=True,
               cwd=root)
subprocess.run([str(exe)], cwd=root, check=True)
files = set(out.glob('perf_*.csv')) - before
assert len(files) == 2
scenes = set()
for path in files:
    with path.open(newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 15
    assert all(None not in row and None not in row.values() for row in rows)
    assert float(rows[-1]['t_s']) == 30
    assert all(float(row['frame_ms']) == 2000 for row in rows)
    assert all(row['variant'] == ('native_lookup' if args.ring_only else 'both') and row['descriptor_calls'] == ('0' if args.ring_only else '1') and
               row['descriptor_calls_unbatched'] == ('0' if args.ring_only else '4') and
               row['draw_timer_reads_saved_min'] == '14' for row in rows)
    scenes.add(rows[0]['scenario'])
assert scenes == {'driving', 'combat'}
print('PASS CSV schema, per-frame deltas, timer count lower bound and driving/combat labels')
