# -*- coding: utf-8 -*-
import json
CSS = """
:root{--bg:#F5F6F3;--surface:#FFFFFF;--surface-2:#EFF1EC;--surface-3:#E6E9E3;--border:#E1E5DE;--border-2:#8A918A;--ink:#171C19;--ink-2:#3B443F;--muted:#5C665F;--dim:#7A837C;--rail:#0F2A22;--rail-ink:#CFDBD4;--rail-dim:#8FA79C;--rail-active:#1F5C4B;--rail-line:#1B3B31;--accent:#6B3FA0;--accent-2:#56338A;--accent-bg:#F0EAF9;--ok:#2B7049;--ok-bg:#E3F1E7;--warn:#8A6510;--warn-bg:#F8EED8;--crit:#B23C2E;--crit-bg:#F9E6E2;--info:#2F5C8F;--info-bg:#E4ECF7;--neutral:#5C665F;--neutral-bg:#ECEFEA;--wa:#1F8A4C;--wa-bg:#E4F4EA;--sans:'Golos Text',ui-sans-serif,system-ui,sans-serif;--mono:'IBM Plex Mono',ui-monospace,Menlo,monospace}
*{box-sizing:border-box}body{margin:0;background:#F5F6F3}
a{color:#6B3FA0}a:hover{color:#56338A}
.root{width:1440px;height:900px;display:grid;grid-template-columns:236px minmax(0,1fr);background:var(--bg);overflow:hidden;color:var(--ink-2);font-family:var(--sans);font-size:14px;line-height:1.45;-webkit-font-smoothing:antialiased}
h1,h2,h3{margin:0;font-weight:600;color:var(--ink);letter-spacing:-.01em}h1{font-size:22px}h2{font-size:15px}h3{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--dim);font-weight:600}
p{margin:0}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}.muted{color:var(--muted)}.dim{color:var(--dim)}.small{font-size:12px}.tiny{font-size:11px}.ink{color:var(--ink)}.b{font-weight:600}
.row{display:flex;align-items:center;gap:8px}.spacer{margin-left:auto}.stack{display:flex;flex-direction:column;gap:16px}
.rail{background:var(--rail);color:var(--rail-ink);border-right:1px solid var(--rail-line);display:flex;flex-direction:column;padding:14px 10px}
.brand{display:flex;align-items:center;gap:10px;padding:6px 8px 16px}
.brand-mark{width:32px;height:32px;border-radius:10px;background:linear-gradient(135deg,#8C5BC7,#5A2E8F);display:grid;place-items:center;color:#fff}
.brand-name{font-weight:700;color:#fff;font-size:15px;line-height:1.1}.brand-sub{font-size:11px;color:var(--rail-dim);margin-top:2px}
.nav{display:flex;flex-direction:column;gap:2px}
.nav-item{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:9px;color:var(--rail-ink);font-weight:500}
.nav-item.on{background:var(--rail-active);color:#fff}.nav-item svg{opacity:.75}.nav-item.on svg{opacity:1}
.nav-item .cnt{margin-left:auto;font-family:var(--mono);font-size:11px;background:rgba(255,255,255,.12);padding:1px 7px;border-radius:999px}
.rail-foot{margin-top:auto;padding:10px 8px;border-top:1px solid var(--rail-line);display:flex;align-items:center;gap:10px}
.rail-foot .shop-n{font-size:13px;color:#fff;font-weight:500}.rail-foot .shop-c{font-size:11px;color:var(--rail-dim)}
.av{width:30px;height:30px;border-radius:50%;background:var(--accent-bg);color:var(--accent);display:inline-grid;place-items:center;font-size:12px;font-weight:600;flex:none}
.av.sm{width:24px;height:24px;font-size:10px}.av.lg{width:44px;height:44px;font-size:16px}.rail .av{background:#1F5C4B;color:#fff}
.main{min-width:0;display:flex;flex-direction:column}
.topbar{background:var(--surface);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:14px;padding:10px 22px;min-height:58px}
.topbar h1{font-size:17px}
.search{display:flex;align-items:center;gap:8px;background:var(--surface-2);border-radius:10px;padding:0 12px;height:36px;width:420px;color:var(--muted);font-size:14px}
.kbd{font-family:var(--mono);font-size:11px;padding:0 5px;border:1px solid var(--border);border-bottom-width:2px;border-radius:5px;color:var(--muted);background:#fff;line-height:16px;margin-left:auto}
.ubtn{display:flex;align-items:center;gap:8px;padding:4px 8px 4px 4px}.ubtn .un{font-size:13px;font-weight:500;color:var(--ink);line-height:1.1}.ubtn .ur{font-size:11px;color:var(--muted)}
.canvas{padding:20px 22px;overflow:hidden;min-height:0}
.page-hd{display:flex;align-items:flex-end;gap:12px;margin-bottom:16px}.page-hd .sub{color:var(--muted);font-size:13px;margin-top:3px}
.btn{display:inline-flex;align-items:center;gap:7px;height:36px;padding:0 14px;border-radius:9px;border:1px solid var(--border);background:#fff;color:var(--ink);font-weight:500;white-space:nowrap}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}.btn.wa{background:var(--wa-bg);border-color:transparent;color:var(--wa)}.btn.ghost{border-color:transparent;background:transparent;color:var(--muted)}.btn.ok{background:var(--ok);border-color:var(--ok);color:#fff}
.btn.sm{height:30px;padding:0 10px;font-size:13px;border-radius:8px}.btn.xs{height:26px;padding:0 8px;font-size:12px;border-radius:7px}
.pills{display:flex;gap:6px}.pill{height:30px;padding:0 12px;border-radius:999px;border:1px solid var(--border);background:#fff;color:var(--ink-2);font-size:13px;display:inline-flex;align-items:center;gap:6px}.pill.on{background:var(--ink);border-color:var(--ink);color:#fff}.pill .cnt{font-family:var(--mono);font-size:11px;opacity:.75}
.tag{display:inline-flex;align-items:center;gap:5px;height:22px;padding:0 8px;border-radius:6px;font-size:12px;font-weight:500;white-space:nowrap;background:var(--neutral-bg);color:var(--neutral)}
.tag.ok{background:var(--ok-bg);color:var(--ok)}.tag.warn{background:var(--warn-bg);color:var(--warn)}.tag.crit{background:var(--crit-bg);color:var(--crit)}.tag.info{background:var(--info-bg);color:var(--info)}.tag.acc{background:var(--accent-bg);color:var(--accent)}.tag.wa{background:var(--wa-bg);color:var(--wa)}
.tag .dot{width:6px;height:6px;border-radius:50%;background:currentColor}
.chip{display:inline-flex;align-items:center;height:24px;padding:0 9px;border-radius:999px;background:var(--surface-2);font-size:12px;color:var(--ink-2)}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;box-shadow:0 1px 2px rgba(20,28,24,.06);min-width:0}
.card-hd{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid var(--border);min-height:48px}.card-bd{padding:16px}.card-bd.tight{padding:0}
.lrow{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:12px;align-items:center;padding:11px 16px;border-top:1px solid var(--border);min-height:58px}.lrow:first-child{border-top:0}
.lrow.sel{background:var(--accent-bg);box-shadow:inset 3px 0 0 var(--accent)}.lrow.done{opacity:.55}
.lrow .t{font-weight:500;color:var(--ink)}.lrow .s{font-size:12px;color:var(--muted);margin-top:2px}.lrow .r{text-align:right;font-size:12px;color:var(--muted);white-space:nowrap}
.qhead{padding:8px 16px 4px;font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--dim);font-weight:600;border-top:1px solid var(--border);background:var(--surface-2)}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.kpi{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 16px;box-shadow:0 1px 2px rgba(20,28,24,.06)}
.kpi .kl{font-size:12px;color:var(--muted)}.kpi .kv{font-size:26px;font-weight:600;color:var(--ink);font-family:var(--mono);line-height:1.2;margin-top:4px}.kpi .kv .u{font-family:var(--sans);font-size:13px;font-weight:500;color:var(--muted);margin-left:4px}.kpi .kf{font-size:12px;color:var(--dim);margin-top:4px}
.seg{display:inline-flex;border:1px solid var(--border);border-radius:9px;overflow:hidden;background:#fff}.seg span{padding:0 12px;height:34px;display:inline-flex;align-items:center;color:var(--muted);font-weight:500}.seg span+span{border-left:1px solid var(--border)}.seg span.on{background:var(--ink);color:#fff}
.dl{display:grid;grid-template-columns:110px minmax(0,1fr);gap:6px 12px;font-size:13px}.dl dt{color:var(--muted)}.dl dd{margin:0;color:var(--ink)}
.prog{height:6px;border-radius:3px;background:var(--surface-3);overflow:hidden;margin-top:6px}.prog i{display:block;height:100%;background:var(--accent)}
.editor{border:1px solid var(--border);border-radius:10px;padding:10px 12px;min-height:84px;font-size:14px;color:var(--ink);background:#fff;line-height:1.5}
.bubble{max-width:420px;background:#DCF8C6;color:#111;border-radius:12px 12px 12px 2px;padding:8px 10px;font-size:13.5px;line-height:1.4;position:relative}
.bubble .time{display:block;text-align:right;font-size:11px;color:#5a6b5a;margin-top:2px}
.wa-bg{background:#ECE5DD;border-radius:12px;padding:14px}
.kanban{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;align-items:start}.kcol{background:var(--surface-2);border-radius:12px;padding:8px}
.kcol-hd{display:flex;align-items:center;gap:8px;padding:6px 8px 10px;font-size:13px;font-weight:600;color:var(--ink)}.kcol-hd .cnt{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--muted);font-weight:500}
.kcard{background:#fff;border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:8px;box-shadow:0 1px 2px rgba(20,28,24,.06)}
.kcard .kb{font-weight:500;color:var(--ink);font-size:13px}.kcard .ks{font-size:12px;color:var(--muted);margin-top:2px}.kcard .kf{display:flex;align-items:center;gap:6px;margin-top:8px;flex-wrap:wrap}
.cal{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px}.cal .dow{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);text-align:center;padding:4px 0}
.cday{background:#fff;border:1px solid var(--border);border-radius:10px;min-height:92px;padding:8px;display:flex;flex-direction:column;gap:4px}.cday.today{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-bg)}.cday.past{opacity:.5}.cday.other{opacity:.35}
.cday .d{font-family:var(--mono);font-size:12px;color:var(--muted)}.cday.today .d{color:var(--accent);font-weight:600}
.ev{font-size:11px;padding:2px 6px;border-radius:5px;background:var(--accent-bg);color:var(--accent);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ev.warn{background:var(--warn-bg);color:var(--warn)}.ev.wr{background:var(--wa-bg);color:var(--wa);font-weight:500}
.toggle{display:inline-flex;align-items:center;gap:8px;font-size:13px}.toggle i{width:34px;height:20px;border-radius:10px;background:var(--surface-3);position:relative;display:inline-block}.toggle i::after{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.2)}.toggle.on i{background:var(--ok)}.toggle.on i::after{left:16px}
.ghead{display:flex;align-items:center;gap:8px;padding:10px 16px 6px;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;border-top:1px solid var(--border);background:var(--surface-2)}
.ghead.crit{color:var(--crit)}.ghead.acc{color:var(--accent)}.ghead.dim{color:var(--dim)}
.srow{display:grid;grid-template-columns:76px auto minmax(0,1fr) auto;gap:12px;align-items:center;padding:10px 16px;border-top:1px solid var(--border)}
.srow .when{font-family:var(--mono);font-size:12px;color:var(--ink);line-height:1.25}.srow .when small{display:block;color:var(--muted);font-family:var(--sans);font-size:11px}
.srow .t{font-weight:500;color:var(--ink)}.srow .s{font-size:12px;color:var(--muted);margin-top:2px}.srow .acts{display:flex;gap:6px}
.chk{width:20px;height:20px;border-radius:50%;border:2px solid var(--border-2);background:#fff;display:inline-block}.chk.ok{background:var(--ok);border-color:var(--ok)}
"""
ICONS = {
 'today':'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path></svg>',
 'orders':'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="5" height="16" rx="1.5"></rect><rect x="10" y="4" width="5" height="11" rx="1.5"></rect><rect x="17" y="4" width="4" height="14" rx="1.5"></rect></svg>',
 'clients':'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M16 20v-1.5a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4V20"></path><circle cx="9" cy="7" r="3.2"></circle><path d="M22 20v-1.5a4 4 0 0 0-3-3.8"></path><path d="M16 4.2a3.2 3.2 0 0 1 0 5.9"></path></svg>',
 'reminders':'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8.5a6 6 0 0 0-12 0c0 6-2.5 7.5-2.5 7.5h17S18 14.5 18 8.5z"></path><path d="M10.3 19.5a2 2 0 0 0 3.4 0"></path></svg>',
 'deliveries':'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h11v9H3z"></path><path d="M14 10h4l3 3v3h-7z"></path><circle cx="7" cy="18" r="1.8"></circle><circle cx="17" cy="18" r="1.8"></circle></svg>',
 'settings':'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"></path></svg>',
}
BRAND_SVG='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22V12"></path><path d="M12 12c-4 0-6-2.2-6-5 0-2 1.5-3.5 3.5-3.5 1.1 0 2 .5 2.5 1.3.5-.8 1.4-1.3 2.5-1.3C16.5 3.5 18 5 18 7c0 2.8-2 5-6 5z"></path><path d="M12 17c-2.2 0-3.5-1.2-3.5-3"></path><path d="M12 19c2.2 0 3.5-1.2 3.5-3"></path></svg>'
SEARCH_SVG='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"></circle><path d="M20 20l-3.5-3.5"></path></svg>'
WA_SVG='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 1-13.4 7.8L3 21l1.3-4.5A9 9 0 1 1 21 12z"></path></svg>'
CHECK_SVG='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"></path></svg>'
NAV=[('today','Сегодня',''),('orders','Заказы','9'),('clients','Клиенты',''),('reminders','Напоминания','6'),('deliveries','Доставка','8'),('settings','Настройки','')]
def rail():
    items=''.join('<div class="nav-item%s">%s%s%s</div>'%(' on' if k=='reminders' else '',ICONS[k],n,('<span class="cnt">%s</span>'%c) if c else '') for k,n,c in NAV)
    return ('<div class="rail"><div class="brand"><div class="brand-mark">'+BRAND_SVG+'</div><div><div class="brand-name">Tapme Flowers</div><div class="brand-sub">Кабинет магазина</div></div></div>'
            '<div class="nav">'+items+'</div><div class="rail-foot"><span class="av">GS</span><div><div class="shop-n">Gul Studio</div><div class="shop-c">Бишкек · ул. Токтогула 125</div></div></div></div>')
