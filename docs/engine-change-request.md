# Change Request: Enhanced send_event Action with JSON Payload Parsing

**Status:** Draft  
**Priority:** High  
**Type:** Enhancement  
**Component:** statemachine-engine core  
**Target Version:** 0.0.15  
**Submitted:** 2025-10-09  
**Submitted By:** image-generator-fsm team

---

## User Story

**As a** state machine developer building multi-machine orchestration architectures,  
**I want** the `send_event` action to automatically parse JSON string payloads and support field extraction via templates,  
**So that** I can relay events between machines with dynamic data without writing custom bash actions or losing payload information.

---

## Business Value

### Current Pain Points

1. **Manual Workarounds Required**
   - Users must write bash actions calling `statemachine-db send-event` to forward payloads
   - Custom relay actions needed for each forwarding pattern
   - Inconsistent patterns across different FSMs

2. **Limited Orchestration Patterns**
   - Controller/orchestrator machines can't efficiently relay data between workers
   - Multi-stage pipelines require complex workarounds
   - Cannot build reusable relay patterns

3. **Performance Impact**
   - Bash subprocess overhead for every relay operation
   - External process invocation slower than internal event dispatch
   - Increased resource usage in high-throughput scenarios

### Expected Benefits

1. **Simplified FSM Development**
   - Natural template syntax for payload forwarding: `{event_data.payload.field}`
   - Single action type for all event forwarding scenarios
   - Reduced code complexity and maintenance burden

2. **Enabled Architecture Patterns**
   - Efficient orchestrator/controller machines
   - Data pipeline architectures with multiple workers
   - Event-driven microservice patterns with FSMs

3. **Performance Improvement**
   - Internal event dispatch (no subprocess overhead)
   - 10-50x faster relay operations
   - Better resource utilization

---

## Acceptance Criteria

### Functional Requirements

**Must Have:**

- [ ] **AC1:** When `statemachine-db send-event` sends a payload as JSON string, the engine automatically parses it to a dictionary before action execution
- [ ] **AC2:** Template syntax `{event_data.payload.field_name}` extracts values from parsed payload dictionaries
- [ ] **AC3:** Payloads already provided as dictionaries (internal events) continue to work unchanged
- [ ] **AC4:** Invalid JSON strings log a warning and use empty dict `{}` as fallback (no crash)
- [ ] **AC5:** Nested field access works: `{event_data.payload.nested.field}`

**Should Have:**

- [ ] **AC6:** Debug logging shows when JSON parsing occurs and number of fields parsed
- [ ] **AC7:** Warning logs include snippet of invalid JSON (first 100 chars) for debugging
- [ ] **AC8:** Parsing happens once per event (cached for all actions in that state)

**Won't Have (Out of Scope):**

- Array indexing: `{event_data.payload.items[0]}` (future enhancement)
- Dynamic field names: `{event_data.payload[variable_name]}` (future enhancement)
- Payload schema validation (separate feature)

### Non-Functional Requirements

- [ ] **NFR1:** JSON parsing adds <1ms latency per event (tested with 1KB payloads)
- [ ] **NFR2:** No memory leaks with large payloads (tested up to 10MB)
- [ ] **NFR3:** Backward compatible - all existing FSMs continue to work without changes
- [ ] **NFR4:** Unit test coverage ≥95% for new parsing logic
- [ ] **NFR5:** Integration tests cover relay scenarios with real FSMs

---

## Use Cases

### Use Case 1: Image Processing Pipeline (Primary Motivation)

**Context:** Three-machine architecture for AI image generation
- `sdxl_generator`: Creates base images
- `face_processor`: Enhances faces in images  
- `controller`: Orchestrates the pipeline

**Current Workaround (Bash Action):**
```yaml
# controller.yaml
relaying_to_face_processor:
  - type: bash
    command: |
      statemachine-db send-event \
        --target face_processor \
        --type sdxl_job_done_relay \
        --job-id '{event_data.job_id}' \
        --payload '{event_data.payload}'
    timeout: 5
    success: sdxl_event_relayed
```

