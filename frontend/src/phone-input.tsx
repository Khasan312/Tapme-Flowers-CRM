import { useState, type InputHTMLAttributes } from "react";

function normalizePhone(value: string): string {
  const compact = value.replace(/[\s()\-]/g, "");
  if (/^[1-9][0-9]{8}$/.test(compact)) return "+996" + compact;
  if (/^0[1-9][0-9]{8}$/.test(compact)) return "+996" + compact.slice(1);
  if (/^996[1-9][0-9]{8}$/.test(compact)) return "+" + compact;
  if (/^\+9960[1-9][0-9]{8}$/.test(compact)) return "+996" + compact.slice(5);
  return compact;
}

type PhoneProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "type" | "value" | "defaultValue" | "onChange"
> & {
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
};

export function PhoneInput({
  value,
  defaultValue,
  onChange,
  onBlur,
  ...props
}: PhoneProps) {
  const [localValue, setLocalValue] = useState(defaultValue || "+996");
  function change(next: string) {
    setLocalValue(next);
    onChange?.(next);
  }
  return (
    <input
      type="tel"
      autoComplete="tel"
      maxLength={40}
      {...props}
      value={(value ?? localValue) || "+996"}
      onChange={(e) => change(e.target.value)}
      onBlur={(e) => {
        change(normalizePhone(e.target.value));
        onBlur?.(e);
      }}
    />
  );
}

export function AdditionalPhones({
  phone,
  values,
  onChange,
  disabled = false,
}: {
  phone: string;
  values: string[];
  onChange: (phone: string, values: string[]) => void;
  disabled?: boolean;
}) {
  return (
    <section
      className="stack additional-phones"
      aria-label="Дополнительные телефоны"
    >
      {values.map((number, index) => (
        <div className="phone-extra-row" key={index}>
          <label>
            Дополнительный телефон {index + 1}
            <PhoneInput
              value={number}
              disabled={disabled}
              onChange={(value) =>
                onChange(
                  phone,
                  values.map((v, i) => (i === index ? value : v)),
                )
              }
            />
          </label>
          <button
            type="button"
            disabled={disabled || !number.trim() || number === "+996"}
            aria-label={`Сделать телефон ${index + 1} основным`}
            onClick={() =>
              onChange(
                number,
                values.map((v, i) => (i === index ? phone : v)),
              )
            }
          >
            Основной
          </button>
          <button
            type="button"
            disabled={disabled}
            aria-label={`Удалить дополнительный телефон ${index + 1}`}
            onClick={() =>
              onChange(
                phone,
                values.filter((_, i) => i !== index),
              )
            }
          >
            Удалить
          </button>
        </div>
      ))}
      <div>
        <button
          type="button"
          disabled={disabled || values.length >= 9}
          onClick={() => onChange(phone, [...values, ""])}
        >
          Добавить телефон
        </button>
      </div>
      {values.length > 0 && (
        <p className="hint">
          Первый телефон — основной для связи и заказов. Одинаковые номера
          сохранятся один раз.
        </p>
      )}
    </section>
  );
}
