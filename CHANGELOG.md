# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.8] - 2025-10-24

### Added
- **websocket_server.py**: Persistent file logging for WebSocket server
  - Automatically logs to `logs/websocket-server.log` in working directory
  - Creates log directory if it doesn't exist
  - Dual output: both file and console (stdout)
  - Formatted logs with timestamp, logger name, level, and message
  - Append mode preserves logs across restarts
  - Critical for debugging server issues in production environments

### Improved
- Enhanced logging visibility for WebSocket server operations
- Better troubleshooting capabilities for real-time monitoring system

## [1.0.7] - 2025-10-24

### Fixed
- **CI**: Added missing `httpx` dependency for FastAPI TestClient
  - GitHub Actions CI was failing on Python 3.10
  - New websocket tests require httpx for TestClient
  - Added `httpx>=0.25.0` to dev dependencies

## [1.0.6] - 2025-10-24

### Fixed
- **CRITICAL: websocket_server.py**: Fixed connection leak causing server to stop sending initial state
  - Database objects were created but never cleaned up on reconnections
  - After several minutes/many reconnections, server stopped responding
  - Removed blocking `check_process_running()` that could hang event loop
  - Extracted `get_initial_state()` function with proper cleanup
  
### Added
- **test_websocket_server.py**: Comprehensive websocket connection tests (11 new tests)
  - Tests multiple reconnections without resource leaks (20 consecutive)
  - Verifies proper database connection cleanup
  - Tests refresh command and initial state delivery
  - `/initial` HTTP endpoint for debugging
  
### Improved
- WebSocket `refresh` command allows clients to request fresh state
- Enhanced `/health` endpoint with socket activity tracking
- Better error handling with exc_info logging
- Proper cleanup on WebSocket disconnection

## [1.0.5] - 2025-10-15

### Fixed
- **CRITICAL: bash_action.py**: Properly kill timed-out processes to prevent zombies
  - Added explicit `process.kill()` when timeout occurs
  - Added 5-second grace period with fallback to `process.terminate()`
  - Prevents resource leaks and background process interference
  - Bug: `asyncio.wait_for()` cancelled waiting but didn't kill the subprocess

### Added
- **test_bash_action_timeout.py**: Comprehensive timeout test suite (11 new tests)
  - Verifies processes are actually killed on timeout (not just waited)
  - Tests default 30-second timeout and custom values
  - Tests error context population and message formatting
  - Tests edge cases (very short timeouts, custom success events)
  - Tests process cleanup with temp file verification

### Improved
- Process cleanup now guaranteed for timed-out bash commands
- Better resource management prevents zombie processes
- Full test coverage for timeout behavior (168 total tests passing, +11 new)

## [1.0.4] - 2025-10-13

### Fixed
- Removed remaining `get_pipeline_model()` references from cli.py
- Removed `pipeline_results` table references (cleanup command and remove-job)
- Fixed `details` command error when viewing job information

### Documentation
- Added comprehensive migration guide for v1.0.3 add-job changes
- Breaking change warning with OLD vs NEW examples
- 4 common migration patterns with before/after code
- Helper bash function for backward compatibility
- Updated all database command examples in README
- Fixed command names: `list-jobs` → `list`, `job-details` → `details`

### Improved
- README now clearly shows how to migrate existing scripts
- All CLI examples use correct v1.0.3+ syntax
- Documentation covers all deprecated parameters and their replacements

## [1.0.3] - 2025-10-13

### Removed
- **Complete Database CLI Genericization**: Removed ~150 lines of remaining domain-specific code
  - Removed `cmd_migrate_queue()` - deprecated legacy queue.json migration
  - Removed face processing job counts from `cmd_status()`
  - Removed domain-specific job type breakdowns from `cmd_machine_status()`
  - Removed domain-specific display formatting from `cmd_list_jobs()` and `cmd_job_details()`
  - Removed hardcoded job type choices (face_processing, pony_flux, sdxl_generation)
  - Removed domain-specific argparse parameters: --input-image, --prompt, --pony-prompt, --flux-prompt, --padding-factor, --mask-padding-factor
  - Removed domain-specific validation logic from add-job

### Changed
- **BREAKING: Generic add-job Command**: Redesigned with flexible parameters
  - `--type` now accepts any string (no hardcoded choices)
  - Added `--machine-type` to specify target machine (defaults to job type)
  - Added `--input-file` for generic file input
  - Added `--payload` for arbitrary JSON data
- **Simplified Job Display**: List and details commands show only core generic fields
- **Module Description**: Changed from "face-changer pipeline" to "state machine engine"
- **Truly Generic**: Database CLI has zero domain assumptions

