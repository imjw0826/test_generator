export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const LLM_PROVIDER_STORAGE_KEY = "study-qgen-llm-provider";
export type LlmProvider = "claude" | "deepseek";

export function getSelectedLlmProvider(): LlmProvider {
  if (typeof window === "undefined") return "claude";
  const provider = localStorage.getItem(LLM_PROVIDER_STORAGE_KEY);
  return provider === "deepseek" ? "deepseek" : "claude";
}

function llmHeaders(): Record<string, string> {
  return { "X-LLM-Provider": getSelectedLlmProvider() };
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...llmHeaders(), ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

export async function apiUpload<T>(
  path: string,
  formData: FormData
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { ...llmHeaders() },
    body: formData,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

export async function apiDownload(
  path: string,
  options?: RequestInit
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...llmHeaders(), ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }

  const disposition = res.headers.get("content-disposition") ?? "";
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
  return {
    blob: await res.blob(),
    filename: filenameMatch?.[1] ?? "exam.pdf",
  };
}
