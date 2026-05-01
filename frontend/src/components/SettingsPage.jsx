import { useEffect, useState } from "react";
import { apiFetch } from "../api.js";
import ThemeToggle from "./ThemeToggle.jsx";

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

export default function SettingsPage({ token, theme, onToggleTheme, onLogout }) {
  const [user, setUser] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadUser() {
      setIsLoading(true);
      setError("");
      try {
        const data = await apiFetch("/me", { token });
        if (isMounted) {
          setUser(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || "Unable to load settings.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadUser();

    return () => {
      isMounted = false;
    };
  }, [token]);

  return (
    <main className="settings-shell">
      <header className="chat-header">
        <div className="chat-title">
          <p className="eyebrow">Account</p>
          <h1>Settings</h1>
        </div>
        <div className="chat-actions">
          <ThemeToggle theme={theme} onToggleTheme={onToggleTheme} />
        </div>
      </header>

      <section className="settings-content">
        {isLoading ? <p className="center-note">Loading settings...</p> : null}
        {!isLoading && error ? <p className="form-error">{error}</p> : null}

        {!isLoading && user ? (
          <>
            <section className="settings-card">
              <div>
                <p className="eyebrow">Account</p>
                <h2>{user.email}</h2>
                <p>Joined {formatDate(user.created_at)}</p>
              </div>
              <button className="secondary-button" type="button" onClick={onLogout}>
                Log out
              </button>
            </section>

            <section className="settings-card">
              <div>
                <p className="eyebrow">Preferences</p>
                <h2>Theme</h2>
                <p>Current theme: {theme === "dark" ? "Dark" : "Light"}</p>
              </div>
              <ThemeToggle theme={theme} onToggleTheme={onToggleTheme} />
            </section>

            <section className="settings-card settings-card--muted">
              <div>
                <p className="eyebrow">Learning</p>
                <h2>Progress controls</h2>
                <p>
                  Progress reset is not available yet. Your lessons, XP, badges, and
                  practice history remain preserved.
                </p>
              </div>
            </section>
          </>
        ) : null}
      </section>
    </main>
  );
}
