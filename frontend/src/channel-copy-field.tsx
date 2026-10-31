import { useState } from "react";
import { Copy } from "lucide-react";
export function CopyField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);
  const [manual, setManual] = useState(false);
  return (
    <label>
      {label}
      <div className="chat-copy">
        {value.length > 130 ? (
          <textarea readOnly value={value} onFocus={(e) => e.target.select()} />
        ) : (
          <input readOnly value={value} onFocus={(e) => e.target.select()} />
        )}
        <button
          type="button"
          className="btn"
          aria-label={`Копировать ${label}`}
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(value);
              setCopied(true);
            } catch {
              setCopied(false);
              setManual(true);
            }
          }}
        >
          <Copy size={16} />
          {copied ? "Скопировано" : "Копировать"}
        </button>
      </div>
      {manual && (
        <small>
          Нажмите на текст: он выделится. Затем выберите «Копировать» в меню
          телефона.
        </small>
      )}
    </label>
  );
}
