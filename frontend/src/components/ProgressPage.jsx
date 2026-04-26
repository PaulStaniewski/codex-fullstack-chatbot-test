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

export default function ProgressPage({ token, theme, onToggleTheme, onAchievementUnlocked }) {
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
  const xpPoints = progress?.xp_points || 0;
  const level = progress?.level || 1;
  const currentLevelXp = xpPoints % 100;
  const nextLevelTotalXp = level * 100;
  const xpPercent = Math.min(100, Math.max(0, currentLevelXp));

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
                  <span>{currentLevelXp} / 100 XP</span>
                  <span>{nextLevelTotalXp} total XP for next level</span>
                </div>
                <div className="level-progress__track" aria-label={`${currentLevelXp} of 100 XP`}>
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
                  <span>Sessions</span>
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
                <h2>Earned badges</h2>
              </div>
              {progress.achievements.length > 0 ? (
                <div className="achievement-list">
                  {progress.achievements.map((achievement) => (
                    <article className="achievement-card" key={achievement.id}>
                      <div className="achievement-icon">{achievement.icon}</div>
                      <div>
                        <h3>{achievement.name}</h3>
                        <p>{achievement.description}</p>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="empty-state progress-empty">
                  <div className="empty-mark">0</div>
                  <h2>No achievements yet</h2>
                  <p>Start a chat and send a message to earn your first badges.</p>
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
