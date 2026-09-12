import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

function wsUrl(): string {
  const token = sessionStorage.getItem("token");
  if (!token) return "";
  const base = import.meta.env.VITE_API_URL || window.location.origin;
  const proto = base.startsWith("https") ? "wss" : "ws";
  return `${proto}://${base.replace(/^https?:\/\//, "")}/api/v1/dashboard/ws?token=${token}`;
}

const EVENT_QUERY_MAP: Record<string, string[]> = {
  dashboard_update: ["dashboard"],
  product_created: ["catalog", "products"],
  product_updated: ["catalog", "products"],
  product_deleted: ["catalog", "products"],
  inventory_updated: ["stock", "catalog"],
  purchase_created: ["purchases", "stock", "catalog", "dashboard"],
  sale_created: ["sales", "stock", "catalog", "invoices", "dashboard"],
};

export function useWebSocket() {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const url = wsUrl();
    if (!url) return;

    let reconnectTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      if (wsRef.current?.readyState === WebSocket.OPEN) return;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const type: string = data.type ?? data;
          const keys = EVENT_QUERY_MAP[type];
          if (keys) {
            for (const key of keys) {
              queryClient.invalidateQueries({ queryKey: [key] });
            }
          }
        } catch {
          /* ignora mensajes no-JSON */
        }
      };

      ws.onclose = () => {
        if (wsRef.current === ws) {
          wsRef.current = null;
          reconnectTimeout = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => ws.close();
    }

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [queryClient]);
}
