import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  getPracticeHistory,
  streamLessonStudyAssistant,
  streamPracticeFeedback,
} from "../api.js";

const STUDY_ACTIONS = [
  { action: "summarize", label: "Summarize" },
  { action: "key_points", label: "Key points" },
  { action: "explain", label: "Explain simply" },
  { action: "example", label: "Give example" },
  { action: "ask_questions", label: "Ask me questions" },
];

const THEORY_STEP_TYPES = new Set([
  "intro",
  "concept",
  "deep_dive",
  "explanation",
  "example",
  "checklist",
  "summary",
  "article",
]);

function formatDifficulty(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : "";
}

function isCodeParagraph(paragraph) {
  const trimmed = paragraph.trim();
  const codeSignals = [
    "#!/bin/",
    "FROM ",
    "WORKDIR ",
    "COPY ",
    "RUN ",
    "CMD ",
    "ENV ",
    "USER ",
    "services:",
    "volumes:",
    "healthcheck:",
    "test:",
    "pg_isready ",
    "until ",
    "done",
    "uvicorn ",
    "docker ",
    "alembic ",
    "@app.",
    "def ",
    "set -e",
  ];

  return (
    codeSignals.some((signal) => trimmed.includes(signal)) ||
    /^\s{2,}\S/m.test(paragraph) ||
    /^[A-Z_]+=.*/m.test(trimmed)
  );
}

function formatLessonContent(content) {
  const paragraphs = content.split(/\n\s*\n/).filter((paragraph) => paragraph.trim());

  return (
    <div className="lesson-content">
      {paragraphs.map((paragraph, index) =>
        isCodeParagraph(paragraph) ? (
          <pre className="lesson-code" key={`${index}-${paragraph.slice(0, 16)}`}>
            {paragraph}
          </pre>
        ) : (
          <p key={`${index}-${paragraph.slice(0, 16)}`}>{paragraph}</p>
        ),
      )}
    </div>
  );
}

