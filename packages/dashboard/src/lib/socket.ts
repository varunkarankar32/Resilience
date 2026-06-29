import { io, Socket } from "socket.io-client";
import config from "../config";

let socket: Socket | null = null;

export function getSocket(): Socket {
  if (!socket) {
    socket = io(config.socketUrl, {
      path: "/socket.io",
      transports: ["websocket", "polling"],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 10000,
    });

    socket.on("connect", () => {
      console.log("[Socket.io] Connected:", socket?.id);
    });

    socket.on("disconnect", (reason) => {
      console.log("[Socket.io] Disconnected:", reason);
    });

    socket.on("connect_error", (error) => {
      console.error("[Socket.io] Connection error:", error.message);
    });
  }

  return socket;
}

export function disconnectSocket(): void {
  if (socket) {
    socket.removeAllListeners();
    socket.disconnect();
    socket = null;
    console.log("[Socket.io] Disconnected and cleaned up");
  }
}
