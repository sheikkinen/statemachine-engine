# Plan: Consolidate Templated Machine Tabs

## Current State
- Each templated machine instance gets its own tab (patient_record_job_001, _002, _003)
- All show the same Kanban view when clicked
- Clutters the tab bar

## Goal
Single tab per template showing count: `patient_record_job (3)`

## Changes Needed

### 1. TabList.js - Group machines with same template
- When rendering tabs, detect machines with `_NNN` suffix pattern
- Group by base name (e.g., `patient_record_job`)
- Render as single tab with count badge

### 2. app-modular.js - Handle consolidated tab clicks
- Templated tab click → show Kanban view (already works)
- Track which template tab is active

### 3. style.css - Style count badge
- Small badge showing count in tab label

## Implementation
1. Modify `TabList.renderTabs()` to group by base name
2. Update tab click handler to recognize grouped tabs
3. Add CSS for count badge

That's it - the Kanban view already handles everything else correctly.