def topbar():
    return ('<div class="topbar"><div><h1>Напоминания</h1></div><div class="search">'+SEARCH_SVG+'<span>Телефон, имя, ID клиента, № или ID заказа</span><span class="kbd">/</span></div><div class="spacer"></div>'
            '<span class="btn primary">+ Заказ</span><div class="ubtn"><span class="av">АИ</span><div><div class="un">Айнура</div><div class="ur">Менеджер</div></div></div></div>')
def page(body):
    return ('<!doctype html>\n<html>\n<head>\n<meta charset="utf-8">\n<script src="./support.js"></script>\n</head>\n<body>\n<x-dc>\n<helmet>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600;700&amp;family=IBM+Plex+Mono:wght@400;500&amp;display=swap">\n'
            '<style>'+CSS+'</style>\n</helmet>\n<div class="root">'+rail()+'<div class="main">'+topbar()+'<div class="canvas">'+body+'</div></div></div>\n</x-dc>\n</body>\n</html>\n')
def av(n,cls=''):
    ini=''.join(w[0] for w in n.split()[:2]).upper()
    return '<span class="av %s">%s</span>'%(cls,ini)
def tag(t,cls='',dot=False):
    return '<span class="tag %s">%s%s</span>'%(cls,'<i class="dot"></i>' if dot else '',t)

