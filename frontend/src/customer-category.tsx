import { useEffect, useState } from "react";

const categories = ["VIP", "Корпоративный"];

export function CustomerCategory({
  tags,
  onChange,
  disabled = false,
}: {
  tags: string[];
  onChange: (tags: string[]) => void;
  disabled?: boolean;
}) {
  const vip = tags.includes("VIP"),
    corporate = tags.includes("Корпоративный");
  const others = tags.filter((tag) => !categories.includes(tag));
  const otherText = others.join(", ");
  const [draft, setDraft] = useState(otherText);
  useEffect(() => setDraft(otherText), [otherText]);
  return (
    <div className="stack">
      <label>
        Категория клиента
        <select
          aria-label="Категория клиента"
          value={
            vip && corporate
              ? "both"
              : vip
                ? "vip"
                : corporate
                  ? "corporate"
                  : "regular"
          }
          disabled={disabled}
          onChange={(e) =>
            onChange([
              ...others,
              ...(["vip", "both"].includes(e.target.value) ? ["VIP"] : []),
              ...(["corporate", "both"].includes(e.target.value)
                ? ["Корпоративный"]
                : []),
            ])
          }
        >
          <option value="regular">Обычный</option>
          <option value="vip">VIP</option>
          <option value="corporate">Корпоративный</option>
          <option value="both">VIP и корпоративный</option>
        </select>
      </label>
      <details>
        <summary>
          Другие метки{others.length ? ` · ${others.join(", ")}` : ""}
        </summary>
        <label>
          Дополнительные метки
          <input
            disabled={disabled}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Например: Постоянный, Любит розы"
            onBlur={(e) =>
              onChange([
                ...tags.filter((tag) => categories.includes(tag)),
                ...e.target.value
                  .split(",")
                  .map((t) => t.trim())
                  .filter((t) => t && !categories.includes(t)),
              ])
            }
          />
        </label>
      </details>
    </div>
  );
}
