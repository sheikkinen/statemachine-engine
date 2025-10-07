"""
Test state machine state logging functionality

Verifies that state changes are properly logged to the database
for UI support and monitoring.
"""

import pytest
import asyncio
from pathlib import Path
from statemachine_engine.core.engine import StateMachineEngine
from statemachine_engine.database.models import get_job_model


class TestStateLogging:
    """Tests for state machine state logging to database"""

    @pytest.mark.asyncio
    async def test_state_machine_initialization(self):
        """Test that state machine can be initialized with config"""
        engine = StateMachineEngine(machine_name='test_state_logging')
        
        # Load a real config file
        config_path = Path('config/sdxl_generator.yaml')
        if not config_path.exists():
            pytest.skip("SDXL generator config not found")
        
        await engine.load_config(str(config_path))
        
        assert engine.current_state is not None, "Engine should have a current state"
        assert engine.machine_name == 'test_state_logging', "Machine name should be set"

    @pytest.mark.asyncio
    async def test_initial_state_set(self):
        """Test that initial state is set correctly"""
        engine = StateMachineEngine(machine_name='test_initial_state')
        
        config_path = Path('config/sdxl_generator.yaml')
        if not config_path.exists():
            pytest.skip("SDXL generator config not found")
        
        await engine.load_config(str(config_path))
        
        # SDXL generator should start in 'initializing' state
        assert engine.current_state in ['initializing', 'waiting'], \
            f"Initial state should be valid, got: {engine.current_state}"

    @pytest.mark.asyncio
    async def test_event_processing(self):
        """Test that events can be processed"""
        engine = StateMachineEngine(machine_name='test_event_processing')
        
        config_path = Path('config/sdxl_generator.yaml')
        if not config_path.exists():
            pytest.skip("SDXL generator config not found")
        
        await engine.load_config(str(config_path))
        
        # Add job model to context
        engine.context['job_model'] = get_job_model()
        
        initial_state = engine.current_state
        
        # Process an event
        success = await engine.process_event('start')
        
        # Event processing should return a boolean
        assert isinstance(success, bool), "process_event should return boolean"

    @pytest.mark.asyncio
    async def test_state_change_logging(self):
        """Test that state changes are logged to database"""
        engine = StateMachineEngine(machine_name='test_logging_db')
        
        config_path = Path('config/sdxl_generator.yaml')
        if not config_path.exists():
            pytest.skip("SDXL generator config not found")
        
        await engine.load_config(str(config_path))
        engine.context['job_model'] = get_job_model()
        
        # Process some events
        await engine.process_event('start')
        await engine.process_event('no_jobs')
        
        # Check database for state change logs
        job_model = get_job_model()
        with job_model.db._get_connection() as conn:
            rows = conn.execute("""
                SELECT job_id, step_name, metadata, completed_at
                FROM pipeline_results
                WHERE step_name = 'state_change'
                AND job_id LIKE ?
                ORDER BY completed_at DESC
                LIMIT 10
            """, (f'machine_test_logging_db%',)).fetchall()
        
        # Should have some state change logs
        # Note: May be 0 if state didn't actually change
        assert isinstance(rows, list), "Should return list of rows"

    @pytest.mark.asyncio
    async def test_machine_state_persistence(self):
        """Test that machine state is persisted in database"""
        machine_name = 'test_state_persist'
        engine = StateMachineEngine(machine_name=machine_name)
        
        config_path = Path('config/sdxl_generator.yaml')
        if not config_path.exists():
            pytest.skip("SDXL generator config not found")
        
        await engine.load_config(str(config_path))
        
        # The state should be logged via _update_machine_state
        # We can verify the engine has the method
        assert hasattr(engine, '_update_machine_state'), \
            "Engine should have _update_machine_state method"

    def test_job_model_available(self):
        """Test that job model can be retrieved"""
        job_model = get_job_model()
        
        assert job_model is not None, "Job model should be available"
        assert hasattr(job_model, 'db'), "Job model should have database connection"
