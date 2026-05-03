import { Suspense, lazy, useEffect, useRef, useState } from "react";
import ThemeToggle from "./ThemeToggle.jsx";

const MarkdownContent = lazy(() => import("./MarkdownContent.jsx"));

export default function ChatWindow({
  conversation,
  lessonContext,
  messages,
  onSendMessage,
  onRetryMessage,
  onUpdateMode,
  onExportConversation,
  isStreaming,
  isLoading,
  isExporting,
  theme,
  onToggleTheme,
}) {
  const [draft, setDraft] = useState("");
  const [copiedMessageId, setCopiedMessageId] = useState(null);
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [hasNewActivityAwayFromBottom, setHasNewActivityAwayFromBottom] = useState(false);
  const listRef = useRef(null);
  const wasNearBottomRef = useRef(true);

  useEffect(() => {
    const element = listRef.current;
    if (!element) {
      return;
    }

    if (wasNearBottomRef.current) {
      scrollToLatest("auto");
    } else {
      setHasNewActivityAwayFromBottom(true);
    }
  }, [messages]);

  useEffect(() => {
    if (isStreaming && !wasNearBottomRef.current) {
      setHasNewActivityAwayFromBottom(true);
    }
  }, [isStreaming]);

  function isElementNearBottom(element) {
    return element.scrollHeight - element.scrollTop - element.clientHeight < 96;
  }

  function handleMessageListScroll() {
    const element = listRef.current;
    if (!element) {
      return;
    }

    const nextIsNearBottom = isElementNearBottom(element);
    wasNearBottomRef.current = nextIsNearBottom;
    setIsNearBottom(nextIsNearBottom);
    if (nextIsNearBottom) {
      setHasNewActivityAwayFromBottom(false);
    }
  }

  function scrollToLatest(behavior = "smooth") {
    const element = listRef.current;
    if (!element) {
      return;
    }

    element.scrollTo({ top: element.scrollHeight, behavior });
    wasNearBottomRef.current = true;
    setIsNearBottom(true);
    setHasNewActivityAwayFromBottom(false);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const cleanDraft = draft.trim();
    if (!cleanDraft || isStreaming) {
      return;
    }

    setDraft("");
    await onSendMessage(cleanDraft);
  }

  async function copyMessage(message) {
    if (!message.content) {
      return;
    }

    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedMessageId(message.id);
      window.setTimeout(() => {
        setCopiedMessageId((current) => (current === message.id ? null : current));
      }, 1400);
    } catch {
      setCopiedMessageId(null);
    }
  }

  async function handleExport(format) {
    setIsExportMenuOpen(false);
    await onExportConversation(format);
  }

  function renderMessageContent(message) {
    if (message.role !== "assistant") {
      return <p className="plain-message">{message.content}</p>;
    }

    return (
      <div className="markdown-content">
        <Suspense fallback={<p className="plain-message">{message.content}</p>}>
          <MarkdownContent theme={theme}>{message.content}</MarkdownContent>
        </Suspense>
      </div>
    );
  }

  const modeBadgeLabel =
    conversation?.mode === "learn"
      ? "Learn mode"
      : conversation?.mode === "interview"
        ? "Interview mode"
        : null;

  return (
    <main className="chat-shell">
      <header className="chat-header">
        <div className="chat-title">
          <p className="eyebrow">
            {lessonContext ? lessonContext.course_title : "Assistant"}
          </p>
          <h1>{lessonContext?.lesson_title || conversation?.title || "Select or start a chat"}</h1>
        </div>
        <div className="chat-actions">
          {modeBadgeLabel ? <span className="mode-badge">{modeBadgeLabel}</span> : null}
          {conversation ? (
            <div className="mode-toggle" aria-label="Conversation mode">
              <button
                type="button"
                className={conversation.mode === "chat" ? "active" : ""}
                onClick={() => onUpdateMode(conversation, "chat")}
                disabled={isStreaming}
              >
                Chat
              </button>
              <button
                type="button"
                className={conversation.mode === "learn" ? "active" : ""}
                onClick={() => onUpdateMode(conversation, "learn")}
                disabled={isStreaming}
              >
                Learn
              </button>
              <button
                type="button"
                className={conversation.mode === "interview" ? "active" : ""}
                onClick={() => onUpdateMode(conversation, "interview")}
                disabled={isStreaming}
              >
                Interview
              </button>
            </div>
          ) : null}
          {conversation ? (
            <div className="export-menu">
              <button
                className="export-button"
                type="button"
                onClick={() => setIsExportMenuOpen((isOpen) => !isOpen)}
                disabled={isStreaming || isExporting}
                aria-expanded={isExportMenuOpen}
              >
                {isExporting ? "Exporting" : "Export"}
              </button>
              {isExportMenuOpen ? (
                <div className="export-options">
                  <button type="button" onClick={() => handleExport("txt")}>
                    Export as TXT
                  </button>
                  <button type="button" onClick={() => handleExport("md")}>
                    Export as Markdown
                  </button>
                  <button type="button" onClick={() => handleExport("json")}>
                    Export as JSON
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
          {isStreaming ? <span className="status-pill">Streaming</span> : null}
          <ThemeToggle theme={theme} onToggleTheme={onToggleTheme} />
        </div>
      </header>

      <section
        className="message-list"
        ref={listRef}
        aria-live="polite"
        onScroll={handleMessageListScroll}
      >
        {isLoading ? <p className="center-note">Loading messages...</p> : null}
        {!isLoading && !conversation ? (
          <div className="empty-state">
            <div className="empty-mark">{lessonContext ? "L" : "AI"}</div>
            <h2>{lessonContext ? lessonContext.lesson_title : "Start a conversation"}</h2>
            <p>
              {lessonContext
                ? `Ask a question or start practicing ${lessonContext.lesson_title}.`
                : "Create a chat from the sidebar, then send a message here."}
            </p>
          </div>
        ) : null}
        {!isLoading && conversation && messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-mark">+</div>
            <h2>Ready when you are</h2>
            <p>Send the first message in this conversation.</p>
          </div>
        ) : null}

        {messages.length > 0 ? (
          <div className="message-thread">
            {messages.map((message) => (
              <article
                key={message.id}
                className={`message-row ${message.role}${isStreaming && message.role === "assistant" && !message.content ? " streaming" : ""}`}
              >
                <div className="message-bubble">
                  <div className="message-meta">
                    <span>{message.role === "assistant" ? "Assistant" : "You"}</span>
                    <div className="message-actions">
                      {isStreaming && message.role === "assistant" ? <span>typing</span> : null}
                      {message.content ? (
                        <button type="button" onClick={() => copyMessage(message)}>
                          {copiedMessageId === message.id ? "Copied" : "Copy"}
                        </button>
                      ) : null}
                    </div>
                  </div>
                  {message.content ? (
                    renderMessageContent(message)
                  ) : (
                    <div className="typing-dots" aria-label="Assistant is typing">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  )}
                  {message.failed ? (
                    <div className="message-retry">
                      <button
                        type="button"
                        onClick={() => onRetryMessage(message.retryContent)}
                        disabled={isStreaming}
                      >
                        Retry
                      </button>
                    </div>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </section>

      {!isNearBottom && hasNewActivityAwayFromBottom ? (
        <button className="jump-latest-button" type="button" onClick={() => scrollToLatest()}>
          Jump to latest
        </button>
      ) : null}

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
