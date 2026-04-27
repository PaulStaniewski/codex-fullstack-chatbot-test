import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { getPracticeHistory, streamLessonTutor, streamPracticeFeedback } from "../api.js";

const QUICK_ACTIONS = ["Explain simply", "Give an example", "Why does this matter?"];

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

export default function LessonView({ lesson, isLoading, token, onNextStep }) {
  const [tutorQuestion, setTutorQuestion] = useState("");
  const [tutorAnswer, setTutorAnswer] = useState("");
  const [tutorError, setTutorError] = useState("");
  const [isTutorStreaming, setIsTutorStreaming] = useState(false);
  const [practiceAnswer, setPracticeAnswer] = useState("");
  const [practiceFeedback, setPracticeFeedback] = useState("");
  const [practiceError, setPracticeError] = useState("");
  const [isPracticeStreaming, setIsPracticeStreaming] = useState(false);
  const [practiceHistory, setPracticeHistory] = useState([]);
  const [selectedAttemptId, setSelectedAttemptId] = useState(null);
  const [historyError, setHistoryError] = useState("");
  const closeTutorStreamRef = useRef(null);
  const closePracticeStreamRef = useRef(null);

  useEffect(() => {
    setTutorQuestion("");
    setTutorAnswer("");
    setTutorError("");
    setIsTutorStreaming(false);
    setPracticeAnswer("");
    setPracticeFeedback("");
    setPracticeError("");
    setIsPracticeStreaming(false);
    setPracticeHistory([]);
    setSelectedAttemptId(null);
    setHistoryError("");
    closeTutorStreamRef.current?.();
    closeTutorStreamRef.current = null;
    closePracticeStreamRef.current?.();
    closePracticeStreamRef.current = null;
  }, [lesson?.lesson_id, lesson?.current_step_index]);

  useEffect(() => {
    if (!lesson || lesson.completed) {
      return;
    }

    const currentStep = lesson.steps[lesson.current_step_index] || lesson.steps[0];
    if (currentStep?.type !== "practice") {
      return;
    }

    loadPracticeHistory();
  }, [lesson?.lesson_id, lesson?.current_step_index, lesson?.completed]);

  useEffect(() => {
    return () => {
      closeTutorStreamRef.current?.();
      closePracticeStreamRef.current?.();
    };
  }, []);

  if (isLoading) {
    return <p className="center-note">Loading lesson...</p>;
  }

  if (!lesson) {
    return null;
  }

  const currentStep = lesson.steps[lesson.current_step_index] || lesson.steps[0];
  const stepNumber = Math.min(lesson.current_step_index + 1, lesson.steps.length);
  const selectedAttempt = practiceHistory.find((attempt) => attempt.id === selectedAttemptId);

  async function loadPracticeHistory() {
    try {
      setHistoryError("");
      const history = await getPracticeHistory(lesson.lesson_id, token);
      setPracticeHistory(history);
      setSelectedAttemptId((currentId) =>
        history.some((attempt) => attempt.id === currentId) ? currentId : null,
      );
    } catch (err) {
      setHistoryError(err.message || "Unable to load practice history.");
    }
  }

  function formatAttemptTime(value) {
    return new Date(value).toLocaleString();
  }

  function previewAnswer(value) {
    const cleanValue = value.trim().replace(/\s+/g, " ");
    return cleanValue.length > 84 ? `${cleanValue.slice(0, 81)}...` : cleanValue;
  }

  function askTutor(question = tutorQuestion) {
    const cleanQuestion = question.trim();
    if (!cleanQuestion || isTutorStreaming) {
      return;
    }

    closeTutorStreamRef.current?.();
    setTutorQuestion(cleanQuestion);
    setTutorAnswer("");
    setTutorError("");
    setIsTutorStreaming(true);

    closeTutorStreamRef.current = streamLessonTutor({
      lessonId: lesson.lesson_id,
      question: cleanQuestion,
      stepIndex: lesson.current_step_index,
      token,
      onToken: (_chunk, fullAnswer) => {
        setTutorAnswer(fullAnswer);
      },
      onError: (message) => {
        setTutorError(message || "Unable to get tutor response.");
      },
      onDone: () => {
        setIsTutorStreaming(false);
        closeTutorStreamRef.current = null;
      },
    });
  }

  function handleTutorSubmit(event) {
    event.preventDefault();
    askTutor();
  }

  function requestPracticeFeedback() {
    const cleanAnswer = practiceAnswer.trim();
    if (!cleanAnswer || isPracticeStreaming) {
      return;
    }

    closePracticeStreamRef.current?.();
    setPracticeFeedback("");
    setPracticeError("");
    setIsPracticeStreaming(true);

    closePracticeStreamRef.current = streamPracticeFeedback({
      lessonId: lesson.lesson_id,
      stepIndex: lesson.current_step_index,
      answer: cleanAnswer,
      token,
      onToken: (_chunk, fullAnswer) => {
        setPracticeFeedback(fullAnswer);
      },
      onError: (message) => {
        setPracticeError(message || "Unable to get practice feedback.");
      },
      onDone: () => {
        setIsPracticeStreaming(false);
        closePracticeStreamRef.current = null;
        loadPracticeHistory();
      },
    });
  }

  function handlePracticeSubmit(event) {
    event.preventDefault();
    requestPracticeFeedback();
  }

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

      {!lesson.completed && currentStep.type === "practice" ? (
        <div className="lesson-card lesson-practice-card">
          <div className="lesson-card-header">
            <div>
              <p className="eyebrow">Practice Answer</p>
              <h2>Try it yourself</h2>
            </div>
            {isPracticeStreaming ? <span className="status-pill">Streaming</span> : null}
          </div>

          <form className="lesson-practice-form" onSubmit={handlePracticeSubmit}>
            <textarea
              value={practiceAnswer}
              onChange={(event) => setPracticeAnswer(event.target.value)}
              placeholder="Write your answer for this practice step..."
              rows={4}
              disabled={isPracticeStreaming}
            />
            <button
              className="primary-button"
              type="submit"
              disabled={!practiceAnswer.trim() || isPracticeStreaming}
            >
              {isPracticeStreaming ? "Getting feedback..." : "Get AI feedback"}
            </button>
          </form>

          {practiceError ? <p className="form-error">{practiceError}</p> : null}
          {practiceFeedback ? (
            <div className="lesson-feedback">
              <ReactMarkdown>{practiceFeedback}</ReactMarkdown>
            </div>
          ) : null}

          <div className="practice-history">
            <div>
              <p className="eyebrow">Previous attempts</p>
              {historyError ? <p className="form-error">{historyError}</p> : null}
            </div>
            {practiceHistory.length > 0 ? (
              <div className="practice-attempt-list">
                {practiceHistory.map((attempt, index) => (
                  <button
                    type="button"
                    key={attempt.id}
                    className={
                      selectedAttemptId === attempt.id
                        ? "practice-attempt active"
                        : "practice-attempt"
                    }
                    onClick={() =>
                      setSelectedAttemptId((currentId) =>
                        currentId === attempt.id ? null : attempt.id,
                      )
                    }
                  >
                    <span>
                      Attempt {practiceHistory.length - index}
                      {attempt.score !== null && attempt.score !== undefined ? (
                        <em>{attempt.score}/100</em>
                      ) : null}
                    </span>
                    <time dateTime={attempt.created_at}>{formatAttemptTime(attempt.created_at)}</time>
                    <strong>{previewAnswer(attempt.answer)}</strong>
                  </button>
                ))}
              </div>
            ) : (
              <p className="practice-history-empty">No previous attempts for this lesson yet.</p>
            )}

            {selectedAttempt ? (
              <div className="practice-attempt-detail">
                <div>
                  <h3>Your answer</h3>
                  <p>{selectedAttempt.answer}</p>
                </div>
                <div>
                  <h3>AI feedback</h3>
                  {selectedAttempt.score !== null && selectedAttempt.score !== undefined ? (
                    <div className="practice-score-badge">Score {selectedAttempt.score}/100</div>
                  ) : null}
                  {selectedAttempt.strengths?.length > 0 ? (
                    <div className="practice-metadata-list">
                      <h4>Strengths</h4>
                      <ul>
                        {selectedAttempt.strengths.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {selectedAttempt.improvements?.length > 0 ? (
                    <div className="practice-metadata-list">
                      <h4>Improvements</h4>
                      <ul>
                        {selectedAttempt.improvements.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <ReactMarkdown>{selectedAttempt.feedback}</ReactMarkdown>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="lesson-card lesson-tutor-card">
        <div className="lesson-card-header">
          <div>
            <p className="eyebrow">AI Tutor</p>
            <h2>Ask about this step</h2>
          </div>
          {isTutorStreaming ? <span className="status-pill">Streaming</span> : null}
        </div>

        <div className="quick-actions">
          {QUICK_ACTIONS.map((action) => (
            <button
              type="button"
              key={action}
              onClick={() => askTutor(action)}
              disabled={isTutorStreaming}
            >
              {action}
            </button>
          ))}
        </div>

        <form className="lesson-tutor-form" onSubmit={handleTutorSubmit}>
          <textarea
            value={tutorQuestion}
            onChange={(event) => setTutorQuestion(event.target.value)}
            placeholder="Ask AI about this step..."
            rows={3}
            disabled={isTutorStreaming}
          />
          <button
            className="primary-button"
            type="submit"
            disabled={!tutorQuestion.trim() || isTutorStreaming}
          >
            {isTutorStreaming ? "Asking..." : "Ask AI"}
          </button>
        </form>

        {tutorError ? <p className="form-error">{tutorError}</p> : null}
        {tutorAnswer ? (
          <div className="lesson-tutor-answer">
            <ReactMarkdown>{tutorAnswer}</ReactMarkdown>
          </div>
        ) : null}
      </div>
    </section>
  );
}