**Desired (Enhanced send_event):**
```yaml
# controller.yaml
relaying_to_face_processor:
  - type: send_event
    target_machine: face_processor
    event_type: sdxl_job_done_relay
    payload:
      base_image: "{event_data.payload.base_image}"
      face_job_id: "{event_data.payload.face_job_id}"
      face_prompt: "{event_data.payload.face_prompt}"
    success: sdxl_event_relayed
```

**Benefit:** Cleaner syntax, faster execution, explicit field forwarding

---

### Use Case 2: Complete Payload Forwarding

**Context:** Relay entire payload without modification

**Current Workaround:**
```yaml
- type: bash
  command: statemachine-db send-event --target worker --payload '{event_data.payload}'
```

**Desired:**
```yaml
- type: send_event
  target_machine: worker
  event_type: work_request
  payload: "{event_data.payload}"  # Forward entire dict
```

**Note:** This requires payload field to accept both dict and template string types.

---

### Use Case 3: Payload Transformation

**Context:** Extract subset of fields and add metadata

**Current:** Not possible without custom action

**Desired:**
```yaml
- type: send_event
  target_machine: logger
  event_type: log_entry
  payload:
    timestamp: "{context.current_timestamp}"
    original_job: "{event_data.payload.job_id}"
    status: "{event_data.payload.status}"
    machine: "{context.machine_name}"
```

**Benefit:** Flexible payload transformation inline

---

## Technical Design

### Proposed Implementation

**Option A: Pre-parse in Event Reception (Recommended)**

Modify the event reception handler to parse JSON strings before queuing:

```python
# src/core/machine.py or event_handler.py

async def _receive_event(self, event_data: dict) -> None:
    """Receive and prepare event for processing."""
    
    # Parse JSON string payloads to dicts
    if 'payload' in event_data:
        payload = event_data['payload']
        
        if isinstance(payload, str):
            try:
                event_data['payload'] = json.loads(payload)
                self.logger.debug(
                    f"Parsed JSON payload for {event_data.get('type')}: "
                    f"{len(event_data['payload'])} fields"
                )
            except json.JSONDecodeError as e:
                self.logger.warning(
                    f"Failed to parse JSON payload for {event_data.get('type')}: {e}. "
                    f"Using empty dict. Raw payload: {payload[:100]}..."
                )
                event_data['payload'] = {}
        
        # Dict payloads pass through unchanged
    
    await self._event_queue.put(event_data)
```

**Rationale:**
- ✅ Single point of parsing - benefits all actions
- ✅ Cleaner context for action execution
- ✅ Easier to test
- ✅ All actions (log, bash, send_event) can access dict fields

**Alternative Considered:**
- Option B: Parse in send_event action only
  - ❌ Redundant parsing if multiple actions need payload
  - ❌ Inconsistent context between actions
  - ✅ Lower risk (smaller scope)

### Edge Cases

| Scenario | Expected Behavior | Test Required |
|----------|-------------------|---------------|
| Empty string `""` | Parse to `{}` or keep as `""` | Yes |
| Whitespace only `"   "` | Parse to `{}` | Yes |
| Invalid JSON `{bad}` | Log warning, use `{}` | Yes |
| Nested JSON string | Parse outer only | Yes |
| Very large payload (10MB) | Parse successfully, monitor memory | Performance test |
| Dict payload (backward compat) | Pass through unchanged | Regression test |
| Missing payload field | No error, field optional | Yes |

### Migration Impact

**No Breaking Changes:**
- Existing FSMs with dict payloads → unchanged behavior
- Existing FSMs with string payloads → enhanced (can now use field extraction)
- Existing FSMs not using payloads → unchanged

**Optional Enhancements:**
Users can optionally update FSMs to use simpler syntax:

```yaml
# Before (workaround)
- type: bash
  command: statemachine-db send-event --target X --payload '{event_data.payload}'

# After (enhanced)
- type: send_event
  target_machine: X
  payload: "{event_data.payload}"
```

---

## Testing Strategy

### Unit Tests

