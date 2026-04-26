import { useEffect, useRef, useState } from "react";
import { apiFetch, getStreamUrl } from "./api.js";
import AuthView from "./components/AuthView.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import Sidebar from "./components/Sidebar.jsx";

const TOKEN_KEY = "chatbot_access_token";
const ACTIVE_CONVERSATION_KEY = "chatbot_active_conversation_id";
const THEME_KEY = "chatbot_theme";

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [theme, setTheme] = useState(() => localStorage.getItem(THEME_KEY) || "dark");
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState("");
  const [isConversationsLoading, setIsConversationsLoading] = useState(false);
  const [isMessagesLoading, setIsMessagesLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    if (token) {
      loadConversations();
    }

    return () => {
      eventSourceRef.current?.close();
    };
  }, [token]);

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
    setConversations([]);
    setSelectedConversation(null);
    setMessages([]);
    setError("");
    setIsStreaming(false);
  }

  function toggleTheme() {
    setTheme((currentTheme) => (currentTheme === "dark" ? "light" : "dark"));
  }

  async function loadConversations() {
    setIsConversationsLoading(true);
    setError("");

    try {
      const data = await apiFetch("/conversations", { token });
      setConversations(data);
      if (!selectedConversation) {
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
    setConversations((current) => [conversation, ...current]);
    localStorage.setItem(ACTIVE_CONVERSATION_KEY, String(conversation.id));
    setSelectedConversation(conversation);
    setMessages([]);
    return conversation;
  }

  async function selectConversation(conversation) {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setIsStreaming(false);
    localStorage.setItem(ACTIVE_CONVERSATION_KEY, String(conversation.id));
    setSelectedConversation(conversation);
    await loadMessages(conversation.id);
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
        current.map((item) =>
          item.id === updatedConversation.id ? updatedConversation : item,
        ),
      );

      if (selectedConversation?.id === updatedConversation.id) {
        setSelectedConversation(updatedConversation);
      }
    } catch (err) {
      handleRequestError(err);
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
    } catch (err) {
      handleRequestError(err);
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
        current.map((item) =>
          item.id === updatedConversation.id ? updatedConversation : item,
        ),
      );
      setSelectedConversation(updatedConversation);
    } catch (err) {
      handleRequestError(err);
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
    let conversation = selectedConversation;

    try {
      if (!conversation) {
        conversation = await createConversation(makeTitle(content));
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
              ? { ...message, content: assistantContent, isStreaming: false }
              : message,
          ),
        );
      };
    } catch (err) {
      setIsStreaming(false);
      handleRequestError(err);
    }
  }

  function handleRequestError(err) {
    if (err.message.includes("Could not validate credentials")) {
      logout();
      return;
    }
    setError(err.message);
  }

  function makeTitle(content) {
    const clean = content.trim().replace(/\s+/g, " ");
    return clean.length > 48 ? `${clean.slice(0, 45)}...` : clean || "New conversation";
  }

  if (!token) {
    return (
      <AuthView
        onLogin={login}
        onRegister={register}
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
        onCreateConversation={() => createConversation().catch(handleRequestError)}
        onSelectConversation={selectConversation}
        onRenameConversation={renameConversation}
        onDeleteConversation={deleteConversation}
        onLogout={logout}
        isLoading={isConversationsLoading}
      />

      <ChatWindow
        conversation={selectedConversation}
        messages={messages}
        onSendMessage={sendMessage}
        onUpdateMode={updateConversationMode}
        isStreaming={isStreaming}
        isLoading={isMessagesLoading}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {error ? <div className="toast" role="alert">{error}</div> : null}
    </div>
  );
}
