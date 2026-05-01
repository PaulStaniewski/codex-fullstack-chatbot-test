import { useEffect, useRef, useState } from "react";
import {
  apiFetch,
  completeLessonStep,
  getApiBaseUrl,
  getLesson,
  getLessonProgress,
  getStreamUrl,
  nextLessonStep,
  recordProgressActivity,
} from "./api.js";
import AchievementsPage from "./components/AchievementsPage.jsx";
import AchievementToast from "./components/AchievementToast.jsx";
import AuthView from "./components/AuthView.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import DashboardPage from "./components/DashboardPage.jsx";
import LessonView from "./components/LessonView.jsx";
import ProfilePage from "./components/ProfilePage.jsx";
import ProgressPage from "./components/ProgressPage.jsx";
import SettingsPage from "./components/SettingsPage.jsx";
import Sidebar from "./components/Sidebar.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";
import ToastStack from "./components/ToastStack.jsx";

const TOKEN_KEY = "chatbot_access_token";
const ACTIVE_CONVERSATION_KEY = "chatbot_active_conversation_id";
const THEME_KEY = "chatbot_theme";
const ACTIVITY_PING_SECONDS = 60;

function sortConversations(conversations) {
  return [...conversations].sort((a, b) => {
    if (a.is_pinned !== b.is_pinned) {
      return a.is_pinned ? -1 : 1;
    }
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [authStatus, setAuthStatus] = useState(() => (localStorage.getItem(TOKEN_KEY) ? "checking" : "anonymous"));
  const [theme, setTheme] = useState(() => localStorage.getItem(THEME_KEY) || "dark");
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState("");
  const [toasts, setToasts] = useState([]);
  const [isConversationsLoading, setIsConversationsLoading] = useState(false);
  const [isMessagesLoading, setIsMessagesLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [failedMessage, setFailedMessage] = useState(null);
  const [activeView, setActiveView] = useState("dashboard");
  const [achievementToast, setAchievementToast] = useState(null);
  const [lessonContext, setLessonContext] = useState(null);
  const [activeLesson, setActiveLesson] = useState(null);
  const [lessonProgress, setLessonProgress] = useState([]);
  const [isLessonLoading, setIsLessonLoading] = useState(false);
  const [isCompletingLessonStep, setIsCompletingLessonStep] = useState(false);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    let isCancelled = false;

    async function bootstrapAuth() {
      if (!token) {
        if (!isCancelled) {
          setAuthStatus("anonymous");
        }
        return;
      }

      if (!isCancelled) {
        setAuthStatus("checking");
      }

      try {
        await apiFetch("/me", { token });
        if (!isCancelled) {
          setAuthStatus("authenticated");
        }
      } catch (err) {
        if (isCancelled) {
          return;
        }

        if (
          err?.status === 401 ||
          err?.status === 403 ||
          err?.message?.includes("Could not validate credentials")
        ) {
          logout();
          setAuthStatus("anonymous");
          return;
        }

        logout();
        setAuthStatus("anonymous");
      }
    }

    bootstrapAuth();

    return () => {
      isCancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (authStatus !== "authenticated") {
      return () => {
        eventSourceRef.current?.close();
      };
    }

    if (token) {
      loadConversations();
      loadLessonProgress();
    }

    return () => {
      eventSourceRef.current?.close();
    };
  }, [authStatus, token]);

  useEffect(() => {
    if (!token || authStatus !== "authenticated") {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      if (document.visibilityState !== "visible") {
        return;
      }

      recordProgressActivity(ACTIVITY_PING_SECONDS, token)
        .then((progress) => {
          if (progress?.time_spent_seconds >= 3600) {
            checkProgressAchievements();
          }
        })
        .catch(() => {
          // Activity pings are best-effort and should never interrupt learning.
        });
    }, ACTIVITY_PING_SECONDS * 1000);

    return () => window.clearInterval(intervalId);
  }, [authStatus, token]);

  async function login(email, password) {
    const data = await apiFetch("/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setToken(data.access_token);
    setError("");
  }

  async function register(email, password) {
    await apiFetch("/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    await login(email, password);
  }

  function logout() {
    eventSourceRef.current?.close();
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ACTIVE_CONVERSATION_KEY);
    setToken("");
    setAuthStatus("anonymous");
    setConversations([]);
    setSelectedConversation(null);
    setMessages([]);
    setError("");
    setIsStreaming(false);
    setActiveView("dashboard");
    setAchievementToast(null);
    setLessonContext(null);
    setActiveLesson(null);
    setLessonProgress([]);
  }

  function toggleTheme() {
    setTheme((currentTheme) => (currentTheme === "dark" ? "light" : "dark"));
  }

  function showToast(type, message) {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((current) => [...current, { id, type, message }]);
    window.setTimeout(() => {
      dismissToast(id);
    }, 3600);
  }

  function dismissToast(id) {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }

  function showAchievementToast(achievements = []) {
    if (achievements.length > 0) {
      setAchievementToast(achievements[0]);
    }
  }

  async function checkProgressAchievements() {
    if (!token) {
      return;
    }

    try {
      const data = await apiFetch("/progress", { token });
      showAchievementToast(data?.new_achievements || []);
    } catch {
      // Achievement notifications should never interrupt chat or navigation flows.
    }
  }

  async function loadLessonProgress() {
    try {
      const data = await getLessonProgress(token);
      setLessonProgress(data);
    } catch (err) {
      handleRequestError(err);
    }
  }

  async function loadConversations() {
    setIsConversationsLoading(true);
    setError("");

    try {
      const data = await apiFetch("/conversations", { token });
      setConversations(sortConversations(data));
      if (selectedConversation) {
        const updatedSelectedConversation = data.find(
          (conversation) => conversation.id === selectedConversation.id,
        );
        if (updatedSelectedConversation) {
          setSelectedConversation(updatedSelectedConversation);
        }
      } else {
        const savedConversationId = Number(localStorage.getItem(ACTIVE_CONVERSATION_KEY));
        const savedConversation = data.find(
          (conversation) => conversation.id === savedConversationId,
        );

        if (savedConversation) {
          setSelectedConversation(savedConversation);
          await loadMessages(savedConversation.id);
        } else if (savedConversationId) {
          localStorage.removeItem(ACTIVE_CONVERSATION_KEY);
          setSelectedConversation(null);
          setMessages([]);
        }
      }
    } catch (err) {
      handleRequestError(err);
    } finally {
      setIsConversationsLoading(false);
    }
  }

  async function createConversation(title = "New conversation") {
    setError("");
    const conversation = await apiFetch("/conversations", {
      method: "POST",
      token,
      body: JSON.stringify({ title }),
    });
    setConversations((current) => sortConversations([conversation, ...current]));
    localStorage.setItem(ACTIVE_CONVERSATION_KEY, String(conversation.id));
    setSelectedConversation(conversation);
    setMessages([]);
    setActiveView("chat");
    await checkProgressAchievements();
    return conversation;
  }

  async function startNewConversation() {
    setLessonContext(null);
    setActiveLesson(null);
    await createConversation();
  }

  async function selectConversation(conversation) {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setIsStreaming(false);
    setLessonContext(null);
    setActiveLesson(null);
    localStorage.setItem(ACTIVE_CONVERSATION_KEY, String(conversation.id));
    setSelectedConversation(conversation);
    setActiveView("chat");
    await loadMessages(conversation.id);
  }

  async function selectLesson(lesson) {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setIsStreaming(false);
    setFailedMessage(null);
    setIsLessonLoading(true);
    localStorage.removeItem(ACTIVE_CONVERSATION_KEY);
    setSelectedConversation(null);
    setMessages([]);
    setLessonContext(lesson);
    setActiveView("chat");
    try {
      const data = await getLesson(lesson.lesson_id, token);
      setActiveLesson(data.completed ? { ...data, current_step_index: 0 } : data);
      await loadLessonProgress();
    } catch (err) {
      handleRequestError(err);
      showToast("error", "Unable to load lesson.");
    } finally {
      setIsLessonLoading(false);
    }
  }

  async function advanceLesson() {
    if (!activeLesson || isLessonLoading) {
      return;
    }

    if (activeLesson.completed) {
      setActiveLesson((currentLesson) => {
        if (!currentLesson) {
          return currentLesson;
        }

        return {
          ...currentLesson,
          current_step_index: Math.min(
            currentLesson.current_step_index + 1,
            currentLesson.steps.length - 1,
          ),
        };
      });
      return;
    }

    setIsLessonLoading(true);
    try {
      const wasCompleted = activeLesson.completed;
      const nextLesson = await nextLessonStep(activeLesson.lesson_id, token);
      setActiveLesson(nextLesson);
      await loadLessonProgress();
      await checkProgressAchievements();
      if (!wasCompleted && nextLesson.completed) {
        showToast("success", `Lesson completed: ${nextLesson.title}`);
      }
    } catch (err) {
      handleRequestError(err);
      showToast("error", "Unable to update lesson.");
    } finally {
      setIsLessonLoading(false);
    }
  }

  function previousLessonStep() {
    if (!activeLesson || isLessonLoading) {
      return;
    }

    setActiveLesson((currentLesson) => {
      if (!currentLesson) {
        return currentLesson;
      }

      return {
        ...currentLesson,
        current_step_index: Math.max(currentLesson.current_step_index - 1, 0),
      };
    });
  }

  async function markLessonStepRead(stepIndex) {
    if (!activeLesson || isCompletingLessonStep) {
      return;
    }

    setIsCompletingLessonStep(true);
    try {
      const nextLesson = await completeLessonStep(activeLesson.lesson_id, stepIndex, token);
      const completedStep = nextLesson.steps[stepIndex];
      setActiveLesson(nextLesson);
      await loadLessonProgress();
      await checkProgressAchievements();
      if (completedStep?.xp_awarded > 0) {
        showToast("success", `Reading complete: +${completedStep.xp_awarded} XP`);
      }
    } catch (err) {
      handleRequestError(err);
      showToast("error", "Unable to mark step as read.");
    } finally {
      setIsCompletingLessonStep(false);
    }
  }

  function showProgress() {
    setActiveView("progress");
  }

  function showAchievements() {
    setActiveView("achievements");
    setLessonContext(null);
    setActiveLesson(null);
  }

  function showDashboard() {
    setActiveView("dashboard");
    setLessonContext(null);
    setActiveLesson(null);
  }

  function showProfile() {
    setActiveView("profile");
    setLessonContext(null);
    setActiveLesson(null);
  }

  function showSettings() {
    setActiveView("settings");
    setLessonContext(null);
    setActiveLesson(null);
  }

  async function renameConversation(conversation, title) {
    const cleanTitle = title.trim();
    if (!cleanTitle) {
      return;
    }

    setError("");
    try {
      const updatedConversation = await apiFetch(`/conversations/${conversation.id}`, {
        method: "PATCH",
        token,
        body: JSON.stringify({ title: cleanTitle }),
      });

      setConversations((current) =>
        sortConversations(
          current.map((item) =>
            item.id === updatedConversation.id ? updatedConversation : item,
          ),
        ),
      );

      if (selectedConversation?.id === updatedConversation.id) {
        setSelectedConversation(updatedConversation);
      }
      showToast("success", "Conversation renamed.");
    } catch (err) {
      handleRequestError(err);
      showToast("error", "Unable to rename conversation.");
      throw err;
    }
  }

  async function deleteConversation(conversation) {
    setError("");
    try {
      await apiFetch(`/conversations/${conversation.id}`, {
        method: "DELETE",
        token,
      });

      setConversations((current) => current.filter((item) => item.id !== conversation.id));

      if (selectedConversation?.id === conversation.id) {
        eventSourceRef.current?.close();
        eventSourceRef.current = null;
        localStorage.removeItem(ACTIVE_CONVERSATION_KEY);
        setSelectedConversation(null);
        setMessages([]);
        setIsStreaming(false);
      }
      showToast("success", "Conversation deleted.");
    } catch (err) {
      handleRequestError(err);
      showToast("error", "Unable to delete conversation.");
      throw err;
    }
  }

  async function updateConversationMode(conversation, mode) {
    if (!conversation || conversation.mode === mode) {
      return;
    }

    setError("");
    try {
      const updatedConversation = await apiFetch(`/conversations/${conversation.id}/mode`, {
        method: "PATCH",
        token,
        body: JSON.stringify({ mode }),
      });

      setConversations((current) =>
        sortConversations(
          current.map((item) =>
            item.id === updatedConversation.id ? updatedConversation : item,
          ),
        ),
      );
      setSelectedConversation(updatedConversation);
    } catch (err) {
      handleRequestError(err);
    }
  }

  async function exportConversation(format) {
    if (!selectedConversation) {
      return;
    }

    setIsExporting(true);
    setError("");
    try {
      const response = await fetch(
        `${getApiBaseUrl()}/conversations/${selectedConversation.id}/export?format=${encodeURIComponent(format)}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!response.ok) {
        let message = "Unable to export conversation.";
        try {
          const data = await response.json();
          message = data?.detail || message;
        } catch {
          // Keep the generic message when the response is not JSON.
        }
        throw new Error(message);
      }

      const blob = await response.blob();
      const contentDisposition = response.headers.get("content-disposition") || "";
      const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
      const filename = filenameMatch?.[1] || `conversation-${selectedConversation.id}.${format}`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      showToast("success", "Conversation exported.");
    } catch (err) {
      handleRequestError(err);
      showToast("error", "Unable to export conversation.");
    } finally {
      setIsExporting(false);
    }
  }

  async function toggleConversationPin(conversation) {
    setError("");
    try {
      const updatedConversation = await apiFetch(`/conversations/${conversation.id}/pin`, {
        method: "PATCH",
        token,
      });

      setConversations((current) =>
        sortConversations(
          current.map((item) =>
            item.id === updatedConversation.id ? updatedConversation : item,
          ),
        ),
      );

      if (selectedConversation?.id === updatedConversation.id) {
        setSelectedConversation(updatedConversation);
      }

      showToast(
        "success",
        updatedConversation.is_pinned ? "Conversation pinned." : "Conversation unpinned.",
      );
    } catch (err) {
      handleRequestError(err);
      showToast("error", "Unable to update pin.");
    }
  }

  async function loadMessages(conversationId) {
    setIsMessagesLoading(true);
    setError("");

    try {
      const data = await apiFetch(`/messages?conversation_id=${encodeURIComponent(conversationId)}`, {
        token,
      });
      setMessages(data);
    } catch (err) {
      handleRequestError(err);
    } finally {
      setIsMessagesLoading(false);
    }
  }

  async function sendMessage(content) {
    setError("");
    setFailedMessage(null);
    let conversation = selectedConversation;

    try {
      if (!conversation) {
        conversation = await createConversation(lessonContext?.lesson_title || makeTitle(content));
      }

      const tempUserMessage = {
        id: `temp-user-${Date.now()}`,
        conversation_id: conversation.id,
        role: "user",
        content,
      };
      const tempAssistantMessage = {
        id: `temp-assistant-${Date.now()}`,
        conversation_id: conversation.id,
        role: "assistant",
        content: "",
      };

      setMessages((current) => [...current, tempUserMessage, tempAssistantMessage]);
      setIsStreaming(true);

      let assistantContent = "";
      let didFinalizeStream = false;
      const stream = new EventSource(getStreamUrl(conversation.id, content, token));
      eventSourceRef.current = stream;

      stream.onmessage = (event) => {
        assistantContent += event.data;
        const isStreamError = assistantContent.startsWith("Error:");
        setMessages((current) =>
          current.map((message) =>
            message.id === tempAssistantMessage.id
              ? { ...message, content: assistantContent }
              : message,
          ),
        );

        if (isStreamError) {
          didFinalizeStream = true;
          stream.close();
          eventSourceRef.current = null;
          setIsStreaming(false);
          setFailedMessage(content);
          setMessages((current) =>
            current.map((message) =>
              message.id === tempAssistantMessage.id
                ? { ...message, failed: true, retryContent: content }
                : message,
            ),
          );
          showToast("error", "Unable to generate response.");
        }
      };

      stream.onerror = () => {
        if (didFinalizeStream || eventSourceRef.current !== stream) {
          return;
        }

        didFinalizeStream = true;
        stream.close();
        eventSourceRef.current = null;
        setIsStreaming(false);
        setMessages((current) =>
          current.map((message) =>
            message.id === tempAssistantMessage.id
              ? {
                  ...message,
                  content: assistantContent || "Streaming failed. Please try again.",
                  failed: !assistantContent,
                  retryContent: !assistantContent ? content : undefined,
                  isStreaming: false,
                }
              : message,
          ),
        );
        if (!assistantContent) {
          setFailedMessage(content);
          showToast("error", "Streaming failed. Please try again.");
        } else {
          setFailedMessage(null);
          loadConversations();
          checkProgressAchievements();
        }
      };
    } catch (err) {
      setIsStreaming(false);
      setFailedMessage(content);
      handleRequestError(err);
      showToast("error", "Streaming failed. Please try again.");
    }
  }

  async function retryMessage(content = failedMessage) {
    if (!content || isStreaming) {
      return;
    }
    await sendMessage(content);
  }

  function handleRequestError(err) {
    if (err?.status === 401 || err?.status === 403 || err.message.includes("Could not validate credentials")) {
      logout();
      return;
    }
    setError(err.message);
  }

  function handleAuthError(message) {
    showToast("error", message || "Authentication failed.");
  }

  function makeTitle(content) {
    const clean = content.trim().replace(/\s+/g, " ");
    return clean.length > 48 ? `${clean.slice(0, 45)}...` : clean || "New conversation";
  }

  if (authStatus === "checking") {
    return (
      <main className="auth-shell">
        <section className="auth-panel">
          <p className="center-note">Checking session...</p>
        </section>
      </main>
    );
  }

  if (!token || authStatus !== "authenticated") {
    return (
      <AuthView
        onLogin={login}
        onRegister={register}
        onAuthError={handleAuthError}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
    );
  }

  return (
    <div className="app-shell">
      <Sidebar
        conversations={conversations}
        selectedConversationId={selectedConversation?.id}
        onCreateConversation={() => startNewConversation().catch(handleRequestError)}
        onSelectConversation={selectConversation}
        onRenameConversation={renameConversation}
        onDeleteConversation={deleteConversation}
        onTogglePin={toggleConversationPin}
        onSelectLesson={(lesson) => selectLesson(lesson).catch(handleRequestError)}
        onShowAchievements={showAchievements}
        onShowDashboard={showDashboard}
        onShowProfile={showProfile}
        onShowProgress={showProgress}
        onShowSettings={showSettings}
        onLogout={logout}
        selectedLessonId={lessonContext?.lesson_id}
        lessonProgress={lessonProgress}
        isAchievementsActive={activeView === "achievements"}
        isDashboardActive={activeView === "dashboard"}
        isProfileActive={activeView === "profile"}
        isProgressActive={activeView === "progress"}
        isSettingsActive={activeView === "settings"}
        isLoading={isConversationsLoading}
        isMessagesLoading={isMessagesLoading}
        isStreaming={isStreaming}
      />

      {activeView === "dashboard" ? (
        <DashboardPage
          token={token}
          theme={theme}
          onToggleTheme={toggleTheme}
          lessonProgress={lessonProgress}
          onSelectLesson={(lesson) => selectLesson(lesson).catch(handleRequestError)}
          onShowProgress={showProgress}
          onCreateConversation={() => startNewConversation().catch(handleRequestError)}
          onAchievementUnlocked={showAchievementToast}
        />
      ) : activeView === "progress" ? (
        <ProgressPage
          token={token}
          theme={theme}
          onToggleTheme={toggleTheme}
          onAchievementUnlocked={showAchievementToast}
          onShowAchievements={showAchievements}
        />
      ) : activeView === "achievements" ? (
        <AchievementsPage
          token={token}
          theme={theme}
          onToggleTheme={toggleTheme}
          onAchievementUnlocked={showAchievementToast}
        />
      ) : activeView === "profile" ? (
        <ProfilePage
          token={token}
          theme={theme}
          onToggleTheme={toggleTheme}
          onLogout={logout}
          onAchievementUnlocked={showAchievementToast}
        />
      ) : activeView === "settings" ? (
        <SettingsPage
          token={token}
          theme={theme}
          onToggleTheme={toggleTheme}
          onLogout={logout}
        />
      ) : lessonContext ? (
        <main className="chat-shell">
          <header className="chat-header">
            <div className="chat-title">
              <p className="eyebrow">{lessonContext.course_title}</p>
              <h1>{lessonContext.lesson_title}</h1>
            </div>
            <div className="chat-actions">
              <ThemeToggle theme={theme} onToggleTheme={toggleTheme} />
            </div>
          </header>
          <LessonView
            lesson={activeLesson}
            isLoading={isLessonLoading}
            isCompletingStep={isCompletingLessonStep}
            token={token}
            onPreviousStep={previousLessonStep}
            onNextStep={advanceLesson}
            onMarkStepRead={markLessonStepRead}
          />
        </main>
      ) : (
        <ChatWindow
          conversation={selectedConversation}
          lessonContext={lessonContext}
          messages={messages}
          onSendMessage={sendMessage}
          onRetryMessage={retryMessage}
          onUpdateMode={updateConversationMode}
          onExportConversation={exportConversation}
          isStreaming={isStreaming}
          isLoading={isMessagesLoading}
          isExporting={isExporting}
          theme={theme}
          onToggleTheme={toggleTheme}
        />
      )}

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
      {achievementToast ? (
        <AchievementToast
          achievement={achievementToast}
          onClose={() => setAchievementToast(null)}
        />
      ) : null}
    </div>
  );
}
