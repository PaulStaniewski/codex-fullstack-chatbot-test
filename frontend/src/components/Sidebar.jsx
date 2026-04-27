import { useState } from "react";
import { learningStructure } from "../learningStructure.js";
import Modal from "./Modal.jsx";

const COLLAPSED_SECTIONS_STORAGE_KEY = "sidebar.collapsedSections";

function loadCollapsedSections() {
  try {
    const savedSections = localStorage.getItem(COLLAPSED_SECTIONS_STORAGE_KEY);
    return savedSections ? JSON.parse(savedSections) : {};
  } catch {
    return {};
  }
}

export default function Sidebar({
  conversations,
  selectedConversationId,
  onCreateConversation,
  onSelectConversation,
  onRenameConversation,
  onDeleteConversation,
  onTogglePin,
  onSelectLesson,
  onShowProgress,
  onLogout,
  selectedLessonId,
  isProgressActive,
  isLoading,
  isMessagesLoading,
  isStreaming,
}) {
  const [modalState, setModalState] = useState(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [modalError, setModalError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [collapsedSections, setCollapsedSections] = useState(loadCollapsedSections);
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

  function getSectionId(label) {
    return label.toLowerCase().replaceAll(" ", "-");
  }

  function toggleSection(sectionId) {
    setCollapsedSections((currentSections) => {
      const nextSections = {
        ...currentSections,
        [sectionId]: !currentSections[sectionId],
      };

      localStorage.setItem(COLLAPSED_SECTIONS_STORAGE_KEY, JSON.stringify(nextSections));
      return nextSections;
    });
  }

  function renderLesson(course, lesson) {
    const lessonKey = `${course.id}:${lesson.id}`;
    const isActive = lessonKey === selectedLessonId;

    return (
      <button
        type="button"
        key={lessonKey}
        className={isActive ? "lesson-item active" : "lesson-item"}
        onClick={() =>
          onSelectLesson({
            lesson_id: lessonKey,
            lesson_title: lesson.title,
            course_id: course.id,
            course_title: course.title,
          })
        }
        disabled={isMessagesLoading || isStreaming}
      >
        <span className="lesson-status" aria-hidden="true">
          {isActive ? "●" : "○"}
        </span>
        <span className="lesson-title">{lesson.title}</span>
      </button>
    );
  }

  function renderLearningSection(course) {
    const sectionId = `course-${course.id}`;
    const isCollapsed = Boolean(collapsedSections[sectionId]);
    const headingId = `learning-${course.id}`;
    const listId = `${headingId}-list`;

    return (
      <section
        className="conversation-section learning-section"
        aria-labelledby={headingId}
        key={course.id}
      >
        <button
          type="button"
          className="conversation-section-label"
          id={headingId}
          aria-expanded={!isCollapsed}
          aria-controls={listId}
          onClick={() => toggleSection(sectionId)}
        >
          <span className="section-label-text">
            <span className="section-chevron" aria-hidden="true">
              {">"}
            </span>
            <span>{course.title}</span>
          </span>
          <span className="section-count">{course.lessons.length}</span>
        </button>
        <div
          className={
            isCollapsed
              ? "conversation-section-body collapsed"
              : "conversation-section-body"
          }
          id={listId}
          aria-hidden={isCollapsed}
        >
          <div className="lesson-list">
            {course.lessons.map((lesson) => renderLesson(course, lesson))}
          </div>
        </div>
      </section>
    );
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

  function renderSection(label, sectionId, sectionConversations) {
    const isCollapsed = Boolean(collapsedSections[sectionId]);
    const headingId = `conversations-${sectionId}`;
    const listId = `${headingId}-list`;

    return (
      <section className="conversation-section" aria-labelledby={headingId} key={sectionId}>
        <button
          type="button"
          className="conversation-section-label"
          id={headingId}
          aria-expanded={!isCollapsed}
          aria-controls={listId}
          onClick={() => toggleSection(sectionId)}
        >
          <span className="section-label-text">
            <span className="section-chevron" aria-hidden="true">
              ›
            </span>
            <span>{label}</span>
          </span>
          <span className="section-count">{sectionConversations.length}</span>
        </button>
        <div
          className={
            isCollapsed
              ? "conversation-section-body collapsed"
              : "conversation-section-body"
          }
          id={listId}
          aria-hidden={isCollapsed}
        >
          <div className="conversation-section-list">
            {sectionConversations.map(renderConversation)}
          </div>
        </div>
      </section>
    );
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div>
          <p className="eyebrow">Learning</p>
          <h2>Courses</h2>
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
        <button
          className={isProgressActive ? "sidebar-nav-button active" : "sidebar-nav-button"}
          type="button"
          onClick={onShowProgress}
        >
          <span aria-hidden="true">📘</span>
          <span>Progress</span>
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

      <nav className="conversation-list" aria-label="Learning">
        <div className="learning-nav">
          {learningStructure.map(renderLearningSection)}
        </div>

        <div className="conversation-history-heading">
          <span>Conversation history</span>
        </div>

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
          renderSection("Pinned", "pinned", pinnedConversations)
        ) : null}

        {!isLoading
          ? groupedRecentConversations.map((group) =>
              renderSection(group.label, getSectionId(group.label), group.conversations),
            )
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
