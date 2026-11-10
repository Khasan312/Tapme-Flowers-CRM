import { useState, type FormEvent, type ReactNode } from "react";
import { ArrowUpRight, Flower2 } from "lucide-react";
import { errorText, request } from "./api";
import { Notice } from "./components";
import { LoginBloom, LoginHangingBloom } from "./login-bloom";
import { LoginStoryCopy } from "./login-story-copy";
import { siteUrl } from "./marketing/routes";

export const crmUrl = () => siteUrl("login");
export const platformUrl = () => `${import.meta.env.BASE_URL}platform/`;

function AuthLayout({
  children,
  platform = false,
}: {
  children: ReactNode;
  platform?: boolean;
}) {
  return (
    <main className="login-page">
      <section className="login-story">
        {!platform && (
          <>
            <LoginHangingBloom />
            <LoginBloom />
          </>
        )}
        <div className="brand">
          <span className="brand-mark">
            <Flower2 />
          </span>
          <span>
            tapme<small>Flowers</small>
          </span>
        </div>
        {platform ? (
          <div>
            <span className="eyebrow">УПРАВЛЕНИЕ ПЛАТФОРМОЙ</span>
            <h1>
              Магазины под вашим
              <br />
              управлением.
            </h1>
            <p>Подключайте магазины и выдавайте первый доступ их владельцам.</p>
          </div>
        ) : (
          <LoginStoryCopy />
        )}
        <span className="login-foot">Tapme Flowers · Бишкек</span>
      </section>
      <section className="login-panel">{children}</section>
    </main>
  );
}

export function SignInPage({
  onSubmit,
  error,
  busy,
  platform = false,
}: {
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  error: string;
  busy: boolean;
  platform?: boolean;
}) {
  return (
    <AuthLayout platform={platform}>
      <form className="login-card" onSubmit={onSubmit}>
        {!platform && (
          <a className="login-site-link" href={siteUrl()}>
            На главную Tapme Flowers
          </a>
        )}
        <span className="eyebrow">
          {platform ? "КОМАНДА TAPME" : "ВАШ МАГАЗИН"}
        </span>
        <h2>{platform ? "Вход в панель TapMe" : "С возвращением"}</h2>
        <p className="muted">
          {platform
            ? "Используйте личную учётную запись администратора платформы."
            : "Войдите, чтобы начать рабочий день."}
        </p>
        {error && <Notice>{error}</Notice>}
        <label>
          Логин
          <input
            name="username"
            required
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
          />
        </label>
        <label>
          Пароль
          <input
            name="password"
            type="password"
            required
            autoComplete="current-password"
          />
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Входим…" : platform ? "Войти в панель TapMe" : "Войти в CRM"}
          <ArrowUpRight size={18} />
        </button>
        <p className="login-hint">
          {platform
            ? "Доступ только для администраторов TapMe."
            : "Доступ сотрудникам выдаёт владелец магазина."}
        </p>
        {!platform && (
          <a className="login-site-link" href={siteUrl("privacy")}>
            Политика конфиденциальности
          </a>
        )}
      </form>
    </AuthLayout>
  );
}

export function FirstPasswordPage({
  signedOut,
  changed,
}: {
  signedOut: () => void;
  changed: () => void;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    setError("");
    if (data.get("new_password") !== data.get("confirmation")) {
      setError("Новые пароли не совпадают.");
      return;
    }
    setBusy(true);
    try {
      await request("/auth/password/", {
        method: "POST",
        body: JSON.stringify({
          current_password: data.get("current_password"),
          new_password: data.get("new_password"),
        }),
      });
      changed();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <AuthLayout>
      <form className="login-card" onSubmit={submit}>
        <span className="eyebrow">ПЕРВЫЙ ВХОД</span>
        <h2>Задайте свой пароль</h2>
        <p className="muted">
          Для начала работы замените временный пароль, который вам передали.
          Новый пароль должен содержать не менее 12 символов.
        </p>
        {error && <Notice>{error}</Notice>}
        <label>
          Временный пароль
          <input
            type="password"
            name="current_password"
            autoComplete="current-password"
            required
          />
        </label>
        <label>
          Новый пароль
          <input
            type="password"
            name="new_password"
            autoComplete="new-password"
            required
            minLength={12}
            maxLength={128}
          />
        </label>
        <label>
          Повторите новый пароль
          <input
            type="password"
            name="confirmation"
            autoComplete="new-password"
            required
            minLength={12}
            maxLength={128}
          />
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Сохраняем…" : "Сохранить и открыть CRM"}
        </button>
        <button type="button" disabled={busy} onClick={signedOut}>
          Выйти
        </button>
      </form>
    </AuthLayout>
  );
}
