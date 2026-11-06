// Mercenaries 2 (Switch): GEN-only, game-owned and session-specific profiles.
// Ported 2026-10-16 from Prototype 2 (project/src/switch_pgo.cpp, WORKLOG #126/#127; guide "Практика Prototype 2").
// Every 3 minutes a helper thread dumps the counters (libgcov merges them into the files already there) and resets
// them, so any play session of 3+ minutes leaves a usable profile even though the game is never exited cleanly.
// Compiled to nothing unless MERCENARIES2_PGO=GEN. A GEN build is slow (counters) and only for collecting data.
#if defined(MERCENARIES2_PGO_GEN) && MERCENARIES2_PGO_GEN
#include <chrono>
#include <thread>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <dirent.h>
#include <sys/stat.h>
#include <string>
#include <rex/logging.h>

extern "C" void __gcov_dump(void);
extern "C" void __gcov_reset(void);

namespace {
constexpr const char* kDirectory = MERCENARIES2_PGO_DEVICE_DIR;
struct ProfileFiles {
  uint64_t files = 0, bytes = 0;
};
ProfileFiles CountProfileFiles(const char* directory) {
  ProfileFiles result;
  DIR* dir = opendir(directory);
  if (!dir) return result;
  while (auto* entry = readdir(dir)) {
    const size_t length = std::strlen(entry->d_name);
    if (length < 5 || std::strcmp(entry->d_name + length - 5, ".gcda")) continue;
    const std::string path = std::string(directory) + "/" + entry->d_name;
    struct stat info{};
    if (!stat(path.c_str(), &info) && S_ISREG(info.st_mode) && info.st_size >= 16) {
      ++result.files;
      result.bytes += uint64_t(info.st_size);
    }
  }
  closedir(dir);
  return result;
}
struct PgoDumper {
  PgoDumper() {
    // libnx: std::thread::detach() throws (pthread_detach unsupported); the thread is simply never joined.
    new std::thread([] {
      for (int i = 1;; ++i) {
        std::this_thread::sleep_for(std::chrono::minutes(3));
        if ((mkdir("sdmc:/switch/Mercenaries2/pgo", 0777) && errno != EEXIST) ||
            (mkdir(kDirectory, 0777) && errno != EEXIST)) {
          REXLOG_ERROR("[mercs2-pgo] cannot create {} errno={}; counters retained", kDirectory, errno);
          continue;
        }
        const auto begin = std::chrono::steady_clock::now();
        __gcov_dump();
        const auto files = CountProfileFiles(kDirectory);
        if (files.files) __gcov_reset();
        // dump() has no success return. File presence is evidence, not a guarantee
        // that every counter was written; validate all expected gcda after pull.
        REXLOG_WARN("[mercs2-pgo] dump {} finished path={} files={} bytes={} reset={} in {} ms", i,
                    kDirectory, files.files, files.bytes, bool(files.files),
                    std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - begin)
                        .count());
      }
    });
  }
};
PgoDumper g_dumper;
}  // namespace
#endif
