# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-21

### Added
- Initial release.
- Spec-driven implementation: `spec/` folder with EARS requirements,
  JSON schema contracts, and golden examples.
- Python CLI `readerfriction` with `scan`, `trace`, `explain`, `report`,
  `diff` commands.
- Metrics: trace depth, file jumps, wrapper depth, thin wrapper count,
  flow fragmentation, context width, pass-through ratio.
- Configurable weights via `[tool.readerfriction]` in `pyproject.toml`.
- Reports in text, JSON, and markdown formats.
