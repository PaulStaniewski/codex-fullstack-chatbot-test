const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
let authRefreshConfig = null;
let refreshInFlightPromise = null;

export function getApiBaseUrl() {
  return API_BASE_URL.replace(/\/$/, "");
}

export function configureAuthRefresh(config) {
  authRefreshConfig = config || null;
}

async function tryRefreshAccessToken() {
  if (!authRefreshConfig) {
    return null;
  }

  const refreshToken = authRefreshConfig.getRefreshToken?.();
  if (!refreshToken) {
    return null;
  }

  if (!refreshInFlightPromise) {
    refreshInFlightPromise = (async () => {
      try {
        const data = await apiFetch("/refresh", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken }),
          skipAuthRefresh: true,
        });
        if (!data?.access_token) {
          return null;
        }
        authRefreshConfig.onTokens?.({
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
        });
        return data.access_token;
      } catch {
        return null;
      } finally {
        refreshInFlightPromise = null;
      }
    })();
  }

  return refreshInFlightPromise;
}

export function getStreamUrl(conversationId, message, token) {
  const params = new URLSearchParams({
    conversation_id: String(conversationId),
    message,
    token,
  });

  return `${getApiBaseUrl()}/chat-stream?${params.toString()}`;
}

export function getLessonStudyStreamUrl({ lessonId, action, question, stepIndex, token }) {
  const params = new URLSearchParams({
    action,
    token,
  });

  if (question) {
    params.set("question", question);
  }

  if (stepIndex !== undefined && stepIndex !== null) {
    params.set("step_index", String(stepIndex));
  }

  return `${getApiBaseUrl()}/lessons/${encodeURIComponent(lessonId)}/study-stream?${params.toString()}`;
}

function getSseEventData(event) {
  return typeof event?.data === "string" ? event.data : "";
}

export function streamLessonStudyAssistant({
  lessonId,
  action,
  question,
  stepIndex,
  token,
  onToken,
  onError,
  onDone,
}) {
  const stream = new EventSource(
    getLessonStudyStreamUrl({ lessonId, action, question, stepIndex, token }),
  );
  let receivedContent = "";
  let didFinalize = false;

  stream.onmessage = (event) => {
    receivedContent += event.data;
    onToken?.(event.data, receivedContent);

    if (receivedContent.startsWith("Error:")) {
      didFinalize = true;
      stream.close();
      onError?.(receivedContent);
      onDone?.(receivedContent);
    }
  };

  stream.addEventListener("done", () => {
    if (didFinalize) {
      return;
    }

    didFinalize = true;
    stream.close();
    onDone?.(receivedContent);
  });

  stream.addEventListener("error", (event) => {
    if (didFinalize) {
      return;
    }

    didFinalize = true;
    stream.close();
    const errorMessage = getSseEventData(event) || "Unable to get study response.";
    onError?.(errorMessage);
    onDone?.(receivedContent || errorMessage);
  });

  return () => {
    didFinalize = true;
    stream.close();
  };
}

export function getPracticeFeedbackStreamUrl({ lessonId, stepIndex, answer, token }) {
  const params = new URLSearchParams({
    step_index: String(stepIndex),
    answer,
    token,
  });

  return `${getApiBaseUrl()}/lessons/${encodeURIComponent(lessonId)}/practice-feedback-stream?${params.toString()}`;
}

export function streamPracticeFeedback({
  lessonId,
  stepIndex,
  answer,
  token,
  onToken,
  onError,
  onDone,
}) {
  const stream = new EventSource(
    getPracticeFeedbackStreamUrl({ lessonId, stepIndex, answer, token }),
  );
  let receivedContent = "";
  let didFinalize = false;

  stream.onmessage = (event) => {
    receivedContent += event.data;
    onToken?.(event.data, receivedContent);

    if (receivedContent.startsWith("Error:")) {
      didFinalize = true;
      stream.close();
      onError?.(receivedContent);
      onDone?.(receivedContent);
    }
  };

  stream.addEventListener("done", () => {
    if (didFinalize) {
      return;
    }

    didFinalize = true;
    stream.close();
    onDone?.(receivedContent);
  });

  stream.addEventListener("error", (event) => {
    if (didFinalize) {
      return;
    }

    didFinalize = true;
    stream.close();
    const errorMessage = getSseEventData(event) || "Unable to get practice feedback.";
    onError?.(errorMessage);
    onDone?.(receivedContent || errorMessage);
  });

  return () => {
    didFinalize = true;
    stream.close();
  };
}

export async function apiFetch(path, { token, skipAuthRefresh = false, ...options } = {}) {
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
    if (!skipAuthRefresh && token && (response.status === 401 || response.status === 403)) {
      const refreshedAccessToken = await tryRefreshAccessToken();
      if (refreshedAccessToken) {
        return apiFetch(path, {
          ...options,
          token: refreshedAccessToken,
          skipAuthRefresh: true,
        });
      }
    }

    const message = data?.detail || "Request failed";
    const error = new Error(message);
    error.status = response.status;
    error.detail = data?.detail;
    throw error;
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

export function completeLessonStep(lessonId, stepIndex, token) {
  return apiFetch(
    `/lessons/${encodeURIComponent(lessonId)}/steps/${encodeURIComponent(stepIndex)}/complete`,
    {
      method: "POST",
      token,
    },
  );
}

export function getLessonProgress(token) {
  return apiFetch("/lessons/progress", { token });
}

export function getPracticeHistory(lessonId, token) {
  return apiFetch(`/lessons/${encodeURIComponent(lessonId)}/practice-history`, { token });
}

export function recordProgressActivity(activeSeconds, token) {
  return apiFetch("/progress/activity", {
    method: "POST",
    token,
    body: JSON.stringify({ active_seconds: activeSeconds }),
  });
}

export function logoutUser(token) {
  return apiFetch("/logout", {
    method: "POST",
    token,
  });
}
