/**
 * WebSocketManager - Handles WebSocket connection and event routing
 */
export class WebSocketManager {
    constructor(eventHandlers) {
        this.websocket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectDelay = 30000; // 30 seconds
        this.pingInterval = null;
        this.eventHandlers = eventHandlers;
    }

    connect() {
        this.log('info', 'Connecting to WebSocket server...');

        try {
            this.websocket = new WebSocket('ws://localhost:3002/ws/events');

            this.websocket.onopen = () => {
                this.isConnected = true;
                this.log('success', '✓ WebSocket connection established');
                this.reconnectAttempts = 0;
                this.startPingInterval();
            };

            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.debug('WebSocket message received:', data);
                    this.handleEvent(data);
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e, 'Raw data:', event.data);
                }
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.log('error', 'WebSocket error occurred');
            };

            this.websocket.onclose = () => {
                this.isConnected = false;
                this.stopPingInterval();
                this.log('warning', 'WebSocket disconnected. Reconnecting...');
                this.scheduleReconnect();
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.log('error', `Connection failed: ${error.message}`);
            this.scheduleReconnect();
        }
    }

    handleEvent(data) {
        const handler = this.eventHandlers[data.type];
        if (handler) {
            handler(data);
        } else if (data.type !== 'pong') {
            console.warn('Unknown event type:', data.type, 'Full event:', data);
        }
    }

    startPingInterval() {
        this.pingInterval = setInterval(() => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send('ping');
            }
        }, 30000);
    }

    stopPingInterval() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    scheduleReconnect() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }

        const delay = Math.min(
            1000 * Math.pow(2, this.reconnectAttempts),
            this.maxReconnectDelay
        );

        this.reconnectAttempts++;
        this.log('info', `Reconnecting in ${delay/1000}s...`);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    log(level, message) {
        if (this.eventHandlers.log) {
            this.eventHandlers.log(level, message);
        }
    }

    destroy() {
        this.stopPingInterval();
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
    }
}
