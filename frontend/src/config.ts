/**
 * Constantes centralizadas del frontend.
 * Cambiar aquí en lugar de hardcodear en múltiples archivos.
 */

// Key propia: la sesión es independiente de la app de Champions (no se pisan).
export const AUTH_STORAGE_KEY = "mundial-auth";

// Cierre de sesión por inactividad: 1 h sin interacción del usuario. La marca de
// última actividad se persiste para aplicarlo también tras recargar/reabrir.
export const SESSION_IDLE_MS = 60 * 60 * 1000;
export const LAST_ACTIVITY_KEY = "mundial-last-activity";

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8001";

export const TOASTER_STYLE = {
  background: "#1a1f3d",
  color: "#c9c9d1",
  border: "1px solid rgba(255,255,255,0.1)",
} as const;
