import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { streamLessonTutor, streamPracticeFeedback } from "../api.js";

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
    closeTutorStreamRef.current?.();
    closeTutorStreamRef.current = null;
    closePracticeStreamRef.current?.();
    closePracticeStreamRef.current = null;
  }, [lesson?.lesson_id, lesson?.current_step_index]);

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