```python
def test_json_string_payload_parsed_to_dict():
    """JSON string payloads are automatically parsed."""
    event = {'type': 'test', 'payload': '{"key": "value"}'}
    machine._receive_event(event)
    assert isinstance(event['payload'], dict)
    assert event['payload']['key'] == 'value'

def test_dict_payload_unchanged():
    """Dict payloads pass through without modification."""
    event = {'type': 'test', 'payload': {'key': 'value'}}
    machine._receive_event(event)
    assert event['payload'] == {'key': 'value'}

def test_invalid_json_uses_empty_dict():
    """Invalid JSON logs warning and uses empty dict fallback."""
    event = {'type': 'test', 'payload': '{invalid}'}
    machine._receive_event(event)
    assert event['payload'] == {}
    assert "Failed to parse JSON payload" in log_capture

def test_nested_field_extraction_in_send_event():
    """send_event can extract nested fields after parsing."""
    # Send event with nested payload
    await send_external_event('test', 'data', '{"user": {"id": 123}}')
    # FSM with nested extraction
    config = {
        'actions': {
            'forwarding': [{
                'type': 'send_event',
                'payload': {'user_id': '{event_data.payload.user.id}'}
            }]
        }
    }
    # Verify forwarded event has extracted value
    result = await wait_for_event('target', 'forwarded')
    assert result['payload']['user_id'] == 123
```

### Integration Tests

```python
async def test_three_machine_relay_pipeline():
    """Test controller relaying events between two workers."""
    
    # Start three machines
    sdxl = await start_machine('sdxl_generator')
    face = await start_machine('face_processor')
    controller = await start_machine('controller')
    
    # SDXL sends completion with payload
    await sdxl.send_event(
        target='controller',
        type='sdxl_job_done',
        payload={'base_image': 'test.png', 'face_job_id': 'f123'}
    )
    
    # Controller should relay to face processor
    face_event = await face.wait_for_event('sdxl_job_done_relay', timeout=5)
    
    # Verify payload fields were forwarded
    assert face_event['payload']['base_image'] == 'test.png'
    assert face_event['payload']['face_job_id'] == 'f123'
    
    # Face processor completes and sends back
    await face.send_event(
        target='controller',
        type='face_job_done',
        payload={'final_image': 'result.png', 'original_job_id': 'j123'}
    )
    
    # Controller relays to descriptor
    desc_event = await descriptor.wait_for_event('face_job_done_relay', timeout=5)
    assert desc_event['payload']['final_image'] == 'result.png'
```

### Performance Tests

```python
def test_parsing_performance():
    """JSON parsing adds <1ms latency."""
    payloads = [
        '{"small": "data"}',  # 16 bytes
        '{"medium": "' + 'x'*1000 + '"}',  # 1KB
        '{"large": "' + 'x'*100000 + '"}'  # 100KB
    ]
    
    for payload_str in payloads:
        start = time.perf_counter()
        event = {'payload': payload_str}
        machine._receive_event(event)
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.001, f"Parsing took {elapsed*1000:.2f}ms"
```

---

## Documentation Updates

### User Guide Updates

**Section: "Event Payloads"**

Add:
```markdown
### Payload Processing

Payloads can be provided in two formats:

1. **Dictionary (recommended):** When creating events within FSM actions
   ```yaml
   payload:
     key: "value"
     number: 42
   ```

2. **JSON String:** When using `statemachine-db send-event` CLI
   ```bash
   statemachine-db send-event --payload '{"key": "value", "number": 42}'
   ```

**Automatic Parsing:** JSON string payloads are automatically parsed to 
dictionaries when events are received. Your FSM actions always work with 
dictionaries.

### Field Extraction

Extract payload fields using template syntax:

```yaml
- type: send_event
  target_machine: worker
  event_type: process_request
  payload:
    input_file: "{event_data.payload.filename}"
    job_id: "{event_data.payload.id}"
    metadata: "{event_data.payload.user.name}"  # Nested access
```

**Template Variables:**
- `{event_data.payload.field}` - Field from received event payload
- `{context.variable}` - Variable from action context
- Static values - Literal strings or numbers

### Error Handling

If a JSON string payload cannot be parsed:
- Warning is logged with error details
- Empty dictionary `{}` is used as fallback
- FSM continues execution (no crash)
- Check logs if payload data is missing
```

### API Reference Updates

**send_event Action:**

