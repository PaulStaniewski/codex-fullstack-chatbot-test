import { useEffect, useMemo, useState } from "react";
import ThemeToggle from "./ThemeToggle.jsx";

const REMEMBERED_EMAIL_KEY = "chatbot_remembered_email";

function getAuthErrorMessage(err, isLogin) {
  const status = err?.status;
  const detail = err?.detail;
  const rawMessage = `${err?.message || ""}`.toLowerCase();

  if (status === 429) {
    return "Too many login attempts. Please try again later.";
  }

  if (isLogin && (status === 401 || status === 403 || rawMessage.includes("invalid credentials"))) {
    return "Invalid email or password.";
  }

  if (!isLogin && (rawMessage.includes("email already registered") || rawMessage.includes("already registered"))) {
    return "This email is already registered.";
  }

  if (!isLogin && status === 422) {
    const detailText =
      typeof detail === "string"
        ? detail.toLowerCase()
        : Array.isArray(detail)
          ? JSON.stringify(detail).toLowerCase()
          : "";

    if (
      detailText.includes("password") ||
      detailText.includes("at least 10 characters") ||
      detailText.includes("letter and one number") ||
      detailText.includes("string_too_short")
    ) {
      return "Password must be at least 10 characters and include a letter and a number.";
    }
  }

  return "Something went wrong. Please try again.";
}

export default function AuthView({ onLogin, onRegister, onAuthError, theme, onToggleTheme }) {
  const rememberedEmail = useMemo(() => localStorage.getItem(REMEMBERED_EMAIL_KEY) || "", []);
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState(rememberedEmail);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [rememberEmail, setRememberEmail] = useState(Boolean(rememberedEmail));

  const isLogin = mode === "login";

  useEffect(() => {
    if (isLogin) {
      return;
    }
    setRememberEmail(false);
  }, [isLogin]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      if (isLogin) {
        await onLogin(email, password);
        if (rememberEmail && email.trim()) {
          localStorage.setItem(REMEMBERED_EMAIL_KEY, email.trim());
        } else {
          localStorage.removeItem(REMEMBERED_EMAIL_KEY);
        }
      } else {
        await onRegister(email, password);
      }
    } catch (err) {
      const friendlyMessage = getAuthErrorMessage(err, isLogin);
      setError(friendlyMessage);
      onAuthError(friendlyMessage);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <div className="auth-theme">
        <ThemeToggle theme={theme} onToggleTheme={onToggleTheme} />
      </div>
      <section className="auth-layout" aria-labelledby="auth-title">
        <aside className="auth-hero" aria-label="Platform overview">
          <p className="eyebrow">Learning Platform</p>
          <h1 id="auth-title">Learn engineering by building real systems.</h1>
          <p className="auth-hero-copy">
            Build practical confidence across backend services, infrastructure, and AI workflows.
          </p>
          <ul className="auth-hero-points">
            <li>Real-world backend, Docker, database, and AI scenarios</li>
            <li>Practice tasks with feedback</li>
            <li>Progress, XP, and achievements</li>
          </ul>
          <p className="auth-status-line">Production-style learning workspace</p>
        </aside>

        <section className="auth-panel auth-card" aria-label="Authentication form">
          <div className="auth-mode-tabs" role="tablist" aria-label="Authentication mode">
            <button
              type="button"
              className={isLogin ? "auth-mode-tab active" : "auth-mode-tab"}
              role="tab"
              aria-selected={isLogin}
              aria-controls="auth-form-stage"
              onClick={() => {
                setMode("login");
                setError("");
              }}
            >
              Log in
            </button>
            <button
              type="button"
              className={!isLogin ? "auth-mode-tab active" : "auth-mode-tab"}
              role="tab"
              aria-selected={!isLogin}
              aria-controls="auth-form-stage"
              onClick={() => {
                setMode("register");
                setError("");
              }}
            >
              Register
            </button>
          </div>

          <div className="auth-brand auth-card-header">
            <p className="eyebrow">{isLogin ? "Welcome back" : "Create your account"}</p>
            <h2>{isLogin ? "Continue your learning streak" : "Start your learning workspace"}</h2>
            <p className="auth-helper-copy">
              {isLogin
                ? "Log in to resume lessons, conversations, and progress."
                : "Create an account to track progress and unlock achievements."}
            </p>
          </div>

          <div
            id="auth-form-stage"
            className={isLogin ? "auth-form-stage mode-login" : "auth-form-stage mode-register"}
          >
            <form className="auth-form" onSubmit={handleSubmit}>
              <label>
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  autoComplete="email"
                  required
                />
              </label>

              <label>
                Password
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete={isLogin ? "current-password" : "new-password"}
                  minLength={10}
                  required
                />
              </label>

              {isLogin ? (
                <label className="auth-remember-row">
                  <input
                    className="auth-remember-checkbox"
                    type="checkbox"
                    checked={rememberEmail}
                    onChange={(event) => setRememberEmail(event.target.checked)}
                  />
                  <span>Remember email on this device</span>
                </label>
              ) : (
                <p className="auth-help">Use at least 10 characters, including a letter and a number.</p>
              )}

              {error ? <p className="form-error" role="alert">{error}</p> : null}

              <button className="primary-button" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Please wait..." : isLogin ? "Log in" : "Create account"}
              </button>
            </form>
          </div>
        </section>
      </section>
    </main>
  );
}
