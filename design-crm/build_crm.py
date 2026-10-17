# -*- coding: utf-8 -*-
"""CRM like Kelesu: chats inbox, auto-created clients, client card with conversation.

Reuses tokens/helpers from ../design-reminders/v2/build_v2.py (which reuses ../build.py).
Run: python3 build_crm.py  ->  writes *.html next to this file.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(HERE, "..", "design-reminders", "v2", "build_v2.py")
ns = {"__file__": V2}
exec(open(V2, encoding="utf-8").read().split("# ---------------- shared data ----------------")[0], ns)
svg, I, WA, av, page, ICONS = ns["svg"], ns["I"], ns["WA"], ns["av"], ns["page"], ns["ICONS"]

ICONS["chats"] = svg('<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.6A8 8 0 1 1 21 12z"/><path d="M8.5 11h7M8.5 14h4"/>', 16)
ns["NAV"] = [("orders", "Заказы", "12"), ("chats", "Чаты", "3"), ("clients", "Клиенты", ""),
             ("reminders", "Напоминания", "22"), ("deliveries", "Доставка", "9"), ("settings", "Настройки", "")]

IG = svg('<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".6" fill="currentColor"/>', 13, 2)
WA13 = svg('<path d="M21 12a9 9 0 0 1-13.4 7.8L3 21l1.3-4.5A9 9 0 1 1 21 12z"/>', 13, 2)
BOT = svg('<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 4v4M9 13h.01M15 13h.01M9 17h6"/>', 13, 2)
IMG = svg('<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/>', 18)
SEND = svg('<path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/>', 15)
MERGE = svg('<path d="M6 3v6a6 6 0 0 0 6 6h6M6 21v-6M15 12l3 3-3 3"/>', 14)
NEW = svg('<path d="M12 5v14M5 12h14"/>', 12, 2.4)
PIN = svg('<path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>', 13)

CSS = """
.canvas.full{padding:0;height:calc(900px - 58px)}
.inbox{display:grid;grid-template-columns:330px minmax(0,1fr) 350px;height:100%}
.pane{background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;min-width:0;overflow:hidden}
.pane:last-child{border-right:0;border-left:1px solid var(--border)}
.phd{padding:14px 16px 10px;border-bottom:1px solid var(--border)}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.chips span{height:28px;padding:0 10px;border-radius:999px;border:1px solid var(--border);font-size:12.5px;display:inline-flex;align-items:center;gap:6px;background:#fff;color:var(--ink-2)}
.chips span.on{background:var(--ink);border-color:var(--ink);color:#fff}
.chips span .n{font-family:var(--mono);font-size:11px;opacity:.75}
.chips span.hot{border-color:var(--crit-bg);background:var(--crit-bg);color:var(--crit)}
.conv{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;padding:11px 16px;border-top:1px solid var(--border);align-items:start}
.conv:first-child{border-top:0}
.conv .nm{font-weight:600;color:var(--ink);font-size:13.5px;display:flex;gap:6px;align-items:center;white-space:nowrap;overflow:hidden}
.conv .cpv{font-size:12.5px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px}
.conv .meta{display:flex;flex-direction:column;align-items:flex-end;gap:5px;font-size:11.5px;color:var(--dim);font-family:var(--mono)}
.conv.sel{background:var(--accent-bg);box-shadow:inset 3px 0 0 var(--accent)}
.conv.unread .cpv{color:var(--ink-2);font-weight:500}
.ub{min-width:18px;height:18px;border-radius:9px;background:var(--wa);color:#fff;font-size:11px;display:inline-grid;place-items:center;padding:0 5px;font-family:var(--mono)}
.avc{position:relative}.avc .ch{position:absolute;right:-3px;bottom:-3px;width:16px;height:16px;border-radius:50%;display:grid;place-items:center;color:#fff;border:2px solid #fff}
.ch.wa{background:var(--wa)}.ch.ig{background:#C13584}
.ch svg{width:9px;height:9px}
.mini{display:inline-flex;align-items:center;gap:4px;height:18px;padding:0 6px;border-radius:5px;font-size:11px;font-weight:500;font-family:var(--sans)}
.mini.new{background:var(--info-bg);color:var(--info)}.mini.bot{background:var(--accent-bg);color:var(--accent)}.mini.wait{background:var(--crit-bg);color:var(--crit)}.mini.pay{background:var(--warn-bg);color:var(--warn)}
.thread{display:flex;flex-direction:column;background:#F1EFEA;min-width:0}
.thd{display:flex;align-items:center;gap:12px;padding:12px 18px;background:var(--surface);border-bottom:1px solid var(--border)}
.tbody{flex:1;padding:16px 22px;display:flex;flex-direction:column;gap:9px;overflow:hidden}
.msg{max-width:78%;padding:8px 11px;border-radius:12px;font-size:13.5px;line-height:1.45;color:#111;box-shadow:0 1px 1px rgba(0,0,0,.06)}
.msg .t{display:block;text-align:right;font-size:11px;color:#667;margin-top:2px;font-family:var(--mono)}
.msg.in{background:#fff;align-self:flex-start;border-bottom-left-radius:3px}
.msg.out{background:#D9FDD3;align-self:flex-end;border-bottom-right-radius:3px}
.msg.bot{background:#F0EAF9;align-self:flex-end;border-bottom-right-radius:3px}
.msg .who{font-size:11px;font-weight:600;color:var(--accent);display:flex;gap:4px;align-items:center;margin-bottom:3px}
.msg .who.mgr{color:var(--wa)}
.sys{align-self:center;font-size:11.5px;color:var(--muted);background:rgba(255,255,255,.7);border-radius:999px;padding:3px 10px;display:flex;gap:6px;align-items:center}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:6px 0 4px}
.ph{height:84px;border-radius:8px;background:repeating-linear-gradient(135deg,#E6DDF2 0 8px,#EFE8F7 8px 16px);display:grid;place-items:center;color:var(--accent);font-size:11px;text-align:center}
.cap{font-size:12px;margin-top:4px}.cap b{font-family:var(--mono)}
.qbtn{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}.qbtn span{height:28px;padding:0 10px;border-radius:7px;background:#fff;color:var(--accent);font-size:12.5px;font-weight:500;display:inline-flex;align-items:center;border:1px solid #DED3EE}
.comp{padding:10px 18px 14px;background:var(--surface);border-top:1px solid var(--border)}
.comp .box{display:flex;align-items:center;gap:10px;border:1px solid var(--border-2);border-radius:10px;padding:0 8px 0 14px;height:44px;color:var(--dim);background:#fff}
.comp .qr{display:flex;gap:6px;margin-bottom:8px}
.comp .qr span{height:28px;padding:0 10px;border-radius:7px;background:var(--surface-2);font-size:12.5px;display:inline-flex;align-items:center;gap:6px;color:var(--ink-2)}
.sendb{width:32px;height:32px;border-radius:8px;background:var(--wa);color:#fff;display:grid;place-items:center;margin-left:auto}
.side{padding:14px 16px;display:flex;flex-direction:column;gap:14px;overflow:hidden}
.autonew{border:1px dashed var(--info);background:var(--info-bg);border-radius:10px;padding:10px 12px;font-size:12.5px;color:var(--info)}
.autonew b{color:var(--ink)}
.field{display:grid;grid-template-columns:96px minmax(0,1fr);gap:8px;align-items:baseline;font-size:13px;padding:5px 0;border-top:1px solid var(--border)}
.field:first-of-type{border-top:0}
.field .k{color:var(--muted);font-size:12px}.field .val{color:var(--ink)}
.field .val .src{display:block;font-size:11.5px;color:var(--dim);margin-top:1px}
.field .q{color:var(--warn)}
.draft{border:1px solid var(--border);border-radius:12px;overflow:hidden}
.draft .dh{display:flex;align-items:center;gap:8px;padding:10px 12px;background:var(--surface-2);border-bottom:1px solid var(--border)}
.draft .db{padding:6px 12px 10px}
.draft .tot{display:flex;align-items:center;padding:10px 12px;border-top:1px solid var(--border);font-weight:600;color:var(--ink)}
.live{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;color:var(--ok);font-weight:500}.live i{width:7px;height:7px;border-radius:50%;background:var(--ok);box-shadow:0 0 0 3px var(--ok-bg)}
.input{height:34px;border:1px solid var(--border-2);border-radius:8px;display:flex;align-items:center;padding:0 10px;color:var(--dim);font-size:13px;background:#fff}
/* clients list */
.stages{display:flex;gap:2px;border-bottom:1px solid var(--border);background:var(--surface);border:1px solid var(--border);border-radius:12px 12px 0 0;padding:0 8px;align-items:center}
.stages span{padding:11px 13px;font-weight:500;color:var(--muted);border-bottom:2px solid transparent;margin-bottom:-1px;display:inline-flex;gap:7px;align-items:center;white-space:nowrap}
.stages span.on{color:var(--ink);border-bottom-color:var(--ink)}
.stages .n{font-family:var(--mono);font-size:11px;background:var(--surface-2);border-radius:999px;padding:1px 7px;color:var(--muted)}
.stages span.on .n{background:var(--ink);color:#fff}
.tbl{background:var(--surface);border:1px solid var(--border);border-top:0;border-radius:0 0 12px 12px;overflow:hidden}
.th,.tr{display:grid;grid-template-columns:250px 118px minmax(0,1fr) 108px 112px 150px;gap:14px;align-items:center;padding:0 18px}
.th{height:36px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);font-weight:600;background:var(--surface-2);border-bottom:1px solid var(--border)}
.tr{min-height:58px;border-top:1px solid var(--border)}.th + .tr{border-top:0}
.tr .nm{font-weight:600;color:var(--ink);font-size:13.5px}.tr .sub{font-size:12px;color:var(--muted)}
.tr .last{font-size:12.5px;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tr .lt{font-size:11.5px;color:var(--dim);display:flex;gap:5px;align-items:center;margin-top:2px}
.tr .num{font-family:var(--mono);font-size:13px;color:var(--ink);text-align:right}
.tr .num small{display:block;font-size:11.5px;color:var(--muted)}
.tr.fresh{background:#F7FAFD}
.stg{display:inline-flex;align-items:center;gap:6px;height:24px;padding:0 9px;border-radius:999px;font-size:12px;font-weight:500}
.stg i{width:7px;height:7px;border-radius:50%;background:currentColor}
.st-new{background:var(--info-bg);color:var(--info)}.st-talk{background:var(--warn-bg);color:var(--warn)}
.st-ord{background:var(--ok-bg);color:var(--ok)}.st-loyal{background:var(--accent-bg);color:var(--accent)}.st-lost{background:var(--neutral-bg);color:var(--neutral)}
.owner{display:flex;gap:7px;align-items:center;font-size:12.5px;color:var(--ink-2)}
.merge{display:flex;align-items:center;gap:14px;padding:12px 16px;border:1px solid #CFDDF0;background:var(--info-bg);border-radius:12px;margin-bottom:12px}
.merge .mi{width:34px;height:34px;border-radius:9px;background:#fff;color:var(--info);display:grid;place-items:center;flex:none}
.merge b{color:var(--ink)}
.date{font-size:12.5px;color:var(--ink-2)}.date small{display:block;color:var(--dim);font-size:11.5px}
/* card */
.cardhd{display:flex;align-items:center;gap:14px;padding:16px 20px;background:var(--surface);border:1px solid var(--border);border-radius:12px;margin-bottom:12px}
.chan{display:inline-flex;align-items:center;gap:6px;height:26px;padding:0 9px;border-radius:7px;font-size:12.5px;background:var(--surface-2);color:var(--ink-2)}
.chan .d{width:16px;height:16px;border-radius:50%;display:grid;place-items:center;color:#fff}
.cgrid{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:12px;height:676px}
.feed{background:var(--surface);border:1px solid var(--border);border-radius:12px;display:flex;flex-direction:column;overflow:hidden}
.ftabs{display:flex;gap:2px;padding:0 10px;border-bottom:1px solid var(--border)}
.ftabs span{padding:11px 12px;font-weight:500;color:var(--muted);border-bottom:2px solid transparent;margin-bottom:-1px;display:inline-flex;gap:6px;align-items:center}
.ftabs span.on{color:var(--ink);border-bottom-color:var(--ink)}
.ftabs .n{font-family:var(--mono);font-size:11px;color:var(--dim)}
.tl{padding:6px 20px;overflow:hidden;flex:1}
.ti{display:grid;grid-template-columns:62px 30px minmax(0,1fr);gap:10px;padding:10px 0;border-top:1px solid var(--border);align-items:start}
.ti:first-child{border-top:0}
.ti .tm{font-family:var(--mono);font-size:12px;color:var(--muted);padding-top:5px}
.ti .ic{width:28px;height:28px;border-radius:8px;display:grid;place-items:center;color:#fff}
.ti .tt{font-size:13.5px;color:var(--ink)}.ti .ts{font-size:12.5px;color:var(--muted);margin-top:2px}
.ti .quote{margin-top:6px;background:var(--surface-2);border-radius:8px;padding:7px 10px;font-size:13px;color:var(--ink-2)}
.dayh{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--dim);font-weight:600;padding:12px 0 4px}
.facts{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:12px;overflow:hidden}
.kv4{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.kv4 > div{background:var(--surface-2);border-radius:9px;padding:9px 11px}.kv4 .l{font-size:11.5px;color:var(--muted)}.kv4 .v{font-family:var(--mono);font-size:17px;font-weight:600;color:var(--ink);margin-top:2px}
.ai{border:1px solid #DED3EE;background:#FBF9FE;border-radius:10px;padding:10px 12px}
.ai .ah{display:flex;gap:6px;align-items:center;font-size:12px;font-weight:600;color:var(--accent);margin-bottom:6px}
.ai .li{display:flex;gap:8px;align-items:flex-start;font-size:13px;color:var(--ink-2);padding:4px 0}
.ai .li .src{font-size:11.5px;color:var(--dim)}
.ai .acts{display:flex;gap:6px;margin-top:6px}
"""


def avc(name, ch, cls="", unknown=False):
    inner = ('<span class="av %s" style="background:var(--surface-2);color:var(--muted)">%s</span>' % (cls, svg('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>', 15))
             if unknown else av(name, cls))
    return '<span class="avc">%s<span class="ch %s">%s</span></span>' % (inner, ch, WA13 if ch == "wa" else IG)


def full_page(title, body, top, active):
    html = page(title, body, top=top, active=active)
    return html.replace('<div class="canvas">', '<div class="canvas full">', 1).replace("</style>", CSS + "</style>", 1)


def std_page(title, body, top, active):
    return page(title, body, top=top, active=active).replace("</style>", CSS + "</style>", 1)


# ---------------- 1. Chats inbox ----------------
def chats():
    convs = [
        ("+996 700 481 209", "wa", True, '<span class="mini new">' + NEW + ' новый клиент</span>', "Хочу первый, но можно добавить открытку?", "10:04", '<span class="mini wait">ждёт 2 мин</span>', True, True),
        ("Мария Ким", "wa", False, '<span class="mini pay">чек</span>', "Оплатила, вот чек 📎", "09:58", '<span class="ub">1</span>', True, False),
        ("@bermet_u", "ig", True, '<span class="mini new">' + NEW + ' новый</span>', "Бот: Да, доставляем в Кант — 400 сом", "09:51", '<span class="mini bot">' + BOT + ' бот</span>', False, False),
        ("+996 555 902 114", "wa", True, '<span class="mini new">' + NEW + ' новый</span>', "Бот: Выбран «Букет дня №3» · ждём адрес", "09:47", '<span class="mini bot">' + BOT + ' бот</span>', False, False),
        ("@aidana.karimova", "ig", True, "", "Сколько стоит вот этот? 📷", "09:30", '<span class="ub">2</span>', True, False),
        ("Данияр Исаев", "wa", False, "", "Подумаю до вечера, спасибо", "вчера", "", False, False),
        ("Тимур Осмонов", "wa", False, "", "Вы: Заказ №64 доставлен 🌷", "вчера", "", False, False),
        ("Алина Садыкова", "wa", False, "", "Спасибо, мама была очень рада! 🙏", "12 сен", "", False, False),
    ]
    rows = ""
    for nm, ch, unknown, badge, pv, t, right, unread, sel in convs:
        rows += ('<div class="conv%s%s">%s<div style="min-width:0"><div class="nm">%s %s</div><div class="cpv">%s</div></div>'
                 '<div class="meta"><span>%s</span>%s</div></div>'
                 % (" sel" if sel else "", " unread" if unread else "", avc(nm, ch, unknown=unknown), nm, badge, pv, t, right))
    left = ('<div class="pane"><div class="phd"><div class="row"><b class="ink" style="font-size:16px">Чаты</b><span class="spacer"></span>'
            '<span class="small muted">WhatsApp · Instagram</span></div>'
            '<div class="chips"><span class="on">Все <i class="n">14</i></span><span class="hot">Ждут ответа <i class="n">3</i></span>'
            '<span>' + BOT + ' Ведёт бот <i class="n">4</i></span><span>Мои <i class="n">5</i></span></div></div>'
            '<div style="overflow:hidden">' + rows + '</div></div>')
    thread = (
        '<div class="thread"><div class="thd">' + avc("", "wa", unknown=True) +
        '<div><div class="row"><b class="ink" style="font-size:15px">+996 700 481 209</b><span class="mini new">' + NEW + ' новый клиент</span></div>'
        '<div class="small muted" style="margin-top:2px">WhatsApp · номер заказов · пишет с 10:02</div></div>'
        '<span class="spacer"></span><span class="owner">' + av("Айгуль Садыкова", "sm") + ' Айгуль</span></div>'
        '<div class="tbody">'
        '<div class="sys">Сегодня</div>'
        '<div class="msg in">Здравствуйте! Есть букет из пионов на завтра? Бюджет до 5000<span class="t">10:02</span></div>'
        '<div class="msg bot"><div class="who">' + BOT + ' Бот</div>Здравствуйте! Это Tapme Flowers 🌷 Вот букеты дня с пионами:'
        '<div class="cards"><div><div class="ph">' + IMG + '<br>фото флориста<br>утром 08:40</div><div class="cap">Пионы ×11 · <b>4 800</b></div></div>'
        '<div><div class="ph">' + IMG + '<br>фото флориста<br>утром 08:42</div><div class="cap">Пионы и эустома · <b>5 200</b></div></div></div>'
        '<div class="qbtn"><span>Выбрать №1</span><span>Выбрать №2</span><span>Позвать менеджера</span></div><span class="t">10:02</span></div>'
        '<div class="msg in">Позвать менеджера<span class="t">10:03</span></div>'
        '<div class="sys">' + BOT + ' Бот передал диалог · Айгуль получила уведомление со звуком</div>'
        '<div class="msg in">Хочу первый, но можно добавить открытку? Это маме на день рождения, доставка на Токтогула 125, к 10 утра<span class="t">10:04</span></div>'
        '</div>'
        '<div class="comp"><div class="qr"><span>Отправить QR</span><span>Букеты дня</span><span>Шаблоны</span><span>' + I["spark"] + ' Подсказать ответ</span></div>'
        '<div class="box">Ответить в WhatsApp…<span class="sendb">' + SEND + '</span></div></div></div>')
    side = (
        '<div class="pane"><div class="side">'
        '<div class="autonew"><div class="row"><b>Клиент создан автоматически</b></div>'
        '<div style="margin-top:4px">Написал(а) впервые в 10:02 — карточка уже в «Клиентах». Имя пока неизвестно.</div>'
        '<div class="input" style="margin-top:8px">Как зовут клиента?</div></div>'
        '<div class="draft"><div class="dh"><b class="ink">Черновик заказа</b><span class="spacer"></span><span class="live"><i></i>заполняется из чата</span></div>'
        '<div class="db">'
        '<div class="field"><span class="k">Букет</span><span class="val">Пионы ×11 · 4 800 сом<span class="src">букет дня №1 · забронирован на 30 мин</span></span></div>'
        '<div class="field"><span class="k">Открытка</span><span class="val">+100 сом<span class="src q">текст открытки — уточнить</span></span></div>'
        '<div class="field"><span class="k">Повод</span><span class="val">День рождения мамы</span></div>'
        '<div class="field"><span class="k">Когда</span><span class="val">Завтра, 18 окт · 09:00–11:00<span class="src">«к 10 утра» → ближайшее окно</span></span></div>'
        '<div class="field"><span class="k">Адрес</span><span class="val">ул. Токтогула, 125<span class="src q">квартира и телефон получателя — уточнить</span></span></div>'
        '</div><div class="tot">Итого<span class="spacer"></span><span class="mono">4 900 сом</span></div></div>'
        '<span class="btn primary" style="justify-content:center;height:40px">Создать заказ и отправить QR</span>'
        '<div class="ai" style="margin-top:2px"><div class="ah">' + I["spark"] + ' Сохранить в карточку?</div>'
        '<div class="li">' + I["gift"] + '<span>Важная дата: ДР мамы — 18 октября<span class="src"> · из сообщения 10:04</span></span></div>'
        '<div class="acts"><span class="btn sm">Сохранить</span><span class="btn ghost sm">Не нужно</span></div></div>'
        '</div></div>')
    body = '<div class="inbox">' + left + thread + side + '</div>'
    return full_page("CRM · Чаты", body, "Чаты", "chats")


# ---------------- 2. Clients list ----------------
def clients():
    def row(name, ch, unknown, sub, stage, last, lt, lch, owner, orders, total, date, dsub, fresh=False, extra=""):
        own = ('<span class="owner">' + av(owner, "sm") + owner.split()[0] + '</span>') if owner != "бот" else '<span class="owner"><span class="mini bot">' + BOT + ' бот</span></span>'
        return ('<div class="tr%s"><div class="row" style="gap:11px;min-width:0">%s<div style="min-width:0"><div class="nm">%s %s</div><div class="sub">%s</div></div></div>'
                '<div>%s</div><div style="min-width:0"><div class="last">%s</div><div class="lt">%s %s</div></div>'
                '<div>%s</div><div class="num">%s<small>%s</small></div><div class="date">%s<small>%s</small></div></div>'
                % (" fresh" if fresh else "", avc(name, ch, unknown=unknown), name, extra, sub, stage, last,
                   WA13 if lch == "wa" else IG, lt, own, orders, total, date, dsub))
    S = {
        "new": '<span class="stg st-new"><i></i>Новый</span>', "talk": '<span class="stg st-talk"><i></i>В диалоге</span>',
        "ord": '<span class="stg st-ord"><i></i>Заказал</span>', "loyal": '<span class="stg st-loyal"><i></i>Постоянный</span>',
        "lost": '<span class="stg st-lost"><i></i>Давно не был</span>',
    }
    auto = '<span class="mini new">' + NEW + ' из чата</span>'
    rows = (
        row("+996 700 481 209", "wa", True, "WhatsApp · сегодня 10:02", S["new"], "Хочу первый, но можно добавить открытку?", "10:04", "wa", "Айгуль Садыкова", "0", "—", "ДР мамы · 18 окт", "найдено в чате", True, auto) +
        row("@bermet_u", "ig", True, "Instagram · сегодня 09:49", S["new"], "Доставляете в Кант?", "09:51", "ig", "бот", "0", "—", "—", "", True, auto) +
        row("+996 555 902 114", "wa", True, "WhatsApp · сегодня 09:40", S["talk"], "Бот: выбран «Букет дня №3», ждём адрес", "09:47", "wa", "бот", "0", "—", "—", "", True, auto) +
        row("Мария Ким", "wa", False, '<span class="mono">+996 555 120 404</span>', S["ord"], "Оплатила, вот чек 📎", "09:58", "wa", "Тимур Нуров", "4", "18 550", "ДР · Айжан", "20 окт") +
        row("Алина Садыкова", "wa", False, '<span class="mono">+996 555 120 400</span>', S["loyal"], "Спасибо, мама была очень рада! 🙏", "12 сен", "wa", "Айгуль Садыкова", "8", "36 450", "ДР мамы · Айжан", "18 окт · завтра") +
        row("Данияр Исаев", "wa", False, '<span class="mono">+996 555 120 403</span>', S["talk"], "Подумаю до вечера, спасибо", "вчера", "wa", "Айгуль Садыкова", "3", "13 220", "Годовщина", "20 окт") +
        row("Тимур Осмонов", "wa", False, '<span class="mono">+996 555 120 401</span>', S["loyal"], "Вы: Заказ №64 доставлен 🌷", "вчера", "wa", "Тимур Нуров", "6", "21 090", "Годовщина · Елена", "18 окт · завтра") +
        row("Бакыт Асанов", "wa", False, '<span class="mono">+996 555 120 409</span>', S["lost"], "Вы: Спасибо за заказ!", "2 июл", "wa", "Айгуль Садыкова", "2", "6 800", "—", "107 дней без заказа")
    )
    body = (
        '<div class="page-hd"><div><h1>Клиенты</h1><div class="sub">128 клиентов · 9 новых из чатов за неделю — добавились сами</div></div>'
        '<div class="spacer"></div><span class="btn">Импорт</span><span class="btn primary">Новый клиент</span></div>'
        '<div class="merge"><span class="mi">' + MERGE + '</span><div><b>Похоже, это один человек</b>'
        '<div class="small muted" style="margin-top:2px">Айдана Каримова (+996 555 120 402, WhatsApp) и @aidana.karimova в Instagram — одинаковое имя, писали про один заказ</div></div>'
        '<span class="spacer"></span><span class="btn sm">Это разные люди</span><span class="btn primary sm">Объединить</span></div>'
        '<div class="stages"><span class="on">Все <i class="n">128</i></span><span>Новые <i class="n">9</i></span><span>В диалоге <i class="n">6</i></span>'
        '<span>Заказали <i class="n">82</i></span><span>Постоянные <i class="n">31</i></span><span>Давно не были <i class="n">12</i></span>'
        '<span class="spacer"></span><span style="color:var(--muted)">Канал: все ' + I["chev"] + '</span><span style="color:var(--muted)">Ответственный: все ' + I["chev"] + '</span></div>'
        '<div class="tbl"><div class="th"><span>Клиент</span><span>Этап</span><span>Последнее сообщение</span><span>Ответственный</span>'
        '<span style="text-align:right">Заказов · сом</span><span>Ближайшая дата</span></div>' + rows + '</div>')
    return std_page("CRM · Клиенты", body, "Клиенты", "clients")


# ---------------- 3. Client card ----------------
def card():
    def ti(tm, color, icon, title, sub="", quote=""):
        return ('<div class="ti"><span class="tm">%s</span><span class="ic" style="background:%s">%s</span><div><div class="tt">%s</div>%s%s</div></div>'
                % (tm, color, icon, title, ('<div class="ts">%s</div>' % sub) if sub else "", ('<div class="quote">%s</div>' % quote) if quote else ""))
    wa, ig, acc, ok, warn = "var(--wa)", "#C13584", "var(--accent)", "var(--ok)", "var(--warn)"
    feed = (
        '<div class="dayh">Сегодня</div>' +
        ti("09:42", wa, WA13, "Напоминание отправлено", "сценарий «День рождения · за 1 день» · отправила Айгуль") +
        ti("10:12", wa, WA13, "Алина написала в WhatsApp", "номер заказов · ответила Айгуль",
           "Добрый день! Маме завтра 60 — хочу как в прошлом году, но побольше. Без лилий, у неё аллергия.") +
        ti("10:15", acc, I["bag"], "Заказ №67 создан из переписки", "«Нежность» XL · 5 200 сом · завтра 09:00–11:00 · доставка") +
        ti("10:21", warn, I["check"], "Чек об оплате прикреплён к заказу", "задача «Проверить оплату» · Айгуль") +
        '<div class="dayh">12 сентября</div>' +
        ti("18:03", ig, IG, "Сообщение в Instagram Direct", "@alina.sadykova", "Спасибо, мама была очень рада! 🙏") +
        ti("11:30", ok, I["check"], "Заказ №49 вручён", "Пион ×11 → Айжан · самовывоз · 6 350 сом")
    )
    left = ('<div class="feed"><div class="ftabs"><span class="on">Всё</span><span>Переписка <i class="n">46</i></span>'
            '<span>Заказы <i class="n">8</i></span><span>Получатели и даты <i class="n">4</i></span><span>Заметки</span></div>'
            '<div class="tl">' + feed + '</div>'
            '<div class="comp"><div class="box">Написать Алине в WhatsApp…<span class="sendb">' + SEND + '</span></div></div></div>')
    right = (
        '<div class="facts"><div class="kv4"><div><div class="l">Заказов</div><div class="v">8</div></div>'
        '<div><div class="l">Сумма</div><div class="v">36 450</div></div><div><div class="l">Средний чек</div><div class="v">4 556</div></div>'
        '<div><div class="l">Клиент с</div><div class="v">2024</div></div></div>'
        '<div class="ai"><div class="ah">' + I["spark"] + ' Узнали из переписки</div>'
        '<div class="li"><span style="color:var(--crit)">' + I["warn"] + '</span><span><b>Без лилий</b> — у мамы аллергия<span class="src"> · сегодня 10:12</span></span></div>'
        '<div class="li">' + I["gift"] + '<span>Маме 18 октября исполняется 60 — юбилей<span class="src"> · сегодня 10:12</span></span></div>'
        '<div class="li">' + I["heart"] + '<span>Любит пионы и «Нежность»<span class="src"> · 3 заказа</span></span></div>'
        '<div class="acts"><span class="btn sm">Сохранить в заметки</span><span class="btn ghost sm">Скрыть</span></div></div>'
        '<div><div class="lbl">Получатели и важные даты</div>'
        '<div class="field"><span class="k">Айжан · мама</span><span class="val">ДР 18 окт · завтра<span class="src">ул. Цветочная, 1, кв. 1</span></span></div>'
        '<div class="field"><span class="k">Елена · коллега</span><span class="val">Годовщина 23 окт<span class="src">ул. Цветочная, 1, кв. 2</span></span></div></div>'
        '<div><div class="lbl">Заметки</div><div class="small" style="color:var(--ink-2);line-height:1.5">Звонить после 11. Оплачивает переводом MBank.</div></div>'
        '</div>')
    hd = ('<div class="cardhd">' + av("Алина Садыкова", "lg") +
          '<div><div class="row"><h2 style="font-size:20px">Алина Садыкова</h2><span class="stg st-loyal"><i></i>Постоянный</span><span class="tag acc">VIP</span></div>'
          '<div class="row" style="margin-top:7px"><span class="chan"><span class="d" style="background:var(--wa)">' + WA13 + '</span><span class="mono">+996 555 120 400</span></span>'
          '<span class="chan"><span class="d" style="background:#C13584">' + IG + '</span>@alina.sadykova</span>'
          '<span class="small muted">объединено 12 сен</span></div></div><span class="spacer"></span>'
          '<span class="owner">Ответственный ' + av("Айгуль Садыкова", "sm") + ' Айгуль ' + I["chev"] + '</span>'
          '<span class="btn wa sm">' + WA13 + ' Чат</span><span class="btn primary sm">Новый заказ</span></div>')
    body = ('<div class="row small muted" style="margin-bottom:10px">' + I["back"] + ' Клиенты</div>' + hd +
            '<div class="cgrid">' + left + right + '</div>')
    return std_page("CRM · Карточка клиента", body, "Клиенты", "clients")


# ---------------- 4. Mobile ----------------
def mobile():
    css = """
    body{background:#E9ECE6;margin:0}.stage{width:1440px;height:900px;display:flex;gap:56px;align-items:center;justify-content:center;font-family:var(--sans);color:var(--ink-2);font-size:14px}
    .phn{width:390px;height:812px;border-radius:44px;background:#111;padding:12px;box-shadow:0 30px 60px rgba(15,42,34,.25)}
    .scr{width:100%;height:100%;border-radius:34px;background:var(--surface);overflow:hidden;display:flex;flex-direction:column}
    .sb{height:44px;display:flex;align-items:center;justify-content:space-between;padding:0 26px;font-weight:600;font-size:14px;color:#111}
    .capt{width:300px;font-size:15px;line-height:1.5}.capt h2{font-size:22px;margin-bottom:10px}
    .sheet{border-top:1px solid var(--border);background:#fff;padding:12px 16px 24px;box-shadow:0 -8px 20px rgba(20,28,24,.06)}
    .push{margin:0 12px 8px;background:rgba(255,255,255,.92);border:1px solid var(--border);border-radius:16px;padding:10px 12px;display:flex;gap:10px;align-items:center;box-shadow:0 8px 20px rgba(0,0,0,.12)}
    """
    convs = ""
    for nm, ch, unknown, badge, pv, t, right in [
        ("+996 700 481 209", "wa", True, '<span class="mini new">новый</span>', "Хочу первый, но можно добавить открытку?", "10:04", '<span class="mini wait">2 мин</span>'),
        ("Мария Ким", "wa", False, '<span class="mini pay">чек</span>', "Оплатила, вот чек 📎", "09:58", '<span class="ub">1</span>'),
        ("@bermet_u", "ig", True, '<span class="mini new">новый</span>', "Бот: Да, доставляем в Кант", "09:51", '<span class="mini bot">бот</span>'),
        ("+996 555 902 114", "wa", True, '<span class="mini new">новый</span>', "Бот: ждём адрес", "09:47", '<span class="mini bot">бот</span>'),
        ("@aidana.karimova", "ig", True, "", "Сколько стоит вот этот? 📷", "09:30", '<span class="ub">2</span>'),
        ("Данияр Исаев", "wa", False, "", "Подумаю до вечера, спасибо", "вчера", ""),
        ("Тимур Осмонов", "wa", False, "", "Вы: Заказ №64 доставлен 🌷", "вчера", ""),
    ]:
        convs += ('<div class="conv">%s<div style="min-width:0"><div class="nm">%s %s</div><div class="cpv">%s</div></div>'
                  '<div class="meta"><span>%s</span>%s</div></div>' % (avc(nm, ch, unknown=unknown), nm, badge, pv, t, right))
    p1 = ('<div class="phn"><div class="scr"><div class="sb"><span>10:05</span><span>●●● ▮</span></div>'
          '<div class="push"><span class="avc"><span class="av sm">TF</span></span><div style="min-width:0"><div class="small b ink">Tapme · клиент зовёт менеджера</div>'
          '<div class="small muted" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">+996 700 481 209: Хочу первый, но можно…</div></div></div>'
          '<div class="phd" style="padding-top:6px"><div class="row"><b class="ink" style="font-size:22px">Чаты</b></div>'
          '<div class="chips"><span class="on">Все 14</span><span class="hot">Ждут 3</span><span>Бот 4</span><span>Мои 5</span></div></div>'
          '<div style="flex:1;overflow:hidden">' + convs + '</div></div></div>')
    p2 = ('<div class="phn"><div class="scr" style="background:#F1EFEA"><div class="sb" style="background:#fff"><span>10:05</span><span>●●● ▮</span></div>'
          '<div class="thd" style="padding:8px 14px">' + I["back"] + avc("", "wa", unknown=True) + '<div><b class="ink">+996 700 481 209</b><div class="small muted">новый клиент · WhatsApp</div></div></div>'
          '<div class="tbody" style="padding:12px 14px">'
          '<div class="msg bot" style="max-width:86%"><div class="who">' + BOT + ' Бот</div>Вот букеты дня с пионами: №1 — 4 800, №2 — 5 200<span class="t">10:02</span></div>'
          '<div class="sys">Бот передал диалог · Айгуль</div>'
          '<div class="msg in" style="max-width:86%">Хочу первый, но можно добавить открытку? Это маме на день рождения, доставка на Токтогула 125, к 10 утра<span class="t">10:04</span></div>'
          '</div>'
          '<div class="sheet"><div class="row"><b class="ink">Черновик заказа</b><span class="spacer"></span><span class="live"><i></i>из чата</span></div>'
          '<div class="small" style="margin-top:6px;color:var(--ink-2);line-height:1.5">Пионы ×11 + открытка · завтра 09:00–11:00 · Токтогула, 125</div>'
          '<div class="small" style="color:var(--warn);margin-top:2px">уточнить: текст открытки, квартира</div>'
          '<div class="row" style="margin-top:10px;gap:8px"><span class="btn primary" style="flex:1;justify-content:center;height:44px">Создать · 4 900 сом</span>'
          '<span class="btn" style="height:44px">QR</span></div>'
          '<div class="box" style="margin-top:10px;display:flex;align-items:center;border:1px solid var(--border-2);border-radius:10px;height:42px;padding:0 6px 0 12px;color:var(--dim)">Ответить…<span class="sendb">' + SEND + '</span></div></div></div></div>')
    cap = ('<div class="capt"><h2>На телефоне менеджера</h2><p class="muted">Push со звуком, когда клиент зовёт менеджера или прислал чек. '
           'Ответ — прямо из CRM с номера заказов; черновик заказа собирается внизу экрана.</p></div>')
    head = page("x", "", top="", active="chats").split("<body>")[0]
    return head.replace("</style>", CSS + css + "</style>", 1) + '<body><div class="stage">' + cap + p1 + p2 + '</div></body></html>'


OUT = {"1-chats.html": chats(), "2-clients.html": clients(), "3-client-card.html": card(), "4-mobile.html": mobile()}
for name, html in OUT.items():
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", name)