### Migration Guide
```bash
# OLD (domain-specific):
add-job job123 --type face_processing --input-image photo.jpg --prompt "enhance"

# NEW (generic):
add-job job123 --type face_processing --input-file photo.jpg --payload '{"prompt": "enhance"}'
```

## [1.0.2] - 2025-10-13

### Removed
- **Database CLI Cleanup**: Removed 281 lines of obsolete and domain-specific code
  - Removed pony-flux specific commands (`list-pony-flux`, `pony-flux-details`, `cleanup-pony`, `update-pony-flux-status`)
  - Removed 5 deprecated functions that queried old pony_flux_jobs table
  - Removed hardcoded output directory checks from health command
  - Removed domain-specific file path validation
  - Removed ambiguous `machine_type = 'legacy'` code

### Fixed
- **Diagram Rendering**: Fixed Mermaid error "Could not find a suitable point for the given distance"
  - Added `[*]` start points to initial composite subdiagrams (INITIALIZATION)
  - Diagrams now render correctly without SVG path calculation errors
  - Fixed: Initial composites had no entry point causing Mermaid to fail

### Improved
- **True Generic Framework**: Database CLI now contains zero domain-specific assumptions
  - Use unified `jobs` table commands instead of deprecated pony-flux commands
  - Cleaner, more maintainable codebase (281 lines removed)
  - All tests passing (47 passed, 2 skipped)
- **Better Diagram Generation**: Composite subdiagrams always have proper entry points

## [1.0.1] - 2025-10-13

### Removed
- **UI Cleanup**: Removed stale status indicators and database CLI dependencies
  - Removed "Stopped/Running" status indicator from machine cards
  - Removed Start/Stop control buttons (machines managed externally now)
  - Removed all `statemachine_engine.database.cli` dependencies from UI server
  - Removed `/api/machines`, `/api/errors`, and machine start/stop endpoints
  - Removed 500+ lines of unused code and CSS

### Changed
- **WebSocket-Only State Updates**: UI now relies entirely on WebSocket events
  - Initial state loaded from WebSocket `initial` event instead of REST API
  - Machine state updates handled purely through real-time events
  - Simpler, more reliable state management without polling

### Improved
- Cleaner UI with focus on state visualization
- Reduced coupling between UI and database layer
- More maintainable codebase with fewer dependencies

## [0.1.2] - 2025-10-13

### Added
- **PID Field in API**: `machine-state` CLI now returns `pid` and `metadata` fields
  - Enables accurate process detection in UI
  - Table view now shows PID column for debugging
  - JSON output includes PID for programmatic checking

- **Debugging Improvements**: Enhanced logging for troubleshooting UI state issues
  - Server logs now show which PROJECT_ROOT is being queried
  - Detailed process checking logs show PID validation results
  - Logs show: process exists, PID in output, is statemachine process
  - Helps diagnose issues with multiple databases or stale PIDs

### Fixed
- **Missing PID Data**: API was not returning PID field from database
  - Prevented accurate process detection
  - Caused all machines to show as "Stopped" even when running
  - Now includes PID for reliable status checking

### Improved
- Better diagnostic information when machines show incorrect status
- Easier to identify PROJECT_ROOT configuration issues
- Console logs help debug database location problems

## [0.1.1] - 2025-10-13

### Fixed
- **UI Machine State Tracking**: Fixed incorrect "Stopped" status showing for running machines
  - UI was displaying outdated status from localStorage after page refresh
  - Process detection now uses PID-based checking (`ps -p <PID>`) instead of unreliable grep
  - Added staleness detection: machines inactive for >60 seconds marked as stale/stopped
  - Clear localStorage on fresh machine list update to prevent stale data
  - Only persist state when machines are actually running
  
### Changed
- **Process Detection**: More reliable machine status checking
  - `checkProcessRunning()` now validates actual PID from database
  - Validates process is actually a statemachine process, not just matching name
  - Added `stale` and `stale_seconds` fields to machine API response
  
### Improved
- Machine status display now shows staleness indicator when inactive
- Better handling of crashed or killed machine processes
- More accurate running/stopped state in Web UI

## [0.1.0] - 2025-10-12

### Added
- **Engine-Level Variable Interpolation**: Major feature enabling consistent variable substitution across all actions
  - New `_substitute_variables()` method supporting simple and nested placeholders
  - New `_interpolate_config()` method for recursive config processing
  - Supports `{variable}` and `{nested.path.variable}` syntax
  - Custom actions can modify context for subsequent actions to use
  - Works with strings, dicts, lists, and mixed types
  - Handles special characters and numeric values correctly
  - Unknown placeholders preserved for debugging
  - All actions (built-in and custom) benefit automatically

- **Machine-Agnostic Job Queue**: Enhanced database queue support for v2.0 controller architecture
  - `get_next_job()` with `machine_type=None` now claims ANY pending job
  - Enables centralized controller polling jobs by type only
  - Backward compatible with v1.0 distributed polling
  - Fixed bug where claimed jobs returned stale status='pending'

