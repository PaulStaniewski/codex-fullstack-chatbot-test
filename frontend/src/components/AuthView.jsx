import { useState } from "react";
import ThemeToggle from "./ThemeToggle.jsx";

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
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isLogin = mode === "login";

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      if (isLogin) {
        await onLogin(email, password);
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
      <section className="auth-panel" aria-labelledby="auth-title">
        <div className="auth-brand">
          <div className="brand-mark">AI</div>
          <p className="eyebrow">Fullstack Chatbot</p>
          <h1 id="auth-title">{isLogin ? "Welcome back" : "Create your account"}</h1>
        </div>

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
          {!isLogin ? (
            <p className="auth-help">Use at least 10 characters, including a letter and a number.</p>
          ) : null}

          {error ? <p className="form-error" role="alert">{error}</p> : null}

          <button className="primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Please wait..." : isLogin ? "Log in" : "Register"}
          </button>
        </form>

        <div className="auth-switch">
          <span>{isLogin ? "Need an account?" : "Already have an account?"}</span>
          <button
            className="link-button"
            type="button"
            onClick={() => {
              setMode(isLogin ? "register" : "login");
              setError("");
            }}
          >
            {isLogin ? "Register" : "Log in"}
          </button>
        </div>
      </section>
    </main>
  );
}
