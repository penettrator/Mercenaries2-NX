// Startup-only extension included in place of an existing blank line.
// Preserve original renderer/EOF source locations for strict existing PGO.
#if defined(__GNUC__)
__attribute__((no_profile_instrument_function))
#endif
void Renderer::WaitForKnownPipelines() {
  Impl& im = *impl_;
  if (!im.prewarm_thread.joinable()) return;
  im.prewarm_thread.join();
  im.DrainPrewarmed();
}
