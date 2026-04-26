import { useEffect, useRef, useState } from "react";
import ThemeToggle from "./ThemeToggle.jsx";

export default function ChatWindow({
  conversation,
  messages,
  onSendMessage,
  isStreaming,
  isLoading,
  theme,
  onToggleTheme,
}) {
  const [draft, setDraft] = useState("");
  const listRef = useRef(null);

  useEffect(() => {
    const element = listRef.current;
    if (element) {
      element.scrollTop = element.scrollHeight;
    }
  }, [messages]);

  async function handleSubmit(event) {
    event.preventDefault();
    const cleanDraft = draft.trim();
    if (!cleanDraft || isStreaming) {
      return;
    }

    setDraft("");
    await onSendMessage(cleanDraft);
  }

  return (
    <main className="chat-shell">
      <header className="chat-header">
        <div className="chat-title">
          <p className="eyebrow">Assistant</p>
          <h1>{conversation?.title || "Select or start a chat"}</h1>
        </div>
        <div className="chat-actions">
          {isStreaming ? <span className="status-pill">Streaming</span> : null}
          <ThemeToggle theme={theme} onToggleTheme={onToggleTheme} />
        </div>
      </header>

      <section className="message-list" ref={listRef} aria-live="polite">
        {isLoading ? <p className="center-note">Loading messages...</p> : null}
        {!isLoading && !conversation ? (
          <div className="empty-state">
            <div className="empty-mark">AI</div>
            <h2>Start a conversation</h2>
            <p>Create a chat from the sidebar or send a message to begin.</p>
          </div>
        ) : null}
        {!isLoading && conversation && messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-mark">+</div>
            <h2>Ready when you are</h2>
            <p>Send the first message in this conversation.</p>
          </div>
        ) : null}

        {messages.map((message) => (
          <article
            key={message.id}
            className={`message ${message.role}${isStreaming && message.role === "assistant" && !message.content ? " streaming" : ""}`}
          >
            <div className="message-meta">
              <span>{message.role === "assistant" ? "Assistant" : "You"}</span>
              {isStreaming && message.role === "assistant" ? <span>typing</span> : null}
            </div>
            {message.content ? (
              <p>{message.content}</p>
            ) : (
              <div className="typing-dots" aria-label="Assistant is typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            )}
          </article>
        ))}
      </section>

      <form className="composer" onSubmit={handleSubmit}>
        <div className="composer-input">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Type your message..."
            rows={1}
            disabled={isStreaming}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form.requestSubmit();
              }
            }}
          />
        </div>
        <button className="primary-button send-button" type="submit" disabled={!draft.trim() || isStreaming}>
          {isStreaming ? "Wait" : "Send"}
        </button>
      </form>
    </main>
  );
}
