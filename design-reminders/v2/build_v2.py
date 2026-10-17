# -*- coding: utf-8 -*-
"""Reminders redesign v2: three main-screen options, scenario settings, mobile.

Reuses tokens and rail icons from ../build.py so mockups match the CRM.
Run: python3 build_v2.py  ->  writes *.html next to this file.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "build.py"), encoding="utf-8").read()
ns = {}
exec(src.split("# ---------- A. Очередь (Main) ----------")[0], ns)
CSS, ICONS, BRAND_SVG, SEARCH_SVG, WA_SVG = (
    ns["CSS"], ns["ICONS"], ns["BRAND_SVG"], ns["SEARCH_SVG"], ns["WA_SVG"]
)


def svg(path, size=16, sw=1.8):
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{path}</svg>'
    )


I = {
    "gear": svg('<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>', 15),
    "clock": svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>', 14),
    "skip": svg('<path d="M5 5l14 14M19 5L5 19"/>', 13),
    "more": svg('<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>', 16, 2.4),
    "next": svg('<path d="M5 12h14M13 6l6 6-6 6"/>', 15),
    "back": svg('<path d="M19 12H5M11 6l-6 6 6 6"/>', 15),
    "spark": svg('<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>', 14),
    "gift": svg('<rect x="3" y="8" width="18" height="13" rx="2"/><path d="M12 8v13M3 12h18M12 8c-2-3-6-3-6-.5S9 8 12 8zm0 0c2-3 6-3 6-.5S15 8 12 8z"/>', 14),
    "heart": svg('<path d="M20.8 5.6a5 5 0 0 0-7.1 0L12 7.3l-1.7-1.7a5 5 0 0 0-7.1 7.1L12 21.5l8.8-8.8a5 5 0 0 0 0-7.1z"/>', 14),
    "cal": svg('<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>', 14),
    "repeat": svg('<path d="M17 2l4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>', 14),
    "check": svg('<path d="M5 12l5 5L20 7"/>', 13, 2.4),
    "plus": svg('<path d="M12 5v14M5 12h14"/>', 14, 2),
    "moon": svg('<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>', 14),
    "shield": svg('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>', 14),
    "pause": svg('<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>', 14),
    "chev": svg('<path d="M6 9l6 6 6-6"/>', 14),
    "phone": svg('<rect x="6" y="2" width="12" height="20" rx="3"/><path d="M11 18h2"/>', 14),
    "warn": svg('<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18h.01"/>', 13),
    "bag": svg('<path d="M6 7h12l1 14H5z"/><path d="M9 7a3 3 0 0 1 6 0"/>', 14),
}
WA = svg('<path d="M21 12a9 9 0 0 1-13.4 7.8L3 21l1.3-4.5A9 9 0 1 1 21 12z"/>', 15, 2)

EXTRA = """
.canvas{padding:18px 22px 0}
.page-hd h1{font-size:22px}
.btn svg{flex:none}
.btn.wa{background:var(--wa);color:#fff;border-color:var(--wa)}
.btn.wa-soft{background:var(--wa-bg);color:var(--wa);border-color:transparent}
.btn.lg{height:44px;padding:0 18px;font-size:15px;border-radius:10px}
.icon-btn{width:30px;height:30px;border-radius:8px;display:inline-grid;place-items:center;color:var(--muted);border:1px solid var(--border);background:#fff}
.today{display:grid;grid-template-columns:auto 1fr auto;gap:24px;align-items:center;padding:14px 18px;background:var(--surface);border:1px solid var(--border);border-radius:12px;margin-bottom:14px}
.today .big{font-family:var(--mono);font-size:30px;font-weight:600;color:var(--ink);line-height:1}
.today .big small{font-family:var(--sans);font-size:14px;color:var(--muted);font-weight:500}
.today .bar{height:8px;border-radius:4px;background:var(--surface-3);overflow:hidden}.today .bar i{display:block;height:100%;background:var(--wa)}
.today .facts{display:flex;gap:18px;margin-top:8px;font-size:13px;color:var(--muted)}.today .facts b{color:var(--ink);font-weight:600}
.tabs{display:flex;gap:2px;border-bottom:1px solid var(--border);margin-bottom:0}
.tabs span{padding:10px 14px;font-weight:500;color:var(--muted);border-bottom:2px solid transparent;margin-bottom:-1px;display:inline-flex;gap:7px;align-items:center}
.tabs span.on{color:var(--ink);border-bottom-color:var(--ink)}
.tabs .n{font-family:var(--mono);font-size:11px;background:var(--surface-2);border-radius:999px;padding:1px 7px;color:var(--muted)}
.tabs span.on .n{background:var(--ink);color:#fff}
.list{background:var(--surface);border:1px solid var(--border);border-radius:0 0 12px 12px;border-top:0;overflow:hidden}
.grp{display:flex;align-items:center;gap:8px;padding:9px 18px 7px;font-size:11.5px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);background:var(--surface-2);border-top:1px solid var(--border)}
.grp:first-child{border-top:0}.grp.hot{color:var(--crit)}.grp .gn{font-family:var(--mono);font-weight:500}
.rrow{display:grid;grid-template-columns:auto minmax(0,1fr) 150px auto;gap:14px;align-items:center;padding:10px 18px;border-top:1px solid var(--border)}
.grp + .rrow{border-top:0}
.rrow .nm{font-weight:600;color:var(--ink)}.rrow .why{font-size:13px;color:var(--ink-2)}
.rrow .msg{font-size:12.5px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px}
.rrow .past{font-size:12px;color:var(--muted);line-height:1.35}.rrow .past b{color:var(--ink-2);font-weight:500;font-family:var(--mono)}
.rrow .acts{display:flex;gap:6px;align-items:center}
.rrow.sent{background:#FAFBF9}.rrow.sent .nm{color:var(--ink-2)}
.when{font-family:var(--mono);font-size:12px;font-weight:500;border-radius:6px;padding:2px 7px;background:var(--surface-2);color:var(--ink-2)}
.when.hot{background:var(--crit-bg);color:var(--crit)}.when.soon{background:var(--warn-bg);color:var(--warn)}
.note{font-size:12px;color:var(--dim);display:flex;gap:6px;align-items:center}
/* option 2 */
.split{display:grid;grid-template-columns:400px minmax(0,1fr);gap:14px;height:776px}
.qcol{background:var(--surface);border:1px solid var(--border);border-radius:12px;display:flex;flex-direction:column;overflow:hidden}
.qtop{padding:14px 16px 12px;border-bottom:1px solid var(--border)}
.qrow{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;padding:9px 16px;border-top:1px solid var(--border)}
.grp + .qrow{border-top:0}
.qrow .nm{font-weight:500;color:var(--ink);font-size:13.5px}.qrow .why{font-size:12px;color:var(--muted)}
.qrow.sel{background:var(--accent-bg);box-shadow:inset 3px 0 0 var(--accent)}
.qrow.done .nm{color:var(--dim);text-decoration:line-through;text-decoration-color:var(--border-2)}
.dot-ok{width:18px;height:18px;border-radius:50%;background:var(--ok);display:inline-grid;place-items:center;color:#fff}
.focus{background:var(--surface);border:1px solid var(--border);border-radius:12px;display:grid;grid-template-columns:minmax(0,1fr);grid-template-rows:auto 1fr auto;overflow:hidden;min-width:0}
.fhd{display:flex;gap:14px;align-items:center;padding:16px 22px;border-bottom:1px solid var(--border)}
.fbd{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:22px;padding:18px 22px;min-height:0}
.reason{display:flex;gap:12px;align-items:flex-start;padding:14px 16px;border-radius:12px;background:var(--crit-bg)}
.reason .ri{width:34px;height:34px;border-radius:9px;background:#fff;color:var(--crit);display:grid;place-items:center;flex:none}
.reason b{color:var(--ink);font-size:15px}
.hist{border-top:1px solid var(--border);margin-top:16px;padding-top:14px}
.hrow{display:grid;grid-template-columns:86px minmax(0,1fr) auto;gap:10px;font-size:13px;padding:6px 0}
.hrow .d{font-family:var(--mono);color:var(--muted);font-size:12px}.hrow .a{font-family:var(--mono);color:var(--ink)}
.hint{display:flex;gap:8px;align-items:flex-start;background:var(--accent-bg);color:var(--accent-2);border-radius:10px;padding:10px 12px;font-size:13px;margin-top:12px}
.ffoot{display:flex;gap:10px;align-items:center;padding:14px 22px;border-top:1px solid var(--border);background:#FBFCFA}
.kbdx{font-family:var(--mono);font-size:11px;padding:1px 6px;border:1px solid var(--border);border-bottom-width:2px;border-radius:5px;color:var(--muted);background:#fff}
.waphone{background:#ECE5DD;border-radius:14px;padding:14px;display:flex;flex-direction:column;gap:8px;height:100%}
.wahd{display:flex;align-items:center;gap:8px;font-size:12px;color:#54656F}
.bubble{background:#D9FDD3;max-width:100%;border-radius:10px 10px 2px 10px;align-self:flex-end;box-shadow:0 1px 1px rgba(0,0,0,.08)}
.bubble.in{background:#fff;border-radius:10px 10px 10px 2px;align-self:flex-start}
.var{display:inline-flex;align-items:center;height:20px;padding:0 6px;border-radius:5px;background:var(--accent-bg);color:var(--accent);font-size:12.5px;font-weight:500;margin:0 1px}
.tpl{display:flex;gap:6px;flex-wrap:wrap}
.tpl span{height:28px;padding:0 10px;border-radius:999px;border:1px solid var(--border);font-size:12.5px;display:inline-flex;align-items:center;gap:6px;background:#fff;color:var(--ink-2)}
.tpl span.on{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
/* option 3 */
.board{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;align-items:start}
.col{background:var(--surface-2);border-radius:12px;padding:8px;min-height:600px}
.col-hd{display:flex;align-items:center;gap:8px;padding:6px 8px 10px;font-weight:600;color:var(--ink);font-size:13.5px}
.col-hd .n{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--muted);font-weight:500}
.col-hd .sw{width:8px;height:8px;border-radius:50%}
.kc{background:#fff;border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:8px}
.kc .nm{font-weight:500;color:var(--ink);font-size:13.5px}.kc .why{font-size:12px;color:var(--muted);margin-top:2px}
.kc .ft{display:flex;gap:6px;align-items:center;margin-top:9px}
.funnel{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0;background:var(--surface);border:1px solid var(--border);border-radius:12px;margin-bottom:14px;overflow:hidden}
.funnel div{padding:12px 16px;border-left:1px solid var(--border)}.funnel div:first-child{border-left:0}
.funnel .l{font-size:12px;color:var(--muted)}.funnel .v{font-family:var(--mono);font-size:24px;font-weight:600;color:var(--ink);margin-top:2px}
.funnel .v small{font-family:var(--sans);font-size:12px;color:var(--ok);font-weight:500;margin-left:6px}
/* settings */
.set{display:grid;grid-template-columns:280px minmax(0,1fr) 310px;gap:14px;height:774px}
.scol{background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.sc{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;padding:11px 14px;border-top:1px solid var(--border)}
.grp + .sc{border-top:0}
.sc .nm{font-weight:500;color:var(--ink);font-size:13.5px}.sc .why{font-size:12px;color:var(--muted);margin-top:1px}
.sc.sel{background:var(--accent-bg);box-shadow:inset 3px 0 0 var(--accent)}
.sc .ic{width:30px;height:30px;border-radius:8px;display:grid;place-items:center;background:var(--surface-2);color:var(--ink-2)}
.sw-on,.sw-off{width:30px;height:18px;border-radius:9px;position:relative;display:inline-block;flex:none}
.sw-on{background:var(--ok)}.sw-off{background:var(--surface-3)}
.sw-on::after,.sw-off::after{content:"";position:absolute;top:2px;width:14px;height:14px;border-radius:50%;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.2)}
.sw-on::after{right:2px}.sw-off::after{left:2px}
.ed{background:var(--surface);border:1px solid var(--border);border-radius:12px;display:flex;flex-direction:column;overflow:hidden}
.edb{padding:16px 20px;display:flex;flex-direction:column;gap:16px;overflow:hidden}
.lbl{font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px}
.sentence{display:flex;flex-wrap:wrap;align-items:center;gap:7px;font-size:15px;color:var(--ink)}
.slot{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 10px;border-radius:8px;border:1px solid var(--border-2);background:#fff;font-weight:500}
.slot.num{font-family:var(--mono)}
.steps{display:flex;gap:6px}
.steps span{height:32px;padding:0 12px;border-radius:8px;border:1px solid var(--border);display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--ink-2);background:#fff}
.steps span.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.txt{border:1px solid var(--border-2);border-radius:10px;padding:12px 14px;font-size:14.5px;line-height:1.6;color:var(--ink);min-height:118px;background:#fff}
.ins{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--muted)}
.ins .var{cursor:pointer}
.assist{display:flex;flex-direction:column;gap:10px}
.abox{border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.chks{display:flex;flex-wrap:wrap;gap:6px 14px}.chk-l{display:flex;gap:6px;align-items:center;font-size:12.5px;color:var(--ink-2)}
.chk-l .ok{color:var(--ok)}.chk-l .wn{color:var(--warn)}
.gen{display:flex;flex-wrap:wrap;gap:6px}
.gen span{display:flex;gap:8px;align-items:center;height:32px;padding:0 10px;border-radius:8px;background:var(--surface-2);font-size:13px;color:var(--ink-2)}
.rules{padding:12px 14px;border-top:1px solid var(--border);margin-top:auto;background:#FBFCFA}
.rule{display:flex;gap:9px;align-items:center;font-size:12.5px;color:var(--ink-2);padding:4px 0}
.rule .v{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--ink)}
.pv{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:10px}
"""

NAV = [("orders", "Заказы", "12"), ("clients", "Клиенты", ""), ("reminders", "Напоминания", "22"),
       ("deliveries", "Доставка", "9"), ("settings", "Настройки", "")]


def rail(active="reminders"):
    items = "".join(
        '<div class="nav-item%s">%s%s%s</div>' % (" on" if k == active else "", ICONS[k], n,
                                                 ('<span class="cnt">%s</span>' % c) if c else "")
        for k, n, c in NAV)
    return ('<div class="rail"><div class="brand"><div class="brand-mark">' + BRAND_SVG +
            '</div><div><div class="brand-name">Tapme Flowers</div><div class="brand-sub">Кабинет магазина</div></div></div>'
            '<div class="nav">' + items + '</div><div class="rail-foot"><span class="av">TF</span><div>'
            '<div class="shop-n">Tapme Flowers</div><div class="shop-c">Контакты магазина</div></div></div></div>')


def topbar(title):
    return ('<div class="topbar"><div><h1>' + title + '</h1></div><div class="search">' + SEARCH_SVG +
            '<span>Телефон, имя или № заказа</span><span class="kbd">/</span></div>'
            '<div class="spacer"></div><span class="btn primary">+ Заказ</span>'
            '<div class="ubtn"><span class="av">АС</span><div><div class="un">Айгуль</div><div class="ur">Менеджер</div></div></div></div>')


def page(title, body, top="Напоминания", active="reminders"):
    return ('<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>' + title + '</title>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">'
            '<style>' + CSS + EXTRA + '</style></head><body><div class="root">' + rail(active) +
            '<div class="main">' + topbar(top) + '<div class="canvas">' + body + '</div></div></div></body></html>')


def av(n, cls=""):
    return '<span class="av %s">%s</span>' % (cls, "".join(w[0] for w in n.split()[:2]).upper())


def v(name):
    return '<span class="var">' + name + '</span>'


# ---------------- shared data ----------------
QUEUE = [
    ("hot", "Завтра", [
        ("Алина Садыкова", "День рождения мамы · Айжан", "18 окт", "hot", "6 350 сом", "12 сен",
         "Алина, здравствуйте! Это Tapme Flowers. Завтра у мамы Айжан день рождения — собрать похожий букет, как в прошлом году?"),
        ("Тимур Осмонов", "Годовщина свадьбы · Елена", "18 окт", "hot", "4 200 сом", "3 авг",
         "Тимур, добрый день! Завтра годовщина с Еленой. Успеем собрать и доставить к нужному часу — подобрать варианты?"),
    ]),
    ("", "Через 3 дня", [
        ("Мария Ким", "День рождения · Айжан", "20 окт", "soon", "6 350 сом", "29 сен",
         "Мария, здравствуйте! Через три дня день рождения у Айжан. Забронировать доставку на утро?"),
        ("Данияр Исаев", "Годовщина · Нурзат", "20 окт", "soon", "3 500 сом", "14 июл",
         "Данияр, через три дня годовщина с Нурзат. Подберём что-то особенное к вашей дате?"),
    ]),
    ("", "Через неделю", [
        ("Айдана Каримова", "День рождения мамы · Елена", "24 окт", "", "2 050 сом", "1 сен",
         "Айдана, напоминаем: через неделю день рождения мамы. Успеем собрать что-то особенное — подобрать варианты?"),
        ("Руслан Абдраев", "День рождения · Анастасия", "24 окт", "", "5 800 сом", "18 авг",
         "Руслан, через неделю день рождения Анастасии. Подобрать композицию в коробке, как в прошлый раз?"),
    ]),
    ("", "Давно не заказывали", [
        ("Бакыт Асанов", "107 дней без заказа", "с 2 июл", "", "3 500 сом", "2 июл",
         "Бакыт, здравствуйте! Давно вас не видели. На этой неделе свежие пионы и гортензии — прислать фото?"),
    ]),
]


def wa_btn(cls="wa sm", label="WhatsApp"):
    return '<span class="btn %s">%s %s</span>' % (cls, WA, label)


# ---------------- Option 1: list of the day ----------------
def option1():
    rows = ""
    for gcls, gname, items in QUEUE:
        rows += '<div class="grp %s">%s<span class="gn">· %d</span></div>' % (gcls, gname, len(items))
        for nm, why, when, wcls, last, lastd, msg in items:
            rows += (
                '<div class="rrow">' + av(nm) +
                '<div><div class="row"><span class="nm">' + nm + '</span><span class="when ' + wcls + '">' + when +
                '</span><span class="why">' + why + '</span></div><div class="msg">' + msg + '</div></div>'
                '<div class="past">Прошлый заказ<br><b>' + last + '</b> · ' + lastd + '</div>'
                '<div class="acts">' + wa_btn() + '<span class="btn ghost sm">' + I["clock"] + ' Позже</span>'
                '<span class="icon-btn">' + I["more"] + '</span></div></div>')
    rows += ('<div class="rrow sent">' + av("Нурия Султанова") +
             '<div><div class="row"><span class="nm">Нурия Султанова</span><span class="when">17 окт</span>'
             '<span class="why">День рождения · Анастасия</span></div><div class="msg">Отправлено в 09:42 · ждём ответа</div></div>'
             '<div class="past">Прошлый заказ<br><b>3 500 сом</b> · 20 авг</div>'
             '<div class="acts"><span class="btn sm">Ответила</span><span class="btn sm">' + I["bag"] + ' Заказала</span>'
             '<span class="icon-btn">' + I["more"] + '</span></div></div>')
    body = (
        '<div class="page-hd"><div><h1>Кому написать сегодня</h1><div class="sub">Суббота, 17 октября · '
        'список собирается сам каждое утро</div></div><div class="spacer"></div>'
        '<span class="btn">' + I["gear"] + ' Настройки напоминаний</span></div>'
        '<div class="today"><div class="big">6 <small>из 28 отправлено</small></div>'
        '<div><div class="bar"><i style="width:21%"></i></div><div class="facts"><span>Ждём ответа <b>6</b></span>'
        '<span>Ответили <b>3</b></span><span>Заказали за неделю <b>4</b> · <b>18 200 сом</b></span></div></div>'
        '<div class="note">' + I["clock"] + ' осталось ≈ 10 минут</div></div>'
        '<div class="tabs" style="background:var(--surface);border:1px solid var(--border);border-radius:12px 12px 0 0;padding:0 8px">'
        '<span class="on">Написать <span class="n">22</span></span><span>Ждём ответа <span class="n">6</span></span>'
        '<span>Ответили <span class="n">3</span></span><span>Заказали <span class="n">4</span></span>'
        '<span>Пропущено <span class="n">2</span></span><div class="spacer"></div>'
        '<span style="color:var(--muted)">Все поводы ' + I["chev"] + '</span></div>'
        '<div class="list">' + rows + '</div>')
    return page("Вариант 1 · Список дня", body)


# ---------------- Option 2: queue + client card ----------------
def option2():
    q = ""
    first = True
    for gcls, gname, items in QUEUE:
        q += '<div class="grp %s">%s<span class="gn">· %d</span></div>' % (gcls, gname, len(items))
        for nm, why, when, wcls, *_ in items:
            q += ('<div class="qrow%s">' % (" sel" if first else "") + av(nm, "sm") +
                  '<div><div class="nm">' + nm + '</div><div class="why">' + why + '</div></div>'
                  '<span class="when ' + wcls + '">' + when + '</span></div>')
            first = False
    q += ('<div class="grp">Готово сегодня<span class="gn">· 6</span></div>'
          '<div class="qrow done"><span class="dot-ok">' + I["check"] + '</span><div><div class="nm">Нурия Султанова</div>'
          '<div class="why">Написали в 09:42</div></div><span class="when">17 окт</span></div>'
          '<div class="qrow done"><span class="dot-ok">' + I["check"] + '</span><div><div class="nm">Анна Иванова</div>'
          '<div class="why">Написали в 09:38</div></div><span class="when">19 окт</span></div>')
    left = ('<div class="qcol"><div class="qtop"><div class="row"><b class="ink" style="font-size:15px">Очередь на сегодня</b>'
            '<span class="spacer"></span><span class="mono ink b">6 / 28</span></div>'
            '<div class="prog" style="height:6px;margin-top:10px"><i style="width:21%;background:var(--wa)"></i></div>'
            '<div class="row small muted" style="margin-top:8px">' + I["clock"] + ' ≈ 10 минут · ответили 3 · заказали 4</div></div>'
            '<div style="overflow:hidden">' + q + '</div></div>')
    msg = ('Алина, здравствуйте! Это Tapme Flowers 🌷 Завтра у мамы Айжан день рождения. '
           'В прошлом году вы дарили «Нежность» — собрать похожий или что-то новое? Доставим к удобному часу.')
    right = (
        '<div class="focus"><div class="fhd">' + av("Алина Садыкова", "lg") +
        '<div><div class="row"><h2 style="font-size:18px">Алина Садыкова</h2><span class="tag acc">VIP</span></div>'
        '<div class="small muted" style="margin-top:3px"><span class="mono">+996 555 120 400</span> · клиент с 2024 · 7 заказов</div></div>'
        '<div class="spacer"></div><span class="btn sm">Карточка клиента</span></div>'
        '<div class="fbd"><div>'
        '<div class="reason"><span class="ri">' + I["gift"] + '</span><div><b>Завтра день рождения мамы — Айжан</b>'
        '<div class="small muted" style="margin-top:3px">Суббота, 18 октября · напоминание «за 1 день»</div></div></div>'
        '<div class="hint">' + I["spark"] + '<span>Год назад на этот же повод Алина заказывала букет «Нежность» за 3 500 сом — предложите похожий.</span></div>'
        '<div class="hist"><div class="lbl">Заказы на этот повод и последние</div>'
        '<div class="hrow"><span class="d">18.10.2025</span><span>Букет «Нежность» → Айжан · доставка</span><span class="a">3 500</span></div>'
        '<div class="hrow"><span class="d">12.09.2026</span><span>Пион ×11, упаковка → Айжан · самовывоз</span><span class="a">6 350</span></div>'
        '<div class="hrow"><span class="d">14.02.2026</span><span>Роза красная ×15 → себе</span><span class="a">4 100</span></div></div>'
        '<div style="margin-top:16px"><div class="lbl">Текст можно поправить перед отправкой</div>'
        '<div class="tpl"><span class="on">За 1 день</span><span>Короче</span><span>С фото букетов дня</span><span>' + I["spark"] + ' Ещё вариант</span></div></div>'
        '</div>'
        '<div class="waphone"><div class="wahd">' + av("Алина Садыкова", "sm") + '<b style="color:#111">Алина Садыкова</b><span class="spacer"></span>так увидит клиент</div>'
        '<div style="flex:1"></div>'
        '<div class="bubble in" style="padding:8px 10px;font-size:13px;max-width:80%">Спасибо, мама была очень рада! 🙏<span class="time">12.09</span></div>'
        '<div class="bubble" style="padding:8px 10px;font-size:13.5px;line-height:1.45">' + msg + '<span class="time">сейчас</span></div></div>'
        '</div>'
        '<div class="ffoot">' + wa_btn("wa lg", "Открыть WhatsApp") +
        '<span class="small muted">«Написали» отметим сами</span><span class="spacer"></span>'
        '<span class="btn ghost sm">' + I["clock"] + ' Завтра</span><span class="btn ghost sm">' + I["skip"] + ' Не в этом году</span>'
        '<span class="btn sm">Следующий ' + I["next"] + '</span></div></div>')
    body = '<div class="split">' + left + right + '</div>'
    return page("Вариант 2 · Очередь и карточка", body)


# ---------------- Option 3: weekly board ----------------
def option3():
    def kc(nm, why, when, wcls, foot):
        return ('<div class="kc"><div class="row">' + av(nm, "sm") + '<span class="nm">' + nm + '</span></div>'
                '<div class="why">' + why + '</div><div class="ft"><span class="when ' + wcls + '">' + when + '</span>' + foot + '</div></div>')
    cols = [
        ("Написать", "var(--accent)", "22", [
            kc("Алина Садыкова", "ДР мамы · Айжан", "завтра", "hot", '<span class="spacer"></span>' + wa_btn("wa-soft xs", "")),
            kc("Тимур Осмонов", "Годовщина · Елена", "завтра", "hot", '<span class="spacer"></span>' + wa_btn("wa-soft xs", "")),
            kc("Мария Ким", "ДР · Айжан", "20 окт", "soon", '<span class="spacer"></span>' + wa_btn("wa-soft xs", "")),
            kc("Данияр Исаев", "Годовщина · Нурзат", "20 окт", "soon", '<span class="spacer"></span>' + wa_btn("wa-soft xs", "")),
            kc("Бакыт Асанов", "107 дней без заказа", "давно", "", '<span class="spacer"></span>' + wa_btn("wa-soft xs", "")),
        ]),
        ("Ждём ответа", "var(--warn)", "6", [
            kc("Нурия Султанова", "ДР · Анастасия", "17 окт", "", '<span class="small muted">09:42</span>'),
            kc("Анна Иванова", "ДР мамы · Елена", "19 окт", "", '<span class="small muted">09:38</span>'),
            kc("Самат Жумаев", "Годовщина · Айжан", "21 окт", "", '<span class="small muted">вчера</span>'),
        ]),
        ("Ответили", "var(--info)", "3", [
            kc("Айпери Тилекова", "ДР · Нурзат", "22 окт", "", '<span class="tag info">просит фото</span>'),
            kc("Михаил Орлов", "Годовщина · Елена", "19 окт", "", '<span class="tag">подумает</span>'),
        ]),
        ("Заказали", "var(--ok)", "4", [
            kc("Бермет Усенова", "ДР мамы · Айжан", "18 окт", "", '<span class="tag ok">№ 63 · 6 350</span>'),
            kc("Азамат Нуров", "Годовщина · Анастасия", "20 окт", "", '<span class="tag ok">№ 64 · 4 200</span>'),
            kc("Ксения Белова", "ДР · Елена", "21 окт", "", '<span class="tag ok">№ 66 · 3 500</span>'),
        ]),
        ("Без ответа 3+ дня", "var(--dim)", "2", [
            kc("Эрмек Алиев", "ДР · Нурзат", "16 окт", "", '<span class="small muted">написали 13 окт</span>'),
        ]),
    ]
    board = "".join('<div class="col"><div class="col-hd"><span class="sw" style="background:%s"></span>%s<span class="n">%s</span></div>%s</div>'
                    % (c, n, cnt, "".join(cards)) for n, c, cnt, cards in cols)
    body = (
        '<div class="page-hd"><div><h1>Напоминания</h1><div class="sub">Неделя 13–19 октября · что дали напоминания</div></div>'
        '<div class="spacer"></div><div class="seg"><span>Сегодня</span><span class="on">Неделя</span></div>'
        '<span class="btn">' + I["gear"] + ' Настройки</span></div>'
        '<div class="funnel"><div><div class="l">Написали</div><div class="v">41</div></div>'
        '<div><div class="l">Ответили</div><div class="v">17 <small>41%</small></div></div>'
        '<div><div class="l">Заказали</div><div class="v">9 <small>22%</small></div></div>'
        '<div><div class="l">Выручка с напоминаний</div><div class="v">38 900 <small>сом</small></div></div></div>'
        '<div class="board">' + board + '</div>')
    return page("Вариант 3 · Доска недели", body)


# ---------------- Settings: scenarios ----------------
def settings():
    def sc(icon, nm, why, on, sel=False):
        return ('<div class="sc%s"><span class="ic">%s</span><div><div class="nm">%s</div><div class="why">%s</div></div>'
                '<span class="%s"></span></div>' % (" sel" if sel else "", I[icon], nm, why, "sw-on" if on else "sw-off"))
    left = (
        '<div class="scol"><div class="qtop"><div class="row"><b class="ink" style="font-size:15px">Сценарии</b>'
        '<span class="spacer"></span><span class="btn sm">' + I["plus"] + ' Новый</span></div>'
        '<div class="small muted" style="margin-top:6px">Сценарий = когда написать + что написать</div></div>'
        '<div class="grp">Перед важной датой</div>' +
        sc("gift", "День рождения", "за 14 · 3 · 1 день", True, True) +
        sc("heart", "Годовщина и свадьба", "за 7 · 1 день", True) +
        sc("cal", "Другие важные даты", "за 3 дня", True) +
        '<div class="grp">После покупки</div>' +
        sc("repeat", "Давно не заказывали", "через 90 дней после заказа", True) +
        sc("bag", "Спасибо после доставки", "через 1 день · отзыв", False) +
        '<div class="grp">Праздники</div>' +
        sc("spark", "8 Марта", "за 5 дней · всем с согласием", False) +
        '<div class="rules"><div class="lbl" style="margin-bottom:4px">Общие правила</div>'
        '<div class="rule">' + I["moon"] + ' Писать только<span class="v">09:00–20:00</span></div>'
        '<div class="rule">' + I["shield"] + ' Только с согласием клиента<span class="sw-on"></span></div>'
        '<div class="rule">' + I["pause"] + ' Пауза при открытой жалобе<span class="sw-on"></span></div>'
        '<div class="rule">' + I["repeat"] + ' Не чаще одного в<span class="v">7 дней</span></div></div></div>')
    txt = (v("Имя") + ', здравствуйте! Это ' + v("Магазин") + ' 🌷 Завтра у ' + v("Получатель") + ' ' + v("Повод") +
           '. В прошлом году вы дарили ' + v("Прошлый букет") + ' — собрать похожий или что-то новое? Доставим к удобному часу.')
    center = (
        '<div class="ed"><div class="fhd" style="padding:14px 20px"><span class="ic" style="width:34px;height:34px;border-radius:9px;display:grid;place-items:center;background:var(--accent-bg);color:var(--accent)">' + I["gift"] + '</span>'
        '<div><h2 style="font-size:17px">День рождения</h2><div class="small muted">Включён · 22 клиента в октябре</div></div>'
        '<span class="spacer"></span><span class="btn sm">Отправить себе тест</span><span class="btn primary sm">Сохранить</span></div>'
        '<div class="edb">'
        '<div><div class="lbl">Когда</div><div class="sentence">Напомнить за'
        '<span class="slot num">14</span><span class="slot num">3</span><span class="slot num">1</span>'
        '<span class="slot" style="border-style:dashed;color:var(--muted)">' + I["plus"] + '</span>'
        'дн. до события<span class="slot">День рождения ' + I["chev"] + '</span></div></div>'
        '<div><div class="lbl">Что написать</div><div class="steps"><span>За 14 дней</span><span>За 3 дня</span><span class="on">За 1 день</span></div></div>'
        '<div class="txt">' + txt + '</div>'
        '<div class="ins">Вставить:' + v("Имя") + v("Получатель") + v("Повод") + v("Дата") + v("Прошлый букет") + v("Магазин") + '</div>'
        '<div class="assist"><div class="abox"><div class="lbl">Проверка текста</div><div class="chks">'
        '<div class="chk-l"><span class="ok">' + I["check"] + '</span>Обращение по имени</div>'
        '<div class="chk-l"><span class="ok">' + I["check"] + '</span>Повод и дата</div>'
        '<div class="chk-l"><span class="ok">' + I["check"] + '</span>Вопрос в конце</div>'
        '<div class="chk-l"><span class="ok">' + I["check"] + '</span>Без ссылок и КАПСА</div>'
        '<div class="chk-l"><span class="wn">' + I["warn"] + '</span>212 символов — короче читают чаще</div></div></div>'
        '<div class="abox"><div class="lbl">Помощник ' + I["spark"] + '</div><div class="gen">'
        '<span>' + I["spark"] + ' Сделать теплее</span><span>' + I["spark"] + ' Короче, до 150 символов</span>'
        '<span>' + I["spark"] + ' Добавить фото букетов дня</span><span>' + I["spark"] + ' Три новых варианта</span></div></div></div>'
        '</div></div>')
    msg = ('Алина, здравствуйте! Это Tapme Flowers 🌷 Завтра у мамы Айжан день рождения. '
           'В прошлом году вы дарили «Нежность» — собрать похожий или что-то новое? Доставим к удобному часу.')
    right = (
        '<div class="pv"><div class="row"><b class="ink">Так увидит клиент</b><span class="spacer"></span>'
        '<span class="small muted">пример ' + I["chev"] + '</span></div>'
        '<div class="small muted">Алина Садыкова · ДР мамы Айжан, 18 октября</div>'
        '<div class="waphone" style="height:auto;flex:1"><div class="wahd">' + av("Tapme Flowers", "sm") + '<b style="color:#111">Tapme Flowers</b></div>'
        '<div style="flex:1"></div><div class="bubble" style="padding:8px 10px;font-size:13.5px;line-height:1.45">' + msg + '<span class="time">10:05</span></div></div>'
        '<div class="small muted" style="line-height:1.5">Сообщение отправляет сотрудник из своего WhatsApp — CRM только готовит текст и открывает чат.</div></div>')
    body = ('<div class="page-hd" style="margin-bottom:12px"><div><div class="row small muted">' + I["back"] + ' К напоминаниям</div>'
            '<h1 style="margin-top:4px">Настройки напоминаний</h1></div></div>'
            '<div class="set" style="height:742px">' + left + center + right + '</div>')
    return page("Настройки напоминаний · сценарии", body)


# ---------------- Mobile: option 2 on a phone ----------------
def mobile():
    css = CSS + EXTRA + """
    body{background:#E9ECE6}.stage{width:1440px;height:900px;display:flex;gap:56px;align-items:center;justify-content:center;font-family:var(--sans);color:var(--ink-2);font-size:14px}
    .ph{width:390px;height:812px;border-radius:44px;background:#111;padding:12px;box-shadow:0 30px 60px rgba(15,42,34,.25)}
    .scr{width:100%;height:100%;border-radius:34px;background:var(--bg);overflow:hidden;display:flex;flex-direction:column}
    .sb{height:44px;display:flex;align-items:center;justify-content:space-between;padding:0 26px;font-weight:600;font-size:14px;color:#111}
    .mh{padding:6px 18px 12px;background:var(--bg)}
    .mh h1{font-size:22px}.cap{width:300px;font-size:15px;line-height:1.5}
    .cap h2{font-size:22px;margin-bottom:10px}
    .mrow{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;padding:11px 16px;border-top:1px solid var(--border);background:#fff}
    .mrow .nm{font-weight:500;color:var(--ink)}.mrow .why{font-size:12.5px;color:var(--muted)}
    .mbtn{height:50px;border-radius:12px;background:var(--wa);color:#fff;font-weight:600;font-size:16px;display:flex;align-items:center;justify-content:center;gap:8px}
    """
    rows = ""
    for gcls, gname, items in QUEUE:
        rows += '<div class="grp %s">%s<span class="gn">· %d</span></div>' % (gcls, gname, len(items))
        for nm, why, when, wcls, *_ in items:
            rows += ('<div class="mrow">' + av(nm, "sm") + '<div><div class="nm">' + nm + '</div><div class="why">' + why +
                     '</div></div><span class="when ' + wcls + '">' + when + '</span></div>')
    phone1 = ('<div class="ph"><div class="scr"><div class="sb"><span>9:41</span><span>●●● ▮</span></div>'
              '<div class="mh"><div class="row"><h1>Сегодня</h1><span class="spacer"></span><span class="mono b ink">6 / 28</span></div>'
              '<div class="prog" style="height:6px;margin-top:10px"><i style="width:21%;background:var(--wa)"></i></div>'
              '<div class="small muted" style="margin-top:8px">≈ 10 минут · начните сверху</div></div>'
              '<div style="flex:1;overflow:hidden">' + rows + '</div>'
              '<div style="padding:12px 16px 26px;background:#fff;border-top:1px solid var(--border)"><div class="mbtn">Начать по очереди ' + I["next"] + '</div></div></div></div>')
    msg = ('Алина, здравствуйте! Это Tapme Flowers 🌷 Завтра у мамы Айжан день рождения. '
           'В прошлом году вы дарили «Нежность» — собрать похожий?')
    phone2 = ('<div class="ph"><div class="scr"><div class="sb"><span>9:41</span><span>●●● ▮</span></div>'
              '<div class="mh"><div class="row small muted">' + I["back"] + ' Очередь<span class="spacer"></span><span class="mono">1 из 22</span></div></div>'
              '<div style="padding:0 16px;display:flex;flex-direction:column;gap:12px;flex:1">'
              '<div class="row">' + av("Алина Садыкова", "lg") + '<div><div class="b ink" style="font-size:17px">Алина Садыкова</div>'
              '<div class="small muted">7 заказов · VIP</div></div></div>'
              '<div class="reason" style="padding:12px"><span class="ri">' + I["gift"] + '</span><div><b style="font-size:14px">Завтра ДР мамы — Айжан</b>'
              '<div class="small muted">Год назад: «Нежность», 3 500 сом</div></div></div>'
              '<div class="waphone" style="height:auto;flex:1;border-radius:12px"><div style="flex:1"></div>'
              '<div class="bubble" style="padding:8px 10px;font-size:13.5px;line-height:1.45">' + msg + '<span class="time">сейчас</span></div></div>'
              '<div class="tpl"><span class="on">За 1 день</span><span>Короче</span><span>' + I["spark"] + ' Другой</span></div></div>'
              '<div style="padding:12px 16px 26px;background:#fff;border-top:1px solid var(--border);display:flex;flex-direction:column;gap:10px">'
              '<div class="mbtn">' + WA + ' Открыть WhatsApp</div>'
              '<div class="row" style="justify-content:space-between;font-size:14px;color:var(--muted)"><span>' + I["clock"] + ' Завтра</span>'
              '<span>' + I["skip"] + ' Не в этом году</span><span class="ink b">Следующий ' + I["next"] + '</span></div></div></div></div>')
    cap = ('<div class="cap"><h2>На телефоне</h2><p class="muted">Утром флорист или менеджер открывает «Сегодня» и идёт по очереди: '
           'одна карточка — одна кнопка. После WhatsApp возвращается в CRM, и следующая карточка уже открыта.</p></div>')
    return ('<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Мобильная очередь</title>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">'
            '<style>' + css + '</style></head><body><div class="stage">' + cap + phone1 + phone2 + '</div></body></html>')


OUT = {
    "1-list.html": option1(),
    "2-queue-card.html": option2(),
    "3-week-board.html": option3(),
    "4-settings-scenarios.html": settings(),
    "5-mobile.html": mobile(),
}
for name, html in OUT.items():
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", name)
