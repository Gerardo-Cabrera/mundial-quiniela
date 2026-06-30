import axios from "axios";
import { API_BASE_URL, AUTH_STORAGE_KEY } from "@/config";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

/**
 * Lee el token JWT desde el store persistido de Zustand.
 * Zustand persist guarda en localStorage bajo la key "mundial-auth".
 */
function getPersistedToken(): string | null {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.state?.token ?? null;
  } catch {
    return null;
  }
}

// Adjunta el token JWT en cada request
apiClient.interceptors.request.use((config) => {
  const token = getPersistedToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirige al login si el token expira (excepto en endpoints de auth,
// donde el 401 es parte del flujo normal: credenciales incorrectas).
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const isAuthRequest = err.config?.url?.includes("/api/auth/");
    if (err.response?.status === 401 && !isAuthRequest) {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

/**
 * Normaliza un error de axios a un string seguro para mostrar. FastAPI devuelve los
 * errores de validación (422) como `detail: [{type, loc, msg, ...}]` (array de
 * objetos); renderizar ese objeto como hijo de React rompe la app (error #31). Aquí se
 * extrae el texto: string directo, o los `msg` del array; si no, el `fallback`.
 */
export function apiErrorMessage(err: unknown, fallback: string): string {
  const detail = (err as any)?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => (d && typeof d.msg === "string" ? (d.msg as string) : ""))
      .filter(Boolean);
    if (msgs.length) return msgs.join(". ");
  }
  return fallback;
}

export default apiClient;
