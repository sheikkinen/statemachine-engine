# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
