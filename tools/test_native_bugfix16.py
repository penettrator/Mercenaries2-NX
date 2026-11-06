"""Run the production stream completion/routing and read-only timing probe with mocks."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
out = root / 'out/bugfix-16/host-tests'
out.mkdir(parents=True, exist_ok=True)
textures = (root / 'app/src/native/native_textures.cpp').read_text()
system = (root / 'app/src/native/mercs2_native_system.cpp').read_text()
wait = textures[textures.index('  bool WaitForStream(StreamJob& job) {'):
                textures.index('  std::deque<std::shared_ptr<StreamJob>> stream_jobs;')]
route = textures[textures.index('    if (im.demand_wait && !im.WaitForStream(job))'):
                 textures.index('    if (!job.ok) {', textures.index('    if (im.demand_wait && !im.WaitForStream(job))'))]
enqueue = textures[textures.index('      im.stream_cv.notify_one();'):
                   textures.index('      ++stats_.uploads;', textures.index('      im.stream_cv.notify_one();'))]
timing = system[system.index('  void ReportGameTiming(Clock::time_point now) {'):
                system.index('  void ReportSlowFrame() {')]
code = r'''
#include <algorithm>
#include <atomic>
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <future>
#include <memory>
#include <mutex>
#include <thread>
using namespace std::chrono_literals;
using Clock=std::chrono::steady_clock;
struct StreamJob { std::atomic<bool> done{false}; bool ok=false; unsigned pixels=0; };
struct Worker {
 std::mutex stream_mutex;
 std::condition_variable stream_cv,stream_done_cv;
 bool stream_stop=false,demand_wait=false;
 uint64_t demand_waits=0,demand_wait_ns=0,demand_wait_max_ns=0;
 WAIT
 void Stop(){ {std::lock_guard lock(stream_mutex);stream_stop=true;}stream_done_cv.notify_all(); }
};
struct Cache {
 Worker im; StreamJob job; unsigned pending=0,draws=0,enqueues=0,depth=0,peak_depth=0;
 unsigned GetViewUncached(int fetch=0,int dimension=0,int is_signed=0,int upload=0,unsigned null_view=0){
  (void)fetch;(void)dimension;(void)is_signed;(void)upload;
  ++depth;peak_depth=std::max(peak_depth,depth);
  struct Pop {unsigned& d;~Pop(){--d;}}pop{depth};
  if(enqueues){
   struct Stats {unsigned& pending;}stats_{pending};
   ENQUEUE_ROUTE
   if(!job.ok)return null_view;
   assert(job.pixels==0x12345678);++draws;return job.pixels;
  }
  ++enqueues;
  ENQUEUE_WAIT
  return null_view;
 }
};
namespace rex {
namespace memory {enum class PageAccess{kNoAccess,kReadOnly};template<class T>T load_and_swap(const void* p){T t;std::memcpy(&t,p,sizeof t);return __builtin_bswap32(t);}}
namespace chrono {struct Clock {static inline uint64_t ticks=0,hz=50000000;static uint64_t QueryGuestTickCount(){return ticks;}static uint64_t guest_tick_frequency(){return hz;}};}
}
struct Memory {
 uint32_t object=__builtin_bswap32(0x83300000u),scale=__builtin_bswap32(0x3f800000u);bool accessible=true;
 struct Heap {Memory& m;rex::memory::PageAccess QueryRangeAccess(uint32_t a,uint32_t z){return m.accessible&&a<=z?rex::memory::PageAccess::kReadOnly:rex::memory::PageAccess::kNoAccess;}}heap{*this};
 Heap* LookupHeap(uint32_t a){return a==0x83134130u||a==0x83300000u?&heap:nullptr;}
 const void* TranslateVirtual(uint32_t a){assert(accessible);if(a==0x83134130u)return &object;assert(a==0x8330003cu);return &scale;}
};
static unsigned reports=0;static double reported_host=0,reported_guest=0;static float reported_scale=0;static uint32_t reported_object=0;
static void Record(const char*,double h,double g,uint64_t frequency,uint64_t,uint64_t,uint32_t object,float scale,uint32_t,uint32_t){
 ++reports;reported_host=h;reported_guest=g;reported_scale=scale;reported_object=object;assert(frequency==50000000);
}
#define REXLOG_WARN Record
#define REXCVAR_GET(x) 2u
struct Probe {
 bool game_timing_diagnostics_=false;Clock::time_point timing_previous_{};
 uint64_t timing_ticks_=0,timing_vblanks_=0,timing_swaps_=0,swaps_=0;
 std::atomic<uint64_t> vblanks_{0};Memory* memory_=nullptr;
 TIMING
};
int main(){
 // The original route still returns empty while a job is pending; demand route
 // waits for exactly the same job. Completion can occur before/after the wait.
 for(unsigned run=0;run<1000;++run){
  Cache c;c.im.demand_wait=true;
  auto result=std::async(std::launch::async,[&]{return c.GetViewUncached();});
  if(run&1)std::this_thread::yield();
  c.job.pixels=0x12345678;c.job.ok=true;c.im.PublishStream(c.job);
  assert(result.wait_for(2s)==std::future_status::ready);assert(result.get()==0x12345678);
  assert(c.enqueues==1&&c.draws==1&&c.pending==0&&c.peak_depth==2);
 }
 {Cache c;assert(c.GetViewUncached()==0);assert(c.GetViewUncached()==0&&c.pending==1&&c.draws==0);}
 {Cache c;c.im.demand_wait=true;c.im.PublishStream(c.job);assert(c.GetViewUncached()==0&&c.draws==0);}
 {Cache c;c.im.demand_wait=true;auto f=std::async(std::launch::async,[&]{return c.GetViewUncached();});c.im.Stop();assert(f.wait_for(2s)==std::future_status::ready&&f.get()==0);assert(c.draws==0);}
 // A publication wakes every waiter and acquire observes the completed payload.
 {Worker w;StreamJob j;auto one=std::async(std::launch::async,[&]{return w.WaitForStream(j);});
  // Production has only one consumer; keep counters single-writer here.
  j.pixels=0x12345678;j.ok=true;w.PublishStream(j);assert(one.get()&&j.ok&&j.pixels==0x12345678);}
 Memory mem;Probe p;p.memory_=&mem;
 auto at=[](int sec){return Clock::time_point(std::chrono::seconds(sec));};
 p.ReportGameTiming(at(1));assert(reports==0);p.game_timing_diagnostics_=true;
 p.ReportGameTiming(at(1));rex::chrono::Clock::ticks=250000000;p.ReportGameTiming(at(5));assert(reports==0);
 p.ReportGameTiming(at(6));assert(reports==1&&reported_host==5&&reported_guest==5&&reported_scale==1&&reported_object==0x83300000);
 mem.scale=__builtin_bswap32(0x3f000000u);rex::chrono::Clock::ticks+=250000000;p.ReportGameTiming(at(11));assert(reported_scale==0.5f);
 mem.object=0;p.ReportGameTiming(at(16));assert(reported_object==0);
 mem.object=__builtin_bswap32(0xfffffff0u);p.ReportGameTiming(at(21));assert(reported_object==0);
 mem.accessible=false;p.ReportGameTiming(at(26));assert(reported_object==0);
 puts("PASS: production demand routing/completion 1000 interleavings, OFF/failure/shutdown; production timing OFF/5s/1.0/0.5/unmapped/overflow; no guest writes");
}
'''
code = code.replace('\n WAIT\n', '\n'+wait+'\n').replace('ENQUEUE_ROUTE',route).replace('ENQUEUE_WAIT',enqueue).replace('TIMING',timing)
# The production pending branch references the existing diagnostic color view;
# the host test keeps the usual null color, independent of readiness semantics.
code=code.replace('(im.null_texture_probe && null_view == im.null_views[0]) ? im.null_views[3] : null_view','null_view')
cpp=out/'demand-timing.cpp';cpp.write_text(code)
exe=out/'demand-timing'
subprocess.run(['g++','-std=c++23','-O2','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-pthread',str(cpp),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True,timeout=30)
