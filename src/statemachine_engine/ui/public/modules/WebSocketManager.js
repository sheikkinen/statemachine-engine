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
        this.websocketUrl = null;
    }

    async connect() {
        this.log('info', 'Connecting to WebSocket server...');

        // Fetch configuration if not already available
        if (!this.websocketUrl) {
            try {
                const response = await fetch('/api/config');
                const config = await response.json();
                this.websocketUrl = config.websocket_url;
                this.log('info', `WebSocket URL: ${this.websocketUrl}`);
            } catch (error) {
                console.error('Failed to fetch WebSocket configuration:', error);
                this.log('error', 'Failed to get WebSocket configuration');
                // Fallback to default port 3002 or derive from UI port
                const uiPort = window.location.port || '3001';
                const fallbackWsPort = uiPort === '3001' ? '3002' : (parseInt(uiPort) + 1);
                this.websocketUrl = `ws://localhost:${fallbackWsPort}/ws/events`;
                this.log('warning', 'Using fallback WebSocket URL: ' + this.websocketUrl);
            }
        }

        try {
            this.websocket = new WebSocket(this.websocketUrl);

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
        // Handle control messages (keepalive protocol)
        if (data.type === 'ping') {
            // Server sent keepalive ping, optionally respond with pong
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send('pong');
            }
            return;
        }
        
        if (data.type === 'pong') {
            // Server acknowledged our ping, ignore
            return;
        }
        
        // Handle application events
        const handler = this.eventHandlers[data.type];
        if (handler) {
            handler(data);
        } else {
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

        setTimeout(async () => {
            await this.connect();
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
