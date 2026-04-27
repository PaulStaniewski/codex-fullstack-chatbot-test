const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export function getApiBaseUrl() {
  return API_BASE_URL.replace(/\/$/, "");
}

export function getStreamUrl(conversationId, message, token) {
  const params = new URLSearchParams({
    conversation_id: String(conversationId),
    message,
    token,
  });

  return `${getApiBaseUrl()}/chat-stream?${params.toString()}`;
}

export async function apiFetch(path, { token, ...options } = {}) {
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...options,
    headers,
  });

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    const message = data?.detail || "Request failed";
    throw new Error(message);
  }

  return data;
}

export function getLesson(lessonId, token) {
  return apiFetch(`/lessons/${encodeURIComponent(lessonId)}`, { token });
}

export function nextLessonStep(lessonId, token) {
  return apiFetch(`/lessons/${encodeURIComponent(lessonId)}/next`, {
    method: "POST",
    token,
  });
}

export function getLessonProgress(token) {
  return apiFetch("/lessons/progress", { token });
}
