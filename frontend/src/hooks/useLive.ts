import { useEffect, useRef, useState } from 'react';
import { websocketUrl } from '../services/api';
import type { EngineState } from '../types';

export function useLive(onUpdate: () => void, onState: (state: EngineState) => void) {
  const [connected, setConnected] = useState(false);
  const callbacks = useRef({ onUpdate, onState });
  callbacks.current = { onUpdate, onState };
  useEffect(() => {
    let socket: WebSocket | undefined;
    let timer: ReturnType<typeof setTimeout>;
    let stopped = false;
    let attempts = 0;
    function connect() {
      if (stopped) return;
      socket = new WebSocket(websocketUrl);
      socket.onopen = () => { attempts = 0; setConnected(true); callbacks.current.onUpdate(); };
      socket.onmessage = event => {
        const message = JSON.parse(event.data);
        if (message.state) callbacks.current.onState(message.state);
        if (message.type !== 'heartbeat') callbacks.current.onUpdate();
      };
      socket.onclose = () => {
        setConnected(false);
        if (!stopped) timer = setTimeout(connect, Math.min(1000 * 2 ** attempts++, 15000));
      };
      socket.onerror = () => socket?.close();
    }
    connect();
    return () => { stopped = true; clearTimeout(timer); socket?.close(); };
  }, []);
  return connected;
}
