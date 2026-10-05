import { useState, type FormEvent } from "react";
import { errorText, request } from "./api";
import { Modal, Notice } from "./components";

export function PasswordPanel({ close }: { close: () => void }) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [done, setDone] = useState(false);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    const d = new FormData(e.currentTarget);
    if (d.get("new_password") !== d.get("confirmation")) {
      setError("Новые пароли не совпадают.");
      return;
    }
    setBusy(true);
    try {
      await request("/auth/password/", {
        method: "POST",
        body: JSON.stringify({
          current_password: d.get("current_password"),
          new_password: d.get("new_password"),
        }),
      });
      setDone(true);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Личный пароль" close={close} busy={busy}>
      <div className="modal-body stack">
        {error && <Notice>{error}</Notice>}
        {done ? (
          <p role="status">Пароль изменён. Другие сессии будут завершены.</p>
        ) : (
          <form className="stack" onSubmit={save}>
            <label>
              Текущий пароль
              <input
                type="password"
                name="current_password"
                required
                autoComplete="current-password"
              />
            </label>
            <label>
              Новый пароль
              <input
                type="password"
                name="new_password"
                required
                minLength={12}
                maxLength={128}
                autoComplete="new-password"
              />
            </label>
            <label>
              Повторите новый пароль
              <input
                type="password"
                name="confirmation"
                required
                minLength={12}
                autoComplete="new-password"
              />
            </label>
            <button className="primary" disabled={busy}>
              Сменить пароль
            </button>
          </form>
        )}
      </div>
    </Modal>
  );
}