- **Comprehensive Test Suite**: 15 new tests for variable interpolation
  - Tests for simple variables, nested variables, missing placeholders
  - Tests for special characters, numeric values, deeply nested structures
  - Tests for custom action context modification (key use case)
  - All 172 tests passing (157 passed, 15 new interpolation tests)

### Changed
- **Context Propagation**: Custom actions can now add variables to context
  - Variables added by one action are available to subsequent actions
  - No more repetitive `{event_data.payload.*}` references throughout YAML
  - Cleaner, more maintainable state machine configurations
  
- **Action Execution**: Engine now interpolates variables before passing config to actions
  - Consistent behavior across all action types
  - Individual actions no longer need to implement interpolation
  - Performance optimized with single-pass processing

### Fixed
- **Job Status Bug**: `get_next_job()` now returns correct `status='processing'` after claiming
  - Previously returned stale row data with `status='pending'`
  - Now updates returned dict to reflect database changes
  - Critical for v2.0 controller architecture

### Documentation
- Added comprehensive "Variable Interpolation" section to README
- Updated change request documentation with implementation status
- Added examples for simple variables, nested variables, and custom actions
- Documented benefits, use cases, and implementation details

### Breaking Changes
- None - fully backward compatible with existing configurations

## [0.0.20] - 2025-10-11

### Added
- **Real-time Event Delivery**: CLI `send-event` now delivers events instantly to Web UI
  - Extends `send-event` to write to `/tmp/statemachine-events.sock` (WebSocket server)
  - Activity logs sent via CLI appear immediately in Web UI (no refresh needed)
  - Sends to both database AND Unix socket for dual-path reliability
  - New `--source` parameter for custom attribution in UI (defaults to "cli")
  - Graceful fallback to database-only if WebSocket server unavailable

- **Enhanced send-event Command**: Improved event routing
  - UI target (`--target ui`) sends to WebSocket socket only
  - Non-UI targets send to both WebSocket socket AND machine control socket
  - Better status reporting showing which sockets were used
  - JSON payload parsing with error handling

- **Comprehensive Test Suite**: 8 new tests for real-time socket functionality
  - Tests for WebSocket socket delivery
  - Tests for dual-socket routing (WebSocket + control)
  - Tests for graceful error handling
  - Tests for JSON payload parsing
  - Total test count increased from 92 to 143 tests (136 passing, 7 skipped)

### Changed
- **send-event Behavior**: Now sends to multiple destinations for reliability
  - Database write (persistent storage)
  - WebSocket server socket (real-time UI updates)
  - Machine control socket (direct machine communication, if applicable)
  - All sends are non-blocking with error recovery

### Fixed
- Activity log messages from CLI now appear in Web UI without page refresh
- Resolved gap where CLI events required polling/refresh to appear

## [0.0.19] - 2025-10-11

### Added
- **New CLI Commands**: State transition and error history tracking
  - `transition-history` - Query state transitions from realtime_events table
  - `error-history` - Query error/exception history from realtime_events table
  - Both support filtering by machine name, time range, and output format (table/JSON)

- **Enhanced Exception Handling**: Comprehensive error handling in realtime_event model
  - `log_event()` returns Optional[int], catches JSON serialization and database errors
  - `get_unconsumed_events()` returns empty list on failure, handles per-row JSON errors
  - `mark_events_consumed()` returns bool for success/failure indication
  - `cleanup_old_events()` returns count of deleted events (-1 on error)

- **Error Emission**: Engine now logs all exceptions to realtime_events table
  - Action not found errors automatically logged
  - Action execution exceptions logged with job context
  - Action loading exceptions logged
  - All errors emit to `realtime_events` for auditing and monitoring

- **Comprehensive Test Suite**: 38 new tests added (100% pass rate)
  - 17 tests for realtime_event model exception handling
  - 11 tests for CLI history commands
  - 11 tests for engine error emission
  - Total test count increased from 54 to 92 tests

### Changed
- **Database Logging**: All engine errors now persisted to realtime_events table
  - Enables post-mortem debugging and error analysis
  - Provides audit trail for system failures
  - Integrated with existing monitoring infrastructure

### Fixed
- Improved error resilience in database operations
- Graceful degradation when database logging fails

## [0.0.18] - 2025-10-11

### Changed
- **Web UI Improvements**: Dynamic tab creation for state machine diagrams
  - Tabs are now created dynamically based on running machines from API
  - No more hardcoded machine tabs in HTML
  - Better handling of machines appearing/disappearing
  - Improved initialization flow with proper async loading

### Removed
- Removed legacy monolithic `app.js` file
- Fully migrated to modular architecture (`app-modular.js`)

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