# ---------- A. Очередь (Main) ----------
def qitem(name,reason,chip,chipcls='',state='',sel=False,done=False):
    r='<span class="r">'
    if done: r+=tag('Готово','ok')
    elif state: r+=state
    else: r+='<span class="chip">%s</span>'%chip
    r+='</span>'
    return '<div class="lrow%s%s">%s<div><div class="t">%s</div><div class="s">%s</div></div>%s</div>'%(' sel' if sel else '',' done' if done else '',av(name),name,reason,r)
A_BODY = ('<div class="page-hd"><div><h1>Напоминания</h1><div class="sub">Очередь на сегодня · 10 клиентов · написали 1 · заказали 3</div></div><div class="spacer"></div>'
 '<div class="seg"><span class="on">Очередь</span><span>Список</span></div><span class="btn">Шаблоны</span></div>'
 '<div class="row" style="gap:16px;align-items:flex-start">'
 '<div class="card" style="width:380px;flex:none">'
 '<div style="padding:12px 16px"><div class="row"><span class="small muted">Сделано 4 из 10</span><span class="spacer"></span><span class="small mono">40 %</span></div><div class="prog"><i style="width:40%"></i></div></div>'
 '<div class="qhead">Сейчас</div>'
 +qitem('Айбек Токтосунов','ДР Айгуль · 3 дек · через 14 дней','14 дн',sel=True)
 +'<div class="qhead">Дальше · 5</div>'
 +qitem('Бекзат Алиев','ДР Айданы · 3 дек · через 14 дней','14 дн')
 +qitem('Азамат Бекбоев','Без заказов 99 дней · последний 12 авг','99 дн')
 +qitem('Нурлан Кадыров','Без заказов 106 дней · один заказ','106 дн')
 +qitem('Чолпон Асанова','Без заказов 141 день','',state=tag('нет согласия'))
 +qitem('Бекзат Алиев','Без заказов 152 дня','152 дн')
 +'<div class="qhead">Готово · 4</div>'
 +qitem('Данияр Осмонов','ДР Асель · 26 ноя · написали в 09:15','',state=tag('Написали','wa'))
 +qitem('Тимур Садыков','Годовщина 22 ноя · заказ №2489','',done=True)
 +qitem('Айгерим Ниязова','ДР мамы сегодня · заказ №2483','',done=True)
 +qitem('Асель Жумабекова','ДР Бурул завтра · заказ №2490','',done=True)
 +'</div>'
 '<div class="card" style="flex:1;min-width:0">'
 '<div class="card-bd" style="padding:18px 20px 14px;border-bottom:1px solid var(--border)"><div class="row" style="gap:14px;align-items:flex-start">'+av('Айбек Токтосунов','lg')+
 '<div style="flex:1;min-width:0"><div class="row"><h2 style="font-size:19px">Айбек Токтосунов</h2>'+tag('VIP','acc')+'<span class="tag mono">ID 100201</span></div>'
 '<div class="row small muted" style="margin-top:4px"><span class="mono ink">+996 555 12-34-56</span><span>·</span><span>Instagram</span><span>·</span><span>24 заказа на 186 400 сом</span></div></div>'
 '<span class="btn ghost sm">Пропустить в этом году</span><span class="btn ghost sm">Напомнить завтра</span></div>'
 '<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:16px">'
 '<div><h3>Повод</h3><div class="ink b" style="margin-top:6px">День рождения Айгуль</div><div class="small muted">супруга · 3 декабря · через 14 дней</div></div>'
 '<div><h3>Прошлый раз</h3><div class="ink b" style="margin-top:6px">25 роз 60 см · 6 550 сом</div><div class="small muted">2 ноября · обычно заказывает за 5 дней до даты</div></div>'
 '<div><h3>Заметка</h3><div class="ink" style="margin-top:6px">Без лилий: у супруги аллергия.</div><div class="small muted">Пудровая гамма, без яркой упаковки</div></div>'
 '</div></div>'
 '<div class="card-bd" style="padding:16px 20px"><div class="row" style="margin-bottom:10px"><h3 style="margin-right:6px">Сообщение</h3><div class="pills"><span class="pill on">За 14 дней</span><span class="pill">За 7 дней</span><span class="pill">За 3 дня</span><span class="pill">Накануне</span><span class="pill">Свой текст</span></div></div>'
 '<div style="display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;align-items:start">'
 '<div><div class="editor">Айбек, здравствуйте! Это Gul Studio. Через две недели день рождения у Айгуль. В прошлый раз ей понравились пудровые розы. Соберём букет заранее и доставим в удобное время?</div>'
 '<div class="row" style="margin-top:12px;gap:8px"><span class="btn wa" style="height:40px;padding:0 16px">'+WA_SVG+'Открыть WhatsApp и перейти к следующему</span><span class="btn">Написал</span><span class="small muted" style="margin-left:6px">Enter открыть · → следующий</span></div>'
 '<div class="small muted" style="margin-top:10px">Текст подставится в чат. Отметка «написали» появится сама, когда откроете WhatsApp.</div></div>'
 '<div class="wa-bg"><div class="tiny muted" style="margin-bottom:8px">Так увидит клиент</div><div class="bubble">Айбек, здравствуйте! Это Gul Studio. Через две недели день рождения у Айгуль. В прошлый раз ей понравились пудровые розы. Соберём букет заранее и доставим в удобное время?<span class="time">10:41</span></div></div>'
 '</div></div>'
 '<div class="card-bd" style="border-top:1px solid var(--border);padding:12px 20px"><div class="row small"><h3 style="margin-right:6px">История</h3><span class="tag ok">14 фев · написали → заказ 6 250</span><span class="tag">22 мар · написали → без ответа</span><span class="tag ok">2 ноя · заказ без напоминания</span></div></div>'
 '</div></div>')

# ---------- B. Воронка ----------
def kc(name,reason,foot):
    return '<div class="kcard"><div class="row"><span class="av sm">%s</span><span class="kb">%s</span></div><div class="ks">%s</div><div class="kf">%s</div></div>'%(''.join(w[0] for w in name.split()[:2]).upper(),name,reason,foot)
