"use client";

import { useEffect, useRef, useCallback } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

type WSEvent = {
  type: string;
  data: Record<string, unknown>;
};

type EventHandler = (data: Record<string, unknown>) => void;

export function useLockerSocket(lockerId: string, handlers: Record<string, EventHandler>) {
  const ws = useRef<WebSocket | null>(null);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  const connect = useCallback(() => {
    const token = localStorage.getItem("va_access_token");
    const url = `${WS_URL}/ws/locker/${lockerId}${token ? `?token=${token}` : ""}`;
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      console.debug(`[VaultAlert WS] Locker room connected: ${lockerId}`);
      // Send keepalive ping every 25s
      const interval = setInterval(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send("ping");
        } else {
          clearInterval(interval);
        }
      }, 25_000);
    };

    ws.current.onmessage = (event) => {
      try {
        const msg: WSEvent = JSON.parse(event.data);
        if (msg.type && handlersRef.current[msg.type]) {
          handlersRef.current[msg.type](msg.data);
        }
        // Generic wildcard handler
        if (handlersRef.current["*"]) {
          handlersRef.current["*"](msg as unknown as Record<string, unknown>);
        }
      } catch {
        // pong response etc
      }
    };

    ws.current.onclose = () => {
      console.debug(`[VaultAlert WS] Locker room disconnected. Reconnecting in 3s...`);
      setTimeout(connect, 3_000);
    };

    ws.current.onerror = () => {
      ws.current?.close();
    };
  }, [lockerId]);

  useEffect(() => {
    connect();
    return () => {
      ws.current?.close();
    };
  }, [connect]);
}

export function useOrgSocket(orgId: string, handlers: Record<string, EventHandler>) {
  const ws = useRef<WebSocket | null>(null);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  const connect = useCallback(() => {
    const token = localStorage.getItem("va_access_token");
    const url = `${WS_URL}/ws/org/${orgId}${token ? `?token=${token}` : ""}`;
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      console.debug(`[VaultAlert WS] Org room connected: ${orgId}`);
      const interval = setInterval(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send("ping");
        } else clearInterval(interval);
      }, 25_000);
    };

    ws.current.onmessage = (event) => {
      try {
        const msg: WSEvent = JSON.parse(event.data);
        if (msg.type && handlersRef.current[msg.type]) {
          handlersRef.current[msg.type](msg.data);
        }
        if (handlersRef.current["*"]) {
          handlersRef.current["*"](msg as unknown as Record<string, unknown>);
        }
      } catch {}
    };

    ws.current.onclose = () => {
      setTimeout(connect, 3_000);
    };

    ws.current.onerror = () => {
      ws.current?.close();
    };
  }, [orgId]);

  useEffect(() => {
    connect();
    return () => ws.current?.close();
  }, [connect]);
}
