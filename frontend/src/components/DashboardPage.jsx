import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "../api.js";
import { learningStructure } from "../learningStructure.js";
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

function flattenLessons() {
  return learningStructure.flatMap((course) =>
    (course.modules || []).flatMap((module) =>
      module.lessons.map((lesson) => ({
        ...lesson,
        course_id: course.id,
        course_title: course.title,
        module_title: module.title,
      })),
    ),
  );
}

function getNextLesson(lessons, lessonProgress) {
  const progressByLessonId = new Map(
    lessonProgress.map((progress) => [progress.lesson_id, progress]),
  );
  const inProgressLesson = lessons.find((lesson) => {
    const progress = progressByLessonId.get(lesson.id);
    return progress && !progress.completed;
  });

  if (inProgressLesson) {
    return inProgressLesson;
  }

  return (
    lessons.find((lesson) => !progressByLessonId.get(lesson.id)?.completed) ||
    lessons[0] ||
    null
  );
}

function formatLevel(progress) {
  if (!progress) {
    return "Level 1";
  }

  return `Level ${progress.level || 1}`;
}

export default function DashboardPage({
  token,
  theme,
  onToggleTheme,
  lessonProgress,
  onSelectLesson,
  onShowProgress,
  onCreateConversation,
  onAchievementUnlocked,
}) {
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const lessons = useMemo(() => flattenLessons(), []);
  const nextLesson = useMemo(
    () => getNextLesson(lessons, lessonProgress),
    [lessons, lessonProgress],
  );
  const completedLessons = lessonProgress.filter((item) => item.completed).length;
  const earnedBadges = progress?.badges?.filter((badge) => badge.earned).length || 0;

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
          setError(err.message || "Unable to load dashboard.");
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

  function continueLearning() {
    if (!nextLesson) {
      return;
    }

    onSelectLesson({
      lesson_id: nextLesson.id,
      lesson_title: nextLesson.title,
      course_id: nextLesson.course_id,
      course_title: nextLesson.course_title,
    });
  }

  return (
    <main className="dashboard-shell">
      <header className="chat-header">
        <div className="chat-title">
          <p className="eyebrow">Home</p>
          <h1>Dashboard</h1>
        </div>
        <div className="chat-actions">
          <ThemeToggle theme={theme} onToggleTheme={onToggleTheme} />
        </div>
      </header>

      <section className="dashboard-content">
        <section className="dashboard-hero">
          <div>
            <p className="eyebrow">Welcome back</p>
            <h2>Continue building production Docker skills.</h2>
            <p>
              Pick up your next lesson, review your progress, or start a focused
              learning chat when you want help reasoning through a concept.
            </p>
          </div>
          <div className="dashboard-actions">
            <button type="button" onClick={continueLearning} disabled={!nextLesson}>
              Continue learning
            </button>
            <button type="button" className="secondary-button" onClick={onShowProgress}>
              Open progress
            </button>
            <button type="button" className="secondary-button" onClick={onCreateConversation}>
              Start new chat
            </button>
          </div>
        </section>

        {isLoading ? <p className="center-note">Loading dashboard...</p> : null}
        {!isLoading && error ? <p className="form-error">{error}</p> : null}

        <section className="dashboard-grid">
          <article className="dashboard-card dashboard-card--wide">
            <div>
              <p className="eyebrow">Continue learning</p>
              <h2>{nextLesson?.title || "No lessons available"}</h2>
              <p>
                {nextLesson
                  ? `${nextLesson.course_title} - ${nextLesson.module_title}`
                  : "Lessons will appear here when the curriculum is available."}
              </p>
            </div>
            <button type="button" onClick={continueLearning} disabled={!nextLesson}>
              Open lesson
            </button>
          </article>

          <article className="dashboard-card">
            <span>Level</span>
            <strong>{formatLevel(progress)}</strong>
          </article>
          <article className="dashboard-card">
            <span>Total XP</span>
            <strong>{progress?.total_xp ?? progress?.xp_points ?? 0}</strong>
          </article>
          <article className="dashboard-card">
            <span>Completed lessons</span>
            <strong>{completedLessons}</strong>
          </article>
          <article className="dashboard-card">
            <span>Badges earned</span>
            <strong>{earnedBadges}</strong>
          </article>

          <article className="dashboard-card dashboard-card--wide">
            <div>
              <p className="eyebrow">Suggested next</p>
              <h2>{nextLesson?.title || "Start with Docker Basics"}</h2>
              <p>
                {nextLesson
                  ? "This is the next practical step based on your lesson progress."
                  : "A starter lesson will be suggested once the catalog loads."}
              </p>
            </div>
          </article>
        </section>
      </section>
    </main>
  );
}
