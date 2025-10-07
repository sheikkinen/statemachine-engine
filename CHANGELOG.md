# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-07

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
