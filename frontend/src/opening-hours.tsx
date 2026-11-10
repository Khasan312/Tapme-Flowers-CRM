import { useState } from "react";

function parseHours(value: string) {
  const match = value
    .trim()
    .match(
      /^((?:[01]?\d|2[0-3]):[0-5]\d)?\s*[–—-]\s*((?:[01]?\d|2[0-3]):[0-5]\d)?$/,
    );
  return match
    ? [match[1] || "", match[2] || ""].map((time) =>
        time ? time.padStart(5, "0") : "",
      )
    : null;
}

export function OpeningHours({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const [manual, setManual] = useState(false);
  const range = parseHours(value);

  return (
    <fieldset className="point-hours" aria-label="Часы работы">
      <div className="point-hours-heading">
        <h4>Часы работы</h4>
        <button
          className="point-hours-mode"
          type="button"
          onClick={() => {
            if (!range || manual) {
              if (!range) onChange("09:00–21:00");
              setManual(false);
            } else {
              setManual(true);
            }
          }}
        >
          {!range || manual ? "Выбрать время" : "Указать другой график"}
        </button>
      </div>
      {!range || manual ? (
        <input
          aria-label="Часы работы"
          maxLength={150}
          placeholder="Например, Пн–Пт 09:00–21:00"
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <div className="point-hours-range">
          {(["Открытие", "Закрытие"] as const).map((label, index) => (
            <label key={label}>
              <span>{label}</span>
              <input
                aria-label={`Время ${index === 0 ? "открытия" : "закрытия"} точки`}
                type="time"
                required
                value={range[index]}
                onChange={(event) => {
                  const next = [...range];
                  next[index] = event.target.value;
                  onChange(next.join("–"));
                }}
              />
            </label>
          ))}
        </div>
      )}
    </fieldset>
  );
}
