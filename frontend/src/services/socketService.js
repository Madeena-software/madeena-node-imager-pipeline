import io from 'socket.io-client';

// Socket URL selection similar to API: prefer explicit env, fall back to dev backend, otherwise same-origin
const isDevServer = window.location.port === '3000' || window.location.hostname === 'localhost';
const SOCKET_URL =
  process.env.REACT_APP_SOCKET_URL ||
  (isDevServer ? `http://${window.location.hostname}:5000` : window.location.origin);

class SocketService {
  constructor() {
    this.socket = null;
  }

  connect() {
    // Guard against duplicate connections (connected or currently connecting)
    if (this.socket && (this.socket.connected || this.socket.active)) {
      return;
    }

    // Disconnect existing socket if it's in a bad state
    if (this.socket) {
      this.socket.disconnect();
    }

    this.socket = io(SOCKET_URL, {
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    this.socket.on('connect', () => {
      console.info('[Socket] Connected to server');
    });

    this.socket.on('disconnect', (reason) => {
      console.info('[Socket] Disconnected:', reason);
    });

    this.socket.on('connect_error', (err) => {
      console.warn('[Socket] Connection error:', err.message);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  on(event, callback) {
    if (this.socket) {
      this.socket.on(event, callback);
    }
  }

  /** Remove a specific listener to prevent memory leaks. */
  off(event, callback) {
    if (this.socket) {
      this.socket.off(event, callback);
    }
  }

  emit(event, data) {
    if (this.socket) {
      this.socket.emit(event, data);
    }
  }
}

export default new SocketService();
