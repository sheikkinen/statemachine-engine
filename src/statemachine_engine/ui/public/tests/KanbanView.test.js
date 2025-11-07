/**
 * KanbanView Tests
 * 
 * RED phase: These tests should fail initially since KanbanView.js doesn't exist yet.
 */

// Import KanbanView - will fail until we create it
import KanbanView from '../modules/KanbanView.js';

describe('KanbanView', () => {
    let container;
    let kanbanView;
    let mockLogger;
    const templateName = 'patient_records';
    const states = [
        'waiting_for_report',
        'summarizing',
        'fact_checking',
        'ready',
        'failed',
        'shutdown'
    ];

    beforeEach(() => {
        // Create container element
        container = document.createElement('div');
        container.id = 'kanban-container';
        document.body.appendChild(container);

        // Mock logger - simple object with functions
        mockLogger = {
            log: () => {},
            error: () => {},
            warn: () => {},
            info: () => {}
        };
    });

    afterEach(() => {
        // Cleanup
        if (container && container.parentNode) {
            container.parentNode.removeChild(container);
        }
        kanbanView = null;
    });

    describe('Constructor', () => {
        it('should initialize with template name and states', () => {
            kanbanView = new KanbanView(container, templateName, states, mockLogger);
            
            expect(kanbanView.container).toBe(container);
            expect(kanbanView.templateName).toBe(templateName);
            expect(kanbanView.states).toEqual(states);
            expect(kanbanView.logger).toBe(mockLogger);
        });

        it('should initialize with empty cards map', () => {
            kanbanView = new KanbanView(container, templateName, states, mockLogger);
            
            expect(kanbanView.cards).toBeDefined();
            expect(Object.keys(kanbanView.cards).length).toBe(0);
        });

        it('should be hidden by default', () => {
            kanbanView = new KanbanView(container, templateName, states, mockLogger);
            
            expect(kanbanView.isVisible).toBe(false);
        });
    });

    describe('render()', () => {
        beforeEach(() => {
            kanbanView = new KanbanView(container, templateName, states, mockLogger);
        });

        it('should create column for each state', () => {
            kanbanView.render();
            
            const columns = container.querySelectorAll('.kanban-column');
            expect(columns.length).toBe(states.length);
        });

        it('should create column headers with state names', () => {
            kanbanView.render();
            
            const headers = container.querySelectorAll('.kanban-column-header');
            expect(headers.length).toBe(states.length);
            
            states.forEach((state, index) => {
                expect(headers[index].textContent).toContain(state);
            });
        });

        it('should create card containers for each column', () => {
            kanbanView.render();
            
            const cardContainers = container.querySelectorAll('.kanban-cards');
            expect(cardContainers.length).toBe(states.length);
        });

        it('should add kanban-view class to container', () => {
            kanbanView.render();
            
            expect(container.classList.contains('kanban-view')).toBe(true);
        });
    });

    describe('addCard()', () => {
        beforeEach(() => {
            kanbanView = new KanbanView(container, templateName, states, mockLogger);
            kanbanView.render();
        });

        it('should add card to correct state column', () => {
            const machineName = 'patient_record_1';
            const state = 'summarizing';
            
            kanbanView.addCard(machineName, state);
            
            const column = container.querySelector(`[data-state="${state}"] .kanban-cards`);
            const card = column.querySelector(`[data-machine="${machineName}"]`);
            
            expect(card).toBeTruthy();
            expect(card.textContent).toContain(machineName);
        });

        it('should track card in internal map', () => {
            const machineName = 'patient_record_1';
            const state = 'summarizing';
            
            kanbanView.addCard(machineName, state);
            
            expect(kanbanView.cards[machineName]).toBeDefined();
            expect(kanbanView.cards[machineName].state).toBe(state);
        });

        it('should add multiple cards to same column', () => {
            kanbanView.addCard('patient_record_1', 'summarizing');
            kanbanView.addCard('patient_record_2', 'summarizing');
            
            const column = container.querySelector(`[data-state="summarizing"] .kanban-cards`);
            const cards = column.querySelectorAll('.kanban-card');
            
            expect(cards.length).toBe(2);
        });

        it('should log error if state does not exist', () => {
            // Should not throw, just log error
            expect(() => {
                kanbanView.addCard('patient_record_1', 'invalid_state');
            }).not.toThrow();
        });
    });

    describe('updateCard()', () => {
        beforeEach(() => {
            kanbanView = new KanbanView(container, templateName, states, mockLogger);
            kanbanView.render();
            kanbanView.addCard('patient_record_1', 'waiting_for_report');
        });

        it('should move card to new state column', () => {
            kanbanView.updateCard('patient_record_1', 'summarizing');
            
            const oldColumn = container.querySelector(`[data-state="waiting_for_report"] .kanban-cards`);
            const newColumn = container.querySelector(`[data-state="summarizing"] .kanban-cards`);
            
            expect(oldColumn.querySelector('[data-machine="patient_record_1"]')).toBeFalsy();
            expect(newColumn.querySelector('[data-machine="patient_record_1"]')).toBeTruthy();
        });

        it('should update internal state tracking', () => {
            kanbanView.updateCard('patient_record_1', 'summarizing');
            
            expect(kanbanView.cards['patient_record_1'].state).toBe('summarizing');
        });

        it('should do nothing if machine not found', () => {
            // Should not throw, just log warning
            expect(() => {
                kanbanView.updateCard('nonexistent_machine', 'summarizing');
            }).not.toThrow();
        });

        it('should do nothing if already in target state', () => {
            const initialHTML = container.innerHTML;
            
            kanbanView.updateCard('patient_record_1', 'waiting_for_report');
            
            expect(container.innerHTML).toBe(initialHTML);
        });
    });

    describe('removeCard()', () => {
        beforeEach(() => {
            kanbanView = new KanbanView(container, templateName, states, mockLogger);
            kanbanView.render();
            kanbanView.addCard('patient_record_1', 'summarizing');
        });

        it('should remove card from DOM', () => {
            kanbanView.removeCard('patient_record_1');
            
            const card = container.querySelector('[data-machine="patient_record_1"]');
            expect(card).toBeFalsy();
        });

        it('should remove card from internal map', () => {
            kanbanView.removeCard('patient_record_1');
            
            expect(kanbanView.cards['patient_record_1']).toBeUndefined();
        });

        it('should do nothing if machine not found', () => {
            // Should not throw, just log warning
            expect(() => {
                kanbanView.removeCard('nonexistent_machine');
            }).not.toThrow();
        });
    });

    describe('show()', () => {
        beforeEach(() => {
            kanbanView = new KanbanView(container, templateName, states, mockLogger);
            kanbanView.render();
        });

        it('should make container visible', () => {
            kanbanView.show();
            
            expect(container.style.display).not.toBe('none');
        });

        it('should set isVisible flag', () => {
            kanbanView.show();
            
            expect(kanbanView.isVisible).toBe(true);
        });

        it('should add visible class', () => {
            kanbanView.show();
            
            expect(container.classList.contains('kanban-visible')).toBe(true);
        });
    });

    describe('hide()', () => {
        beforeEach(() => {
            kanbanView = new KanbanView(container, templateName, states, mockLogger);
            kanbanView.render();
            kanbanView.show();
        });

        it('should hide container', () => {
            kanbanView.hide();
            
            expect(container.style.display).toBe('none');
        });

        it('should clear isVisible flag', () => {
            kanbanView.hide();
            
            expect(kanbanView.isVisible).toBe(false);
        });

        it('should remove visible class', () => {
            kanbanView.hide();
            
            expect(container.classList.contains('kanban-visible')).toBe(false);
        });
    });

    describe('Integration', () => {
        it('should handle full workflow: render, add, update, remove', () => {
            kanbanView = new KanbanView(container, templateName, states, mockLogger);
            kanbanView.render();
            kanbanView.show();
            
            // Add cards
            kanbanView.addCard('patient_record_1', 'waiting_for_report');
            kanbanView.addCard('patient_record_2', 'summarizing');
            kanbanView.addCard('patient_record_3', 'fact_checking');
            
            let cards = container.querySelectorAll('.kanban-card');
            expect(cards.length).toBe(3);
            
            // Update states
            kanbanView.updateCard('patient_record_1', 'summarizing');
            kanbanView.updateCard('patient_record_2', 'fact_checking');
            kanbanView.updateCard('patient_record_3', 'ready');
            
            // Verify positions
            expect(container.querySelector('[data-state="summarizing"] .kanban-cards')
                .querySelectorAll('.kanban-card').length).toBe(1);
            expect(container.querySelector('[data-state="fact_checking"] .kanban-cards')
                .querySelectorAll('.kanban-card').length).toBe(1);
            expect(container.querySelector('[data-state="ready"] .kanban-cards')
                .querySelectorAll('.kanban-card').length).toBe(1);
            
            // Remove one
            kanbanView.removeCard('patient_record_3');
            cards = container.querySelectorAll('.kanban-card');
            expect(cards.length).toBe(2);
        });
    });

    describe('State Groups', () => {
        const stateGroups = [
            {
                name: 'IDLE',
                states: ['waiting_for_report']
            },
            {
                name: 'PROCESSING',
                states: ['summarizing', 'fact_checking']
            },
            {
                name: 'COMPLETION',
                states: ['ready', 'failed', 'shutdown']
            }
        ];

        describe('Constructor with state groups', () => {
            it('should accept state groups parameter', () => {
                kanbanView = new KanbanView(container, templateName, states, mockLogger, stateGroups);
                
                expect(kanbanView.stateGroups).toBe(stateGroups);
            });

            it('should work without state groups (backwards compatibility)', () => {
                kanbanView = new KanbanView(container, templateName, states, mockLogger);
                
                expect(kanbanView.stateGroups).toBeNull();
            });
        });

        describe('Grouped rendering', () => {
            beforeEach(() => {
                kanbanView = new KanbanView(container, templateName, states, mockLogger, stateGroups);
            });

            it('should create group containers when state groups provided', () => {
                kanbanView.render();
                
                const groups = container.querySelectorAll('.kanban-group');
                expect(groups.length).toBe(stateGroups.length);
            });

            it('should create group headers with correct names', () => {
                kanbanView.render();
                
                const groupHeaders = container.querySelectorAll('.kanban-group-header');
                expect(groupHeaders.length).toBe(stateGroups.length);
                
                stateGroups.forEach((group, index) => {
                    expect(groupHeaders[index].textContent).toBe(group.name);
                });
            });

            it('should preserve group order from metadata', () => {
                kanbanView.render();
                
                const groups = container.querySelectorAll('.kanban-group');
                
                stateGroups.forEach((group, index) => {
                    expect(groups[index].getAttribute('data-group')).toBe(group.name);
                });
            });

            it('should create columns within correct groups', () => {
                kanbanView.render();
                
                // Check IDLE group has 1 state section
                const idleGroup = container.querySelector('[data-group="IDLE"]');
                const idleStates = idleGroup.querySelectorAll('.kanban-group-state');
                expect(idleStates.length).toBe(1);
                
                // Check PROCESSING group has 2 state sections
                const processingGroup = container.querySelector('[data-group="PROCESSING"]');
                const processingStates = processingGroup.querySelectorAll('.kanban-group-state');
                expect(processingStates.length).toBe(2);
                
                // Check COMPLETION group has 3 state sections
                const completionGroup = container.querySelector('[data-group="COMPLETION"]');
                const completionStates = completionGroup.querySelectorAll('.kanban-group-state');
                expect(completionStates.length).toBe(3);
            });

            it('should still track all columns in internal map', () => {
                kanbanView.render();
                
                // All states should be in the columns map
                states.forEach(state => {
                    expect(kanbanView.columns[state]).toBeDefined();
                });
            });
        });

        describe('Card operations with groups', () => {
            beforeEach(() => {
                kanbanView = new KanbanView(container, templateName, states, mockLogger, stateGroups);
                kanbanView.render();
            });

            it('should add cards to correct state column within group', () => {
                kanbanView.addCard('patient_record_1', 'waiting_for_report');
                kanbanView.addCard('patient_record_2', 'summarizing');
                
                // Card should be in IDLE group
                const idleGroup = container.querySelector('[data-group="IDLE"]');
                const card1 = idleGroup.querySelector('[data-machine="patient_record_1"]');
                expect(card1).toBeTruthy();
                
                // Card should be in PROCESSING group
                const processingGroup = container.querySelector('[data-group="PROCESSING"]');
                const card2 = processingGroup.querySelector('[data-machine="patient_record_2"]');
                expect(card2).toBeTruthy();
            });

            it('should move cards between groups when state changes', () => {
                kanbanView.addCard('patient_record_1', 'waiting_for_report');
                
                // Initially in IDLE
                let idleGroup = container.querySelector('[data-group="IDLE"]');
                let card = idleGroup.querySelector('[data-machine="patient_record_1"]');
                expect(card).toBeTruthy();
                
                // Move to PROCESSING
                kanbanView.updateCard('patient_record_1', 'summarizing');
                
                // Should now be in PROCESSING
                idleGroup = container.querySelector('[data-group="IDLE"]');
                card = idleGroup.querySelector('[data-machine="patient_record_1"]');
                expect(card).toBeFalsy();
                
                const processingGroup = container.querySelector('[data-group="PROCESSING"]');
                card = processingGroup.querySelector('[data-machine="patient_record_1"]');
                expect(card).toBeTruthy();
            });

            it('should handle full workflow with groups', () => {
                kanbanView.show();
                
                // Add cards to different groups
                kanbanView.addCard('patient_record_1', 'waiting_for_report');  // IDLE
                kanbanView.addCard('patient_record_2', 'summarizing');         // PROCESSING
                kanbanView.addCard('patient_record_3', 'ready');               // COMPLETION
                
                let cards = container.querySelectorAll('.kanban-card');
                expect(cards.length).toBe(3);
                
                // Move cards through workflow
                kanbanView.updateCard('patient_record_1', 'summarizing');     // IDLE → PROCESSING
                kanbanView.updateCard('patient_record_2', 'fact_checking');   // Within PROCESSING
                kanbanView.updateCard('patient_record_3', 'shutdown');        // Within COMPLETION
                
                // Verify all cards still exist
                cards = container.querySelectorAll('.kanban-card');
                expect(cards.length).toBe(3);
                
                // Verify card positions
                const processingGroup = container.querySelector('[data-group="PROCESSING"]');
                const processingCards = processingGroup.querySelectorAll('.kanban-card');
                expect(processingCards.length).toBe(2);
                
                const completionGroup = container.querySelector('[data-group="COMPLETION"]');
                const completionCards = completionGroup.querySelectorAll('.kanban-card');
                expect(completionCards.length).toBe(1);
            });
        });

        describe('Flat vs Grouped rendering', () => {
            it('should render flat when no groups provided', () => {
                kanbanView = new KanbanView(container, templateName, states, mockLogger);
                kanbanView.render();
                
                // Should not have group containers
                const groups = container.querySelectorAll('.kanban-group');
                expect(groups.length).toBe(0);
                
                // Should have direct columns
                const columns = container.querySelectorAll('.kanban-column');
                expect(columns.length).toBe(states.length);
            });

            it('should render grouped when groups provided', () => {
                kanbanView = new KanbanView(container, templateName, states, mockLogger, stateGroups);
                kanbanView.render();
                
                // Should have group containers
                const groups = container.querySelectorAll('.kanban-group');
                expect(groups.length).toBe(stateGroups.length);
                
                // Columns should be within groups
                const directColumns = container.querySelectorAll(':scope > .kanban-column');
                expect(directColumns.length).toBe(0);
            });
        });
    });
});
