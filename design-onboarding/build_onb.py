# -*- coding: utf-8 -*-
"""Shop onboarding: setup checklist, channels, points, staff first login (mobile).

Reuses tokens/helpers from ../design-crm/build_crm.py (-> design-reminders/v2 -> build.py).
Run: python3 build_onb.py  ->  writes *.html next to this file.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CRM = os.path.join(HERE, "..", "design-crm", "build_crm.py")
ns = {"__file__": CRM}
exec(open(CRM, encoding="utf-8").read().split("\n\ndef avc(")[0], ns)
svg, I, WA, av, ICONS, BRAND_SVG = ns["svg"], ns["I"], ns["WA"], ns["av"], ns["ICONS"], ns["ns"]["BRAND_SVG"]
IG, WA13, BOT, IMG, SEND, NEW, PIN = (ns[k] for k in ("IG", "WA13", "BOT", "IMG", "SEND", "NEW", "PIN"))
CRM_CSS = ns["CSS"]

ICONS["setup"] = svg('<path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>', 16)
COPY = svg('<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>', 14)
TG = svg('<path d="M21 4L3 11l6 2 2 6 3-4 5 4z"/><path d="M9 13l12-9"/>', 14)
BELL = ICONS["reminders"]
SHARE = svg('<path d="M12 3v12M8 7l4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/>', 18)
HOMEADD = svg('<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M12 8v8M8 12h8"/>', 18)
CAM = svg('<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>', 18)
VOL = svg('<path d="M4 9v6h4l5 4V5L8 9z"/><path d="M16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12"/>', 16)
HELP = svg('<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6M12 17h.01"/>', 14)
CLOCK, CHECK, CHEV, PLUS = I["clock"], I["check"], I["chev"], I["plus"]

NAV = [("setup", "Подключение", "4/7"), ("orders", "Заказы", ""), ("chats", "Чаты", ""), ("clients", "Клиенты", ""),
       ("reminders", "Напоминания", ""), ("deliveries", "Доставка", ""), ("settings", "Настройки", "")]


def rail(active):
    items = "".join('<div class="nav-item%s">%s%s%s</div>' % (" on" if k == active else "", ICONS[k], n,
                    ('<span class="cnt">%s</span>' % c) if c else "") for k, n, c in NAV)
    return ('<div class="rail"><div class="brand"><div class="brand-mark">' + BRAND_SVG +
            '</div><div><div class="brand-name">Tapme Flowers</div><div class="brand-sub">Кабинет магазина</div></div></div>'
            '<div class="nav">' + items + '</div><div class="rail-foot" style="flex-direction:column;align-items:stretch;gap:6px">'
            '<div class="small" style="color:var(--rail-dim)">Точка</div>'
            '<div class="switch">' + PIN + '<span>Все точки</span><span style="margin-left:auto">' + CHEV + '</span></div></div></div>')


def topbar(title):
    return ('<div class="topbar"><div><h1>' + title + '</h1></div><div class="search">' + ns["ns"]["SEARCH_SVG"] +
            '<span>Телефон, имя или № заказа</span><span class="kbd">/</span></div><div class="spacer"></div>'
            '<span class="btn primary">+ Заказ</span><div class="ubtn"><span class="av">БУ</span><div><div class="un">Бермет</div>'
            '<div class="ur">Владелец</div></div></div></div>')


CSS = """
.root{grid-template-rows:minmax(0,900px)}.main{overflow:hidden}
.switch{display:flex;align-items:center;gap:8px;height:36px;padding:0 10px;border-radius:9px;background:var(--rail-active);color:#fff;font-weight:500}
.prog2{height:8px;border-radius:4px;background:var(--surface-3);overflow:hidden}.prog2 i{display:block;height:100%;background:var(--ok)}
.setup{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:14px}
.steps2{background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.st{display:grid;grid-template-columns:30px minmax(0,1fr) auto;gap:14px;align-items:center;padding:9px 18px;border-top:1px solid var(--border)}
.st:first-child{border-top:0}
.st .n{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;font-family:var(--mono);font-size:12.5px;font-weight:600;border:2px solid var(--border-2);color:var(--muted);background:#fff}
.st.done .n{background:var(--ok);border-color:var(--ok);color:#fff}
.st.cur .n{border-color:var(--accent);color:var(--accent)}
.st .tt{font-weight:600;color:var(--ink)}.st .ss{font-size:12.5px;color:var(--muted);margin-top:1px}
.st.done .tt{color:var(--ink-2)}
.st.cur{background:#FCFBFE;box-shadow:inset 3px 0 0 var(--accent);align-items:start}
.subs{display:flex;flex-direction:column;gap:6px;margin-top:8px}
.subs .r{display:flex;gap:10px;align-items:center;font-size:13px;color:var(--ink-2)}
.subs .r .ic{width:20px;height:20px;border-radius:50%;display:grid;place-items:center;flex:none}
.ic.ok{background:var(--ok);color:#fff}.ic.wait{background:var(--warn-bg);color:var(--warn)}.ic.todo{border:2px solid var(--border-2)}
.copybox{border:1px solid var(--border);border-radius:10px;background:#fff;padding:10px 12px;margin-top:4px}
.copybox .tx{font-size:13px;color:var(--ink);line-height:1.5;background:#D9FDD3;border-radius:8px;padding:8px 10px}
.copybox .how{font-size:12px;color:var(--muted);margin-top:8px;display:flex;gap:10px;align-items:center}
.qr{width:96px;height:96px;border-radius:10px;border:1px solid var(--border);background:
  linear-gradient(90deg,#fff 0 12%,transparent 12% 88%,#fff 88%),
  repeating-conic-gradient(#171C19 0 25%,#fff 0 50%) 0 0/16px 16px;flex:none;position:relative}
.qr::after{content:"wa.me";position:absolute;inset:auto 0 -18px 0;text-align:center;font-size:10.5px;color:var(--dim);font-family:var(--mono)}
.later{margin-top:14px}
.later .row2{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.lt{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 14px}
.lt .tt{font-weight:600;color:var(--ink);font-size:13.5px}.lt .ss{font-size:12.5px;color:var(--muted);margin-top:3px}
.panel{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.panel + .panel{margin-top:12px}
.who{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;padding:7px 0;border-top:1px solid var(--border);font-size:13px}
.who:first-of-type{border-top:0}
.who .rl{font-size:12px;color:var(--muted)}
.okd{display:inline-flex;gap:4px;align-items:center;font-size:12px}
.okd.y{color:var(--ok)}.okd.n{color:var(--dim)}
/* settings tabs */
.stabs{display:flex;gap:2px;border-bottom:1px solid var(--border);margin-bottom:14px}
.stabs span{padding:10px 14px;font-weight:500;color:var(--muted);border-bottom:2px solid transparent;margin-bottom:-1px;display:inline-flex;gap:6px;align-items:center}
.stabs span.on{color:var(--ink);border-bottom-color:var(--ink)}
.stabs .new{font-size:10.5px;font-weight:600;color:var(--accent);background:var(--accent-bg);border-radius:4px;padding:0 5px}
.chgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.chc{background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.chh{display:flex;align-items:center;gap:12px;padding:14px 16px;border-bottom:1px solid var(--border)}
.chh .logo{width:36px;height:36px;border-radius:10px;display:grid;place-items:center;color:#fff;flex:none}
.chh .logo svg{width:18px;height:18px}
.chb{padding:12px 16px;display:flex;flex-direction:column;gap:10px;flex:1}
.kv{display:grid;grid-template-columns:150px minmax(0,1fr);gap:8px;font-size:13px;align-items:baseline}
.kv .k{color:var(--muted)}.kv .v{color:var(--ink)}.kv .v small{display:block;color:var(--dim);font-size:11.5px;margin-top:1px}
.meter{display:flex;gap:3px;align-items:center}.meter i{width:26px;height:6px;border-radius:3px;background:var(--surface-3)}.meter i.on{background:var(--ok)}
.chf{display:flex;gap:8px;align-items:center;padding:10px 16px;border-top:1px solid var(--border);background:#FBFCFA;font-size:12px;color:var(--muted)}
.pulse{width:8px;height:8px;border-radius:50%;background:var(--ok);box-shadow:0 0 0 3px var(--ok-bg)}
.status{display:inline-flex;align-items:center;gap:6px;height:24px;padding:0 9px;border-radius:999px;font-size:12px;font-weight:500}
.status.ok{background:var(--ok-bg);color:var(--ok)}.status.wait{background:var(--warn-bg);color:var(--warn)}.status.off{background:var(--neutral-bg);color:var(--neutral)}
.trow{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--ink-2);padding:6px 0;border-top:1px solid var(--border)}
.trow:first-child{border-top:0}
/* points */
.pts{display:grid;grid-template-columns:300px minmax(0,1fr);gap:12px}
.plist{background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.pt{display:grid;grid-template-columns:auto minmax(0,1fr);gap:10px;padding:12px 14px;border-top:1px solid var(--border)}
.pt:first-child{border-top:0}.pt.sel{background:var(--accent-bg);box-shadow:inset 3px 0 0 var(--accent)}
.pt .tt{font-weight:600;color:var(--ink)}.pt .ss{font-size:12.5px;color:var(--muted);margin-top:2px}
.ped{background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.ped .sec{padding:14px 18px;border-top:1px solid var(--border)}
.ped .sec:first-child{border-top:0}
.form{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.fl label{display:block;font-size:12px;color:var(--muted);margin-bottom:4px}
.fl .in{height:36px;border:1px solid var(--border-2);border-radius:8px;display:flex;align-items:center;padding:0 10px;font-size:13.5px;color:var(--ink);background:#fff}
.wins{display:flex;gap:6px;flex-wrap:wrap}
.wins span{height:30px;padding:0 10px;border-radius:8px;border:1px solid var(--border);display:inline-flex;align-items:center;font-family:var(--mono);font-size:12.5px;color:var(--ink);background:#fff}
.wins span.add{border-style:dashed;color:var(--muted);font-family:var(--sans)}
.zones{display:grid;grid-template-columns:minmax(0,1fr) 110px 110px;gap:0;font-size:13px}
.zones div{padding:7px 0;border-top:1px solid var(--border)}.zones .h{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);font-weight:600;border-top:0}
.zones .m{font-family:var(--mono);text-align:right}
.two{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:18px}
.qrimg{width:100%;height:150px;border-radius:10px;border:1px dashed var(--border-2);display:grid;place-items:center;color:var(--muted);font-size:12.5px;text-align:center;background:var(--surface-2)}
.team{display:flex;gap:8px;flex-wrap:wrap}
.mem{display:flex;gap:8px;align-items:center;height:36px;padding:0 10px 0 4px;border-radius:999px;border:1px solid var(--border);font-size:13px;background:#fff}
.mem small{color:var(--muted);font-size:11.5px}
"""



def html(title, body, top, active):
    base = ns["page"](title, "", top=top, active=active)
    head = base.split("<body>")[0].replace("</style>", CRM_CSS + CSS + "</style>", 1)
    return (head + '<body><div class="root">' + rail(active) + '<div class="main">' + topbar(top) +
            '<div class="canvas">' + body + '</div></div></div></body></html>')


# ---------------- 1. Setup checklist ----------------
def setup():
    def st(n, title, sub, state, right=""):
        mark = CHECK if state == "done" else str(n)
        return ('<div class="st %s"><span class="n">%s</span><div><div class="tt">%s</div><div class="ss">%s</div></div><div>%s</div></div>'
                % (state, mark, title, sub, right))
    wa_step = (
        '<div class="st cur"><span class="n">5</span><div><div class="row"><span class="tt">WhatsApp — номер для заказов</span>'
        '<span class="status wait">' + CLOCK + ' имя на проверке Meta</span></div>'
        '<div class="ss">Главный номер магазина не подключаем — он остаётся на телефоне как раньше.</div>'
        '<div class="subs">'
        '<div class="r"><span class="ic ok">' + CHECK + '</span>Номер <b class="mono" style="margin:0 4px">+996 700 555 010</b> подтверждён кодом из SMS</div>'
        '<div class="r"><span class="ic ok">' + CHECK + '</span>Бизнес-аккаунт Meta «Tapme Flowers» создан на магазин</div>'
        '<div class="r"><span class="ic wait">' + CLOCK + '</span>Имя «Tapme Flowers · заказы» — Meta проверяет, обычно до 24 часов. Можно продолжать.</div>'
        '<div class="r"><span class="ic todo"></span>Автоответ на главном номере — чтобы клиенты узнали о номере заказов</div>'
        '<div style="margin-left:30px">'
        '<div class="copybox"><div class="tx">Здравствуйте! Это Tapme Flowers 🌷 Заказ быстрее оформить здесь: '
        '<b>wa.me/996700555010</b> — покажем букеты дня, менеджер ответит за 10 минут.</div>'
        '<div class="how">' + HELP + ' WhatsApp Business → Инструменты → Приветственное сообщение'
        '<span class="spacer"></span><span class="btn sm">' + COPY + ' Скопировать</span><span class="btn sm">Готово, вставил</span></div></div>'
        '</div>'
        '</div></div><div></div></div>')
    steps = (
        st(1, "Точки", "2 точки: ул. Токтогула, 125 и пр. Чуй, 40 · окна доставки и зоны заданы", "done", '<span class="btn ghost sm">Изменить</span>') +
        st(2, "Команда", "6 сотрудников приглашены по ссылке · 4 уже вошли", "done", '<span class="btn ghost sm">Изменить</span>') +
        st(3, "Прайс и бюджеты", "14 позиций · бюджеты 3 000 / 5 000 / 10 000 сом", "done", '<span class="btn ghost sm">Изменить</span>') +
        st(4, "Оплата", "QR MBank на обе точки · предоплата 100% для доставки", "done", '<span class="btn ghost sm">Изменить</span>') +
        wa_step +
        st(6, "Instagram Direct", "Войдите в аккаунт @tapme.flowers — сообщения из Direct появятся в «Чатах»", "todo", '<span class="btn primary sm">' + IG + ' Подключить</span>') +
        st(7, "Тестовый заказ", "Напишите со своего телефона на номер заказов — проверим путь до доски флориста", "todo", '<span class="btn sm">Начать</span>')
    )
    later = ('<div class="panel"><div class="lbl">После запуска — не мешает начать</div>'
             '<div class="trow">' + PLUS + '<span><b class="ink">Импорт клиентов</b><br><span class="small muted">Excel или контакты телефона</span></span></div>'
             '<div class="trow">' + BELL + '<span><b class="ink">Сценарии напоминаний</b><br><span class="small muted">проверить тексты ДР и годовщин</span></span></div>'
             '<div class="trow">' + WA13 + '<span><b class="ink">Важные чаты из старого WhatsApp</b><br><span class="small muted">экспорт чата → в карточку клиента</span></span></div></div>')
    people = [("Айгуль Садыкова", "Менеджер · Токтогула", True, True), ("Тимур Нуров", "Менеджер · Чуй", True, False),
              ("Алина Каримова", "Флорист · Токтогула", True, True), ("Нурия Исаева", "Флорист · Чуй", True, True),
              ("Бакыт Асанов", "Курьер", False, False), ("Данияр Осмонов", "Курьер", False, False)]
    who = "".join('<div class="who">%s<div><div class="ink">%s</div><div class="rl">%s</div></div><div class="row" style="gap:10px">'
                  '<span class="okd %s">%s приложение</span><span class="okd %s">%s push</span></div></div>'
                  % (av(n, "sm"), n, r, "y" if a else "n", CHECK if a else "—", "y" if p else "n", CHECK if p else "—")
                  for n, r, a, p in people)
    right = ('<div class="panel"><div class="row"><b class="ink">Готовность команды</b><span class="spacer"></span><span class="mono small">4 / 6</span></div>'
             '<div class="small muted" style="margin:4px 0 8px">Без приложения и push сотрудник не услышит новый заказ или чат</div>' + who +
             '<span class="btn sm" style="margin-top:10px">Напомнить остальным в WhatsApp</span></div>'
             '<div class="panel"><div class="row">' + av("Арсен Tapme", "sm") + '<div><b class="ink">Арсен · Tapme</b>'
             '<div class="small muted">подключает ваш магазин</div></div><span class="spacer"></span><span class="btn wa sm">' + WA13 + ' Написать</span></div></div>')
    body = ('<div class="page-hd"><div><h1>Подключение магазина</h1><div class="subs">Осталось 3 шага · обычно 40–60 минут вместе с менеджером Tapme</div></div>'
            '<div class="spacer"></div><div style="width:260px"><div class="row small"><span class="muted">Готово</span><span class="spacer"></span><b class="mono ink">4 из 7</b></div>'
            '<div class="prog2" style="margin-top:6px"><i style="width:57%"></i></div></div></div>'
            '<div class="setup"><div><div class="steps2">' + steps + '</div></div><div>' + right + later + '</div></div>')
    return html("Подключение магазина", body, "Подключение", "setup")


def stabs(on):
    tabs = [("Компания", ""), ("Точки", "new"), ("Команда", ""), ("Прайс", ""), ("Каналы", "new"), ("Бот", "new"), ("Напоминания", "")]
    return '<div class="stabs">' + "".join('<span class="%s">%s%s</span>' % ("on" if t == on else "", t, ' <i class="new">новое</i>' if n else "") for t, n in tabs) + '</div>'


# ---------------- 2. Channels ----------------
def channels():
    wa = (
        '<div class="chc"><div class="chh"><span class="logo" style="background:var(--wa)">' + WA13 + '</span>'
        '<div><b class="ink" style="font-size:15px">WhatsApp · номер для заказов</b><div class="small muted mono">+996 700 555 010</div></div>'
        '<span class="spacer"></span><span class="status ok">' + CHECK + ' Подключён</span></div><div class="chb">'
        '<div class="kv"><span class="k">Имя у клиентов</span><span class="v">Tapme Flowers · заказы<small>одобрено Meta 16 окт</small></span></div>'
        '<div class="kv"><span class="k">Качество номера</span><span class="v"><span class="row"><span class="meter"><i class="on"></i><i class="on"></i><i class="on"></i></span><b style="color:var(--ok)">Высокое</b></span>'
        '<small>Meta оценивает по жалобам и блокировкам клиентов. За 30 дней жалоб нет.</small></span></div>'
        '<div class="kv"><span class="k">Сегодня</span><span class="v">38 входящих · 52 ответа · ответ в среднем за 3 мин</span></div>'
        '<div class="kv"><span class="k">После 24 часов</span><span class="v">Писать первыми можно только шаблонами<small>4 шаблона одобрены · «Заказ доставлен», «Оплата получена»…</small></span></div>'
        '<div class="kv"><span class="k">Оплата Meta</span><span class="v">карта владельца в аккаунте Meta<small>за октябрь ≈ $4,20 — только шаблоны; диалоги, начатые клиентом, бесплатны</small></span></div>'
        '</div><div class="chf"><span class="pulse"></span>Связь работает · последнее сообщение 10:04<span class="spacer"></span><span class="btn sm">Шаблоны</span><span class="btn sm">Проверить связь</span></div></div>')
    ig = (
        '<div class="chc"><div class="chh"><span class="logo" style="background:#C13584">' + IG + '</span>'
        '<div><b class="ink" style="font-size:15px">Instagram Direct</b><div class="small muted">@tapme.flowers</div></div>'
        '<span class="spacer"></span><span class="status ok">' + CHECK + ' Подключён</span></div><div class="chb">'
        '<div class="kv"><span class="k">Что видит CRM</span><span class="v">Все сообщения в Direct и ответы из приложения Instagram</span></div>'
        '<div class="kv"><span class="k">Бот</span><span class="v">Отвечает в течение 24 часов после сообщения клиента<small>дальше — только человек, до 7 дней</small></span></div>'
        '<div class="kv"><span class="k">Сегодня</span><span class="v">11 входящих · 3 новых клиента</span></div>'
        '</div><div class="chf"><span class="pulse"></span>Связь работает · последнее сообщение 09:51<span class="spacer"></span><span class="btn ghost sm">Отключить</span></div></div>')
    main = (
        '<div class="chc"><div class="chh"><span class="logo" style="background:var(--neutral)">' + WA13 + '</span>'
        '<div><b class="ink" style="font-size:15px">Главный номер магазина</b><div class="small muted mono">+996 555 000 111</div></div>'
        '<span class="spacer"></span><span class="status off">Не подключается</span></div><div class="chb">'
        '<div class="small" style="color:var(--ink-2);line-height:1.5">Остаётся только на телефоне — CRM его не читает и с него не пишет. Так номер защищён от блокировки.</div>'
        '<div class="trow">' + CHECK + ' Автоответ со ссылкой на номер заказов вставлен <span class="spacer"></span><span class="small muted">15 окт</span><span class="btn ghost sm">Текст</span></div>'
        '</div></div>')
    notif = (
        '<div class="chc"><div class="chh"><span class="logo" style="background:var(--accent)">' + BELL + '</span>'
        '<div><b class="ink" style="font-size:15px">Уведомления о чатах</b><div class="small muted">кого и как звать, когда клиент ждёт</div></div></div><div class="chb">'
        '<div class="trow">' + VOL + ' Звук в CRM при новом чате, чеке и заказе от бота<span class="spacer"></span><span class="sw-on"></span></div>'
        '<div class="trow">' + BELL + ' Push на телефоны<span class="spacer"></span><span class="small muted">4 из 6 сотрудников</span><span class="btn ghost sm">Кто без push</span></div>'
        '<div class="trow">' + CLOCK + ' Клиент ждёт ответа дольше<span class="spacer"></span><span class="slot num" style="height:28px">5 мин</span><span class="small muted">— повторить звук</span></div>'
        '<div class="trow">' + TG + ' Нет ответа за<span class="slot num" style="height:28px">10 мин</span>— написать в Telegram<span class="spacer"></span><span class="small mono">@aigul_tapme</span></div>'
        '</div></div>')
    body = ('<div class="page-hd" style="margin-bottom:8px"><div><h1>Настройки</h1></div></div>' + stabs("Каналы") +
            '<div class="chgrid">' + wa + ig + main + notif + '</div>')
    return html("Настройки · Каналы", body, "Настройки", "settings")


# ---------------- 3. Points ----------------
def points():
    plist = ('<div class="plist">'
             '<div class="pt sel"><span class="ic" style="width:30px;height:30px;border-radius:8px;display:grid;place-items:center;background:#fff;color:var(--accent)">' + PIN + '</span>'
             '<div><div class="tt">Токтогула</div><div class="ss">ул. Токтогула, 125 · 09:00–21:00</div><div class="row" style="margin-top:6px"><span class="tag ok">основная</span><span class="tag">4 сотрудника</span></div></div></div>'
             '<div class="pt"><span class="ic" style="width:30px;height:30px;border-radius:8px;display:grid;place-items:center;background:var(--surface-2)">' + PIN + '</span>'
             '<div><div class="tt">Чуй</div><div class="ss">пр. Чуй, 40 · 10:00–20:00</div><div class="row" style="margin-top:6px"><span class="tag">3 сотрудника</span></div></div></div>'
             '<div class="pt" style="color:var(--muted)"><span class="ic" style="width:30px;height:30px;border-radius:8px;display:grid;place-items:center;border:1px dashed var(--border-2)">' + PLUS + '</span>'
             '<div style="align-self:center">Добавить точку</div></div>'
             '<div style="padding:12px 14px;border-top:1px solid var(--border);background:#FBFCFA" class="small muted">'
             'Клиенты, прайс, чаты и напоминания — общие для всех точек. У каждой точки свои заказы, окна доставки, букеты дня, QR и команда.</div></div>')
    ed = (
        '<div class="ped"><div class="sec"><div class="row"><h2 style="font-size:17px">Токтогула</h2><span class="tag ok">основная</span>'
        '<span class="spacer"></span><span class="btn primary sm">Сохранить</span></div>'
        '<div class="form" style="margin-top:12px"><div class="fl"><label>Адрес</label><div class="in">ул. Токтогула, 125</div></div>'
        '<div class="fl"><label>Часы работы</label><div class="in">09:00–21:00 ежедневно</div></div>'
        '<div class="fl"><label>Телефон точки</label><div class="in mono">+996 555 000 111</div></div></div></div>'
        '<div class="sec"><div class="lbl">Окна доставки</div><div class="wins"><span>09:00–11:00</span><span>11:00–13:00</span><span>13:00–15:00</span>'
        '<span>15:00–17:00</span><span>17:00–19:00</span><span>19:00–21:00</span><span class="add">' + PLUS + ' окно</span></div>'
        '<div class="row small muted" style="margin-top:8px"><span class="sw-on"></span> Не больше <b class="mono ink">6</b> доставок в одно окно</div></div>'
        '<div class="sec two"><div><div class="lbl">Зоны доставки</div><div class="zones"><div class="h">Зона</div><div class="h" style="text-align:right">Цена</div><div class="h" style="text-align:right">Время</div>'
        '<div>Центр (до 3 км)</div><div class="m">300</div><div class="m">60 мин</div>'
        '<div>Восток-5, Джал, Асанбай</div><div class="m">400</div><div class="m">90 мин</div>'
        '<div>Кант, Сокулук</div><div class="m">800</div><div class="m">2 ч</div></div></div>'
        '<div><div class="lbl">QR для оплаты</div><div class="qrimg">' + IMG + '<br>QR MBank · Токтогула<br><span class="small">бот отправит его после заказа</span></div></div></div>'
        '<div class="sec"><div class="lbl">Команда точки</div><div class="team">'
        '<span class="mem">' + av("Айгуль Садыкова", "sm") + 'Айгуль <small>менеджер</small></span>'
        '<span class="mem">' + av("Алина Каримова", "sm") + 'Алина <small>флорист</small></span>'
        '<span class="mem">' + av("Бакыт Асанов", "sm") + 'Бакыт <small>курьер · обе точки</small></span>'
        '<span class="mem">' + av("Данияр Осмонов", "sm") + 'Данияр <small>курьер · обе точки</small></span>'
        '<span class="mem" style="color:var(--muted)">' + PLUS + ' Пригласить</span></div>'
        '<div class="small muted" style="margin-top:8px">Букеты дня этой точки бот показывает, когда клиент выбрал доставку отсюда или самовывоз с Токтогула.</div></div>'
        '</div>')
    body = ('<div class="page-hd" style="margin-bottom:8px"><div><h1>Настройки</h1></div></div>' + stabs("Точки") +
            '<div class="pts">' + plist + ed + '</div>')
    return html("Настройки · Точки", body, "Настройки", "settings")


# ---------------- 4. Staff first login (mobile) ----------------
def first_login():
    css = """
    body{background:#E9ECE6;margin:0}.stagex{width:1440px;height:900px;display:flex;gap:28px;align-items:center;justify-content:center;font-family:var(--sans);color:var(--ink-2);font-size:14px}
    .phn{width:340px;height:760px;border-radius:44px;background:#111;padding:12px;box-shadow:0 30px 60px rgba(15,42,34,.25)}
    .scr{width:100%;height:100%;border-radius:34px;background:var(--surface);overflow:hidden;display:flex;flex-direction:column;position:relative}
    .sb{height:44px;display:flex;align-items:center;justify-content:space-between;padding:0 26px;font-weight:600;font-size:14px;color:#111}
    .bd{padding:10px 22px;display:flex;flex-direction:column;gap:14px;flex:1}
    .dots{display:flex;gap:6px}.dots i{width:22px;height:5px;border-radius:3px;background:var(--surface-3)}.dots i.on{background:var(--accent)}
    .bd h2{font-size:23px;line-height:1.2}
    .lead{font-size:14.5px;color:var(--muted);line-height:1.5}
    .stepx{display:flex;gap:12px;align-items:center;padding:12px;border:1px solid var(--border);border-radius:12px;font-size:14px;color:var(--ink)}
    .stepx .ic{width:36px;height:36px;border-radius:10px;display:grid;place-items:center;background:var(--surface-2);color:var(--ink);flex:none}
    .ft{padding:14px 22px 28px;display:flex;flex-direction:column;gap:10px}
    .big{height:50px;border-radius:12px;background:var(--accent);color:#fff;font-weight:600;font-size:16px;display:flex;align-items:center;justify-content:center;gap:8px}
    .big.g{background:var(--wa)}
    .skip{text-align:center;color:var(--muted);font-size:14px}
    .sysd{position:absolute;left:34px;right:34px;top:250px;background:rgba(245,245,247,.97);border-radius:16px;box-shadow:0 20px 50px rgba(0,0,0,.25);text-align:center;overflow:hidden}
    .sysd .t{padding:16px 16px 12px;font-size:14px;color:#111;line-height:1.35}.sysd .t b{display:block;font-size:15px;margin-bottom:4px}
    .sysd .b{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid #d7d7db}.sysd .b span{padding:11px;color:#0A64D8;font-size:15px}.sysd .b span+span{border-left:1px solid #d7d7db;font-weight:600}
    .dimov{position:absolute;inset:0;background:rgba(0,0,0,.28)}
    .role{display:inline-flex;align-items:center;gap:6px;height:26px;padding:0 10px;border-radius:999px;background:var(--accent-bg);color:var(--accent);font-size:13px;font-weight:500;align-self:flex-start}
    .capt{width:230px;font-size:15px;line-height:1.5}.capt h2{font-size:22px;margin-bottom:10px}
    .todo{display:flex;flex-direction:column;gap:0;border:1px solid var(--border);border-radius:12px;overflow:hidden}
    .todo div{display:flex;gap:12px;align-items:flex-start;padding:12px;border-top:1px solid var(--border);font-size:14px;color:var(--ink)}
    .todo div:first-child{border-top:0}.todo b{font-family:var(--mono);color:var(--accent)}
    .todo small{display:block;color:var(--muted);font-size:12.5px;margin-top:2px}
    """
    p1 = ('<div class="phn"><div class="scr"><div class="sb"><span>9:12</span><span>●●● ▮</span></div><div class="bd">'
          '<div class="dots"><i class="on"></i><i></i><i></i></div>'
          '<span class="role">Флорист · точка Токтогула</span>'
          '<h2>Здравствуйте, Алина! Поставьте Tapme на телефон</h2>'
          '<div class="lead">Так новые заказы будут приходить со звуком, даже когда браузер закрыт. Займёт 30 секунд.</div>'
          '<div class="stepx"><span class="ic">' + SHARE + '</span><div>Нажмите «Поделиться» внизу Safari</div></div>'
          '<div class="stepx"><span class="ic">' + HOMEADD + '</span><div>Выберите «На экран Домой» → «Добавить»</div></div>'
          '<div class="stepx"><span class="ic" style="background:var(--accent-bg);color:var(--accent)">' + BRAND_SVG + '</span><div>Откройте Tapme с главного экрана</div></div>'
          '</div><div class="ft"><div class="big">Я добавила — дальше</div><div class="skip">У меня Android</div></div></div></div>')
    p2 = ('<div class="phn"><div class="scr"><div class="sb"><span>9:13</span><span>●●● ▮</span></div><div class="bd">'
          '<div class="dots"><i class="on"></i><i class="on"></i><i></i></div>'
          '<h2>Разрешите уведомления</h2>'
          '<div class="lead">Пришлём, когда менеджер передаст заказ на сборку или клиент изменит время. Ничего лишнего.</div>'
          '<div class="stepx"><span class="ic">' + VOL + '</span><div>Звук нового заказа<div class="small muted">нажмите, чтобы послушать</div></div></div>'
          '</div><div class="ft"><div class="big">Разрешить уведомления</div><div class="skip">Позже</div></div>'
          '<div class="dimov"></div><div class="sysd"><div class="t"><b>«Tapme» запрашивает разрешение на уведомления</b>Уведомления могут содержать предупреждения, звуки и наклейки.</div>'
          '<div class="b"><span>Не разрешать</span><span>Разрешить</span></div></div></div></div>')
    p3 = ('<div class="phn"><div class="scr"><div class="sb"><span>9:14</span><span>●●● ▮</span></div><div class="bd">'
          '<div class="dots"><i class="on"></i><i class="on"></i><i class="on"></i></div>'
          '<h2>Готово! Ваше утро в Tapme</h2>'
          '<div class="todo"><div><b>1</b><span>Сфотографируйте букеты дня до 10:00<small>бот будет предлагать клиентам только их</small></span></div>'
          '<div><b>2</b><span>Откройте «Доску»<small>новые заказы появятся сами, со звуком</small></span></div>'
          '<div><b>3</b><span>Нажмите «Собран», когда букет готов<small>курьер и менеджер узнают сразу</small></span></div></div>'
          '</div><div class="ft"><div class="big g">' + CAM + ' Снять первый букет</div><div class="skip">Перейти к доске</div></div></div></div>')
    cap = ('<div class="capt"><h2>Первый вход сотрудника</h2><p class="muted">Три экрана, одна минута. Тексты меняются по роли: '
           'менеджеру — чаты и проверка оплаты, курьеру — «Мои доставки». Без приложения и push сотрудник не услышит новый заказ — поэтому это первым делом.</p></div>')
    base = ns["page"]("Первый вход", "", top="", active="setup")
    head = base.split("<body>")[0].replace("</style>", CRM_CSS + CSS + css + "</style>", 1)
    return head + '<body><div class="stagex">' + cap + p1 + p2 + p3 + '</div></body></html>'


OUT = {"1-setup.html": setup(), "2-channels.html": channels(), "3-points.html": points(), "4-first-login.html": first_login()}
for name, page_html in OUT.items():
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        f.write(page_html)
    print("wrote", name)
