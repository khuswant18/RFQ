const defaultBase = typeof window !== "undefined"
  ? `${window.location.origin}/api/v1`
  : "http://localhost:8000/api/v1"

export const API_BASE = import.meta.env.VITE_API_URL || defaultBase
export const API_ROOT = API_BASE.replace(/\/api\/v1\/?$/, "")
