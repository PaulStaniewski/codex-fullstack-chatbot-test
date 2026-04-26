export default function Sidebar({
  conversations,
  selectedConversationId,
  onCreateConversation,
  onSelectConversation,
  onLogout,
  isLoading,
}) {
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
          <button
            key={conversation.id}
            type="button"
            className={
              conversation.id === selectedConversationId
                ? "conversation-item active"
                : "conversation-item"
            }
            onClick={() => onSelectConversation(conversation)}
          >
            <span className="conversation-title">{conversation.title}</span>
            <time dateTime={conversation.created_at}>
              {new Date(conversation.created_at).toLocaleDateString()}
            </time>
          </button>
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
