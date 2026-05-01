import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "../api.js";
import ThemeToggle from "./ThemeToggle.jsx";

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

function formatEarnedDate(value) {
  if (!value) {
    return "Not unlocked yet";
  }

  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function AchievementsPage({ token, theme, onToggleTheme, onAchievementUnlocked }) {
  const [progress, setProgress] = useState(null);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const badges = progress?.badges || [];
  const earnedCount = badges.filter((badge) => badge.earned).length;
  const lockedCount = badges.length - earnedCount;
  const filteredBadges = useMemo(() => {
    if (filter === "earned") {
      return badges.filter((badge) => badge.earned);
    }
    if (filter === "locked") {
      return badges.filter((badge) => !badge.earned);
    }
    return badges;
  }, [badges, filter]);

  useEffect(() => {
    let isMounted = true;

    async function loadAchievements() {
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
          setError(err.message || "Unable to load achievements.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadAchievements();

    return () => {
      isMounted = false;
    };
  }, [token]);

  return (
    <main className="achievements-shell">
      <header className="chat-header">
        <div className="chat-title">
          <p className="eyebrow">Learning Book</p>
          <h1>Achievements</h1>
        </div>
        <div className="chat-actions">
          <ThemeToggle theme={theme} onToggleTheme={onToggleTheme} />
        </div>
      </header>

      <section className="achievements-content">
        {isLoading ? <p className="center-note">Loading achievements...</p> : null}
        {!isLoading && error ? <p className="form-error">{error}</p> : null}

        {!isLoading && progress ? (
          <>
            <section className="achievements-summary">
              <div>
                <p className="eyebrow">Badges</p>
                <h2>
                  {earnedCount} unlocked, {lockedCount} locked
                </h2>
                <p>
                  Track earned milestones and see what is still waiting to be
                  unlocked as you continue learning.
                </p>
              </div>
              <div className="achievement-filters" aria-label="Achievement filters">
                {["all", "earned", "locked"].map((item) => (
                  <button
                    key={item}
                    type="button"
                    className={filter === item ? "active" : ""}
                    onClick={() => setFilter(item)}
                  >
                    {item.charAt(0).toUpperCase() + item.slice(1)}
                  </button>
                ))}
              </div>
            </section>

            {filteredBadges.length > 0 ? (
              <div className="achievement-list achievement-list--full">
                {filteredBadges.map((badge) => (
                  <article
                    className={
                      badge.earned
                        ? "achievement-card achievement-card--earned"
                        : "achievement-card achievement-card--locked"
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
                      <time dateTime={badge.earned_at || undefined}>
                        {formatEarnedDate(badge.earned_at)}
                      </time>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state progress-empty">
                <div className="empty-mark">0</div>
                <h2>No badges in this filter</h2>
                <p>Try another filter to view the rest of your achievement list.</p>
              </div>
            )}
          </>
        ) : null}
      </section>
    </main>
  );
}