```markdown
### send_event

Sends an event to another state machine.

**Parameters:**
- `target_machine` (string, required): Name of the target machine
- `event_type` (string, required): Type of event to send
- `payload` (dict or template string, optional): Event payload data
- `success` (string, optional): Event to trigger on success
- `failure` (string, optional): Event to trigger on failure

**Payload Template Expansion:**

The `payload` parameter supports template syntax for dynamic values:

```yaml
# Extract specific fields
payload:
  image_path: "{event_data.payload.image}"
  user_id: "{event_data.payload.user.id}"

# Mix templates and static values  
payload:
  input: "{event_data.payload.filename}"
  timestamp: "{context.current_time}"
  status: "processing"

# Forward entire payload (advanced)
payload: "{event_data.payload}"
```

**Payload Processing:**
- External event payloads (JSON strings) are automatically parsed
- Template expansion occurs after parsing
- Invalid JSON results in empty dict with warning log
- Nested field access supported: `{event_data.payload.a.b.c}`

**Example:**

```yaml
relaying_completion:
  - type: send_event
    target_machine: "downstream_worker"
    event_type: "task_complete"
    payload:
      result_file: "{event_data.payload.output}"
      original_request: "{event_data.payload.request_id}"
      processed_at: "{context.timestamp}"
    success: relay_complete
```
```

### Changelog Entry

```markdown
## [0.0.15] - 2025-10-XX

### Added
- **JSON Payload Auto-Parsing:** External event payloads sent as JSON strings 
  are now automatically parsed to dictionaries before action execution.
- **Enhanced send_event Templates:** Payload fields can be extracted using 
  template syntax: `{event_data.payload.field_name}`.
- **Nested Field Access:** Support for nested payload access: 
  `{event_data.payload.user.id}`.

### Changed
- Event reception now pre-processes JSON string payloads for all actions.
- Invalid JSON payloads log warnings and fallback to empty dict instead of 
  causing errors.

### Performance
- Internal event dispatch remains zero-copy for dict payloads.
- JSON parsing adds <1ms overhead for string payloads.

### Migration
- **No breaking changes:** All existing FSMs continue to work.
- **Optional enhancement:** FSMs using bash workarounds for payload forwarding 
  can be simplified using enhanced send_event syntax.

### Examples
See `examples/relay_pattern.yaml` for multi-machine orchestration patterns.
```

---

## Rollout Plan

### Phase 1: Development (Week 1)
- [ ] Implement JSON parsing in event reception handler
- [ ] Add unit tests for parsing logic (all edge cases)
- [ ] Add template expansion tests for send_event
- [ ] Code review and refinement

### Phase 2: Testing (Week 2)
- [ ] Integration tests with multi-machine relay scenarios
- [ ] Performance testing (latency, memory, throughput)
- [ ] Backward compatibility validation with existing FSM suite
- [ ] Beta testing with image-generator-fsm project

### Phase 3: Documentation (Week 2-3)
- [ ] Update user guide with payload processing section
- [ ] Update API reference for send_event action
- [ ] Add relay pattern examples to cookbook
- [ ] Write migration guide for bash workaround removal

### Phase 4: Release (Week 3)
- [ ] Version bump to 0.0.15
- [ ] Publish release notes with examples
- [ ] Update image-generator-fsm to use enhanced syntax
- [ ] Deprecation notice for bash relay workarounds (optional migration)

---

## Success Metrics

### Adoption Metrics
- **Target:** 80% of new relay FSMs use enhanced send_event (not bash workaround)
- **Target:** 3+ projects adopt multi-machine orchestration patterns within 3 months

### Performance Metrics
- **Target:** JSON parsing adds <1ms per event (99th percentile)
- **Target:** No memory increase for dict payloads (backward compat)
- **Target:** 10x faster relay operations vs bash workaround

### Quality Metrics
- **Target:** Zero regression bugs in existing FSMs
- **Target:** 95%+ unit test coverage for parsing logic
- **Target:** All integration tests pass (multi-machine scenarios)

---

## Dependencies

### Technical Dependencies
- Python 3.8+ (for json module)
- No external library dependencies (use stdlib json)

