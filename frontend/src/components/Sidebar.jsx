export default function Sidebar({
  conversations,
  selectedConversationId,
  onCreateConversation,
  onSelectConversation,
  onRenameConversation,
  onDeleteConversation,
  onLogout,
  isLoading,
}) {
  function handleRename(event, conversation) {
    event.stopPropagation();
    const nextTitle = window.prompt("Rename conversation", conversation.title);
    if (nextTitle !== null) {
      onRenameConversation(conversation, nextTitle);
    }
  }

  function handleDelete(event, conversation) {
    event.stopPropagation();
    const shouldDelete = window.confirm(`Delete "${conversation.title}"?`);
    if (shouldDelete) {
      onDeleteConversation(conversation);
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div>
          <p className="eyebrow">Conversations</p>
          <h2>Chats</h2>
        </div>
        <button className="icon-button" type="button" onClick={onCreateConversation} aria-label="New chat">
          +
        </button>
      </div>

      <nav className="conversation-list" aria-label="Conversations">
        {isLoading ? <p className="sidebar-note">Loading conversations...</p> : null}
        {!isLoading && conversations.length === 0 ? (
          <p className="sidebar-note">No conversations yet.</p>
        ) : null}

        {conversations.map((conversation) => (
          <div
            key={conversation.id}
            className={
              conversation.id === selectedConversationId
                ? "conversation-row active"
                : "conversation-row"
            }
          >
            <button
              type="button"
              className="conversation-item"
              onClick={() => onSelectConversation(conversation)}
            >
              <span className="conversation-title">{conversation.title}</span>
              <time dateTime={conversation.created_at}>
                {new Date(conversation.created_at).toLocaleDateString()}
              </time>
            </button>
            <div className="conversation-actions">
              <button
                type="button"
                className="conversation-action"
                onClick={(event) => handleRename(event, conversation)}
                aria-label={`Rename ${conversation.title}`}
              >
                Edit
              </button>
              <button
                type="button"
                className="conversation-action danger"
                onClick={(event) => handleDelete(event, conversation)}
                aria-label={`Delete ${conversation.title}`}
              >
                Del
              </button>
            </div>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button className="secondary-button" type="button" onClick={onLogout}>
          Log out
        </button>
      </div>
    </aside>
  );
}
