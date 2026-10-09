import { Star } from "lucide-react";
import type { Feedback } from "./types";
import "./customer-feedback.css";

export function CustomerFeedback({
  feedback,
  timezone,
}: {
  feedback: Feedback;
  timezone: string;
}) {
  const rating = feedback.rating;
  const rated =
    rating !== null && Number.isInteger(rating) && rating >= 1 && rating <= 5;
  const date = new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: timezone,
  }).format(new Date(feedback.created_at));
  return (
    <article className="customer-feedback">
      <header className="customer-feedback-header">
        <div className="customer-feedback-meta">
          <span
            className={`customer-feedback-kind${feedback.kind === "complaint" ? " is-complaint" : ""}`}
          >
            {feedback.kind === "complaint" ? "Жалоба" : "Отзыв"}
          </span>
          <time dateTime={feedback.created_at}>{date}</time>
        </div>
        {rated ? (
          <span
            className="customer-feedback-rating"
            role="img"
            aria-label={`Оценка: ${rating} из 5`}
          >
            <span className="customer-feedback-stars" aria-hidden="true">
              {[1, 2, 3, 4, 5].map((star) => (
                <Star
                  key={star}
                  size={15}
                  className={star <= rating ? "is-filled" : ""}
                />
              ))}
            </span>
            <span aria-hidden="true">{rating}/5</span>
          </span>
        ) : (
          <span className="customer-feedback-unrated">Без оценки</span>
        )}
      </header>
      <p className="customer-feedback-message">{feedback.message}</p>
      {feedback.outcome && (
        <div className="customer-feedback-outcome">
          <strong>Решение</strong>
          <p>{feedback.outcome}</p>
        </div>
      )}
    </article>
  );
}
