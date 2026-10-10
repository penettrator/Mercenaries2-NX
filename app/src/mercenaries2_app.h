#pragma once
#include <cstdlib>
#include <filesystem>
#include <string>
#include <rex/cvar.h>
#include <rex/filesystem.h>
#include <rex/rex_app.h>
#include <rex/runtime.h>
#include <rex/system/function_dispatcher.h>
#if defined(_WIN32)
#include <chrono>
#include <fstream>
#include <thread>
#include <sstream>
#include <rex/ui/presenter.h>
#include <rex/system/interfaces/graphics.h>
#include <rex/input/input_system.h>
#include "test_input_windows.h"
#include <rex/memory.h>
void mercenaries2_DumpDiagnosticState(uint8_t*, const std::filesystem::path&);
void mercenaries2_DumpReadOnlyImage(rex::memory::Memory*, const std::filesystem::path&);
#endif
void mercenaries2_RegisterAdditionalFunctions(rex::runtime::IModuleRegistrar*);
// guest_perf_switches.cpp (HANDOFF section 67).
void mercs2_ApplyGuestPerfSwitches();
#if defined(__SWITCH__)
#include "native/mercs2_native_system.h"
unsigned int mercenaries2_EnableSystemScreenshots();
#endif

#if defined(__SWITCH__)
REXCVAR_DECLARE(std::string, render_target_path_vulkan);
#endif