export default function LessonView({
  lesson,
  isLoading,
  isCompletingStep = false,
  token,
  onPreviousStep,
  onNextStep,
  onMarkStepRead,
}) {
  const [studyQuestion, setStudyQuestion] = useState("");
  const [studyAnswer, setStudyAnswer] = useState("");
  const [studyError, setStudyError] = useState("");
  const [isStudyStreaming, setIsStudyStreaming] = useState(false);
  const [practiceAnswer, setPracticeAnswer] = useState("");
  const [practiceFeedback, setPracticeFeedback] = useState("");
  const [practiceError, setPracticeError] = useState("");
  const [isPracticeStreaming, setIsPracticeStreaming] = useState(false);
  const [practiceHistory, setPracticeHistory] = useState([]);
  const [selectedAttemptId, setSelectedAttemptId] = useState(null);
  const [historyError, setHistoryError] = useState("");
  const [pendingReadStepIndex, setPendingReadStepIndex] = useState(null);
  const closeStudyStreamRef = useRef(null);
  const closePracticeStreamRef = useRef(null);

  useEffect(() => {
    setStudyQuestion("");
    setStudyAnswer("");
    setStudyError("");
    setIsStudyStreaming(false);
    setPracticeAnswer("");
    setPracticeFeedback("");
    setPracticeError("");
    setIsPracticeStreaming(false);
    setPracticeHistory([]);
    setSelectedAttemptId(null);
    setHistoryError("");
    setPendingReadStepIndex(null);
    closeStudyStreamRef.current?.();
    closeStudyStreamRef.current = null;
    closePracticeStreamRef.current?.();
    closePracticeStreamRef.current = null;
  }, [lesson?.lesson_id, lesson?.current_step_index]);

  useEffect(() => {
    if (!lesson) {
      return;
    }

    const currentStep = lesson.steps[lesson.current_step_index] || lesson.steps[0];
    if (currentStep?.type !== "practice") {
      return;
    }

    loadPracticeHistory();
  }, [lesson?.lesson_id, lesson?.current_step_index]);

  useEffect(() => {
    return () => {
      closeStudyStreamRef.current?.();
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
  const lessonDifficultyLabel = formatDifficulty(lesson.difficulty);
  const stepDifficultyLabel = formatDifficulty(currentStep.difficulty);
  const isTheoryStep = THEORY_STEP_TYPES.has(currentStep.type);
  const isFirstStep = lesson.current_step_index <= 0;
  const isLastStep = lesson.current_step_index >= lesson.steps.length - 1;
  const isCurrentStepMarkingRead = pendingReadStepIndex === lesson.current_step_index;
  const unreadTheoryStepsBeforePractice =
    currentStep.type === "practice" &&
    lesson.steps
      .slice(0, lesson.current_step_index)
      .some((step) => THEORY_STEP_TYPES.has(step.type) && !step.completed);

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

  function askStudyAssistant(action, question = "") {
    const cleanQuestion = question.trim();
    if (isStudyStreaming || (action === "custom_question" && !cleanQuestion)) {
      return;
    }

    closeStudyStreamRef.current?.();
    setStudyAnswer("");
    setStudyError("");
    setIsStudyStreaming(true);

    closeStudyStreamRef.current = streamLessonStudyAssistant({
      lessonId: lesson.lesson_id,
      action,
      question: cleanQuestion,
      stepIndex: isTheoryStep ? lesson.current_step_index : null,
      token,
      onToken: (_chunk, fullAnswer) => {
        setStudyAnswer(fullAnswer);
      },
      onError: (message) => {
        setStudyError(message || "Unable to get study response.");
      },
      onDone: () => {
        setIsStudyStreaming(false);
        closeStudyStreamRef.current = null;
      },
    });
  }

  function handleStudySubmit(event) {
    event.preventDefault();
    askStudyAssistant("custom_question", studyQuestion);
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

  async function handleMarkStepRead() {
    if (currentStep.completed || isCompletingStep || isCurrentStepMarkingRead) {
      return;
    }

    setPendingReadStepIndex(lesson.current_step_index);
    try {
      await onMarkStepRead?.(lesson.current_step_index);
    } finally {
      setPendingReadStepIndex(null);
    }
  }

  return (
    <section className="lesson-view">
      <div className="lesson-card">
        <div className="lesson-card-header">
          <div>
            <p className="eyebrow">Structured lesson</p>
            <h2>{lesson.title}</h2>
          </div>
          <div className="lesson-header-actions">
            {lesson.difficulty ? (
              <span className={`difficulty-badge difficulty-${lesson.difficulty}`}>
                {lessonDifficultyLabel}
              </span>
            ) : null}
            <span className={lesson.completed ? "lesson-complete-badge" : "lesson-step-badge"}>
              {lesson.completed ? "Completed" : `Step ${stepNumber} / ${lesson.steps.length}`}
            </span>
          </div>
        </div>

        {lesson.completed ? (
          <div className="lesson-complete-review-banner">
            <strong>Lesson completed ✓</strong>
            <span>You can still review the lesson content and practice again.</span>
          </div>
        ) : null}

        <div className="lesson-step">
          <div className="lesson-step-meta">
            <span>{currentStep.type}</span>
            {currentStep.type === "practice" && currentStep.difficulty ? (
              <span className={`difficulty-badge difficulty-${currentStep.difficulty}`}>
                {stepDifficultyLabel}
              </span>
            ) : null}
          </div>
          <h3>{currentStep.title}</h3>
          <div className="lesson-step-content">{formatLessonContent(currentStep.content)}</div>
          {isTheoryStep ? (
            <div className="lesson-read-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={handleMarkStepRead}
                disabled={currentStep.completed || isCompletingStep || isCurrentStepMarkingRead}
              >
                {currentStep.completed
                  ? "Read ✓"
                  : isCompletingStep || isCurrentStepMarkingRead
                    ? "Marking..."
                    : "Mark as read"}
              </button>
              {currentStep.completed ? (
                <span className="lesson-xp-badge">
                  +{currentStep.xp_awarded || 0} XP earned
                </span>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="lesson-step-navigation">
          {lesson.completed ? (
            <button
              className="secondary-button"
              type="button"
              onClick={onPreviousStep}
              disabled={isFirstStep}
            >
              Previous step
            </button>
          ) : null}
          {lesson.completed && isLastStep ? (
            <button className="primary-button" type="button" disabled>
              Lesson completed
            </button>
          ) : (
            <button className="primary-button" type="button" onClick={onNextStep}>
              {isLastStep ? "Complete lesson" : "Next step"}
            </button>
          )}
        </div>
      </div>

      {currentStep.type === "practice" ? (
        <div className="lesson-card lesson-practice-card">
          <div className="lesson-card-header">
            <div>
              <p className="eyebrow">Practice Answer</p>
              <h2>Try it yourself</h2>
            </div>
            {isPracticeStreaming ? <span className="status-pill">Streaming</span> : null}
          </div>

          {unreadTheoryStepsBeforePractice ? (
            <div className="lesson-practice-tip">
              Tip: read the lesson content first to get better feedback.
            </div>
          ) : null}

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
                {practiceHistory.map((attempt) => (
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
                      Attempt {attempt.attempt_number}
                      {attempt.score !== null && attempt.score !== undefined ? (
                        <em>{attempt.score}/100</em>
                      ) : null}
                    </span>
                    <time dateTime={attempt.created_at}>
                      {formatAttemptTime(attempt.created_at)}
                    </time>
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

      <div className="lesson-card lesson-study-card">
        <div className="lesson-card-header">
          <div>
            <p className="eyebrow">Study Assistant</p>
            <h2>Study this lesson</h2>
          </div>
          {isStudyStreaming ? <span className="status-pill">Streaming</span> : null}
        </div>

        <div className="quick-actions">
          {STUDY_ACTIONS.map((item) => (
            <button
              type="button"
              key={item.action}
              onClick={() => askStudyAssistant(item.action)}
              disabled={isStudyStreaming}
            >
              {item.label}
            </button>
          ))}
        </div>

        <form className="lesson-tutor-form" onSubmit={handleStudySubmit}>
          <textarea
            value={studyQuestion}
            onChange={(event) => setStudyQuestion(event.target.value)}
            placeholder="Ask AI about this lesson..."
            rows={3}
            disabled={isStudyStreaming}
          />
          <button
            className="primary-button"
            type="submit"
            disabled={!studyQuestion.trim() || isStudyStreaming}
          >
            {isStudyStreaming ? "Asking..." : "Ask AI"}
          </button>
        </form>

        {studyError ? <p className="form-error">{studyError}</p> : null}
        {studyAnswer ? (
          <div className="lesson-tutor-answer">
            <ReactMarkdown>{studyAnswer}</ReactMarkdown>
          </div>
        ) : null}
      </div>
    </section>
  );
}