### Team Dependencies
- Engine core team: Implementation and code review
- Documentation team: User guide and API reference updates
- QA team: Integration testing and performance validation
- Community: Beta testing with production FSMs

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking changes in edge cases | High | Low | Comprehensive backward compat testing |
| Performance regression | Medium | Low | Performance benchmarks before/after |
| Parsing errors causing crashes | High | Low | Strict error handling with fallbacks |
| Users rely on string payloads | Medium | Very Low | Audit codebase for string assumptions |
| Complex nested templates | Low | Medium | Document limitations clearly |

---

## Alternatives Considered

### Alternative 1: Do Nothing (Keep Bash Workaround)

**Pros:**
- No development effort
- Zero risk of bugs

**Cons:**
- Poor developer experience
- Performance overhead of subprocess calls
- Inconsistent patterns across FSMs
- Limits adoption of multi-machine architectures

**Decision:** Rejected - Enhancement provides significant value

---

### Alternative 2: Custom relay_event Action

**Pros:**
- Isolated to relay scenarios
- No changes to core engine

**Cons:**
- Still requires custom action per FSM
- Doesn't solve general template problem
- Inconsistent with other action types

**Decision:** Rejected - Solves narrow use case, not general issue

---

### Alternative 3: Allow Raw JSON in payload Field

Accept `payload: "{event_data.payload}"` (template string) in addition to dict.

**Pros:**
- Smaller scope than full parsing
- Addresses string forwarding use case

**Cons:**
- Doesn't enable field extraction
- Still requires bash for selective forwarding
- Inconsistent (some templates work, others don't)

**Decision:** Rejected - Doesn't fully solve the problem

---

## Questions for Engine Team

1. **Implementation Location:** Do you prefer parsing in event reception handler (Option A) or in send_event action only (Option B)?

2. **Error Handling:** Should invalid JSON fail silently with empty dict, or should there be a configuration option to fail loudly?

3. **Performance Concerns:** Are there scenarios where string payloads should remain unparsed for performance reasons?

4. **Backward Compatibility:** Are there any code paths that expect payload to remain as string?

5. **Future Enhancements:** Should we plan for array indexing `{payload.items[0]}` and dynamic field names in a future version?

---

## Contact

**Submitted By:** image-generator-fsm development team  
**Project:** https://github.com/user/image-generator-fsm  
**Related Issues:** 
- image-generator-fsm#1: Controller relay payload forwarding
- image-generator-fsm#2: Multi-machine orchestration patterns

**For Questions Contact:**
- Technical: [your-email]
- Use Case: [project-email]

---

## Appendix: Real-World Example

### Before Enhancement (Current Workaround)

**controller/config/controller.yaml:**
```yaml
relaying_to_face_processor:
  # Workaround: Use bash action to forward payload
  - type: bash
    description: "Forward SDXL completion to face processor"
    command: |
      statemachine-db send-event \
        --target face_processor \
        --type sdxl_job_done_relay \
        --job-id '{event_data.job_id}' \
        --payload '{event_data.payload}'
    timeout: 5
    success: sdxl_event_relayed
```

**Issues:**
- ❌ Bash subprocess overhead (~10-50ms)
- ❌ Not idiomatic - mixing action types
- ❌ Harder to test (need real subprocess)
- ❌ Error handling complex

---

### After Enhancement (Desired State)

**controller/config/controller.yaml:**
```yaml
relaying_to_face_processor:
  # Clean: Use enhanced send_event with field extraction
  - type: send_event
    description: "Forward SDXL completion to face processor"
    target_machine: "face_processor"
    event_type: "sdxl_job_done_relay"
    payload:
      base_image: "{event_data.payload.base_image}"
      face_job_id: "{event_data.payload.face_job_id}"
      face_prompt: "{event_data.payload.face_prompt}"
    success: sdxl_event_relayed
```

**Benefits:**
- ✅ Internal event dispatch (~0.1ms)
- ✅ Idiomatic - single action type
- ✅ Easy to test and mock
- ✅ Built-in error handling
- ✅ Explicit field forwarding (clear intent)

---

**Total Estimated Lines Changed:** ~50-100 lines  
**Estimated Development Time:** 1-2 weeks  
**Risk Level:** Low-Medium  
**Value:** High
