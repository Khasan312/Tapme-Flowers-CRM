import type { ReactNode } from "react";
export const roleNames: Record<string, string> = {
  owner: "Владелец",
  manager: "Менеджер",
  florist: "Флорист",
  courier: "Курьер",
};
export const roleAccess: Record<string, string> = {
  owner: "Всё, включая суммы и настройки",
  manager: "Заказы, клиенты, напоминания, доставка",
  florist: "Только заказы на сборку, без сумм",
  courier: "Только свой маршрут, без сумм",
};
export function initials(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((s) => s[0])
    .join("")
    .toUpperCase();
}
export function Avatar({ name }: { name: string }) {
  return (
    <span className="av" aria-hidden="true">
      {initials(name)}
    </span>
  );
}
export function Toggle({
  checked,
  onChange,
  disabled,
  children,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <label className={`toggle${checked ? " on" : ""}`}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <i aria-hidden="true" />
      {children}
    </label>
  );
}
export function shopDay(timezone: string, offset = 0) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const value = (name: string) => parts.find((p) => p.type === name)!.value;
  const date = new Date(
    `${value("year")}-${value("month")}-${value("day")}T12:00:00Z`,
  );
  date.setUTCDate(date.getUTCDate() + offset);
  return date.toISOString().slice(0, 10);
}
export function shortDate(day: string) {
  return new Date(day + "T12:00:00").toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
  });
}

export function BrandMark() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 22V12" />
      <path d="M12 12c-4 0-6-2.2-6-5 0-2 1.5-3.5 3.5-3.5 1.1 0 2 .5 2.5 1.3.5-.8 1.4-1.3 2.5-1.3C16.5 3.5 18 5 18 7c0 2.8-2 5-6 5z" />
      <path d="M12 17c-2.2 0-3.5-1.2-3.5-3" />
      <path d="M12 19c2.2 0 3.5-1.2 3.5-3" />
    </svg>
  );
}
