"""
CheckMachineStateAction - Validate target machine state

IMPORTANT: Changes via Change Management, see CLAUDE.md

Queries pipeline_results table to get target machine's current state
and validates it against expected states.
"""
import logging
import subprocess
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base import BaseAction
from statemachine_engine.database.models import get_job_model

logger = logging.getLogger(__name__)

class CheckMachineStateAction(BaseAction):
    """
    Action to check another machine's current state and validate it.

    Returns:
        - in_expected_state: Machine is running and in expected state
        - unexpected_state: Machine is running but in wrong state
        - not_running: Machine process not found or state data stale
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.target_machine = config.get('target_machine', 'unknown')
        self.expected_states = config.get('expected_states', [])
        self.timeout_seconds = config.get('timeout_seconds', 60)
        self.job_model = get_job_model()

    async def execute(self, context: Dict[str, Any]) -> str:
        """Check target machine state and validate"""
        try:
            # 1. Check if machine process is running
            machine_name = self.get_machine_name(context)
            is_running = await self._is_process_running(self.target_machine)
            if not is_running:
                logger.warning(f"[{machine_name}] Machine {self.target_machine} process not found")
                return 'not_running'

            # 2. Get current state from database
            current_state = self._get_current_state(self.target_machine)

            if not current_state:
                logger.warning(f"[{machine_name}] No recent state data for {self.target_machine}")
                return 'not_running'

            # 3. Validate against expected states
            if current_state in self.expected_states:
                logger.info(f"[{machine_name}] Machine {self.target_machine} in expected state: {current_state}")
                return 'in_expected_state'
            else:
                logger.info(f"[{machine_name}] Machine {self.target_machine} in unexpected state: {current_state} (expected: {self.expected_states})")
                # Store unexpected state in context for debugging
                context['unexpected_machine_state'] = current_state
                return 'unexpected_state'

        except Exception as e:
            machine_name = self.get_machine_name(context)
            logger.error(f"[{machine_name}] Error checking machine state: {e}")
            return 'error'

    async def _is_process_running(self, machine_name: str) -> bool:
        """Check if target machine process is running"""
        try:
            # Run ps command asynchronously
            process = await asyncio.create_subprocess_exec(
                'ps', 'aux',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=5
            )

            output = stdout.decode('utf-8')

            # Look for state_machine/cli.py with machine name
            is_running = ('state_machine/cli.py' in output and
                         machine_name in output)

            logger.debug(f"Process check for {machine_name}: {'running' if is_running else 'not found'}")
            return is_running

        except asyncio.TimeoutError:
            logger.error("Process check timed out")  # No context available in helper method
            return False
        except Exception as e:
            logger.error(f"Error checking process: {e}")  # No context available in helper method
            return False

    def _get_current_state(self, machine_name: str) -> Optional[str]:
        """Get current state from pipeline_results table"""
        try:
            with self.job_model.db._get_connection() as conn:
                row = conn.execute("""
                    SELECT
                        json_extract(metadata, '$.state') as current_state,
                        completed_at
                    FROM pipeline_results
                    WHERE step_name = 'state_change'
                      AND json_extract(metadata, '$.machine') = ?
                    ORDER BY completed_at DESC
                    LIMIT 1
                """, (machine_name,)).fetchone()

                if not row:
                    logger.debug(f"No state data found for {machine_name}")  # Keep without prefix - debug level
                    return None

                # Check if state data is fresh
                completed_at_str = row['completed_at']
                state_time = datetime.fromisoformat(completed_at_str)
                # Database stores UTC timestamps, use utcnow() for comparison
                now = datetime.utcnow()
                age = (now - state_time).total_seconds()

                logger.debug(f"State timestamp for {machine_name}: completed_at={completed_at_str}, parsed={state_time}, now={now}, age={age:.1f}s")  # Keep without prefix - debug level

                if age > self.timeout_seconds:
                    logger.warning(f"State data for {machine_name} is stale ({age:.0f}s old, limit {self.timeout_seconds}s)")  # Keep without prefix - internal helper
                    return None

                state = row['current_state']
                logger.debug(f"Current state for {machine_name}: {state} (age: {age:.1f}s)")  # Keep without prefix - debug level
                return state

        except Exception as e:
            logger.error(f"Error querying state for {machine_name}: {e}")  # Keep without prefix - internal helper
            return None
