# Changelog

## [0.2.0a1] - 2026-09-24

### Added
- WQIR v0.2 typed representation envelope (8 representation kinds).
- RepGraph v0.2 DAG with cycle detection and validation.
- Plugin SDK with 5 protocols: FrontendAdapter, TransformationProvider, CompilerAdapter, EvaluatorAdapter, RuntimeAdapter.
- PluginManifest and PluginCapabilities dataclasses.
- EquivalenceKind enum (exact, objective_equivalent, ground_state_equivalent, approximate, unknown, invalid).
- TransformationRecord with metrics_before/after, verification, outcome, cost.
- JSON schemas for WQIR v0.2 and RepGraph v0.2.
- Core unit tests (representation roundtrip, DAG validation, cycle rejection).
- RFC-WAVE1-PLUGIN-SDK.md.
