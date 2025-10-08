"""
State Machine Health Monitoring

Tracks metrics for detecting missing transitions and state machine health issues:
- Event processing counts
- Unhandled events (no transition found)
- State duration tracking
- Periodic health reports

Usage:
    from state_machine.health_monitor import HealthMonitor
    
    monitor = HealthMonitor(machine_name="sdxl_generator", report_interval=10)
    
    # Track event processing
    monitor.record_event("no_events", "waiting")
    
    # Track unhandled events
    monitor.record_unhandled_event("no_events", "waiting_for_controller")
    
    # Track state changes
    monitor.record_state_change("waiting", "generating")
    
    # Get health report (automatic every 10s)
    monitor.get_health_report()
"""

import logging
import time
from typing import Dict, List, Tuple
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor state machine health and detect anomalies"""
    
    def __init__(self, machine_name: str, report_interval: int = 10):
        """
        Initialize health monitor
        
        Args:
            machine_name: Name of the state machine being monitored
            report_interval: Seconds between health reports (default: 10)
        """
        self.machine_name = machine_name
        self.report_interval = report_interval
        
        # Metrics
        self.event_counts: Dict[str, int] = defaultdict(int)
        self.unhandled_events: Dict[Tuple[str, str], int] = defaultdict(int)  # (state, event) -> count
        self.state_durations: Dict[str, float] = defaultdict(float)
        self.events_per_state: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # State tracking
        self.current_state: str = "unknown"
        self.state_entry_time: float = time.time()
        self.last_transition_time: float = time.time()
        
        # Loop tracking
        self.loop_iterations: int = 0
        self.total_events_processed: int = 0
        
        # Reporting
        self.last_report_time: float = time.time()
        self.window_start_time: float = time.time()
        
        # Window metrics (reset after each report)
        self.window_event_counts: Dict[str, int] = defaultdict(int)
        self.window_unhandled: Dict[Tuple[str, str], int] = defaultdict(int)
        self.window_iterations: int = 0
        
    def record_event(self, event_type: str, state: str) -> None:
        """Record a processed event"""
        self.event_counts[event_type] += 1
        self.window_event_counts[event_type] += 1
        self.events_per_state[state][event_type] += 1
        self.total_events_processed += 1
        
    def record_unhandled_event(self, event_type: str, state: str) -> None:
        """Record an event with no transition"""
        key = (state, event_type)
        self.unhandled_events[key] += 1
        self.window_unhandled[key] += 1
        
        # Log warning if repeated unhandled events in window
        count = self.window_unhandled[key]
        if count == 10:
            logger.warning(
                f"[{self.machine_name}] Repeated unhandled event detected: "
                f"'{event_type}' in state '{state}' ({count} times in current window)"
            )
        elif count == 50:
            logger.error(
                f"[{self.machine_name}] HIGH FREQUENCY unhandled event: "
                f"'{event_type}' in state '{state}' ({count} times in current window)"
            )
            self._log_diagnostic(state, event_type)
            
    def record_state_change(self, from_state: str, to_state: str, event: str = None) -> None:
        """Record a state transition"""
        now = time.time()
        
        # Update duration for previous state
        duration = now - self.state_entry_time
        self.state_durations[from_state] += duration
        
        # Update current state
        self.current_state = to_state
        self.state_entry_time = now
        self.last_transition_time = now
        
        if event:
            logger.debug(
                f"[{self.machine_name}] {from_state} --{event}--> {to_state}"
            )
    
    def record_loop_iteration(self) -> None:
        """Record a state machine loop iteration"""
        self.loop_iterations += 1
        self.window_iterations += 1
        
    def check_and_report(self) -> None:
        """Check if report interval elapsed and emit report if needed"""
        now = time.time()
        elapsed = now - self.last_report_time
        
        if elapsed >= self.report_interval:
            self._emit_health_report(elapsed)
            self._reset_window_metrics()
            self.last_report_time = now
            self.window_start_time = now
            
    def _emit_health_report(self, window_duration: float) -> None:
        """Emit periodic health report"""
        now = time.time()
        state_duration = now - self.state_entry_time
        
        # Calculate rates
        events_per_sec = self.window_iterations / window_duration if window_duration > 0 else 0
        
        # Build report
        lines = [
            f"[{self.machine_name}] Health Report ({window_duration:.1f}s window):",
            f"  Current State: {self.current_state} ({state_duration:.1f}s)",
            f"  Loop Iterations: {self.window_iterations} ({events_per_sec:.1f}/sec)",
        ]
        
        # Event counts
        if self.window_event_counts:
            lines.append(f"  Events Processed: {sum(self.window_event_counts.values())}")
            for event_type, count in sorted(self.window_event_counts.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"    - {event_type}: {count}")
                
        # Unhandled events (IMPORTANT)
        if self.window_unhandled:
            total_unhandled = sum(self.window_unhandled.values())
            lines.append(f"  ⚠️  Unhandled Events: {total_unhandled}")
            for (state, event), count in sorted(self.window_unhandled.items(), key=lambda x: -x[1]):
                lines.append(f"    - {state}: {event} ({count} times)")
                
            # Critical alert if many unhandled events
            if total_unhandled > 50:
                logger.error(
                    f"[{self.machine_name}] CRITICAL: {total_unhandled} unhandled events in {window_duration:.1f}s"
                )
        
        # Log as single multi-line message
        logger.info("\n".join(lines))
        
    def _reset_window_metrics(self) -> None:
        """Reset window-specific metrics"""
        self.window_event_counts.clear()
        self.window_unhandled.clear()
        self.window_iterations = 0
        
    def _log_diagnostic(self, state: str, event: str) -> None:
        """Log diagnostic information for missing transition"""
        logger.error(
            f"\n[{self.machine_name}] DIAGNOSIS: Missing transition detected\n"
            f"  Machine: {self.machine_name}\n"
            f"  State: {state}\n"
            f"  Event: {event}\n"
            f"  \n"
            f"  SUGGESTION: Add transition to config YAML:\n"
            f"    - from: {state}\n"
            f"      to: {state}  # or appropriate target state\n"
            f"      event: {event}\n"
        )
        
    def get_health_status(self) -> Dict:
        """Get current health status as dict (for API/WebSocket)"""
        now = time.time()
        state_duration = now - self.state_entry_time
        window_duration = now - self.window_start_time
        
        unhandled_count = sum(self.window_unhandled.values())
        
        # Determine health status
        if unhandled_count > 50:
            status = "critical"
        elif unhandled_count > 10:
            status = "warning"
        elif state_duration > 60 and self.current_state not in ['waiting', 'stopped']:
            status = "warning"
        else:
            status = "healthy"
            
        return {
            "machine_name": self.machine_name,
            "status": status,
            "current_state": self.current_state,
            "state_duration_sec": round(state_duration, 1),
            "events_last_window": sum(self.window_event_counts.values()),
            "unhandled_events_last_window": unhandled_count,
            "loop_iterations": self.loop_iterations,
            "total_events": self.total_events_processed,
            "window_duration_sec": round(window_duration, 1),
            "issues": [
                f"Unhandled event '{event}' in state '{state}' ({count}x)"
                for (state, event), count in self.window_unhandled.items()
                if count > 5
            ]
        }
        
    def get_summary_stats(self) -> str:
        """Get summary statistics as formatted string"""
        return (
            f"[{self.machine_name}] Stats: "
            f"State={self.current_state}, "
            f"Loops={self.loop_iterations}, "
            f"Events={self.total_events_processed}, "
            f"Unhandled={sum(self.unhandled_events.values())}"
        )
