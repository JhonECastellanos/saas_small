const BASE_URL = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : "Error de la API");
    this.status = status;
    this.detail = detail;
  }
}

function getToken(): string | null {
  return sessionStorage.getItem("token");
}

export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown; params?: Record<string, unknown>; formData?: boolean } = {},
): Promise<T> {
  const url = new URL(`${BASE_URL}/api/v1${path}`, window.location.origin);
  if (options.params) {
    for (const [key, value] of Object.entries(options.params)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const fetchOptions: RequestInit = { method: options.method ?? "GET" };
  if (options.body !== undefined) {
    if (options.formData) {
      fetchOptions.body = options.body as BodyInit;
    } else {
      headers["Content-Type"] = "application/json";
      fetchOptions.body = JSON.stringify(options.body);
    }
  }
  fetchOptions.headers = headers;

  const resp = await fetch(url.toString(), fetchOptions);

  if (resp.status === 401 && !path.startsWith("/auth/login")) {
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("user");
    window.location.href = "/login";
    throw new ApiError(401, "Sesión expirada");
  }
  if (!resp.ok) {
    let detail: unknown = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? body;
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(resp.status, detail);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") return error.detail;
    if (error.detail && typeof error.detail === "object") {
      const d = error.detail as Record<string, unknown>;
      if (typeof d.message === "string") return d.message;
      if (Array.isArray(d)) {
        return d
          .map((e) => (typeof e?.msg === "string" ? e.msg : JSON.stringify(e)))
          .join("; ");
      }
      return JSON.stringify(error.detail);
    }
  }
  if (error instanceof Error) return error.message;
  return "Error inesperado";
}
