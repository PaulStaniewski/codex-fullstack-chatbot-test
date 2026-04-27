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

export function getLessonTutorStreamUrl({ lessonId, question, stepIndex, token }) {
  const params = new URLSearchParams({
    question,
    token,
  });

  if (stepIndex !== undefined && stepIndex !== null) {
    params.set("step_index", String(stepIndex));
  }

  return `${getApiBaseUrl()}/lessons/${encodeURIComponent(lessonId)}/tutor-stream?${params.toString()}`;
}

export function streamLessonTutor({
  lessonId,
  question,
  stepIndex,
  token,
  onToken,
  onError,
  onDone,
}) {
  const stream = new EventSource(
    getLessonTutorStreamUrl({ lessonId, question, stepIndex, token }),
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

  stream.onerror = () => {
    if (didFinalize) {
      return;
    }

    didFinalize = true;
    stream.close();
    if (receivedContent) {
      onDone?.(receivedContent);
    } else {
      onError?.("Unable to get tutor response.");
    }
  };

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

  stream.onerror = () => {
    if (didFinalize) {
      return;
    }

    didFinalize = true;
    stream.close();
    if (receivedContent) {
      onDone?.(receivedContent);
    } else {
      onError?.("Unable to get practice feedback.");
    }
  };

  return () => {
    didFinalize = true;
    stream.close();
  };
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
