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
