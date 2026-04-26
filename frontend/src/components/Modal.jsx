import { useEffect } from "react";

export default function Modal({
  title,
  description,
  children,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  isLoading = false,
  error = "",
  onConfirm,
  onClose,
}) {
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape" && !isLoading) {
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isLoading, onClose]);

  function handleBackdropClick(event) {
    if (event.target === event.currentTarget && !isLoading) {
      onClose();
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={handleBackdropClick}>
      <section
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-describedby={description ? "modal-description" : undefined}
      >
        <div className="modal-header">
          <h2 id="modal-title">{title}</h2>
          {description ? <p id="modal-description">{description}</p> : null}
        </div>

        {children ? <div className="modal-body">{children}</div> : null}
        {error ? <p className="modal-error" role="alert">{error}</p> : null}

        <div className="modal-actions">
          <button
            className="secondary-button"
            type="button"
            onClick={onClose}
            disabled={isLoading}
          >
            {cancelLabel}
          </button>
          <button
            className={destructive ? "danger-button" : "primary-button"}
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? "Please wait..." : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
