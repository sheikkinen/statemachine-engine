/**
 * StateGroupManager Tests
 * 
 * Tests for state group extraction and management functionality
 */

import { StateGroupManager } from '../modules/StateGroupManager.js';

describe('StateGroupManager', () => {
    let manager;
    const mockMetadata = {
        machine_name: 'patient_records',
        diagrams: {
            main: {
                file: 'main.mermaid',
                title: 'patient_records Overview',
                composites: ['IDLE', 'PROCESSING', 'COMPLETION']
            },
            IDLE: {
                file: 'IDLE.mermaid',
                title: 'IDLE',
                states: ['waiting_for_report'],
                parent: 'main'
            },
            PROCESSING: {
                file: 'PROCESSING.mermaid',
                title: 'PROCESSING',
                states: ['summarizing', 'fact_checking'],
                parent: 'main'
            },
            COMPLETION: {
                file: 'COMPLETION.mermaid',
                title: 'COMPLETION',
                states: ['ready', 'failed', 'shutdown'],
                parent: 'main'
            }
        }
    };

    describe('Constructor', () => {
        it('should initialize with null metadata', () => {
            manager = new StateGroupManager(null);
            expect(manager.metadata).toBeNull();
        });

        it('should initialize with provided metadata', () => {
            manager = new StateGroupManager(mockMetadata);
            expect(manager.metadata).toBe(mockMetadata);
        });
    });

    describe('setMetadata()', () => {
        beforeEach(() => {
            manager = new StateGroupManager(null);
        });

        it('should update metadata', () => {
            expect(manager.metadata).toBeNull();
            
            manager.setMetadata(mockMetadata);
            
            expect(manager.metadata).toBe(mockMetadata);
        });

        it('should allow metadata to be changed', () => {
            const newMetadata = { ...mockMetadata, machine_name: 'other' };
            
            manager.setMetadata(mockMetadata);
            expect(manager.metadata.machine_name).toBe('patient_records');
            
            manager.setMetadata(newMetadata);
            expect(manager.metadata.machine_name).toBe('other');
        });
    });

    describe('getStates()', () => {
        beforeEach(() => {
            manager = new StateGroupManager(mockMetadata);
        });

        it('should return all states for main diagram', () => {
            const states = manager.getStates('main');
            
            expect(states).toBeTruthy();
            expect(states.length).toBe(6);
            expect(states).toContain('waiting_for_report');
            expect(states).toContain('summarizing');
            expect(states).toContain('fact_checking');
            expect(states).toContain('ready');
            expect(states).toContain('failed');
            expect(states).toContain('shutdown');
        });

        it('should return states for specific composite', () => {
            const states = manager.getStates('PROCESSING');
            
            expect(states).toEqual(['summarizing', 'fact_checking']);
        });

        it('should return states for another composite', () => {
            const states = manager.getStates('IDLE');
            
            expect(states).toEqual(['waiting_for_report']);
        });

        it('should return null for non-existent diagram', () => {
            const states = manager.getStates('NON_EXISTENT');
            
            expect(states).toBeNull();
        });

        it('should return null if no metadata', () => {
            manager.setMetadata(null);
            const states = manager.getStates('main');
            
            expect(states).toBeNull();
        });
    });

    describe('getStateGroups()', () => {
        beforeEach(() => {
            manager = new StateGroupManager(mockMetadata);
        });

        it('should return state groups for main diagram', () => {
            const groups = manager.getStateGroups('main');
            
            expect(groups).toBeTruthy();
            expect(groups.length).toBe(3);
        });

        it('should preserve group order from metadata', () => {
            const groups = manager.getStateGroups('main');
            
            expect(groups[0].name).toBe('IDLE');
            expect(groups[1].name).toBe('PROCESSING');
            expect(groups[2].name).toBe('COMPLETION');
        });

        it('should include states in each group', () => {
            const groups = manager.getStateGroups('main');
            
            expect(groups[0].states).toEqual(['waiting_for_report']);
            expect(groups[1].states).toEqual(['summarizing', 'fact_checking']);
            expect(groups[2].states).toEqual(['ready', 'failed', 'shutdown']);
        });

        it('should return null for subdiagrams', () => {
            const groups = manager.getStateGroups('PROCESSING');
            
            expect(groups).toBeNull();
        });

        it('should return null if no metadata', () => {
            manager.setMetadata(null);
            const groups = manager.getStateGroups('main');
            
            expect(groups).toBeNull();
        });

        it('should return null for diagram without composites', () => {
            const simpleMetadata = {
                diagrams: {
                    main: {
                        file: 'main.mermaid',
                        // No composites
                    }
                }
            };
            manager.setMetadata(simpleMetadata);
            
            const groups = manager.getStateGroups('main');
            
            expect(groups).toBeNull();
        });
    });

    describe('findGroupForState()', () => {
        beforeEach(() => {
            manager = new StateGroupManager(mockMetadata);
        });

        it('should find IDLE group for waiting_for_report', () => {
            const group = manager.findGroupForState('waiting_for_report');
            
            expect(group).toBe('IDLE');
        });

        it('should find PROCESSING group for summarizing', () => {
            const group = manager.findGroupForState('summarizing');
            
            expect(group).toBe('PROCESSING');
        });

        it('should find PROCESSING group for fact_checking', () => {
            const group = manager.findGroupForState('fact_checking');
            
            expect(group).toBe('PROCESSING');
        });

        it('should find COMPLETION group for ready', () => {
            const group = manager.findGroupForState('ready');
            
            expect(group).toBe('COMPLETION');
        });

        it('should return null for non-existent state', () => {
            const group = manager.findGroupForState('non_existent_state');
            
            expect(group).toBeNull();
        });

        it('should return null if no metadata', () => {
            manager.setMetadata(null);
            const group = manager.findGroupForState('summarizing');
            
            expect(group).toBeNull();
        });
    });

    describe('getComposites()', () => {
        beforeEach(() => {
            manager = new StateGroupManager(mockMetadata);
        });

        it('should return list of composite names', () => {
            const composites = manager.getComposites();
            
            expect(composites).toEqual(['IDLE', 'PROCESSING', 'COMPLETION']);
        });

        it('should preserve order from metadata', () => {
            const composites = manager.getComposites();
            
            expect(composites[0]).toBe('IDLE');
            expect(composites[1]).toBe('PROCESSING');
            expect(composites[2]).toBe('COMPLETION');
        });

        it('should return null if no metadata', () => {
            manager.setMetadata(null);
            const composites = manager.getComposites();
            
            expect(composites).toBeNull();
        });

        it('should return null if main diagram has no composites', () => {
            const simpleMetadata = {
                diagrams: {
                    main: {
                        file: 'main.mermaid'
                    }
                }
            };
            manager.setMetadata(simpleMetadata);
            
            const composites = manager.getComposites();
            
            expect(composites).toBeNull();
        });
    });

    describe('Integration', () => {
        it('should handle complete workflow', () => {
            // Initialize without metadata
            manager = new StateGroupManager(null);
            expect(manager.getStates('main')).toBeNull();
            
            // Set metadata
            manager.setMetadata(mockMetadata);
            
            // Get states
            const states = manager.getStates('main');
            expect(states.length).toBe(6);
            
            // Get groups
            const groups = manager.getStateGroups('main');
            expect(groups.length).toBe(3);
            
            // Find group for state
            const group = manager.findGroupForState('summarizing');
            expect(group).toBe('PROCESSING');
            
            // Get composites
            const composites = manager.getComposites();
            expect(composites.length).toBe(3);
        });
    });
});
