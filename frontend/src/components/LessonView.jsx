function formatLessonContent(content) {
  const looksLikeCode =
    content.includes("\n") ||
    content.includes("@app.") ||
    content.includes("docker ") ||
    content.includes("def ");

  if (looksLikeCode) {
    return <pre className="lesson-code">{content}</pre>;
  }

  return <p>{content}</p>;
}

export default function LessonView({ lesson, isLoading, onNextStep }) {
  if (isLoading) {
    return <p className="center-note">Loading lesson...</p>;
  }

  if (!lesson) {
    return null;
  }

  const currentStep = lesson.steps[lesson.current_step_index] || lesson.steps[0];
  const stepNumber = Math.min(lesson.current_step_index + 1, lesson.steps.length);

  return (
    <section className="lesson-view">
      <div className="lesson-card">
        <div className="lesson-card-header">
          <div>
            <p className="eyebrow">Structured lesson</p>
            <h2>{lesson.title}</h2>
          </div>
          <span className={lesson.completed ? "lesson-complete-badge" : "lesson-step-badge"}>
            {lesson.completed ? "Completed" : `Step ${stepNumber} / ${lesson.steps.length}`}
          </span>
        </div>

        {lesson.completed ? (
          <div className="lesson-complete-state">
            <div className="empty-mark">✓</div>
            <h3>Lesson completed</h3>
            <p>You earned XP for finishing this lesson.</p>
          </div>
        ) : (
          <>
            <div className="lesson-step">
              <span>{currentStep.type}</span>
              <h3>{currentStep.title}</h3>
              <div className="lesson-step-content">
                {formatLessonContent(currentStep.content)}
              </div>
            </div>

            <button className="primary-button lesson-next-button" type="button" onClick={onNextStep}>
              {lesson.current_step_index >= lesson.steps.length - 1
                ? "Complete lesson"
                : "Next step"}
            </button>
          </>
        )}
      </div>
    </section>
  );
}