B_BODY = ('<div class="page-hd"><div><h1>Напоминания</h1><div class="sub">Воронка за 30 дней · от напоминания до заказа</div></div><div class="spacer"></div><div class="pills"><span class="pill on">Все</span><span class="pill">Даты</span><span class="pill">Давно не заказывали</span><span class="pill">По шаблону</span></div><span class="btn">Шаблоны</span></div>'
 '<div class="kpis" style="margin-bottom:16px"><div class="kpi"><div class="kl">Ждут сообщения</div><div class="kv">6</div><div class="kf">на сегодня</div></div><div class="kpi"><div class="kl">Написали</div><div class="kv">7</div><div class="kf">за неделю</div></div><div class="kpi"><div class="kl">Ответили</div><div class="kv">4<span class="u">57 %</span></div><div class="kf">в среднем через 3 часа</div></div><div class="kpi"><div class="kl">Заказали</div><div class="kv">3<span class="u">43 %</span></div><div class="kf">16 200 сом по напоминаниям</div></div></div>'
 '<div class="kanban">'
 '<div class="kcol"><div class="kcol-hd">Ждут<span class="cnt">6</span></div>'
 +kc('Айбек Токтосунов','ДР Айгуль · через 14 дней','<span class="chip">14 дн</span><span class="btn xs wa">WhatsApp</span>')
 +kc('Бекзат Алиев','ДР Айданы · через 14 дней','<span class="chip">14 дн</span><span class="btn xs wa">WhatsApp</span>')
 +kc('Азамат Бекбоев','Без заказов 99 дней','<span class="chip">99 дн</span><span class="btn xs wa">WhatsApp</span>')
 +kc('Нурлан Кадыров','Без заказов 106 дней','<span class="chip">106 дн</span><span class="btn xs wa">WhatsApp</span>')
 +kc('Чолпон Асанова','Без заказов 141 день',tag('нет согласия'))
 +kc('Бекзат Алиев','Без заказов 152 дня','<span class="chip">152 дн</span><span class="btn xs wa">WhatsApp</span>')
 +'</div>'
 '<div class="kcol"><div class="kcol-hd">Написали<span class="cnt">2</span></div>'
 +kc('Данияр Осмонов','ДР Асель · через 7 дней',tag('сегодня 09:15','wa')+'<span class="btn xs">Заказ</span>')
 +kc('Мээрим Жолдошева','ДР Алины · через 10 дней',tag('вчера','wa')+'<span class="btn xs">Заказ</span>')
 +'</div>'
 '<div class="kcol"><div class="kcol-hd">Ответили<span class="cnt">1</span></div>'
 +kc('Гульнара Асанова','Просила прислать варианты до 3 000',tag('ждём решения','warn')+'<span class="btn xs">Заказ</span>')
 +'</div>'
 '<div class="kcol"><div class="kcol-hd">Заказали<span class="cnt">3</span></div>'
 +kc('Тимур Садыков','Годовщина · 22 ноя',tag('№2489 · 6 950','ok'))
 +kc('Айгерим Ниязова','ДР мамы · сегодня',tag('№2483 · 3 300','ok'))
 +kc('Асель Жумабекова','ДР Бурул · завтра',tag('№2490 · 2 800','ok'))
 +'</div>'
 '<div class="kcol"><div class="kcol-hd">Пропущено<span class="cnt">1</span></div>'
 +kc('Эркин Абдыраимов','День компании · юрлицо',tag('пишем через бухгалтерию'))
 +'</div></div>')

# ---------- C. Календарь и правила ----------
def cday(d,cls='',evs=()):
    return '<div class="cday %s"><div class="d">%s</div>%s</div>'%(cls,d,''.join('<span class="ev %s">%s</span>'%(c,t) for t,c in evs))
CAL=[]
row1=[('26','other'),('27','other'),('28','other'),('29','other'),('30','other'),('31','other'),('1 ноя','past')]
CAL+= [cday(d,c) for d,c in row1]
CAL+= [cday(str(d),'past') for d in range(2,9)]
CAL+= [cday(str(d),'past') for d in range(9,16)]
CAL+= [cday('16','past'),cday('17','past'),cday('18','past'),
       cday('19','today',[('ДР Салтанат · заказ есть','ok'),('написать 5','wr')]),
       cday('20','',[('ДР Бурул · заказ есть','')]),cday('21',''),cday('22','',[('Годовщина Тимур','warn'),('написать 1','wr')])]
CAL+= [cday('23','',[('написать 1','wr')]),cday('24',''),cday('25','',[('написать 1','wr')]),cday('26','',[('ДР Асель','') ,('написать 2','wr')]),cday('27',''),cday('28','',[('написать 1','wr')]),cday('29','',[('ДР Алины','')])]
CAL+= [cday('30','',[('написать 2','wr')]),cday('1 дек','other'),cday('2','other',[('написать 2','wr')]),cday('3','other',[('ДР Айгуль',''),('ДР Айданы','')]),cday('4','other'),cday('5','other'),cday('6','other')]
def rule(t,s,on=True):
    return '<div class="lrow" style="min-height:52px"><span class="toggle%s"><i></i></span><div><div class="t">%s</div><div class="s">%s</div></div><span class="r"><span class="btn xs">Шаблон</span></span></div>'%(' on' if on else '',t,s)
