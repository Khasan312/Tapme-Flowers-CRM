# Набор вёрстки макетов

HTML-вёрстка всех новых экранов релиза «Каналы и CRM переписки» с общими CSS-файлами.
Нужна, чтобы переносить дизайн в `frontend/src` по готовой разметке и стилям, а не по
скриншотам.

**Это прототипы, а не приложение.** Экраны «Чаты», «Букеты дня», «Подключение» и
остальные в CRM пока не реализованы. Что и как делать — в [ТЗ](../docs/spec/README.md),
порядок работ — в [10-roadmap.md](../docs/spec/10-roadmap.md).

## Как открыть

Откройте [`index.html`](index.html) в браузере (двойной клик или перетащите в окно
браузера). Сервер не нужен. Оглавление показывает все экраны со скриншотами,
статусом («выбран», «не выбран», «новый экран») и ссылками на требования.

## Состав

```text
design-kit/
├── index.html          оглавление со скриншотами и ссылками на ТЗ
├── css/
│   ├── base.css        цвета, шрифты, боковое меню, шапка, кнопки, метки, карточки
│   ├── components.css  общие блоки экранов: список дня, очередь, редактор, пузыри WhatsApp
│   ├── crm.css         чаты, список клиентов, карточка клиента, черновик заказа
│   └── onboarding.css  чек-лист подключения, каналы, точки, первый вход
├── screens/            15 экранов, каждый подключает только нужные CSS
└── build_kit.py        сборка набора из генераторов
```

| Экран | Файл | Скриншот | Требования |
| --- | --- | --- | --- |
| Чаты — версия к понедельнику | `screens/crm-5-chats-monday.html` | `design-crm/png/5-chats-monday.png` | 12-chats-monday: CM-UI |
| Настройки → Каналы, ручное подключение | `screens/onboarding-5-channel-manual.html` | `design-onboarding/png/5-channel-manual.png` | 12-chats-monday: CM-CH |
| Чаты | `screens/crm-1-chats.html` | `design-crm/png/1-chats.png` | FR-CR-003…009, FR-OD-020 |
| Клиенты | `screens/crm-2-clients.html` | `design-crm/png/2-clients.png` | FR-CR-010…012, FR-CR-040 |
| Карточка клиента | `screens/crm-3-client-card.html` | `design-crm/png/3-client-card.png` | FR-CR-045…050 |
| Телефон менеджера | `screens/crm-4-mobile.html` | `design-crm/png/4-mobile.png` | FR-NT-030…034 |
| Кому написать сегодня (выбран) | `screens/reminders-1-list.html` | `design-reminders/v2/png/1-list.png` | FR-RM-001…009 |
| Настройки напоминаний (выбран) | `screens/reminders-4-settings-scenarios.html` | `design-reminders/v2/png/4-settings-scenarios.png` | FR-RM-020…025 |
| Очередь и карточка (не выбран) | `screens/reminders-2-queue-card.html` | `design-reminders/v2/png/2-queue-card.png` | — |
| Доска недели (не выбран) | `screens/reminders-3-week-board.html` | `design-reminders/v2/png/3-week-board.png` | — |
| Мобильная очередь (не выбран) | `screens/reminders-5-mobile.html` | `design-reminders/v2/png/5-mobile.png` | — |
| Подключение магазина | `screens/onboarding-1-setup.html` | `design-onboarding/png/1-setup.png` | FR-ON-010…014 |
| Настройки → Каналы | `screens/onboarding-2-channels.html` | `design-onboarding/png/2-channels.png` | FR-CH-070…075 |
| Настройки → Точки | `screens/onboarding-3-points.html` | `design-onboarding/png/3-points.png` | FR-MP-006…009 |
| Первый вход сотрудника | `screens/onboarding-4-first-login.html` | `design-onboarding/png/4-first-login.png` | FR-ON-030 |

## Как переносить в приложение

1. Найдите блок на экране, откройте его в инструментах разработчика браузера и
   посмотрите классы (например, `.conv`, `.draft`, `.stg`, `.rrow`).
2. Правила этих классов лежат в одном из файлов `css/` — комментарий в начале файла
   указывает генератор-источник.
3. В React переносите разметку как компонент, а стили — в `frontend/src/parity.css` или
   новый файл стилей раздела, с префиксом раздела, чтобы не задеть существующие классы.
4. Данные в макетах вымышленные; иконки — встроенные SVG, их можно взять как есть.

Цвета макетов совпадают с приложением, кроме оттенка вторичного текста:

| Токен макета (`css/base.css`) | Значение | В приложении (`frontend/src/styles.css`) |
| --- | --- | --- |
| `--ink` | `#171C19` | `--ink: #171c19` |
| `--accent` | `#6B3FA0` | `--accent: #6b3fa0` |
| `--border` | `#E1E5DE` | `--border: #e1e5de` |
| `--muted` | `#5C665F` | `--muted: #667068` — использовать значение приложения |
| `--bg` | `#F5F6F3` | `background: #f5f6f3` |
| `--rail` | `#0F2A22` | цвет бокового меню |
| `--wa` | `#1F8A4C` | только для действий WhatsApp |

Шрифты: Golos Text (интерфейс) и IBM Plex Mono (цифры, время, номера).

## Как пересобрать

Набор собирается из генераторов в `design-reminders/v2/`, `design-crm/` и
`design-onboarding/`. Правьте генератор, затем из корня репозитория:

```bash
python3 design-kit/build_kit.py
```

```bash
frontend/node_modules/.bin/prettier --write "design-kit/screens/*.html" "design-kit/css/*.css"
```

Сборка заодно обновляет HTML в папках генераторов. Скриншоты обновляются отдельно
скриптами `shoot.cjs` в каждой папке (инструкция в начале каждого скрипта).
