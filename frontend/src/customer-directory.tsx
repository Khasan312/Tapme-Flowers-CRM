import { useEffect, useState } from "react";
import { Search, Download } from "lucide-react";
import { businessPath, price } from "./api";
import { Notice, Pager, RefreshIndicator } from "./components";
import { useRemote } from "./hooks";
import { Avatar } from "./ui";
import type { Business } from "./types";
type Entry = {
  id: string;
  code: number;
  name: string;
  phone: string;
  additional_phones?: string[];
  source: string;
  tags: string[];
  recipients: { name: string; relation: string }[];
  next_date: { label: string; days: number } | null;
  order_count: number;
  total: string;
  last_order: string | null;
  days_since: number | null;
};
export function CustomerDirectory({
  business,
  revision,
  openCustomer,
  add,
  importClients,
}: {
  business: Business;
  revision: number;
  openCustomer: (id: string) => void;
  add: () => void;
  importClients: () => void;
}) {
  const [query, setQuery] = useState(""),
    [search, setSearch] = useState(""),
    [group, setGroup] = useState("all"),
    [offset, setOffset] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(query);
      setOffset(0);
    }, 200);
    return () => clearTimeout(t);
  }, [query]);
  const source = useRemote<{
    count: number;
    total_count: number;
    consent_count: number;
    results: Entry[];
  }>(
    businessPath(business.id, "customers/directory") +
      "?" +
      new URLSearchParams({
        search,
        group,
        limit: "50",
        offset: String(offset),
      }),
    revision,
  );
  return (
    <>
      <div className="page-hd">
        <div>
          <h1>Клиенты</h1>
          <div className="sub">
            {source.data?.total_count ?? "—"} клиентов ·{" "}
            {source.data?.consent_count ?? "—"} с согласием на сообщения
          </div>
        </div>
        <span className="spacer" />
        <RefreshIndicator active={source.refreshing} />
        <button className="btn" onClick={importClients}>
          <Download size={14} />
          Импорт
        </button>
        <button className="btn primary" onClick={add}>
          Новый клиент
        </button>
      </div>
      <div className="row directory-filters">
        <label className="search">
          <Search size={14} />
          <input
            aria-label="Поиск клиентов"
            placeholder="Имя, телефон, ID, получатель"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <div className="pills">
          {Object.entries({
            all: "Все",
            vip: "VIP",
            corp: "Корпоративные",
            vip_corp: "VIP и корпоративные",
            new: "Новые",
            lapsed: "Давно не заказывали",
          }).map(([key, label]) => (
            <button
              className={`pill${key === group ? " is-on" : ""}`}
              key={key}
              aria-pressed={key === group}
              onClick={() => {
                setGroup(key);
                setOffset(0);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {group === "lapsed" && (
        <p className="small muted">
          Прошло 90 дней или больше от даты получения в последнем заказе.
          Отменённые заказы не учитываются; клиенты без заказов сюда не входят.
        </p>
      )}
      {source.error && <Notice>{source.error}</Notice>}
      <div className="card">
        <div className="tbl-wrap">
          <table className="tbl clients-table">
            <thead>
              <tr>
                {[
                  "ID",
                  "Клиент",
                  "Телефон",
                  "Получатели",
                  "Ближайшая дата",
                  "Заказов",
                  "Сумма, сом",
                  "Последний заказ",
                ].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {source.data?.results.map((c) => (
                <tr key={c.id} onClick={() => openCustomer(c.id)}>
                  <td className="mono muted">{c.code}</td>
                  <td>
                    <button
                      className="plain-button row nowrap"
                      onClick={(e) => {
                        e.stopPropagation();
                        openCustomer(c.id);
                      }}
                    >
                      <Avatar name={c.name} />
                      <span>
                        <span className="b ink">{c.name}</span>
                        <span className="small muted block">
                          {c.tags.map((t) => (
                            <span
                              className={`tag ${t === "VIP" ? "acc" : "info"}`}
                              key={t}
                            >
                              {t}
                            </span>
                          ))}{" "}
                          {c.source}
                        </span>
                      </span>
                    </button>
                  </td>
                  <td className="mono">
                    {[c.phone, ...(c.additional_phones || [])].map((phone) => (
                      <div key={phone}>{phone}</div>
                    ))}
                  </td>
                  <td>
                    {c.recipients.map((r, i) => (
                      <span key={i} className="chip">
                        {r.name}
                        {r.relation && ` · ${r.relation}`}
                      </span>
                    ))}
                    {!c.recipients.length && "—"}
                  </td>
                  <td>
                    {c.next_date ? (
                      <span
                        className={`tag${c.next_date.days <= 14 ? " warn" : ""}`}
                      >
                        {c.next_date.label} ·{" "}
                        {c.next_date.days
                          ? `через ${c.next_date.days} дн.`
                          : "сегодня"}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="num mono">{c.order_count}</td>
                  <td className="num mono">
                    {price(c.total).replace(" сом", "")}
                  </td>
                  <td>
                    {c.days_since === null ? (
                      "—"
                    ) : (
                      <span className={c.days_since >= 90 ? "tag crit" : ""}>
                        {c.days_since === 0
                          ? "сегодня"
                          : c.days_since > 0
                            ? `${c.days_since} дн. назад`
                            : c.last_order}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {!source.data?.count && (
                <tr>
                  <td colSpan={8} className="empty">
                    {source.loading
                      ? "Загружаем клиентов…"
                      : "Никого не нашли. Проверьте телефон или добавьте клиента."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <Pager
          count={source.data?.count || 0}
          offset={offset}
          setOffset={setOffset}
        />
      </div>
    </>
  );
}
