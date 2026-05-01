import { useEffect, useState } from "react";
import { apiFetch } from "../api.js";
import ThemeToggle from "./ThemeToggle.jsx";

function formatTime(seconds) {
  if (!seconds) {
    return "0m";
  }

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function normalizeProgressResponse(data) {
  if (data?.progress) {
    return {
      ...data.progress,
      achievements: data.achievements || [],
      badges: data.badges || data.achievements || [],
    };
  }

  return data;
}

function getLevelTitle(level) {
  if (level >= 10) {
    return "Master";
  }
  if (level >= 5) {
    return "Builder";
  }
  if (level >= 2) {
    return "Learner";
  }
  return "Starter";
}

export default function ProgressPage({
  token,
  theme,
  onToggleTheme,
  onAchievementUnlocked,
  onShowAchievements,
}) {
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadProgress() {
      setIsLoading(true);
      setError("");
      try {
        const data = await apiFetch("/progress", { token });
        if (isMounted) {
          setProgress(normalizeProgressResponse(data));
          onAchievementUnlocked?.(data?.new_achievements || []);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || "Unable to load progress.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadProgress();

    return () => {
      isMounted = false;
    };
  }, [token]);

  const answeredCount = (progress?.correct_answers || 0) + (progress?.incorrect_answers || 0);
  const accuracy = answeredCount
    ? Math.round(((progress?.correct_answers || 0) / answeredCount) * 100)
    : 0;
  const level = progress?.level || 1;
  const totalXp = progress?.total_xp ?? progress?.xp_points ?? 0;
  const currentLevelXp = progress?.xp_into_level ?? 0;
  const xpRequiredForNextLevel = progress?.xp_required_for_next_level ?? 1;
  const xpPercent = Math.min(100, Math.max(0, progress?.progress_percent ?? 0));
  const badges = progress?.badges || [];
  const earnedBadges = badges.filter((badge) => badge.earned);
  const badgePreview = earnedBadges.length > 0 ? earnedBadges.slice(0, 3) : badges.slice(0, 3);

  return (
    <main className="progress-shell">
      <header className="chat-header">
        <div className="chat-title">
          <p className="eyebrow">Learning Book</p>
          <h1>Progress</h1>
        </div>
        <div className="chat-actions">
          <ThemeToggle theme={theme} onToggleTheme={onToggleTheme} />
        </div>
      </header>

      <section className="progress-content">
        {isLoading ? <p className="center-note">Loading progress...</p> : null}
        {!isLoading && error ? <p className="form-error">{error}</p> : null}
        {!isLoading && progress ? (
          <>
            <section className="progress-section level-section">
              <div>
                <p className="eyebrow">Level</p>
                <h2>
                  Level {level} - {getLevelTitle(level)}
                </h2>
              </div>
              <div className="level-progress">
                <div className="level-progress__meta">
                  <span>
                    {currentLevelXp} / {xpRequiredForNextLevel} XP
                  </span>
                  <span>{totalXp} total XP</span>
                </div>
                <div
                  className="level-progress__track"
                  aria-label={`${currentLevelXp} of ${xpRequiredForNextLevel} XP`}
                >
                  <div
                    className="level-progress__bar"
                    style={{ width: `${xpPercent}%` }}
                  />
                </div>
              </div>
            </section>

            <section className="progress-section">
              <div>
                <p className="eyebrow">Learning Summary</p>
                <h2>Your activity</h2>
              </div>
              <div className="progress-stats">
                <div className="progress-stat">
                  <span>Learning sessions</span>
                  <strong>{progress.sessions_count}</strong>
                </div>
                <div className="progress-stat">
                  <span>Messages</span>
                  <strong>{progress.messages_count}</strong>
                </div>
                <div className="progress-stat">
                  <span>Accuracy</span>
                  <strong>{accuracy}%</strong>
                </div>
                <div className="progress-stat">
                  <span>Time spent</span>
                  <strong>{formatTime(progress.time_spent_seconds)}</strong>
                </div>
              </div>
            </section>

            <section className="progress-section">
              <div>
                <p className="eyebrow">Achievements</p>
                <h2>Badge preview</h2>
              </div>
              {badges.length > 0 ? (
                <>
                  <div className="badge-preview-list">
                    {badgePreview.map((badge) => (
                      <article
                        className={
                          badge.earned
                            ? "badge-preview-card achievement-card--earned"
                            : "badge-preview-card achievement-card--locked"
                        }
                        key={badge.key || badge.id}
                      >
                        <div className="achievement-icon">{badge.icon}</div>
                        <div>
                          <div className="achievement-card__title-row">
                            <h3>{badge.title || badge.name}</h3>
                            <span className={badge.earned ? "badge-status earned" : "badge-status"}>
                              {badge.earned ? "Unlocked" : "Locked"}
                            </span>
                          </div>
                          <p>{badge.description}</p>
                        </div>
                      </article>
                    ))}
                  </div>
                  <button
                    type="button"
                    className="secondary-button progress-link-button"
                    onClick={onShowAchievements}
                  >
                    View all achievements
                  </button>
                </>
              ) : (
                <div className="empty-state progress-empty">
                  <div className="empty-mark">0</div>
                  <h2>No badges available</h2>
                  <p>Badges will appear here as learning milestones are configured.</p>
                </div>
              )}
            </section>

            <section className="progress-section">
              <div>
                <p className="eyebrow">Topic Progress</p>
                <h2>Coming next</h2>
              </div>
              <div className="topic-placeholder">
                Topic-level progress will appear here as learning mode gets more structured.
              </div>
            </section>
          </>
        ) : null}
      </section>
    </main>
  );
}
