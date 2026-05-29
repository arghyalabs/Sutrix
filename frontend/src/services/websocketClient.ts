export type SocketMessageCallback = (msg: any) => void;
export type SocketStateCallback = (connected: boolean) => void;

export class ResilientWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private clientId: string;
  private isClosedIntentional: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private baseReconnectDelay: number = 1000; // 1s
  
  private messageListeners: Set<SocketMessageCallback> = new Set();
  private stateListeners: Set<SocketStateCallback> = new Set();

  constructor(clientId: string) {
    this.clientId = clientId;
    const wsBase = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000';
    this.url = `${wsBase}/ws/jobs/${clientId}`;
  }

  public connect() {
    this.isClosedIntentional = false;
    try {
      console.log(`WebSocket: Initializing resilient gateway for ${this.clientId}...`);
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket: Connection established.');
        this.reconnectAttempts = 0;
        this.triggerStateListeners(true);
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          // Handle server-side ping checks automatically
          if (message.type === 'PING') {
            this.send({ type: 'PONG' });
            return;
          }
          
          this.triggerMessageListeners(message);
        } catch (e) {
          console.warn('WebSocket Warning: Failed to parse incoming JSON frame.', e);
        }
      };

      this.ws.onclose = (event) => {
        this.triggerStateListeners(false);
        if (!this.isClosedIntentional) {
          console.warn(`WebSocket Warning: Socket dropped (Code: ${event.code}). Attempting reconnection...`);
          this.handleReconnection();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket Exception encountered:', error);
      };
    } catch (e) {
      console.error('WebSocket Exception during setup:', e);
      this.handleReconnection();
    }
  }

  private handleReconnection() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(`WebSocket Error: Maximum reconnection attempts (${this.maxReconnectAttempts}) exhausted.`);
      return;
    }

    this.reconnectAttempts += 1;
    const delay = Math.min(10000, this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts));
    
    console.log(`WebSocket: Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms...`);
    setTimeout(() => {
      if (!this.isClosedIntentional) {
        this.connect();
      }
    }, delay);
  }

  public send(payload: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  public disconnect() {
    console.log('WebSocket: User-initiated termination.');
    this.isClosedIntentional = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.triggerStateListeners(false);
  }

  // Listener registrations
  public addMessageListener(cb: SocketMessageCallback) {
    this.messageListeners.add(cb);
  }

  public removeMessageListener(cb: SocketMessageCallback) {
    this.messageListeners.delete(cb);
  }

  public addStateListener(cb: SocketStateCallback) {
    this.stateListeners.add(cb);
    // Emit initial status
    cb(this.ws?.readyState === WebSocket.OPEN);
  }

  public removeStateListener(cb: SocketStateCallback) {
    this.stateListeners.delete(cb);
  }

  private triggerMessageListeners(msg: any) {
    this.messageListeners.forEach((listener) => {
      try {
        listener(msg);
      } catch (e) {
        console.error('WebSocket Message Listener Exception:', e);
      }
    });
  }

  private triggerStateListeners(connected: boolean) {
    this.stateListeners.forEach((listener) => {
      try {
        listener(connected);
      } catch (e) {
        console.error('WebSocket State Listener Exception:', e);
      }
    });
  }
}
