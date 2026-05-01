import { useEffect, useState } from "react";
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

function getInitials(email = "") {
  const cleanEmail = email.trim();
  if (!cleanEmail) {
    return "U";
  }

  const [namePart] = cleanEmail.split("@");
  return namePart
    .split(/[._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("") || cleanEmail.charAt(0).toUpperCase();
}

function formatDate(value) {
  if (!value) {
    return "Not available";
  }

  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

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

export default function ProfilePage({
  token,
  theme,
  onToggleTheme,
  onLogout,
  onAchievementUnlocked,
}) {
  const [user, setUser] = useState(null);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const earnedBadges = progress?.badges?.filter((badge) => badge.earned).length || 0;

  useEffect(() => {
    let isMounted = true;

    async function loadProfile() {
      setIsLoading(true);
      setError("");
      try {
        const [userData, progressData] = await Promise.all([
          apiFetch("/me", { token }),
          apiFetch("/progress", { token }),
        ]);

        if (isMounted) {
          setUser(userData);
          setProgress(normalizeProgressResponse(progressData));
          onAchievementUnlocked?.(progressData?.new_achievements || []);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || "Unable to load profile.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadProfile();

    return () => {
      isMounted = false;
    };
  }, [token]);

  return (
    <main className="profile-shell">
      <header className="chat-header">
        <div className="chat-title">
          <p className="eyebrow">Account</p>
          <h1>Profile</h1>
        </div>
        <div className="chat-actions">
          <ThemeToggle theme={theme} onToggleTheme={onToggleTheme} />
        </div>
      </header>

      <section className="profile-content">
        {isLoading ? <p className="center-note">Loading profile...</p> : null}
        {!isLoading && error ? <p className="form-error">{error}</p> : null}

        {!isLoading && user ? (
          <>
            <section className="profile-card profile-card--identity">
              <div className="profile-avatar" aria-hidden="true">
                {getInitials(user.email)}
              </div>
              <div>
                <p className="eyebrow">User identity</p>
                <h2>{user.email}</h2>
                <p>Joined {formatDate(user.created_at)}</p>
              </div>
            </section>

            <section className="profile-grid">
              <article className="profile-card">
                <span>Current level</span>
                <strong>{progress?.level || 1}</strong>
              </article>
              <article className="profile-card">
                <span>Total XP</span>
                <strong>{progress?.total_xp ?? progress?.xp_points ?? 0}</strong>
              </article>
              <article className="profile-card">
                <span>Completed lessons</span>
                <strong>{progress?.lessons_completed || 0}</strong>
              </article>
              <article className="profile-card">
                <span>Badges earned</span>
                <strong>{earnedBadges}</strong>
              </article>
              <article className="profile-card">
                <span>Time spent</span>
                <strong>{formatTime(progress?.time_spent_seconds)}</strong>
              </article>
            </section>

            <section className="profile-card profile-card--actions">
              <div>
                <p className="eyebrow">Account actions</p>
                <h2>Session</h2>
                <p>Sign out of this browser session when you are done learning.</p>
              </div>
              <button className="secondary-button" type="button" onClick={onLogout}>
                Log out
              </button>
            </section>
          </>
        ) : null}
      </section>
    </main>
  );
}
