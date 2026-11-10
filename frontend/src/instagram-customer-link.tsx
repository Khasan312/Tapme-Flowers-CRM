import { useState } from "react";
import { businessPath, errorText, request } from "./api";
import { Notice } from "./components";
import { useDebouncedValue, useRemote } from "./hooks";
import type { Customer, Page } from "./types";

export function InstagramCustomerLink({
  businessId,
  busy,
  link,
}: {
  businessId: string;
  busy: boolean;
  link: (id: string) => Promise<unknown>;
}) {
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const settled = useDebouncedValue(search);
  const customers = useRemote<Page<Customer>>(
    settled.trim()
      ? businessPath(businessId, "customers") +
          `?search=${encodeURIComponent(settled)}&limit=5`
      : null,
  );
  return (
    <div className="chat-profile-card stack">
      <h3>Связать с клиентом</h3>
      <p className="muted">
        Instagram не передаёт номер телефона. Выберите клиента или уточните его
        номер, чтобы открыть карточку, заказы и черновик.
      </p>
      <label>
        Найти клиента
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Имя или телефон"
        />
      </label>
      {customers.data?.results.map((customer) => (
        <button
          key={customer.id}
          className="btn"
          disabled={busy || saving}
          onClick={() => void link(customer.id)}
        >
          {customer.name} · {customer.phone}
        </button>
      ))}
      {(error || customers.error) && (
        <Notice>{error || customers.error}</Notice>
      )}
      <form
        className="stack"
        onSubmit={async (e) => {
          e.preventDefault();
          const form = new FormData(e.currentTarget);
          setSaving(true);
          setError("");
          try {
            const customer = await request<Customer>(
              businessPath(businessId, "customers"),
              {
                method: "POST",
                body: JSON.stringify({
                  name: form.get("name"),
                  phone: form.get("phone"),
                  source: "Instagram",
                  consent: false,
                }),
              },
            );
            await link(customer.id);
          } catch (e) {
            setError(errorText(e));
          } finally {
            setSaving(false);
          }
        }}
      >
        <label>
          Имя нового клиента
          <input name="name" required maxLength={150} />
        </label>
        <label>
          Телефон клиента
          <input name="phone" type="tel" required placeholder="+996…" />
        </label>
        <button className="btn primary" disabled={busy || saving}>
          Создать карточку и связать
        </button>
      </form>
    </div>
  );
}
