import { useState } from "react";
import Modal from "./Modal.jsx";

export default function Sidebar({
  conversations,
  selectedConversationId,
  onCreateConversation,
  onSelectConversation,
  onRenameConversation,
  onDeleteConversation,
  onTogglePin,
  onLogout,
  isLoading,
  isMessagesLoading,
  isStreaming,
}) {
  const [modalState, setModalState] = useState(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [modalError, setModalError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const cleanSearchQuery = searchQuery.trim().toLowerCase();
  const filteredConversations = cleanSearchQuery
    ? conversations.filter((conversation) =>
        conversation.title.toLowerCase().includes(cleanSearchQuery),
      )
    : conversations;
  const pinnedConversations = filteredConversations.filter(
    (conversation) => conversation.is_pinned,
  );
  const recentConversations = filteredConversations.filter(
    (conversation) => !conversation.is_pinned,
  );
  const groupedRecentConversations = groupConversationsByRecency(recentConversations);

  function openRename(conversation) {
    setDraftTitle(conversation.title);
    setModalError("");
    setModalState({ type: "rename", conversation });
  }

  function openDelete(conversation) {
    setModalError("");
    setModalState({ type: "delete", conversation });
  }

  function closeModal() {
    if (isSubmitting) {
      return;
    }
    resetModal();
  }

  function resetModal() {
    setModalState(null);
    setDraftTitle("");
    setModalError("");
  }

  async function confirmRename() {
    const cleanTitle = draftTitle.trim();
    if (!cleanTitle) {
      setModalError("Conversation title cannot be empty.");
      return;
    }

    setIsSubmitting(true);
    setModalError("");
    try {
      await onRenameConversation(modalState.conversation, cleanTitle);
      resetModal();
    } catch (err) {
      setModalError(err.message || "Unable to rename conversation.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function confirmDelete() {
    setIsSubmitting(true);
    setModalError("");
    try {
      await onDeleteConversation(modalState.conversation);
      resetModal();
    } catch (err) {
      setModalError(err.message || "Unable to delete conversation.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function getConversationTimestamp(conversation) {
    return conversation.updated_at || conversation.created_at;
  }

  function startOfDay(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  function getRecencyGroup(conversation) {
    const timestamp = getConversationTimestamp(conversation);
    const conversationDate = timestamp ? new Date(timestamp) : null;

    if (!conversationDate || Number.isNaN(conversationDate.getTime())) {
      return "Older";
    }

    const today = startOfDay(new Date());
    const conversationDay = startOfDay(conversationDate);
    const ageInDays = Math.floor((today - conversationDay) / 86400000);

    if (ageInDays === 0) {
      return "Today";
    }

    if (ageInDays === 1) {
      return "Yesterday";
    }

    if (ageInDays > 1 && ageInDays < 7) {
      return "Last 7 days";
    }

    return "Older";
  }

  function groupConversationsByRecency(items) {
    const groups = {
      Today: [],
      Yesterday: [],
      "Last 7 days": [],
      Older: [],
    };

    items.forEach((conversation) => {
      groups[getRecencyGroup(conversation)].push(conversation);
    });

    return Object.entries(groups)
      .map(([label, groupConversations]) => ({ label, conversations: groupConversations }))
      .filter((group) => group.conversations.length > 0);
  }

  function renderConversation(conversation) {
    const isActive = conversation.id === selectedConversationId;

    return (
      <div
        key={conversation.id}
        className={[
          "conversation-row",
          isActive ? "active" : "",
          conversation.is_pinned ? "pinned" : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <button
          type="button"
          className="conversation-item"
          onClick={() => onSelectConversation(conversation)}
          disabled={isMessagesLoading || isStreaming}
        >
          <span className="conversation-title">
            {conversation.is_pinned ? <span className="pin-marker">Pinned</span> : null}
            <span>{conversation.title}</span>
          </span>
          <time dateTime={conversation.created_at}>
            {new Date(conversation.created_at).toLocaleDateString()}
          </time>
        </button>
        <div className="conversation-actions">
          <button
            type="button"
            className="conversation-action"
            onClick={() => onTogglePin(conversation)}
            aria-label={`${conversation.is_pinned ? "Unpin" : "Pin"} ${conversation.title}`}
            disabled={isStreaming}
          >
            {conversation.is_pinned ? "Unpin" : "Pin"}
          </button>
          <button
            type="button"
            className="conversation-action"
            onClick={() => openRename(conversation)}
            aria-label={`Rename ${conversation.title}`}
            disabled={isStreaming}
          >
            Rename
          </button>
          <button
            type="button"
            className="conversation-action danger"
            onClick={() => openDelete(conversation)}
            aria-label={`Delete ${conversation.title}`}
            disabled={isStreaming}
          >
            Delete
          </button>
        </div>
      </div>
    );
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div>
          <p className="eyebrow">Conversations</p>
          <h2>Chats</h2>
        </div>
        <button
          className="icon-button"
          type="button"
          onClick={onCreateConversation}
          aria-label="New chat"
          disabled={isLoading || isStreaming}
        >
          +
        </button>
      </div>

      <div className="sidebar-controls">
        <button
          className="new-chat-button"
          type="button"
          onClick={onCreateConversation}
          disabled={isLoading || isStreaming}
        >
          <span>New chat</span>
          <span aria-hidden="true">+</span>
        </button>
      </div>

      <div className="conversation-search">
        <input
          type="search"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Search conversations"
          aria-label="Search conversations"
          disabled={isLoading}
        />
      </div>

      <nav className="conversation-list" aria-label="Conversations">
        {isLoading ? <p className="sidebar-note">Loading conversations...</p> : null}
        {!isLoading && conversations.length === 0 ? (
          <div className="sidebar-empty">
            <p>No conversations yet.</p>
            <button type="button" onClick={onCreateConversation} disabled={isLoading || isStreaming}>
              Start one
            </button>
          </div>
        ) : null}
        {!isLoading && conversations.length > 0 && filteredConversations.length === 0 ? (
          <div className="sidebar-empty">
            <p>No matching conversations.</p>
            <button type="button" onClick={() => setSearchQuery("")}>
              Clear search
            </button>
          </div>
        ) : null}

        {!isLoading && pinnedConversations.length > 0 ? (
          <section className="conversation-section" aria-labelledby="pinned-conversations">
            <div className="conversation-section-label" id="pinned-conversations">
              Pinned
            </div>
            <div className="conversation-section-list">
              {pinnedConversations.map(renderConversation)}
            </div>
          </section>
        ) : null}

        {!isLoading
          ? groupedRecentConversations.map((group) => (
              <section
                className="conversation-section"
                aria-labelledby={`conversations-${group.label.toLowerCase().replaceAll(" ", "-")}`}
                key={group.label}
              >
                <div
                  className="conversation-section-label"
                  id={`conversations-${group.label.toLowerCase().replaceAll(" ", "-")}`}
                >
                  {group.label}
                </div>
                <div className="conversation-section-list">
                  {group.conversations.map(renderConversation)}
                </div>
              </section>
            ))
          : null}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-session">
          <span>Session</span>
          <strong>Signed in</strong>
        </div>
        <button className="secondary-button" type="button" onClick={onLogout}>
          Log out
        </button>
      </div>

      {modalState?.type === "rename" ? (
        <Modal
          title="Rename conversation"
          description="Choose a short, recognizable title."
          confirmLabel="Save"
          isLoading={isSubmitting}
          error={modalError}
          onClose={closeModal}
          onConfirm={confirmRename}
        >
          <label>
            Conversation title
            <input
              value={draftTitle}
              onChange={(event) => setDraftTitle(event.target.value)}
              autoFocus
              maxLength={255}
            />
          </label>
        </Modal>
      ) : null}

      {modalState?.type === "delete" ? (
        <Modal
          title="Delete conversation"
          description={`This will permanently delete "${modalState.conversation.title}" and its messages.`}
          confirmLabel="Delete"
          destructive
          isLoading={isSubmitting}
          error={modalError}
          onClose={closeModal}
          onConfirm={confirmDelete}
        />
      ) : null}
    </aside>
  );
}
