import { useState } from "react";
import ThemeToggle from "./ThemeToggle.jsx";

export default function AuthView({ onLogin, onRegister, theme, onToggleTheme }) {
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
      setError(err.message);
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
              minLength={8}
              required
            />
          </label>

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
