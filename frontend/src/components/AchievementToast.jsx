import { useEffect, useState } from "react";

export default function AchievementToast({ achievement, onClose }) {
  const [isClosing, setIsClosing] = useState(false);

  useEffect(() => {
    setIsClosing(false);
    const fadeTimeoutId = window.setTimeout(() => setIsClosing(true), 3600);
    const closeTimeoutId = window.setTimeout(onClose, 4000);
    return () => {
      window.clearTimeout(fadeTimeoutId);
      window.clearTimeout(closeTimeoutId);
    };
  }, [achievement, onClose]);

  if (!achievement) {
    return null;
  }

  return (
    <div
      className={`achievement-toast${isClosing ? " achievement-toast--closing" : ""}`}
      role="status"
      aria-live="polite"
    >
      <div className="achievement-toast__icon">🎉</div>
      <div className="achievement-toast__content">
        <p>Achievement unlocked</p>
        <strong>{achievement.name}</strong>
        <span>{achievement.description}</span>
      </div>
      <button type="button" onClick={onClose} aria-label="Dismiss achievement notification">
        Close
      </button>
    </div>
  );
}
