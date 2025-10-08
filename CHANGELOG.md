# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.12] - 2025-10-08

### Fixed
- Fixed UI arrow highlighting issue by using unique event triggers in state machine configurations
- Eliminated duplicate 'new_job' event in simple_worker config that was causing incorrect arrow highlighting
- Changed completed→waiting transition to use 'continue_work' event instead of 'new_job'
- Simplified DiagramManager.js arrow highlighting logic for better maintainability

### Changed
- State machine configurations now use unique event triggers for each transition
- DiagramManager.js now uses direct event matching instead of complex disambiguation logic

## [0.0.11] - 2025-10-08

### Added
- New `statemachine-ui` command that properly starts the web UI server
- Support for external projects via `--project-root` parameter
- Automatic WebSocket server startup with UI server
- New `statemachine-diagrams` command for diagram generation

### Fixed
- UI server now correctly finds diagrams in external projects
- Fixed CLI entry point naming confusion (statemachine-ui now starts UI, not diagrams)
- Web UI can now display state machines from any project directory

### Changed
- `statemachine-ui` now starts the web server instead of generating diagrams
- Added `statemachine-diagrams` as an alias for the old `statemachine-ui` behavior
- UI server uses PROJECT_ROOT environment variable for external project support

## [0.0.9] - 2025-10-08

### Fixed
- Added missing `tabulate` dependency for database CLI commands
- Fixed `ModuleNotFoundError: No module named 'tabulate'` when using `statemachine-db`

## [0.0.8] - 2025-10-08

### Fixed
- Configured trusted publisher for existing PyPI project (was configured for pending project)
- Should now complete full automated release pipeline

## [0.0.7] - 2025-10-08

### Fixed
- Updated PyPI trusted publisher access rights
- Testing complete automated release pipeline

## [0.0.6] - 2025-10-08

### Fixed
- Configured PyPI trusted publisher (OIDC) for automated releases
- Release workflow should now publish successfully to PyPI

## [0.0.5] - 2025-10-08

### Fixed
- Fixed release workflow: Added repository access permissions

## [0.0.4] - 2025-10-08

### Changed
- Pipeline testing release (rerun)

## [0.0.3] - 2025-10-07

### Changed
- Updated diagram output directory from `docs/fsm` to `docs/fsm-diagrams`
- Updated UI server to read diagrams from `docs/fsm-diagrams` folder
- Pipeline testing release

## [0.0.2] - 2025-10-07

### Fixed
- Fixed test suite: updated socket paths from face-changer to statemachine
- Added missing CLI entry points: statemachine-db, statemachine-fsm, statemachine-ui
- Simplified CI workflow tests

### Changed
- All 48 tests now passing on Python 3.9, 3.10, 3.11, 3.12
- CI workflow validates package build

## [0.0.1] - 2025-10-07

### Added
- Initial pre-release
- GitHub Actions workflows (CI and release automation)
- Package distribution infrastructure

## [1.0.0] - Not Yet Released

### Added
- Initial release of statemachine-engine
- YAML-based state machine configuration
- Event-driven architecture with Unix socket communication
- Database-backed job queue (SQLite)
- Real-time monitoring via WebSocket server
- Web UI for state machine visualization
- Built-in actions: bash, log, check_database_queue, check_events, check_machine_state, clear_events, send_event
- Pluggable action system for custom extensions
- Multi-machine coordination support
- Mermaid diagram generation for FSM visualization
- CLI tools: statemachine, statemachine-db, statemachine-fsm, statemachine-ui
- Example configurations: simple_worker, controller_worker
- Comprehensive documentation and quickstart guide

### Core Features
- State machine engine with transitions and events
- Action loader with automatic discovery
- Health monitoring for machine status
- Database models: Job, MachineEvent, MachineState, RealtimeEvent
- WebSocket server for UI updates
- Control socket per machine for event delivery

### Documentation
- README.md with installation and usage instructions
- CLAUDE.md with architecture details and AI assistant guidance
- Quickstart guide
- FSM documentation for simple_worker, task_controller, task_worker
- API reference and examples

[1.0.0]: https://github.com/sheikkinen/statemachine-engine/releases/tag/v1.0.0