C_BODY = ('<div class="page-hd"><div><h1>Напоминания</h1><div class="sub">Календарь поводов и правила, по которым они превращаются в сообщения</div></div><div class="spacer"></div><div class="seg"><span>‹</span><span class="on">Ноябрь 2026</span><span>›</span></div><div class="seg"><span class="on">Месяц</span><span>Неделя</span></div></div>'
 '<div style="display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:16px;align-items:start">'
 '<div class="card"><div class="card-hd"><h2>Ноябрь</h2><span class="small muted">12 поводов · 15 сообщений по правилам</span><div class="spacer"></div><span class="row small"><span class="ev">дата</span><span class="ev warn">годовщина</span><span class="ev wr">написать</span></span></div><div class="card-bd"><div class="cal">'
 +''.join('<div class="dow">%s</div>'%d for d in ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'])+''.join(CAL)+'</div></div></div>'
 '<div class="stack">'
 '<div class="card"><div class="card-hd"><h2>Правила</h2><div class="spacer"></div><span class="btn sm">Добавить</span></div><div class="card-bd tight">'
 +rule('За 14 дней до даты','шаблон «Дата через 14 дней» · только клиенты с согласием')
 +rule('За 7 дней до даты','шаблон «Дата через 7 дней»')
 +rule('За 3 дня до даты','шаблон «Дата через 3 дня» · если заказа ещё нет')
 +rule('Накануне','шаблон «Дата завтра» · если заказа ещё нет')
 +rule('90 дней без заказа','шаблон «Давно не заказывал» · не чаще раза в месяц')
 +rule('После вручения','«Как вам букет?» · через 2 часа',on=False)
 +'<div class="card-bd" style="border-top:1px solid var(--border);padding:12px 16px"><div class="small muted">Не пишем ночью с 21:00 до 09:00 и клиентам без согласия. Сообщения открываются менеджером в WhatsApp, автоотправка появится с подключением API.</div></div></div></div>'
 '<div class="card"><div class="card-hd"><h2>Четверг, 19 ноября</h2><span class="tag acc">5 написать</span></div><div class="card-bd tight">'
 +qitem('Айбек Токтосунов','ДР Айгуль · за 14 дней','',state='<span class="btn xs wa">WhatsApp</span>')
 +qitem('Бекзат Алиев','ДР Айданы · за 14 дней','',state='<span class="btn xs wa">WhatsApp</span>')
 +qitem('Данияр Осмонов','ДР Асель · за 7 дней','',state=tag('написали','wa'))
 +qitem('Тимур Садыков','Годовщина · за 3 дня','',done=True)
 +qitem('Асель Жумабекова','ДР Бурул · накануне','',done=True)
 +'</div></div></div></div>')

# ---------- D. Лента действий ----------
def srow(when,sub,name,reason,acts,chk=''):
    return '<div class="srow"><div class="when">%s<small>%s</small></div><span class="chk %s">%s</span><div style="min-width:0"><div class="t">%s <span class="muted" style="font-weight:400">· %s</span></div><div class="s">%s</div></div><div class="acts">%s</div></div>'%(when,sub,chk,CHECK_SVG if chk=='ok' else '',name,reason[0],reason[1],acts)
ACT_WA='<span class="btn xs wa">WhatsApp</span><span class="btn xs">Написал</span><span class="btn xs ghost">Отложить</span><span class="btn xs ghost">Пропустить</span>'
D_BODY = ('<div class="page-hd"><div><h1>Напоминания</h1><div class="sub">Один список по срочности · 13 действий</div></div><div class="spacer"></div><span class="toggle on"><i></i>Фокус: только сегодня и просроченные</span><div class="seg"><span class="on">По срочности</span><span>По клиенту</span></div></div>'
 '<div style="display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;align-items:start">'
 '<div class="card"><div class="card-bd tight">'
 '<div class="ghead crit" style="border-top:0">Просрочено · 2</div>'
 +srow('9 дн','назад','Азамат Бекбоев',('Без заказов 99 дней','Написать по шаблону «Давно не заказывал». Последний заказ 12 августа, 7 заказов за год'),ACT_WA)
 +srow('16 дн','назад','Нурлан Кадыров',('Без заказов 106 дней','Один заказ 5 августа. Написать или пропустить как случайного'),ACT_WA)
 +'<div class="ghead acc">Сегодня · 6</div>'
 +srow('3 дек','через 14 дн','Айбек Токтосунов',('ДР Айгуль, супруга','Написать по шаблону «За 14 дней». В прошлом году заказал за 5 дней, 25 роз'),ACT_WA)
 +srow('3 дек','через 14 дн','Бекзат Алиев',('ДР Айданы, девушка','Написать по шаблону «За 14 дней». Три заказа, все до 3 500'),ACT_WA)
 +srow('26 ноя','через 7 дн','Данияр Осмонов',('ДР Асель, жена','Написали в 09:15. Если не ответит до завтра, напомнить'),tag('написали','wa')+'<span class="btn xs">Заказ</span>','ok')
 +srow('22 ноя','через 3 дн','Тимур Садыков',('Годовщина свадьбы','Заказ №2489 уже есть. Ничего писать не нужно'),tag('заказ есть','ok'),'ok')
 +srow('сегодня','','Айгерим Ниязова',('ДР Салтанат, мама','Заказ №2483 в пути. Поздравить после вручения'),tag('в пути','acc'),'ok')
 +srow('141 дн','без заказов','Чолпон Асанова',('Нет согласия на сообщения','Спросить согласие при следующем визите, не писать'),tag('нет согласия')+'<span class="btn xs ghost">Пропустить</span>')
 +'<div class="ghead dim">Завтра · 1</div>'
 +srow('20 ноя','завтра','Асель Жумабекова',('ДР Бурул, мама','Заказ №2490 есть, не оплачен. Напомнить об оплате вместе с поздравлением'),'<span class="btn xs wa">WhatsApp</span><span class="btn xs">Оплачен</span>')
 +'<div class="ghead dim">На этой неделе · 4</div>'
 +srow('29 ноя','через 10 дн','Мээрим Жолдошева',('ДР Алины, дочь','Сообщение уйдёт 22 ноября по правилу «За 7 дней»'),'<span class="btn xs ghost">Написать сейчас</span>')
 +'</div></div>'
 '<div class="stack">'
 '<div class="card"><div class="card-hd"><h2>Эта неделя</h2></div><div class="card-bd"><dl class="dl"><dt>Написали</dt><dd>7</dd><dt>Ответили</dt><dd>4 · 57 %</dd><dt>Заказали</dt><dd>3 · 16 200 сом</dd><dt>Лучший шаблон</dt><dd>«За 7 дней» · 2 заказа из 3</dd><dt>Без согласия</dt><dd>1 клиент</dd></dl></div></div>'
 '<div class="card"><div class="card-hd"><h2>Правила</h2><div class="spacer"></div><span class="btn xs">Изменить</span></div><div class="card-bd small muted">Даты: за 14, 7, 3 дня и накануне, пока нет заказа. Давние клиенты: 90 дней, раз в месяц. Ночью не пишем.</div></div>'
 '</div></div>')


# ================= ВАРИАНТЫ ДОСТУПА К ШАБЛОНАМ И ПРАВИЛАМ (структура A) =================
CSS += """
.main{position:relative}
.tabs{display:flex;gap:2px;border-bottom:1px solid var(--border);margin-bottom:16px}.tab{padding:10px 12px;font-weight:500;color:var(--muted);border-bottom:2px solid transparent;margin-bottom:-1px}.tab.on{color:var(--ink);border-bottom-color:var(--accent)}.tab .cnt{font-family:var(--mono);font-size:11px;margin-left:5px;color:var(--dim)}
.scrim{position:absolute;left:0;right:0;top:58px;bottom:0;background:rgba(15,25,20,.28)}
.drawer{position:absolute;top:58px;right:0;bottom:0;width:460px;background:#fff;border-left:1px solid var(--border);box-shadow:-12px 0 32px rgba(20,28,24,.16);display:flex;flex-direction:column}
.drawer-hd{display:flex;align-items:center;gap:10px;padding:14px 18px;border-bottom:1px solid var(--border)}.drawer-bd{padding:0;overflow:hidden;flex:1}.drawer-ft{padding:12px 18px;border-top:1px solid var(--border);display:flex;gap:8px}
.pop{position:absolute;z-index:5;background:#fff;border:1px solid var(--border);border-radius:12px;box-shadow:0 12px 32px rgba(20,28,24,.16);width:360px}
.band{background:var(--accent-bg);border:1px solid #DCCFF0;border-radius:10px;padding:10px 12px;display:flex;gap:10px;align-items:center;margin-bottom:10px;color:var(--ink);font-size:13px}
.editor.edit{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.var{display:inline-flex;align-items:center;height:24px;padding:0 8px;border-radius:6px;background:var(--surface-2);font-family:var(--mono);font-size:12px;color:var(--ink);border:1px dashed var(--border-2)}
.strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:16px}
.strip .card{display:flex;align-items:center;gap:12px;padding:10px 14px}.strip .ic{width:34px;height:34px;border-radius:9px;background:var(--accent-bg);color:var(--accent);display:grid;place-items:center;flex:none}
.strip .t{font-weight:600;color:var(--ink);font-size:13px}.strip .s{font-size:12px;color:var(--muted);margin-top:1px}
.nav-sub{display:flex;flex-direction:column;gap:2px;margin:2px 0 4px 26px}.nav-sub span{padding:6px 10px;border-radius:7px;font-size:13px;color:var(--rail-dim)}.nav-sub span.on{color:#fff;background:rgba(255,255,255,.08)}
.iconbtn{width:32px;height:32px;display:inline-grid;place-items:center;border-radius:8px;color:var(--muted)}
"""
PENCIL='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="margin-left:6px"><path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"></path></svg>'
GEAR=ICONS['settings'].replace('width="16" height="16"','width="15" height="15"')
CLOSE='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"></path></svg>'
RAIL_SUB=False
_rail_plain=rail
def rail():
    r=_rail_plain()
    if not RAIL_SUB: return r
    sub='<div class="nav-sub"><span class="on">Очередь</span><span>Шаблоны</span><span>Правила</span></div>'
    return r.replace('Напоминания<span class="cnt">6</span></div>','Напоминания<span class="cnt">6</span></div>'+sub,1)

def a_header(right,tabs=''):
    return '<div class="page-hd"><div><h1>Напоминания</h1><div class="sub">Очередь на сегодня · 10 клиентов · написали 1 · заказали 3</div></div><div class="spacer"></div>'+right+'</div>'+tabs
SEG='<div class="seg"><span class="on">Очередь</span><span>Список</span></div>'
def queue_card(top='',trim=False):
    s=('<div class="card" style="width:380px;flex:none;position:relative">'+top+
     '<div style="padding:12px 16px"><div class="row"><span class="small muted">Сделано 4 из 10</span><span class="spacer"></span><span class="small mono">40 %</span></div><div class="prog"><i style="width:40%"></i></div></div>'
     '<div class="qhead">Сейчас</div>'
     +qitem('Айбек Токтосунов','ДР Айгуль · 3 дек · через 14 дней','14 дн',sel=True)
     +'<div class="qhead">Дальше · 5</div>'
     +qitem('Бекзат Алиев','ДР Айданы · 3 дек · через 14 дней','14 дн')
     +qitem('Азамат Бекбоев','Без заказов 99 дней · последний 12 авг','99 дн')
     +qitem('Нурлан Кадыров','Без заказов 106 дней · один заказ','106 дн')
     +qitem('Чолпон Асанова','Без заказов 141 день','',state=tag('нет согласия'))
     +qitem('Бекзат Алиев','Без заказов 152 дня','152 дн')
     +'<div class="qhead">Готово · 4</div>'
     +qitem('Данияр Осмонов','ДР Асель · 26 ноя · написали в 09:15','',state=tag('Написали','wa')))
    if not trim:
        s+=(qitem('Тимур Садыков','Годовщина 22 ноя · заказ №2489','',done=True)
           +qitem('Айгерим Ниязова','ДР мамы сегодня · заказ №2483','',done=True)
           +qitem('Асель Жумабекова','ДР Бурул завтра · заказ №2490','',done=True))
    return s+'</div>'
FOCUS_HEAD=('<div class="card-bd" style="padding:18px 20px 14px;border-bottom:1px solid var(--border)"><div class="row" style="gap:14px;align-items:flex-start">'+av('Айбек Токтосунов','lg')+
 '<div style="flex:1;min-width:0"><div class="row"><h2 style="font-size:19px">Айбек Токтосунов</h2>'+tag('VIP','acc')+'<span class="tag mono">ID 100201</span></div>'
 '<div class="row small muted" style="margin-top:4px"><span class="mono ink">+996 555 12-34-56</span><span>·</span><span>Instagram</span><span>·</span><span>24 заказа на 186 400 сом</span></div></div>'
 '<span class="btn ghost sm">Пропустить в этом году</span><span class="btn ghost sm">Напомнить завтра</span></div>'
 '<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:16px">'
 '<div><h3>Повод</h3><div class="ink b" style="margin-top:6px">День рождения Айгуль</div><div class="small muted">супруга · 3 декабря · через 14 дней</div></div>'
 '<div><h3>Прошлый раз</h3><div class="ink b" style="margin-top:6px">25 роз 60 см · 6 550 сом</div><div class="small muted">2 ноября · обычно заказывает за 5 дней до даты</div></div>'
 '<div><h3>Заметка</h3><div class="ink" style="margin-top:6px">Без лилий: у супруги аллергия.</div><div class="small muted">Пудровая гамма, без яркой упаковки</div></div>'
 '</div></div>')
MSG='Айбек, здравствуйте! Это Gul Studio. Через две недели день рождения у Айгуль. В прошлый раз ей понравились пудровые розы. Соберём букет заранее и доставим в удобное время?'
TPL='{имя}, здравствуйте! Это {магазин}. Через две недели {повод} у {получатель}. В прошлый раз понравились {прошлый_букет}. Соберём букет заранее и доставим в удобное время?'
def preview(txt,who='Так увидит клиент'):
    return '<div class="wa-bg"><div class="tiny muted" style="margin-bottom:8px">'+who+'</div><div class="bubble">'+txt+'<span class="time">10:41</span></div></div>'
HIST='<div class="card-bd" style="border-top:1px solid var(--border);padding:12px 20px"><div class="row small"><h3 style="margin-right:6px">История</h3><span class="tag ok">14 фев · написали → заказ 6 250</span><span class="tag">22 мар · написали → без ответа</span><span class="tag ok">2 ноя · заказ без напоминания</span></div></div>'
def focus_card(mode='normal'):
    if mode=='template':
        body=('<div class="card-bd" style="padding:16px 20px"><div class="row" style="margin-bottom:10px"><h3 style="margin-right:6px">Сообщение</h3><div class="pills"><span class="pill on">За 14 дней'+PENCIL+'</span><span class="pill">За 7 дней</span><span class="pill">За 3 дня</span><span class="pill">Накануне</span><span class="pill">Свой текст</span></div></div>'
         '<div class="band">'+PENCIL.replace('style="margin-left:6px"','')+'<span>Вы меняете шаблон <b>«Дата через 14 дней»</b>. Он стоит в правиле «за 14 дней» и ждёт отправки ещё у 1 клиента в очереди.</span></div>'
         '<div style="display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;align-items:start">'
         '<div><div class="row" style="margin-bottom:8px;gap:6px"><span class="tiny muted" style="margin-right:4px">Вставить:</span><span class="var">{имя}</span><span class="var">{получатель}</span><span class="var">{повод}</span><span class="var">{магазин}</span><span class="var">{прошлый_букет}</span></div>'
         '<div class="editor edit">'+TPL+'</div>'
         '<div class="row" style="margin-top:12px;gap:8px"><span class="btn primary">Сохранить для всех</span><span class="btn">Только для этого сообщения</span><span class="btn ghost">Отмена</span></div>'
         '<div class="small muted" style="margin-top:10px">Подстановки заполняются из карточки клиента. Проверьте предпросмотр справа.</div></div>'
         +preview(MSG,'Так увидит Айбек')+'</div></div>')
    else:
        body=('<div class="card-bd" style="padding:16px 20px"><div class="row" style="margin-bottom:10px"><h3 style="margin-right:6px">Сообщение</h3><div class="pills"><span class="pill on">За 14 дней</span><span class="pill">За 7 дней</span><span class="pill">За 3 дня</span><span class="pill">Накануне</span><span class="pill">Свой текст</span></div></div>'
         '<div style="display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;align-items:start">'
         '<div><div class="editor">'+MSG+'</div>'
         '<div class="row" style="margin-top:12px;gap:8px"><span class="btn wa" style="height:40px;padding:0 16px">'+WA_SVG+'Открыть WhatsApp и перейти к следующему</span><span class="btn">Написал</span><span class="small muted" style="margin-left:6px">Enter открыть · → следующий</span></div>'
         '<div class="small muted" style="margin-top:10px">Текст подставится в чат. Отметка «написали» появится сама, когда откроете WhatsApp.</div></div>'
         +preview(MSG)+'</div></div>')
    return '<div class="card" style="flex:1;min-width:0">'+FOCUS_HEAD+body+HIST+'</div>'
def two_cols(left,right):
    return '<div class="row" style="gap:16px;align-items:flex-start">'+left+right+'</div>'

# --- Main = вариант A как выбран ---
MAIN_BODY = a_header(SEG+'<span class="btn">Шаблоны</span>') + two_cols(queue_card(), focus_card())

# --- A1. Вкладки: Очередь · Шаблоны · Правила · Статистика (открыта вкладка Шаблоны) ---
def trow(name,sub,right,sel=False):
    return '<div class="lrow%s" style="min-height:54px"><span class="av sm" style="background:var(--surface-2);color:var(--ink-2)">Т</span><div><div class="t">%s</div><div class="s">%s</div></div><span class="r">%s</span></div>'%(' sel' if sel else '',name,sub,right)
A1_BODY = ('<div class="page-hd"><div><h1>Напоминания</h1><div class="sub">Шаблоны сообщений · 9 · последнее изменение вчера, «Дата через 7 дней»</div></div><div class="spacer"></div><span class="btn primary">Новый шаблон</span></div>'
 '<div class="tabs"><span class="tab">Очередь<span class="cnt">6</span></span><span class="tab on">Шаблоны<span class="cnt">9</span></span><span class="tab">Правила</span><span class="tab">Статистика</span></div>'
 + two_cols(
   '<div class="card" style="width:380px;flex:none"><div class="qhead" style="border-top:0">Даты</div>'
   +trow('Дата через 14 дней','правило «за 14 дней» · 12 отправок за месяц',tag('3 заказа','ok'),sel=True)
   +trow('Дата через 7 дней','правило «за 7 дней» · 9 отправок',tag('2 заказа','ok'))
   +trow('Дата через 3 дня','правило «за 3 дня» · 4 отправки',tag('1 заказ','ok'))
   +trow('Дата завтра','правило «накануне» · 2 отправки',tag('0'))
   +'<div class="qhead">Клиенты</div>'
   +trow('Давно не заказывал','правило «90 дней» · 6 отправок',tag('1 заказ','ok'))
   +'<div class="qhead">Заказ</div>'
   +trow('Заказ принят','вручную из панели заказа · 41 отправка',tag('подтверждение'))
   +trow('Букет собран','вручную · 18 отправок',tag('фото'))
   +trow('Букет вручён','вручную · 37 отправок',tag('фото'))
   +trow('Как вам букет?','через 2 часа после вручения · выключено',tag('выкл','warn'))
   +'</div>',
   '<div class="card" style="flex:1;min-width:0"><div class="card-hd"><h2>Дата через 14 дней</h2>'+tag('правило: за 14 дней до даты','acc')+'<div class="spacer"></div><span class="btn ghost sm">Дублировать</span><span class="btn ghost sm">Вернуть стандартный</span></div>'
   '<div class="card-bd" style="padding:16px 20px"><div class="row" style="margin-bottom:8px;gap:6px"><span class="tiny muted" style="margin-right:4px">Вставить:</span><span class="var">{имя}</span><span class="var">{получатель}</span><span class="var">{повод}</span><span class="var">{магазин}</span><span class="var">{прошлый_букет}</span><span class="var">{ссылка}</span></div>'
   '<div style="display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;align-items:start"><div><div class="editor edit" style="min-height:110px">'+TPL+'</div>'
   '<div class="row" style="margin-top:12px;gap:8px"><span class="btn primary">Сохранить</span><span class="btn ghost">Отмена</span></div>'
   '<div class="small muted" style="margin-top:10px">Изменение применится к следующим сообщениям. Уже открытые чаты не тронет.</div></div>'+preview(MSG,'Пример: Айбек, ДР Айгуль')+'</div></div>'
   '<div class="card-bd" style="border-top:1px solid var(--border);padding:14px 20px"><div class="row" style="gap:24px"><div><h3>За 30 дней</h3><div class="row" style="margin-top:6px;gap:14px"><span><span class="mono b ink">12</span> <span class="small muted">отправлено</span></span><span><span class="mono b ink">5</span> <span class="small muted">ответили</span></span><span><span class="mono b ink">3</span> <span class="small muted">заказа · 43 %</span></span></div></div><div><h3>Где используется</h3><div class="row" style="margin-top:6px;gap:6px"><span class="chip">Правило «за 14 дней до даты»</span><span class="chip">Кнопка в очереди</span></div></div></div></div></div>'))

# --- A2. Правка на месте: карандаш у шаблона + сводка правил над очередью с раскрытой панелью ---
RULES_TOP=('<div style="padding:10px 16px;border-bottom:1px solid var(--border)"><div class="row small" style="gap:6px"><span class="muted" style="margin-right:2px">Правила:</span><span class="chip">14 дн</span><span class="chip">7 дн</span><span class="chip">3 дн</span><span class="chip">накануне</span><span class="chip">90 дн</span><span class="spacer"></span><a style="text-decoration:none;font-weight:500">Изменить</a></div></div>'
 '<div class="pop" style="left:16px;top:44px"><div class="card-hd"><h2>Правила очереди</h2><div class="spacer"></div><span class="iconbtn">'+CLOSE+'</span></div><div>'
 +rule('За 14 дней до даты','шаблон «Дата через 14 дней»')+rule('За 7 дней до даты','шаблон «Дата через 7 дней»')+rule('За 3 дня до даты','если заказа ещё нет')+rule('Накануне','если заказа ещё нет')+rule('90 дней без заказа','не чаще раза в месяц')
 +'<div class="lrow" style="min-height:52px"><span class="toggle on"><i></i></span><div><div class="t">Тихие часы 21:00–09:00</div><div class="s">и никому без согласия</div></div><span class="r"></span></div>'
 '</div><div class="drawer-ft"><span class="spacer"></span><span class="btn ghost sm">Отмена</span><span class="btn primary sm">Готово</span></div></div>')
A2_BODY = a_header(SEG) + two_cols(queue_card(top=RULES_TOP), focus_card('template'))

# --- A3. Боковая панель настроек поверх очереди ---
DRAWER=('<div class="scrim"></div><div class="drawer"><div class="drawer-hd"><h2 style="font-size:17px">Настройки напоминаний</h2><div class="spacer"></div><span class="iconbtn">'+CLOSE+'</span></div>'
 '<div class="tabs" style="margin:0;padding:0 18px"><span class="tab">Правила</span><span class="tab on">Шаблоны<span class="cnt">9</span></span><span class="tab">Тихие часы</span></div>'
 '<div class="drawer-bd">'
 '<div class="lrow sel" style="min-height:auto;display:block;padding:12px 18px"><div class="row"><span class="b ink">Дата через 14 дней</span>'+tag('за 14 дней','acc')+'<span class="spacer"></span><span class="small muted">12 отправок · 3 заказа</span></div>'
 '<div class="row" style="margin:8px 0 6px;gap:6px"><span class="var">{имя}</span><span class="var">{получатель}</span><span class="var">{повод}</span><span class="var">{магазин}</span></div>'
 '<div class="editor edit" style="min-height:96px;font-size:13px">'+TPL+'</div><div class="row" style="margin-top:8px;gap:8px"><span class="btn primary sm">Сохранить</span><span class="btn ghost sm">Отмена</span></div></div>'
 +trow('Дата через 7 дней','за 7 дней · 9 отправок · 2 заказа','<span class="btn xs">Изменить</span>')
 +trow('Дата через 3 дня','за 3 дня · 4 отправки','<span class="btn xs">Изменить</span>')
 +trow('Дата завтра','накануне · 2 отправки','<span class="btn xs">Изменить</span>')
 +trow('Давно не заказывал','90 дней · 6 отправок','<span class="btn xs">Изменить</span>')
 +trow('Заказ принят','из панели заказа','<span class="btn xs">Изменить</span>')
 +trow('Букет вручён','из панели заказа · с фото','<span class="btn xs">Изменить</span>')
 +'</div><div class="drawer-ft"><span class="btn sm">Новый шаблон</span><span class="spacer"></span><span class="small muted">Очередь продолжает работать под панелью</span></div></div>')
A3_BODY = a_header(SEG+'<span class="btn">'+GEAR+'Настройки напоминаний</span>') + two_cols(queue_card(), focus_card()) + DRAWER

# --- A4. Полоса настроек под заголовком ---
def strip_card(icon,t,s,btn):
    return '<div class="card"><span class="ic">'+icon+'</span><div style="min-width:0;flex:1"><div class="t">'+t+'</div><div class="s">'+s+'</div></div><span class="btn sm">'+btn+'</span></div>'
STRIP=('<div class="strip">'
 +strip_card(ICONS['reminders'],'Правила','За 14, 7, 3 дня и накануне · давние 90 дней, раз в месяц','Изменить')
 +strip_card('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"></rect><path d="M3 9h18"></path><path d="M7 13h7M7 16.5h4"></path></svg>','Шаблоны · 9','Изменён вчера: «Дата через 7 дней» · лучший по заказам: «За 14 дней»','Открыть')
 +strip_card(ICONS['today'],'Тихие часы и согласия','Не пишем 21:00–09:00 · без согласия 1 клиент','Изменить')
 +'</div>')
A4_BODY = a_header(SEG) + STRIP + two_cols(queue_card(trim=True), focus_card())

# --- A5. Подменю в боковой навигации ---
A5_BODY = a_header(SEG) + two_cols(queue_card(), focus_card())

open('Main.dc.html','w',encoding='utf-8').write(page(MAIN_BODY))
open('OptionA1.dc.html','w',encoding='utf-8').write(page(A1_BODY))
open('OptionA2.dc.html','w',encoding='utf-8').write(page(A2_BODY))
open('OptionA3.dc.html','w',encoding='utf-8').write(page(A3_BODY))
open('OptionA4.dc.html','w',encoding='utf-8').write(page(A4_BODY))
RAIL_SUB=True
open('OptionA5.dc.html','w',encoding='utf-8').write(page(A5_BODY))
RAIL_SUB=False
open('Funnel.dc.html','w',encoding='utf-8').write(page(B_BODY))
open('Calendar.dc.html','w',encoding='utf-8').write(page(C_BODY))
open('Stream.dc.html','w',encoding='utf-8').write(page(D_BODY))

canvas={
 "pages":[{"id":"page-1","name":"Вариант A: где живут шаблоны и правила"},{"id":"page-2","name":"Отклонённые направления B, C, D"}],
 "artboards":[
  {"file":"Main.dc.html","title":"A · Очередь (как выбрано)","x":0,"y":0,"w":1440,"h":900,"page":"page-1"},
  {"file":"OptionA1.dc.html","title":"A1 · Вкладки страницы","x":1560,"y":0,"w":1440,"h":900,"page":"page-1"},
  {"file":"OptionA2.dc.html","title":"A2 · Правка на месте","x":3120,"y":0,"w":1440,"h":900,"page":"page-1"},
  {"file":"OptionA3.dc.html","title":"A3 · Боковая панель","x":0,"y":1120,"w":1440,"h":900,"page":"page-1"},
  {"file":"OptionA4.dc.html","title":"A4 · Полоса настроек","x":1560,"y":1120,"w":1440,"h":900,"page":"page-1"},
  {"file":"OptionA5.dc.html","title":"A5 · Подменю в навигации","x":3120,"y":1120,"w":1440,"h":900,"page":"page-1"},
  {"file":"Funnel.dc.html","title":"B · Воронка","x":0,"y":0,"w":1440,"h":900,"page":"page-2"},
  {"file":"Calendar.dc.html","title":"C · Календарь и правила","x":1560,"y":0,"w":1440,"h":900,"page":"page-2"},
  {"file":"Stream.dc.html","title":"D · Лента действий","x":3120,"y":0,"w":1440,"h":900,"page":"page-2"}
 ],
 "annotations":[
  {"id":"note-main","x":0,"y":-150,"w":560,"page":"page-1","text":"A · Очередь, как есть. Проблема: «Шаблоны» спрятаны в кнопку справа сверху, правила не видны вообще. Пять вариантов рядом меняют только это, структура очереди одна и та же."},
  {"id":"note-a1","x":1560,"y":-190,"w":560,"page":"page-1","text":"A1 · Вкладки страницы: Очередь · Шаблоны · Правила · Статистика. Шаблоны и правила равноправны с очередью, видны всегда, у них есть своя полноценная страница с редактором, предпросмотром и цифрами по каждому шаблону. Минус: редактирование уводит из очереди, менеджер теряет контекст «этому клиенту»."},
  {"id":"note-a2","x":3120,"y":-230,"w":560,"page":"page-1","text":"A2 · Правка на месте. Карандаш у активного шаблона прямо в очереди: правишь текст там же, где им пользуешься, с выбором «сохранить для всех» или «только это сообщение». Правила показаны строкой над очередью и раскрываются панелью. Плюс: ноль переходов, контекст сохраняется. Минус: легко задеть общий шаблон, поэтому нужна явная фиолетовая полоса «вы меняете шаблон для всех»."},
  {"id":"note-a3","x":0,"y":930,"w":560,"page":"page-1","text":"A3 · Боковая панель «Настройки напоминаний» поверх очереди: правила, шаблоны и тихие часы в одном месте, очередь остаётся видна и живёт под панелью. Плюс: одна очевидная кнопка с шестерёнкой, всё настраивается без ухода со страницы. Минус: в 460 px тесно для длинных шаблонов, панель перекрывает предпросмотр."},
  {"id":"note-a4","x":1560,"y":930,"w":560,"page":"page-1","text":"A4 · Полоса настроек под заголовком: три плитки, Правила, Шаблоны, Тихие часы, каждая с текущим состоянием и кнопкой. Настройки видны каждый день, ничего искать не нужно. Минус: полоса съедает высоту, и редактирование всё равно уходит в отдельное окно или страницу."},
  {"id":"note-a5","x":3120,"y":930,"w":560,"page":"page-1","text":"A5 · Подменю в боковой навигации: Напоминания раскрываются на Очередь · Шаблоны · Правила. Шаблоны доступны из любого экрана, это привычный паттерн настроек модуля. Минус: меню растёт, а редактор шаблона по-прежнему вне контекста клиента."},
  {"id":"note-p2","x":0,"y":-150,"w":560,"page":"page-2","text":"Направления, от которых отказались после выбора A: воронка, календарь с правилами, лента действий. Оставлены для истории решения."}
 ],
 "launch":{"view":"canvas","page":"page-1"}
}
json.dump(canvas,open('canvas.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('built variants')
