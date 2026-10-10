Empty FidelityFX "SDK root" for the Switch build (HANDOFF B:103).

The SDK's rexui target defines REX_HAS_FIDELITYFX_SDK when REXGLUE_FIDELITYFX_SOURCE_DIR/sdk/include
exists. That define enables the presenter's spatial effects - CAS and FSR 1 (EASU + RCAS) - whose
shaders are already precompiled in reference/masseffect-nx/sdk/src/ui/shaders/vulkan_spirv (AMD
FidelityFX, MIT). The external ffx_api headers are only included under REX_HAS_FIDELITYFX_RUNTIME
(temporal FSR 2/3), which stays off, so no header from here is needed.

Configure: cmake ... -DREXGLUE_FIDELITYFX_SOURCE_DIR=/work/tools/ffx_spatial_only
Use: mercenaries2.toml  present_effect = "fsr"  (or "cas"; "bilinear" = previous behaviour)
