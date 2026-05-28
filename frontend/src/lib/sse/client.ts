const DEFAULT_SSE_BASE_URL = "http://localhost:8000";

export function getSseBaseUrl() {
  return process.env.NEXT_PUBLIC_SSE_BASE_URL ?? DEFAULT_SSE_BASE_URL;
}

export function buildSseUrl(path: string) {
  const baseUrl = getSseBaseUrl().replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  return `${baseUrl}${normalizedPath}`;
}
