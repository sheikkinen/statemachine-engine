# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.17] - 2025-10-10

### Fixed
- **CRITICAL BUG FIX**: Custom actions now properly supplement built-in actions
  - v0.0.16 initial release had critical bug where `--actions-dir` broke built-in actions
  - Built-in actions (bash, log, send_event) were unavailable when using custom actions
  - Fixed in same day - both custom and built-in actions now work together
  - **Skip v0.0.16 and use v0.0.17 instead**

### Note
- This is a patch release fixing critical bug discovered in v0.0.16
- All v0.0.16 features work correctly in v0.0.17
- No API changes, only bug fix

## [0.0.16] - 2025-10-10 [YANKED - Critical Bug]

**⚠️ DO NOT USE - Contains critical bug. Use v0.0.17 instead.**

Critical bug: Using `--actions-dir` made built-in actions unavailable. Fixed in v0.0.17.

### Added
- **Custom Actions Directory**: New `--actions-dir` CLI parameter allows specifying custom actions directory without package installation
- Support for absolute, relative, and ~ (home directory) paths in `--actions-dir`
- Automatic sys.path manipulation for custom action imports
- Dynamic action loading from custom directories using importlib.util
- Path validation and clear error messages for non-existent or invalid directories
- Comprehensive test suite: 21 tests covering discovery, loading, execution, precedence, edge cases
- Support for nested custom action directories

### Changed
- `ActionLoader` now discovers from BOTH custom directory AND built-in actions (fixed critical bug)
- Custom actions supplement built-ins instead of replacing them
- Custom actions take precedence over built-ins with same name (override capability)
- Engine initialization accepts optional `actions_root` parameter
- CLI validates and resolves action directory paths before passing to engine

### Fixed
- **CRITICAL BUG**: Custom actions now supplement built-ins instead of replacing them
  - Previous behavior: `--actions-dir` made built-in actions (bash, log, send_event) unavailable
  - Fixed behavior: Both custom and built-in actions available simultaneously
  - Workflows can now use custom actions alongside bash, log, send_event, etc.

### Developer Experience
- No package installation required for custom actions (eliminates setup.py/pyproject.toml overhead)
- Fast iteration: edit action → test immediately (no reinstall cycle)
- Actions can live alongside YAML configs in project directory structure
- Simplified project setup for domain-specific state machine implementations
- Full access to built-in actions even when using custom actions

### Documentation
- Updated README with `--actions-dir` usage examples and benefits
- Documented action precedence rules (custom overrides built-in)
- Added examples for relative/absolute/~ path specifications
- Documented discovery behavior: BOTH custom and built-in actions available
- Feature request analysis and implementation notes in docs/

### Testing
- All 90 tests passing (no regressions)
- 21 tests for custom actions feature (4 tests added for bug fix verification)
- Tests cover: discovery, loading, execution, caching, path resolution, precedence, error handling
- Tests document expected behavior: custom actions supplement (not replace) built-ins

## [0.0.15] - 2025-10-09

### Added
- **JSON Payload Auto-Parsing**: External event payloads sent as JSON strings are now automatically parsed to dictionaries before action execution
- **Nested Field Access**: Template expansion now supports nested payload access using dot notation (e.g., `{event_data.payload.user.id}`)
- **Whole-Dict Forwarding**: Support for forwarding entire payloads using `payload: "{event_data.payload}"` syntax
- Comprehensive unit tests for JSON parsing edge cases (10+ tests)
- Integration tests for nested field extraction and payload forwarding
- Detailed payload forwarding documentation and examples in README

### Changed
- Event reception now pre-processes JSON string payloads for all actions
- Invalid JSON payloads log warnings and fallback to empty dict instead of causing errors
- Enhanced `send_event` action with more powerful template expansion

### Performance
- Internal event dispatch remains zero-copy for dict payloads
- JSON parsing adds <1ms overhead for string payloads (tested up to 100KB)
- Multi-machine relay operations now 10-50x faster than bash subprocess workarounds

### Documentation
- Added comprehensive "Event Payload Forwarding" section to README
- Included multi-machine orchestration example with controller pattern
- Added usage examples for field extraction, nested access, and complete forwarding
- Updated with benefits comparison vs bash workarounds

## [0.0.14] - 2025-10-09

### Added
- Real-time event monitoring CLI tool: `statemachine-events`
- Three output formats: human (emoji-rich), json (line-delimited), compact (terse)
- Machine filtering and duration-limited monitoring
- Remote monitoring capability via WebSocket connection
- Comprehensive test suite in `monitor-test/` directory with automated scripts
- WebSocket client connection for receiving live state machine events

### Changed
- Event monitor connects to WebSocket server instead of direct Unix socket
- All events from all machines visible in single monitoring stream

### Documentation
- Updated CLAUDE.md with event monitor tool documentation
- Added "Tools & Utilities" section to README
- Created detailed implementation and testing documentation

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
