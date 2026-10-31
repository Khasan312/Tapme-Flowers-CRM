import { useEffect, useState, type FormEvent } from "react";
import { MapPin, Plus } from "lucide-react";
import { businessPath, errorText, request } from "./api";
import { useRemote } from "./hooks";
import { Notice, SettingsConflict } from "./components";
import { PhoneInput } from "./phone-input";
import type { Business, Point, ShopSettings, Staff } from "./types";
import "./points.css";

type PointDetail = Point & ShopSettings;
const blank = (business: Business): PointDetail => ({
  id: "",
  name: "",
  short_name: "",
  address: "",
  city: "",
  phone: "",
  whatsapp: "",
  opening_hours: "09:00–21:00",
  timezone: business.timezone,
  active: true,
  is_primary: false,
  version: 1,
  sort: 0,
  windows: [{ start: "10:00", end: "12:00", price: "0.00", capacity: 6 }],
  pickup_unlimited: true,
  enforce_capacity: false,
});

export function PointsSettings({
  business,
  changed,
}: {
  business: Business;
  changed: () => void;
}) {
  const [revision, setRevision] = useState(0);
  const points = useRemote<Point[]>(
    businessPath(business.id, "points"),
    revision,
  );
  const [selected, setSelected] = useState<string>(
    business.point_id && business.point_id !== "all" ? business.point_id : "",
  );
  const source = useRemote<PointDetail>(
    selected && selected !== "new"
      ? businessPath(business.id, `points/${selected}`)
      : null,
    revision,
    { refreshOnAppear: false },
  );
  const [draft, setDraft] = useState<PointDetail | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [conflict, setConflict] = useState(false);
  useEffect(() => {
    if (!selected && points.data?.length)
      setSelected((points.data.find((p) => p.is_primary) || points.data[0]).id);
  }, [selected, points.data]);
  useEffect(() => {
    setDraft(selected === "new" ? blank(business) : source.data);
    setError("");
    setConflict(false);
  }, [selected, source.data]);
  const owner = business.role === "owner";
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!draft) return;
    setBusy(true);
    setError("");
    setNotice("");
    const {
      name,
      short_name,
      address,
      city,
      phone,
      whatsapp,
      opening_hours,
      windows,
      pickup_unlimited,
      enforce_capacity,
      version,
      is_primary,
      sort,
    } = draft;
    try {
      const result = await request<PointDetail>(
        businessPath(
          business.id,
          selected === "new" ? "points" : `points/${selected}`,
        ),
        {
          method: selected === "new" ? "POST" : "PATCH",
          body: JSON.stringify({
            name,
            short_name,
            address,
            city,
            phone,
            whatsapp,
            opening_hours,
            windows,
            pickup_unlimited,
            enforce_capacity,
            version,
            is_primary,
            sort,
          }),
        },
      );
      setSelected(result.id);
      setDraft(result);
      setRevision((r) => r + 1);
      changed();
      setConflict(false);
      setNotice("Точка сохранена");
    } catch (e) {
      setError(errorText(e));
      setConflict((e as { status?: number }).status === 409);
    } finally {
      setBusy(false);
    }
  }
  async function archive() {
    if (
      !draft ||
      !window.confirm(
        `Архивировать точку «${draft.short_name}»? История заказов сохранится.`,
      )
    )
      return;
    setBusy(true);
    setError("");
    try {
      await request(businessPath(business.id, `points/${draft.id}/archive`), {
        method: "POST",
        body: JSON.stringify({ version: draft.version }),
      });
      setRevision((r) => r + 1);
      changed();
      setNotice("Точка архивирована");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="points-section">
      <div className="card-hd">
        <div>
          <h2>Точки магазина</h2>
          <p className="muted">
            Общие клиенты и прайс. Свои заказы, команда, доставка и очередь
            напоминаний у каждого филиала. Переключайте точку в боковом меню.
          </p>
        </div>
        {owner && (
          <button
            className="btn primary"
            disabled={busy}
            onClick={() => {
              setSelected("new");
              setDraft(blank(business));
              setNotice("");
            }}
          >
            <Plus size={16} /> Добавить точку
          </button>
        )}
      </div>
      {(points.error || source.error || error) && (
        <Notice>{error || source.error || points.error}</Notice>
      )}
      {notice && (
        <p className="save-notice" role="status">
          {notice}
        </p>
      )}
      <div className="points-layout">
        <nav className="point-list" aria-label="Филиалы">
          {points.data?.map((p) => (
            <button
              key={p.id}
              className={
                selected === p.id ? "point-choice selected" : "point-choice"
              }
              onClick={() => setSelected(p.id)}
              disabled={busy}
            >
              <MapPin size={18} />
              <span>
                <strong>{p.short_name}</strong>
                <small>{p.address || "Адрес не указан"}</small>
                <small>
                  {p.is_primary
                    ? "Основная точка"
                    : !p.active
                      ? "В архиве"
                      : p.name}
                </small>
              </span>
            </button>
          ))}
        </nav>
        {draft && (
          <form className="card point-editor" onSubmit={save}>
            <div className="card-hd">
              <h3>{selected === "new" ? "Новая точка" : draft.short_name}</h3>
              {!draft.active && <span className="muted">Архив</span>}
            </div>
            {conflict && (
              <SettingsConflict
                busy={busy}
                reload={() => setRevision((r) => r + 1)}
              />
            )}
            <fieldset
              disabled={!owner || busy || !draft.active}
              className="stack"
            >
              <div className="point-fields">
                <label>
                  Название точки
                  <input
                    required
                    maxLength={150}
                    value={draft.name}
                    onChange={(e) =>
                      setDraft({ ...draft, name: e.target.value })
                    }
                  />
                </label>
                <label>
                  Короткое название
                  <input
                    required
                    maxLength={40}
                    placeholder="Например, Чуй"
                    value={draft.short_name}
                    onChange={(e) =>
                      setDraft({ ...draft, short_name: e.target.value })
                    }
                  />
                </label>
              </div>
              <label>
                Адрес точки
                <input
                  maxLength={500}
                  value={draft.address}
                  onChange={(e) =>
                    setDraft({ ...draft, address: e.target.value })
                  }
                />
              </label>
              <div className="point-fields">
                <label>
                  Город
                  <input
                    value={draft.city}
                    maxLength={100}
                    onChange={(e) =>
                      setDraft({ ...draft, city: e.target.value })
                    }
                  />
                </label>
                <label>
                  Часы работы
                  <input
                    value={draft.opening_hours}
                    maxLength={150}
                    onChange={(e) =>
                      setDraft({ ...draft, opening_hours: e.target.value })
                    }
                  />
                </label>
                <label>
                  Телефон точки
                  <PhoneInput
                    value={draft.phone}
                    onChange={(v) => setDraft({ ...draft, phone: v })}
                  />
                </label>
                <label>
                  WhatsApp точки
                  <PhoneInput
                    value={draft.whatsapp}
                    onChange={(v) => setDraft({ ...draft, whatsapp: v })}
                  />
                </label>
              </div>
              <label className="point-check">
                <input
                  type="checkbox"
                  checked={draft.is_primary}
                  disabled={source.data?.is_primary}
                  onChange={(e) =>
                    setDraft({ ...draft, is_primary: e.target.checked })
                  }
                />
                Основная точка
              </label>
              <h3>Окна доставки</h3>
              <p className="muted">
                Лимит и стоимость действуют только для этой точки.
              </p>
              {draft.windows.map((w, i) => (
                <div className="point-window" key={i}>
                  <label>
                    С
                    <input
                      aria-label={`Начало окна точки ${i + 1}`}
                      type="time"
                      required
                      value={w.start}
                      onChange={(e) =>
                        setDraft({
                          ...draft,
                          windows: draft.windows.map((v, j) =>
                            j === i ? { ...v, start: e.target.value } : v,
                          ),
                        })
                      }
                    />
                  </label>
                  <label>
                    До
                    <input
                      aria-label={`Конец окна точки ${i + 1}`}
                      type="time"
                      required
                      value={w.end}
                      onChange={(e) =>
                        setDraft({
                          ...draft,
                          windows: draft.windows.map((v, j) =>
                            j === i ? { ...v, end: e.target.value } : v,
                          ),
                        })
                      }
                    />
                  </label>
                  <label>
                    Заказов
                    <input
                      type="number"
                      min={1}
                      max={999}
                      required
                      value={w.capacity}
                      onChange={(e) =>
                        setDraft({
                          ...draft,
                          windows: draft.windows.map((v, j) =>
                            j === i
                              ? { ...v, capacity: Number(e.target.value) }
                              : v,
                          ),
                        })
                      }
                    />
                  </label>
                  <label>
                    Цена, сом
                    <input
                      type="number"
                      min={0}
                      step="0.01"
                      required
                      value={w.price}
                      onChange={(e) =>
                        setDraft({
                          ...draft,
                          windows: draft.windows.map((v, j) =>
                            j === i ? { ...v, price: e.target.value } : v,
                          ),
                        })
                      }
                    />
                  </label>
                  <button
                    type="button"
                    aria-label={`Удалить окно точки ${i + 1}`}
                    disabled={draft.windows.length === 1}
                    onClick={() =>
                      setDraft({
                        ...draft,
                        windows: draft.windows.filter((_, j) => j !== i),
                      })
                    }
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                type="button"
                disabled={draft.windows.length >= 24}
                onClick={() =>
                  setDraft({
                    ...draft,
                    windows: [
                      ...draft.windows,
                      {
                        start: "12:00",
                        end: "14:00",
                        capacity: 6,
                        price: "0.00",
                      },
                    ],
                  })
                }
              >
                Добавить окно
              </button>
              <label className="point-check">
                <input
                  type="checkbox"
                  checked={draft.pickup_unlimited}
                  onChange={(e) =>
                    setDraft({ ...draft, pickup_unlimited: e.target.checked })
                  }
                />
                Самовывоз не занимает место в окне
              </label>
              <label className="point-check">
                <input
                  type="checkbox"
                  checked={draft.enforce_capacity}
                  onChange={(e) =>
                    setDraft({ ...draft, enforce_capacity: e.target.checked })
                  }
                />
                Не принимать заказы в заполненное окно
              </label>
              <div className="point-actions">
                {selected !== "new" && !draft.is_primary && (
                  <button
                    type="button"
                    className="danger"
                    onClick={() => void archive()}
                  >
                    Архивировать точку
                  </button>
                )}
                <button className="primary" disabled={conflict}>
                  {busy ? "Сохраняем…" : "Сохранить точку"}
                </button>
              </div>
            </fieldset>
          </form>
        )}
      </div>
    </section>
  );
}

export function StaffPointEditor({
  business,
  staff,
}: {
  business: Business;
  staff: Staff;
}) {
  const points = useRemote<Point[]>(businessPath(business.id, "points"));
  const [ids, setIds] = useState(staff.point_ids || []);
  useEffect(() => {
    if (points.data)
      setIds((current) =>
        current.filter((id) =>
          points.data!.some((p) => p.id === id && p.active),
        ),
      );
  }, [points.data]);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [saved, setSaved] = useState(false);
  async function save() {
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      await request(businessPath(business.id, `staff/${staff.id}/points`), {
        method: "PUT",
        body: JSON.stringify({ point_ids: ids }),
      });
      setSaved(true);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  if (!points.data || points.data.length < 2) return null;
  return (
    <div className="staff-points">
      <h3>Доступ к точкам</h3>
      <p className="muted">
        {staff.role === "manager"
          ? "Если ничего не отмечено, менеджер видит все точки."
          : "Выберите точки, в которых работает сотрудник."}
      </p>
      {points.data
        .filter((p) => p.active)
        .map((p) => (
          <label className="point-check" key={p.id}>
            <input
              type="checkbox"
              checked={ids.includes(p.id)}
              disabled={busy}
              onChange={(e) => {
                setSaved(false);
                setIds(
                  e.target.checked
                    ? [...ids, p.id]
                    : ids.filter((id) => id !== p.id),
                );
              }}
            />
            {p.short_name}
          </label>
        ))}
      {error && <Notice>{error}</Notice>}
      <button type="button" disabled={busy} onClick={() => void save()}>
        {busy ? "Сохраняем…" : "Сохранить доступ к точкам"}
      </button>
      {saved && <p role="status">Доступ к точкам сохранён</p>}
    </div>
  );
}
