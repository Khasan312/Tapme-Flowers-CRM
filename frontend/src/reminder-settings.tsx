import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  CalendarDays,
  Check,
  Gift,
  Heart,
  Info,
  MessageCircle,
  Moon,
  Plus,
  Repeat2,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Trash2,
  TriangleAlert,
  X,
} from "lucide-react";
import { ApiError, businessPath, errorText, request } from "./api";
import { Modal, Notice, SettingsConflict } from "./components";
import { PhoneInput } from "./phone-input";
import { useRemote } from "./hooks";
import { Avatar, Toggle, shopDay, shortDate } from "./ui";
import { newUuid } from "./uuid";
import type {
  Business,
  ReminderConfiguration,
  ReminderPage,
  ReminderScenario,
  ReminderStep,
} from "./types";
import "./reminders.css";

const kindNames: Record<ReminderScenario["kind"], string> = {
  before_event: "Перед важной датой",
  after_last_order: "Давно не заказывали",
  after_delivery: "После доставки",
  holiday: "Праздник",
};
const variables = [
  ["имя", "Имя"],
  ["получатель", "Получатель"],
  ["повод", "Повод"],
  ["дата", "Дата"],
  ["прошлый_букет", "Прошлый букет"],
  ["магазин", "Магазин"],
];
const aliases: Record<string, string> = {
  name: "имя",
  person: "получатель",
  event: "повод",
  date: "дата",
  last_bouquet: "прошлый_букет",
  shop: "магазин",
  number: "номер",
  items: "состав",
  window: "окно",
  address: "адрес",
  total: "сумма",
  link: "ссылка",
  order_link: "ссылка_на_заказ",
};
function ScenarioIcon({ scenario }: { scenario: ReminderScenario }) {
  const Icon =
    scenario.kind === "holiday"
      ? Sparkles
      : scenario.kind === "after_delivery"
        ? ShoppingBag
        : scenario.kind === "after_last_order"
          ? Repeat2
          : scenario.name.includes("рождения")
            ? Gift
            : scenario.name.includes("Годовщина")
              ? Heart
              : CalendarDays;
  return <Icon size={18} />;
}
function stepLabel(s: ReminderScenario, step: ReminderStep) {
  return `${s.kind.startsWith("after_") ? "Через" : "За"} ${step.offset_days} дн.`;
}
function scenarioLabel(s: ReminderScenario) {
  return `${s.kind.startsWith("after_") ? "через" : "за"} ${
    s.steps
      .filter((p) => p.enabled)
      .map((p) => p.offset_days)
      .join(" · ") || "—"
  } дн.${s.kind === "after_last_order" ? " после заказа" : ""}`;
}
function makeScenario(
  name: string,
  kind: ReminderScenario["kind"],
): ReminderScenario {
  return {
    id: newUuid(),
    name,
    kind,
    enabled: true,
    event_labels: kind === "before_event" ? [name] : [],
    holiday_month: 3,
    holiday_day: 8,
    audience: "consented_all",
    daily_cap: 40,
    steps: [
      {
        id: newUuid(),
        offset_days:
          kind === "after_last_order" ? 90 : kind === "after_delivery" ? 1 : 3,
        enabled: true,
        template:
          kind === "after_delivery"
            ? "{имя}, как вам букет? Будем рады отзыву! {магазин}"
            : "{имя}, здравствуйте! {магазин}. Подобрать для вас букет?",
      },
    ],
  };
}
export function ReminderSettings({
  business,
  back,
  settings,
  templates,
}: {
  business: Business;
  back: () => void;
  settings: () => void;
  templates: () => void;
}) {
  const [revision, setRevision] = useState(0);
  const source = useRemote<ReminderConfiguration>(
    businessPath(business.id, "reminder-scenarios"),
    revision,
    { refreshOnAppear: false },
  );
  const [draft, setDraft] = useState<ReminderConfiguration | null>(null),
    [selected, setSelected] = useState("");
  const [stepId, setStepId] = useState("");
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [conflict, setConflict] = useState(false);
  const [adding, setAdding] = useState(false),
    [newName, setNewName] = useState(""),
    [newKind, setNewKind] = useState<ReminderScenario["kind"]>("before_event");
  const [removing, setRemoving] = useState(false),
    [testing, setTesting] = useState(false),
    [testPhone, setTestPhone] = useState("+996");
  const [example, setExample] = useState("");
  const textarea = useRef<HTMLTextAreaElement>(null),
    editor = useRef<HTMLElement>(null);
  const owner = business.role === "owner";
  useEffect(() => {
    if (source.data) {
      setDraft(source.data);
      setSelected((id) =>
        source.data!.scenarios.some((s) => s.id === id)
          ? id
          : source.data!.scenarios[0]?.id || "",
      );
    }
  }, [source.data]);
  const selectedScenario = draft?.scenarios.find((s) => s.id === selected);
  const step =
    selectedScenario?.steps.find((p) => p.id === stepId) ||
    selectedScenario?.steps[0];
  const previewSource = useRemote<ReminderPage>(
    selected
      ? businessPath(business.id, "reminders") +
          `?scenario=${selected}&limit=20`
      : null,
    revision,
    { refreshOnAppear: false },
  );
  useEffect(() => {
    setExample("");
  }, [selected]);
  function updateScenario(changes: Partial<ReminderScenario>) {
    if (draft && selectedScenario) {
      setDraft({
        ...draft,
        scenarios: draft.scenarios.map((s) =>
          s.id === selected ? { ...s, ...changes } : s,
        ),
      });
      setNotice("");
    }
  }
  function updateStep(changes: Partial<ReminderStep>) {
    if (selectedScenario && step)
      updateScenario({
        steps: selectedScenario.steps.map((p) =>
          p.id === step.id ? { ...p, ...changes } : p,
        ),
      });
  }
  function choose(id: string) {
    setSelected(id);
    setStepId("");
    if (window.innerWidth < 900)
      window.setTimeout(
        () =>
          editor.current?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          }),
        0,
      );
  }
  async function save() {
    if (!draft) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const saved = await request<ReminderConfiguration>(
        businessPath(business.id, "reminder-scenarios"),
        { method: "PUT", body: JSON.stringify(draft) },
      );
      setDraft(saved);
      setConflict(false);
      setNotice("Настройки напоминаний сохранены");
    } catch (e) {
      setError(errorText(e));
      setConflict(e instanceof ApiError && e.status === 409);
    } finally {
      setBusy(false);
    }
  }
  function insert(variable: string) {
    if (!step || !textarea.current) return;
    const field = textarea.current,
      start = field.selectionStart,
      end = field.selectionEnd;
    const token = `{${variable}}`;
    updateStep({
      template:
        step.template.slice(0, start) + token + step.template.slice(end),
    });
    requestAnimationFrame(() => {
      field.focus();
      field.setSelectionRange(start + token.length, start + token.length);
    });
  }
  const selectedExample = previewSource.data?.results.find(
    (r) => r.id === example,
  );
  const sampleDate =
    selectedExample?.event_date ||
    shopDay(business.timezone, step?.offset_days || 1);
  const values: Record<string, string> = {
    имя: selectedExample?.customer_name || "Алина",
    получатель: selectedExample?.person || "Айжан",
    повод:
      selectedExample?.event ||
      selectedScenario?.event_labels[0] ||
      selectedScenario?.name ||
      "событие",
    дата: shortDate(sampleDate),
    прошлый_букет: selectedExample
      ? selectedExample.last_year_hint?.items || ""
      : "букет «Нежность»",
    магазин: business.name,
    номер: "",
    состав: "",
    окно: "",
    адрес: "",
    сумма: "",
    ссылка: "",
    ссылка_на_заказ: "",
  };
  const preview = (step?.template || "").replace(
    /\{\{|\}\}|\{([^{}]+)\}/g,
    (match, key: string) =>
      match === "{{"
        ? "{"
        : match === "}}"
          ? "}"
          : (values[aliases[key] || key] ?? match),
  );
  const text = step?.template || "";
  const checks: [boolean, string][] = [
    [/\{(имя|name)\}/.test(text), "Обращение по имени"],
    [
      /\{(повод|event|дата|date)\}/.test(text) ||
        selectedScenario?.kind.startsWith("after_") ||
        false,
      "Повод и дата",
    ],
    [/\?\s*$/.test(text), "Вопрос в конце"],
    [
      !/(https?:\/\/|www\.|[А-ЯA-ZЁ]{4,})/.test(
        text.replaceAll(business.name, ""),
      ),
      "Без ссылок и КАПСА",
    ],
    [
      text.length <= 250,
      `${text.length} символов${text.length > 500 ? " — сократите до 500" : text.length > 250 ? " — короче читают чаще" : ""}`,
    ],
  ];
  return (
    <section className="rm-settings stack">
      <div className="row">
        <button className="plain-button rm-back" onClick={settings}>
          <ArrowLeft size={16} />К настройкам
        </button>
        <button className="plain-button rm-back" onClick={back}>
          К напоминаниям
        </button>
      </div>
      <div className="page-hd">
        <div>
          <h1>Настройки напоминаний</h1>
          <p className="sub">Когда написать клиенту и что предложить</p>
        </div>
        <button className="btn sm" onClick={templates}>
          Другие шаблоны
        </button>
      </div>
      {(error || source.error) && <Notice>{error || source.error}</Notice>}
      {conflict && (
        <SettingsConflict
          busy={busy}
          reload={() => {
            setRevision((v) => v + 1);
            setConflict(false);
            setError("");
          }}
        />
      )}
      {notice && (
        <p className="save-notice" role="status">
          {notice}
        </p>
      )}
      {!owner && (
        <div className="rm-banner">
          <Info size={18} />
          Менеджер может просматривать сценарии. Изменять их может владелец.
        </div>
      )}
      {!draft ? (
        <div className="card rm-empty">
          {source.loading ? (
            "Загружаем сценарии…"
          ) : (
            <button onClick={() => setRevision((v) => v + 1)}>
              Попробовать снова
            </button>
          )}
        </div>
      ) : (
        <div className="rm-settings-grid">
          <aside className="card rm-scenarios" aria-label="Список сценариев">
            <div className="rm-scenario-heading">
              <div className="row">
                <h2>Сценарии</h2>
                {owner && (
                  <button
                    className="btn sm"
                    disabled={busy || draft.scenarios.length >= 30}
                    onClick={() => {
                      setNewName("");
                      setAdding(true);
                    }}
                  >
                    <Plus size={15} />
                    Новый
                  </button>
                )}
              </div>
              <p className="muted">Сценарий = когда написать + что написать</p>
            </div>
            {[
              { title: "Перед важной датой", kinds: ["before_event"] },
              {
                title: "После покупки",
                kinds: ["after_last_order", "after_delivery"],
              },
              { title: "Праздники", kinds: ["holiday"] },
            ].map((group) => (
              <div key={group.title}>
                <h3 className="rm-group-title">{group.title}</h3>
                {draft.scenarios
                  .filter((s) => group.kinds.includes(s.kind))
                  .map((s) => (
                    <div
                      key={s.id}
                      className={`rm-scenario${selected === s.id ? " selected" : ""}`}
                    >
                      <button
                        className="rm-scenario-select"
                        onClick={() => choose(s.id)}
                        aria-pressed={selected === s.id}
                      >
                        <span className="rm-scenario-icon">
                          <ScenarioIcon scenario={s} />
                        </span>
                        <span>
                          <strong>{s.name}</strong>
                          <small>{scenarioLabel(s)}</small>
                        </span>
                      </button>
                      <Toggle
                        checked={s.enabled}
                        disabled={!owner || busy}
                        onChange={(enabled) => {
                          setDraft({
                            ...draft,
                            scenarios: draft.scenarios.map((v) =>
                              v.id === s.id ? { ...v, enabled } : v,
                            ),
                          });
                          setNotice("");
                        }}
                      >
                        <span className="sr-only">Сценарий {s.name}</span>
                      </Toggle>
                    </div>
                  ))}
              </div>
            ))}
            <fieldset
              className="rm-global-rules"
              aria-label="Общие правила"
              disabled={!owner || busy}
            >
              <h3 className="rm-caption">Общие правила</h3>
              <Toggle
                checked={draft.enabled}
                onChange={(enabled) => setDraft({ ...draft, enabled })}
              >
                Напоминания включены
              </Toggle>
              <label className="rm-hours">
                <span>
                  <Moon size={16} />
                  Писать только
                </span>
                <span>
                  <select
                    aria-label="Сообщения с часа"
                    value={draft.start_hour}
                    onChange={(e) =>
                      setDraft({ ...draft, start_hour: Number(e.target.value) })
                    }
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={i}>
                        {String(i).padStart(2, "0")}:00
                      </option>
                    ))}
                  </select>
                  <span>–</span>
                  <select
                    aria-label="Сообщения до часа"
                    value={draft.end_hour}
                    onChange={(e) =>
                      setDraft({ ...draft, end_hour: Number(e.target.value) })
                    }
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i + 1} value={i + 1}>
                        {String(i + 1).padStart(2, "0")}:00
                      </option>
                    ))}
                  </select>
                </span>
              </label>
              <p>
                <ShieldCheck size={16} />
                Только с согласием клиента
                <Check size={15} />
              </p>
              <p>
                <ShieldCheck size={16} />
                Пауза при открытой жалобе
                <Check size={15} />
              </p>
              <label className="rm-frequency">
                <span>
                  <Repeat2 size={16} />
                  Не чаще одного в
                </span>
                <input
                  aria-label="Минимум дней между сообщениями"
                  type="number"
                  min={0}
                  max={365}
                  value={draft.min_days_between}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      min_days_between: Number(e.target.value),
                    })
                  }
                />
                <span>дн.</span>
              </label>
              <small className="muted">
                0 — без дополнительного интервала. Часы указаны для{" "}
                {business.timezone}.
              </small>
            </fieldset>
          </aside>
          <section
            className="card rm-editor"
            ref={editor}
            aria-label="Редактор сценария"
          >
            {selectedScenario && step && (
              <>
                <div className="rm-editor-heading">
                  <span className="rm-scenario-icon">
                    <ScenarioIcon scenario={selectedScenario} />
                  </span>
                  <div>
                    <h2>{selectedScenario.name}</h2>
                    <p className="muted">
                      {selectedScenario.enabled ? "Включён" : "Выключен"} ·{" "}
                      {selectedScenario.steps.filter((p) => p.enabled).length}{" "}
                      шага
                    </p>
                  </div>
                  <div className="rm-editor-buttons">
                    {!owner && (
                      <select
                        aria-label="Шаг для просмотра"
                        value={step.id}
                        onChange={(e) => setStepId(e.target.value)}
                      >
                        {selectedScenario.steps.map((p) => (
                          <option key={p.id} value={p.id}>
                            {stepLabel(selectedScenario, p)}
                          </option>
                        ))}
                      </select>
                    )}
                    <button className="btn sm" onClick={() => setTesting(true)}>
                      Отправить себе тест
                    </button>
                    <button
                      className="btn sm primary"
                      disabled={!owner || busy}
                      onClick={() => void save()}
                    >
                      {busy ? "Сохраняем…" : "Сохранить"}
                    </button>
                  </div>
                </div>
                <fieldset
                  disabled={!owner || busy}
                  className="rm-editor-body stack"
                >
                  <label>
                    Название сценария
                    <input
                      value={selectedScenario.name}
                      maxLength={100}
                      onChange={(e) => updateScenario({ name: e.target.value })}
                    />
                  </label>
                  <div>
                    <h3 className="rm-caption">Когда</h3>
                    <div className="rm-offsets">
                      <span>
                        {selectedScenario.kind.startsWith("after_")
                          ? "Написать через"
                          : "Напомнить за"}
                      </span>
                      {selectedScenario.steps.map((p) => (
                        <div
                          className={`rm-offset${p.id === step.id ? " selected" : ""}`}
                          key={p.id}
                        >
                          <input
                            aria-label={`Интервал шага ${selectedScenario.steps.indexOf(p) + 1}`}
                            type="number"
                            min={
                              selectedScenario.kind === "after_last_order"
                                ? 30
                                : 0
                            }
                            max={
                              selectedScenario.kind === "after_last_order"
                                ? 730
                                : 60
                            }
                            value={p.offset_days}
                            onFocus={() => setStepId(p.id)}
                            onChange={(e) =>
                              updateScenario({
                                steps: selectedScenario.steps.map((v) =>
                                  v.id === p.id
                                    ? {
                                        ...v,
                                        offset_days: Number(e.target.value),
                                      }
                                    : v,
                                ),
                              })
                            }
                          />
                          <button
                            aria-label={`Удалить шаг ${p.offset_days} дней`}
                            disabled={selectedScenario.steps.length === 1}
                            onClick={() => {
                              updateScenario({
                                steps: selectedScenario.steps.filter(
                                  (v) => v.id !== p.id,
                                ),
                              });
                              if (stepId === p.id) setStepId("");
                            }}
                          >
                            <X size={11} />
                          </button>
                        </div>
                      ))}
                      <button
                        className="rm-add-step"
                        aria-label="Добавить шаг"
                        disabled={selectedScenario.steps.length >= 15}
                        onClick={() => {
                          const n = Array.from({ length: 61 }, (_, i) =>
                            selectedScenario.kind === "after_last_order"
                              ? i + 30
                              : i,
                          ).find(
                            (v) =>
                              !selectedScenario.steps.some(
                                (p) => p.offset_days === v,
                              ),
                          )!;
                          const added = {
                            id: newUuid(),
                            offset_days: n,
                            enabled: true,
                            template: step.template,
                          };
                          updateScenario({
                            steps: [...selectedScenario.steps, added],
                          });
                          setStepId(added.id);
                        }}
                      >
                        <Plus size={17} />
                      </button>
                      <span>
                        дн.{" "}
                        {selectedScenario.kind === "after_delivery"
                          ? "после вручения"
                          : selectedScenario.kind === "after_last_order"
                            ? "после последнего заказа"
                            : "до события"}
                      </span>
                    </div>
                  </div>
                  {selectedScenario.kind === "before_event" && (
                    <label>
                      Поводы (через запятую)
                      <input
                        value={selectedScenario.event_labels.join(", ")}
                        onChange={(e) =>
                          updateScenario({
                            event_labels: e.target.value
                              .split(",")
                              .map((v) => v.trimStart()),
                          })
                        }
                        onBlur={() =>
                          updateScenario({
                            event_labels: selectedScenario.event_labels
                              .map((v) => v.trim())
                              .filter(Boolean),
                          })
                        }
                        placeholder="Пусто — все остальные важные даты"
                      />
                      <small className="muted">
                        Названия должны совпадать с поводами в карточке клиента.
                        Пустое поле — остальные даты.
                      </small>
                    </label>
                  )}
                  {selectedScenario.kind === "holiday" && (
                    <>
                      <div className="form-grid">
                        <label>
                          День праздника
                          <input
                            type="number"
                            min={1}
                            max={31}
                            value={selectedScenario.holiday_day}
                            onChange={(e) =>
                              updateScenario({
                                holiday_day: Number(e.target.value),
                              })
                            }
                          />
                        </label>
                        <label>
                          Месяц
                          <select
                            aria-label="Месяц"
                            value={selectedScenario.holiday_month}
                            onChange={(e) =>
                              updateScenario({
                                holiday_month: Number(e.target.value),
                              })
                            }
                          >
                            {Array.from({ length: 12 }, (_, i) => (
                              <option key={i + 1} value={i + 1}>
                                {new Date(2024, i, 1).toLocaleDateString(
                                  "ru-RU",
                                  { month: "long" },
                                )}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                      <label>
                        Аудитория
                        <select
                          value={selectedScenario.audience}
                          onChange={(e) =>
                            updateScenario({
                              audience: e.target
                                .value as ReminderScenario["audience"],
                            })
                          }
                        >
                          <option value="consented_all">
                            Все клиенты с согласием
                          </option>
                          <option value="ordered_last_year">
                            Заказывали за последний год
                          </option>
                        </select>
                      </label>
                      <label>
                        Новых напоминаний в день
                        <input
                          type="number"
                          min={1}
                          max={500}
                          value={selectedScenario.daily_cap}
                          onChange={(e) =>
                            updateScenario({
                              daily_cap: Number(e.target.value),
                            })
                          }
                        />
                      </label>
                    </>
                  )}
                  <div>
                    <h3 className="rm-caption">Что написать</h3>
                    <div
                      className="rm-step-tabs"
                      role="tablist"
                      aria-label="Шаги сценария"
                    >
                      {selectedScenario.steps.map((p) => (
                        <button
                          key={p.id}
                          role="tab"
                          aria-selected={p.id === step.id}
                          className={p.id === step.id ? "active" : ""}
                          onClick={() => setStepId(p.id)}
                        >
                          {stepLabel(selectedScenario, p)}
                        </button>
                      ))}
                    </div>
                    <label className="rm-message-label">
                      <span className="sr-only">Текст шага</span>
                      <textarea
                        ref={textarea}
                        aria-label="Текст шага"
                        rows={6}
                        maxLength={2000}
                        value={text}
                        onChange={(e) =>
                          updateStep({ template: e.target.value })
                        }
                      />
                    </label>
                    <div className="rm-variables">
                      <span>Вставить:</span>
                      {variables.map(([key, label]) => (
                        <button key={key} onClick={() => insert(key)}>
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <Toggle
                    checked={step.enabled}
                    onChange={(enabled) => updateStep({ enabled })}
                  >
                    Этот шаг включён
                  </Toggle>
                  <div className="rm-text-check">
                    <h3 className="rm-caption">Проверка текста</h3>
                    <div>
                      {checks.map(([ok, label]) => (
                        <span key={label} className={ok ? "ok" : "warn"}>
                          {ok ? (
                            <Check size={15} />
                          ) : (
                            <TriangleAlert size={15} />
                          )}
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>
                  <p className="small muted">
                    Нажмите «Сохранить», чтобы применить сценарии и общие
                    правила. Изменения текстов не затронут уже обработанные
                    сообщения.
                  </p>
                  <button
                    className="plain-button rm-delete-scenario"
                    disabled={draft.scenarios.length === 1}
                    onClick={() => setRemoving(true)}
                  >
                    <Trash2 size={15} />
                    Удалить сценарий
                  </button>
                </fieldset>
              </>
            )}
          </section>
          <aside className="card rm-live-preview">
            <div className="row">
              <h2>Так увидит клиент</h2>
              <select
                aria-label="Пример клиента"
                value={example}
                onChange={(e) => setExample(e.target.value)}
              >
                <option value="">Пример</option>
                {previewSource.data?.results.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.customer_name}
                  </option>
                ))}
              </select>
            </div>
            <p className="muted">
              {selectedExample
                ? `${selectedExample.customer_name} · ${selectedExample.event}`
                : "Вымышленный пример · Алина"}
            </p>
            <div className="rm-phone">
              <header>
                <Avatar name={business.name} />
                <strong>{business.name}</strong>
              </header>
              <div className="rm-bubble">
                <p>{preview || "Здесь появится текст сообщения"}</p>
                <span>
                  10:05 <Check size={13} />
                  <Check size={13} />
                </span>
              </div>
            </div>
            <p className="muted rm-preview-note">
              <MessageCircle size={17} />
              Сообщение отправляет сотрудник из своего WhatsApp. CRM подготовит
              текст и откроет чат.
            </p>
          </aside>
        </div>
      )}
      {adding && (
        <Modal title="Новый сценарий" close={() => setAdding(false)}>
          <form
            className="modal-body stack"
            onSubmit={(e) => {
              e.preventDefault();
              if (!draft) return;
              const added = makeScenario(newName.trim(), newKind);
              setDraft({ ...draft, scenarios: [...draft.scenarios, added] });
              setSelected(added.id);
              setStepId("");
              setAdding(false);
            }}
          >
            <label>
              Название нового сценария
              <input
                required
                maxLength={100}
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </label>
            <label>
              Когда напоминать
              <select
                value={newKind}
                onChange={(e) =>
                  setNewKind(e.target.value as ReminderScenario["kind"])
                }
              >
                {Object.entries(kindNames).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <button className="btn primary">Добавить сценарий</button>
          </form>
        </Modal>
      )}
      {removing && selectedScenario && draft && (
        <Modal title="Удалить сценарий?" close={() => setRemoving(false)}>
          <div className="modal-body stack">
            <p>
              «{selectedScenario.name}» перестанет создавать напоминания.
              История сообщений сохранится. Изменение применится после
              сохранения настроек.
            </p>
            <button
              className="btn primary"
              onClick={() => {
                const scenarios = draft.scenarios.filter(
                  (s) => s.id !== selected,
                );
                setDraft({ ...draft, scenarios });
                setSelected(scenarios[0].id);
                setStepId("");
                setRemoving(false);
              }}
            >
              Удалить из настроек
            </button>
          </div>
        </Modal>
      )}
      {testing && (
        <Modal
          title="Проверить сообщение в WhatsApp"
          close={() => setTesting(false)}
        >
          <div className="modal-body stack">
            <p>
              Укажите свой номер. Откроется текст из предпросмотра — тест не
              попадёт в историю клиента.
            </p>
            <label>
              Ваш номер для проверки
              <PhoneInput value={testPhone} onChange={setTestPhone} />
            </label>
            <p className="preserve">{preview}</p>
            {/^\+[1-9]\d{7,14}$/.test(testPhone) ? (
              <a
                className="btn rm-wa"
                target="_blank"
                rel="noopener noreferrer"
                href={`https://wa.me/${testPhone.slice(1)}?text=${encodeURIComponent(preview)}`}
              >
                Открыть WhatsApp
              </a>
            ) : (
              <p className="muted">
                Введите номер полностью, например +996555123456.
              </p>
            )}
          </div>
        </Modal>
      )}
    </section>
  );
}
