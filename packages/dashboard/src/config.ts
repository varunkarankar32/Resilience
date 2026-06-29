const config = {
  socketUrl: import.meta.env.VITE_SOCKET_URL || window.location.origin,
  apiUrl: import.meta.env.VITE_API_URL || window.location.origin,
} as const;

export default config;