// Game logic uses PPC translations; Xbox ABI compatibility is handled separately.
class Mercenaries2App : public rex::ReXApp {
 public:
  using rex::ReXApp::ReXApp;
  static std::unique_ptr<rex::ui::WindowedApp> Create(rex::ui::WindowedAppContext& ctx) {
#if defined(__SWITCH__)
#if defined(MERCENARIES2_GPU_DRAW_TIMING)
    setenv("MERCENARIES2_GPU_DRAW_TIMING", "1", 1);
#endif
    // Emulator diagnostic only; keep native hardware on the normal NAK path.
    std::error_code ec;
    if (std::filesystem::exists("/switch/Mercenaries2/emulator_shader_test.flag", ec)) {
      const char* previous = std::getenv("NAK_DEBUG");
      std::string flags = previous ? previous : "";
      if (!flags.empty()) flags += ",";
      flags += "emu_sm50";
      setenv("NAK_DEBUG", flags.c_str(), 1);
      setenv("MESA_SHADER_CACHE_DISABLE", "true", 1);
    }
#endif
    return std::unique_ptr<Mercenaries2App>(new Mercenaries2App(ctx, "mercenaries2", PPCImageConfig));
  }
  void OnPostLoadXexImage() override {
    mercenaries2_RegisterAdditionalFunctions(runtime()->function_dispatcher());
#if defined(_WIN32)
    if (std::getenv("MERCENARIES2_TEST_DUMP_IMAGE")) {
      if (const char* folder = std::getenv("MERCENARIES2_TEST_FRAME_DIR"))
        mercenaries2_DumpReadOnlyImage(runtime()->memory(), folder);
    }
#endif
  }
#if defined(__SWITCH__)
  void OnPreSetup(rex::RuntimeConfig& config) override {
    mercs2_ApplyGuestPerfSwitches();
    // Native renderer (src/native, project8-sw): replaces the SDK's emulated GPU entirely
    // when mercs2_renderer = "native". Default stays the FSI emulation below.
    if (mercs2::native::Enabled()) {
      config.graphics = mercs2::native::CreateGraphicsSystem();
      REXLOG_INFO("Mercenaries 2 Switch renderer: native");
    }
    // Config/environment/command-line values are already loaded at this point.
    // Only replace the SDK default: FBO gave red output and costly transfers
    // on this title; FSI plus corrected resolve kernels is hardware verified.
    if (rex::cvar::GetFlagSource("render_target_path_vulkan") ==
        rex::cvar::Source::kDefault && REXCVAR_GET(render_target_path_vulkan).empty()) {
      REXCVAR_SET(render_target_path_vulkan, std::string("fsi"));
    }
    REXLOG_INFO("Mercenaries 2 Switch render target path: {}",
                REXCVAR_GET(render_target_path_vulkan));
    // 0 = Capture button enabled; 0xFFFFFFFF = not an Application (album launch).
    REXLOG_INFO("Mercenaries 2 Switch screenshot permission: result 0x{:08X}",
                mercenaries2_EnableSystemScreenshots());
  }
#endif
#if defined(_WIN32)
  void OnPreSetup(rex::RuntimeConfig& config) override {
    mercs2_ApplyGuestPerfSwitches();
    if (!std::getenv("MERCENARIES2_TEST_SCRIPTED_INPUT")) return;
    config.input_factory = [](bool) -> std::unique_ptr<rex::system::IInputSystem> {
      auto input = std::make_unique<rex::input::InputSystem>(nullptr);
      auto driver = std::make_unique<MercenariesTestInput>();
      if (driver->Setup() != 0) REX_FATAL("Invalid scripted input file");
      input->AddDriver(std::move(driver));
      input->SetDeviceAssignment(std::make_unique<rex::input::SlotAssignment>());
      return input;
    };
  }
  // Opt-in test output: capture the game's own render target, not the desktop.
  void OnPostLaunchModule(rex::system::XThread*) override {
    const char* supplied = std::getenv("MERCENARIES2_TEST_FRAME_DIR");
    if (!supplied || !*supplied) return;
    const std::filesystem::path folder = supplied;
    std::filesystem::create_directories(folder);
    test_capture_ = std::jthread([this, folder](std::stop_token stop) {
      const auto start = std::chrono::steady_clock::now();
      std::vector<int> capture_seconds{10, 30, 55, 90, 110};
      if (const char* supplied = std::getenv("MERCENARIES2_TEST_CAPTURE_SECONDS")) {
        capture_seconds.clear();
        std::istringstream input(supplied);
        int seconds;
        while (input >> seconds) capture_seconds.push_back(seconds);
      }
      for (const int seconds : capture_seconds) {
        while (!stop.stop_requested() &&
               std::chrono::steady_clock::now() - start < std::chrono::seconds(seconds))
          std::this_thread::sleep_for(std::chrono::milliseconds(100));
        if (stop.stop_requested()) return;
        mercenaries2_DumpDiagnosticState(runtime()->memory()->virtual_membase(),
          folder / ("guest-state-" + std::to_string(seconds) + ".txt"));
        auto* graphics = runtime()->graphics_system();
        rex::ui::RawImage image;
        const bool captured = graphics && graphics->presenter() &&
                              graphics->presenter()->CaptureGuestOutput(image);
        std::ofstream status(folder / ("frame-" + std::to_string(seconds) + ".txt"));
        status << "captured=" << captured << " width=" << image.width
               << " height=" << image.height << "\n";
        if (!captured || !image.width || !image.height) continue;
        std::ofstream out(folder / ("frame-" + std::to_string(seconds) + ".ppm"), std::ios::binary);
        out << "P6\n" << image.width << " " << image.height << "\n255\n";
        for (uint32_t y = 0; y < image.height; ++y)
          for (uint32_t x = 0; x < image.width; ++x)
            out.write(reinterpret_cast<const char*>(image.data.data() + y * image.stride + x * 4), 3);
      }
    });
  }
  void OnShutdown() override {
    if (test_capture_.joinable()) {
      test_capture_.request_stop();
      test_capture_.join();
    }
  }
#endif
  void OnPostInitLogging() override {
#if defined(_WIN32)
    if (std::getenv("MERCENARIES2_TEST_KERNEL_TRACE")) {
      rex::cvar::SetFlagByName("log_noisy", "true");
      rex::SetCategoryLevel(rex::log::krnl(), spdlog::level::trace);
      rex::SetCategoryLevel(rex::log::sys(), spdlog::level::debug);
      rex::SetCategoryLevel(rex::log::fs(), spdlog::level::debug);
      rex::SetRootLevel(rex::log::gpu(), spdlog::level::warn);
    }
#endif
    if (!rex::cvar::HasNonDefaultValue("gpu_plugin")) {
      rex::cvar::SetFlagByName("gpu_plugin", "xenos");
    }
  }
  void OnConfigurePaths(rex::PathConfig& paths) override {
    if (!paths.game_data_root.empty()) return;
    if (const char* supplied = std::getenv("MERCENARIES2_GAME_ROOT")) {
      paths.game_data_root = supplied;
      return;
    }
    std::error_code ec;
    const auto extracted = rex::filesystem::GetExecutableFolder() / "game_root";
    if (std::filesystem::is_directory(extracted, ec)) {
      paths.game_data_root = extracted;
      return;
    }
#if defined(__SWITCH__)
    // Some NRO loaders do not supply argv[0]. Use the packaged SD location
    // only when data beside the executable could not be found.
    const std::filesystem::path packaged = "/switch/Mercenaries2/game_root";
    ec.clear();
    if (std::filesystem::is_directory(packaged, ec)) paths.game_data_root = packaged;
#endif
  }
#if defined(_WIN32)
 private:
  std::jthread test_capture_;
#endif
};
