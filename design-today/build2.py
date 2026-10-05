# -*- coding: utf-8 -*-
import json
from lib import ICONS
NOW=10*60+40
def mins(t):
    h,m=t.split(':');return int(h)*60+int(m)
def dur(m):
    h,mm=divmod(abs(m),60);return (str(h)+' ч '+str(mm)+' м') if h else (str(mm)+' мин')
# id, window, client, recipient, items, sum, address, status, courier, badges
O=[
 (2494,'08:00–10:00','Эльмира Касымова','','Букет из тюльпанов','3 100','ул. Байтик Баатыра 41','route','Канат',['не дозвонился']),
 (2483,'10:00–12:00','Айгерим Ниязова','Салтанат','Авторский букет','3 300','ул. Киевская 95, кв. 12','route','Улан',[]),
 (2487,'10:00–12:00','Гульнара Асанова','офис','Авторский букет','3 500','ул. Ахунбаева 119','route','Яндекс',[]),
 (2484,'12:00–14:00','Айбек Токтосунов','Айгуль','25 роз 60 см','6 550','ул. Исанова 105, офис 4','ready','Улан',[]),
 (2491,'12:00–14:00','Бакыт Жээнбеков','','Букет из хризантем','2 500','ул. Панфилова 42, роддом №2','work','Канат',[]),
 (2492,'13:00','Мээрим Жолдошева','','Корзина фрукты и цветы','5 500','самовывоз','ready',None,[]),
 (2485,'14:00–16:00','Эркин Абдыраимов','Приёмная «Азия Трейд»','Композиция в корзине ×2','11 300','пр. Чуй 155, БЦ «Аврора»','work','Канат',['по счёту']),
 (2488,'16:00–18:00','Данияр Осмонов','Асель','Коробка шляпная','5 100','мкр. Джал 23, д. 7','new','Улан',['наличные']),
 (2486,'17:00','Айсулуу Токтосунова','','Букет дня','2 500','самовывоз','new',None,[]),
 (2493,'18:00–20:00','Салтанат Орозова','','Букет дня, упаковка премиум','3 200','мкр. Асанбай 24/1','new','Улан',['наличные','домофон не работает']),
 (2482,'08:00–10:00','Данияр Осмонов','Нургуль','Букет дня','2 800','пр. Чуй 155, 5 этаж','done','Канат',['жалоба']),
 (2477,'08:00–10:00','Айдай Сулайманова','','Букет дня','2 800','ул. Медерова 44, кв. 9','done','Улан',[]),
]
STATUS={'new':'Ждёт флориста','work':'У флориста','ready':'Собран','route':'В пути','done':'Вручён'}
ACTION={'new':'Передать флористу','work':'Собран','ready':'Курьер забрал','route':'Вручён','done':''}
def timing(o):
    id,win,c,rec,items,sm,addr,st,cour,badges=o
    if st=='done':
        return ('mute','вручён')
    a=win.split('–')[0];b=win.split('–')[-1];s=mins(a);e=mins(b)
    if e<NOW: return ('crit','опоздание '+dur(NOW-e))
    if s<=NOW<=e: return ('ok','окно идёт, до '+b+' '+dur(e-NOW))
    if s-NOW<=90 and st in('new','work'): return ('warn','до '+a+' '+dur(s-NOW))
    return ('mute','до '+a+' '+dur(s-NOW))
def ticket(o,dark):
    id,win,c,rec,items,sm,addr,st,cour,badges=o
    tone,tt=timing(o)
    if st=='ready' and o[7]=='ready': tone='ok' if tone=='mute' else tone
    act=ACTION[st]
    if st=='ready' and cour is None: act='Выдан'
    if st=='ready' and cour=='Яндекс': act='Передан Яндексу'
    b=''.join('<span class="badge %s">%s</span>'%('crit' if x in('не дозвонился','жалоба') else 'warn' if x=='по счёту' else '',x) for x in badges)
    who=c+(' → '+rec if rec else '')
    return ('<div class="tk %s%s"><div class="tk-top"><span class="tk-win">%s</span><span class="tk-st">%s</span></div><div class="tk-time %s">%s</div>'
            '<div class="tk-items">%s</div><div class="tk-who">%s</div><div class="tk-addr">%s · %s сом%s</div>'
            '%s<div class="tk-foot">%s<span class="tk-more">···</span></div></div>')%(
            tone,' done' if st=='done' else '',win,STATUS[st],tone,tt,items,who,addr,sm,(' · '+cour) if cour else '',
            ('<div class="tk-badges">'+b+'</div>') if b else '',
            ('<span class="tk-btn %s">%s</span>'%('primary' if tone!='mute' or st=='ready' else '',act)) if act else '<span class="tk-done">вручён, фото есть</span>')
def wall(dark):
    order=[o for o in O if o[7]!='done']+[o for o in O if o[7]=='done']
    return ('<div class="hd"><div><div class="hd-day">Четверг, 19 ноября</div><div class="hd-clock">10:40</div></div>'
            '<div class="hd-nums"><div><b>12</b>заказов</div><div><b class="ok">2</b>вручено</div><div><b>3</b>в пути</div><div><b class="warn">5</b>ждут сборки</div><div><b class="crit">1</b>опаздывает</div></div>'
            '<div class="hd-filters"><span class="f on">Все</span><span class="f">Собрать <i>5</i></span><span class="f">В пути <i>3</i></span><span class="f">Самовывоз <i>2</i></span><span class="f">Вручено <i>2</i></span></div></div>'
            '<div class="strip"><span class="strip-l">Вне заказов</span><span class="pin crit">Жалоба по №2482 · Данияр</span><span class="pin">Счёт №118 бухгалтерии</span><span class="pin">Спросить, как букет №2477</span><span class="pin">Написать 6 клиентам</span><span class="pin mute">+2</span></div>'
            '<div class="wall">'+''.join(ticket(o,dark) for o in order)+'</div>')
# ---------- timeline ----------
HOUR=64;H0=8
def y(m): return int((m-H0*60)/60*HOUR)
def tl_block(win,items,tone):
    a,b=win.split('–');top=y(mins(a));h=y(mins(b))-top
    return '<div class="win %s" style="top:%dpx;height:%dpx"><div class="win-l">%s</div>%s</div>'%(tone,top,h,win,''.join(items))
def tl_row(o):
    id,win,c,rec,items,sm,addr,st,cour,badges=o
    tone={'new':'info','work':'acc','ready':'ok','route':'ok','done':'mute'}[st]
    return '<div class="orow"><span class="ost %s"></span><span class="on">№%d</span><span class="ow">%s</span><span class="oi">%s</span><span class="os">%s</span><span class="oc">%s</span></div>'%(tone,id,(rec or c),items,STATUS[st],cour or 'самовывоз')
def pickup(o):
    id,win,c,rec,items,sm,addr,st,cour,badges=o
    return '<div class="pick" style="top:%dpx"><span class="pk-t">%s</span> самовывоз · №%d · %s · <b>%s</b></div>'%(y(mins(win)),win,id,c,STATUS[st])
def timeline(dark):
    wins={}
    for o in O:
        if '–' in o[1]: wins.setdefault(o[1],[]).append(o)
    blocks=''
    for w,os_ in sorted(wins.items()):
        e=mins(w.split('–')[1]);s=mins(w.split('–')[0])
        tone='past' if e<=NOW else 'cur' if s<=NOW<=e else 'next' if s-NOW<=120 else ''
        blocks+=tl_block(w,[tl_row(o) for o in os_],tone)
    for o in O:
        if '–' not in o[1]: blocks+=pickup(o)
    hours=''.join('<div class="hr" style="top:%dpx"><span>%02d:00</span></div>'%(y(h*60),h) for h in range(H0,21))
    flags=[(9*60+35,'crit','Не дозвонился №2494'),(10*60+20,'crit','Жалоба №2482'),(11*60+40,'info','Спросить, как букет №2477'),(13*60,'warn','Выдать №2492'),(14*60,'info','Счёт №118 бухгалтерии'),(15*60,'info','Написать 6 клиентам'),(18*60,'warn','Позвонить: домофон №2493')]
    fl=''.join('<div class="flag %s" style="top:%dpx"><i></i>%s</div>'%(t,y(m)-9,x) for m,t,x in flags)
    now='<div class="now" style="top:%dpx"><span>10:40</span></div>'%y(NOW)
    side=('<div class="side"><div class="side-h">Сейчас · окно 10:00–12:00</div>'
          '<div class="sc"><div class="sc-t">№2483 · Салтанат</div><div class="sc-s">Улан в пути с 10:12 · ул. Киевская 95</div><span class="tk-btn primary">Вручён</span></div>'
          '<div class="sc"><div class="sc-t">№2487 · офис Ахунбаева 119</div><div class="sc-s">Яндекс Доставка с 10:20</div><span class="tk-btn">Вручён</span></div>'
          '<div class="sc crit"><div class="sc-t">№2494 · Эльмира · опоздание 40 мин</div><div class="sc-s">Канат не дозвонился в 09:35</div><span class="tk-btn primary">Позвонить</span><span class="tk-btn">Связались</span></div>'
          '<div class="side-h">Дальше · 12:00, через 1 ч 20 м</div>'
          '<div class="sc"><div class="sc-t">№2484 · Айгуль · 25 роз</div><div class="sc-s">собран, фото есть · Улан заберёт после 10:00 окна</div><span class="tk-btn">Курьер забрал</span></div>'
          '<div class="sc warn"><div class="sc-t">№2491 · Бакыт · хризантемы</div><div class="sc-s">у Бермет с 10:30 · роддом №2, встретит у входа</div><span class="tk-btn primary">Собран</span></div>'
          '<div class="sc"><div class="sc-t">№2492 · Мээрим · самовывоз 13:00</div><div class="sc-s">собран, ждёт клиента</div><span class="tk-btn">Выдан</span></div></div>')
    return ('<div class="hd"><div><div class="hd-day">Четверг, 19 ноября</div><div class="hd-clock">10:40</div></div>'
            '<div class="hd-nums"><div><b>12</b>заказов</div><div><b class="ok">2</b>вручено</div><div><b>3</b>в пути</div><div><b class="warn">5</b>ждут сборки</div><div><b class="crit">1</b>опаздывает</div></div><div class="hd-filters"><span class="f on">День</span><span class="f">Неделя</span></div></div>'
            '<div class="tl-wrap"><div class="tl"><div class="hours">'+hours+'</div><div class="flags">'+fl+'</div><div class="lanes">'+blocks+now+'</div></div>'+side+'</div>')
# ---------- styles ----------
LIGHT="""
:root{--bg:#FFFFFF;--ink:#141414;--mute:#6E6E6E;--line:#E7E7E7;--soft:#F5F5F4;--ok:#1B9E5A;--warn:#E39B00;--crit:#E5484D;--info:#2F6FED;--acc:#7C3AED;--ok-bg:#E7F6EE;--warn-bg:#FFF4DC;--crit-bg:#FDE8E9;--info-bg:#E8EFFF;--mono:'JetBrains Mono',ui-monospace,Menlo,monospace}
body{margin:0;background:#fff}
.root{width:1440px;height:1000px;background:var(--bg);color:var(--ink);font-family:'Onest',ui-sans-serif,system-ui,sans-serif;font-size:15px;overflow:hidden;display:flex;flex-direction:column}
.nav{height:56px;display:flex;align-items:center;gap:28px;padding:0 32px;border-bottom:1px solid var(--line)}
.nav .logo{font-weight:800;letter-spacing:-.02em;font-size:17px;margin-right:12px}.nav a{color:var(--mute);font-weight:600;text-decoration:none}.nav a.on{color:var(--ink);border-bottom:2px solid var(--ink);padding-bottom:16px;margin-bottom:-18px}
.nav .sp{margin-left:auto}.nav .ub{width:34px;height:34px;border-radius:50%;background:var(--soft);display:grid;place-items:center;font-weight:700;font-size:12px}
.nav .plus{background:var(--ink);color:#fff;border-radius:10px;padding:8px 14px;font-weight:700}
.body{padding:20px 32px 0;flex:1;min-height:0;display:flex;flex-direction:column}
.hd{display:flex;align-items:flex-end;gap:36px;margin-bottom:14px}
.hd-day{color:var(--mute);font-weight:600}.hd-clock{font-size:44px;font-weight:800;letter-spacing:-.04em;line-height:1;font-family:var(--mono)}
.hd-nums{display:flex;gap:26px;padding-bottom:4px}.hd-nums div{display:flex;flex-direction:column;color:var(--mute);font-size:13px;font-weight:600}.hd-nums b{font-size:26px;letter-spacing:-.03em;line-height:1.1;color:var(--ink);font-family:var(--mono)}
.hd-nums b.ok{color:var(--ok)}.hd-nums b.warn{color:var(--warn)}.hd-nums b.crit{color:var(--crit)}
.hd-filters{margin-left:auto;display:flex;gap:6px;padding-bottom:6px}.f{padding:8px 14px;border-radius:999px;background:var(--soft);font-weight:600;color:var(--mute)}.f.on{background:var(--ink);color:#fff}.f i{font-style:normal;opacity:.6;margin-left:4px;font-family:var(--mono);font-size:12px}
.strip{display:flex;align-items:center;gap:8px;padding:10px 0 14px;border-top:1px solid var(--line)}.strip-l{color:var(--mute);font-weight:600;font-size:13px;margin-right:6px}
.pin{padding:6px 10px;border-radius:8px;background:var(--soft);font-weight:600;font-size:13px}.pin.crit{background:var(--crit-bg);color:var(--crit)}.pin.mute{color:var(--mute)}
.wall{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;align-content:start}
.tk{border:1px solid var(--line);border-radius:16px;padding:14px 16px;display:flex;flex-direction:column;gap:6px;background:#fff;position:relative;min-height:236px}
.tk.crit{border-color:var(--crit);box-shadow:0 0 0 3px var(--crit-bg)}.tk.warn{border-color:var(--warn)}.tk.ok{border-color:var(--ok)}
.tk.done{opacity:.55}
.tk-top{display:flex;justify-content:space-between;align-items:baseline}.tk-win{font-family:var(--mono);font-weight:700;font-size:20px;letter-spacing:-.02em}.tk-st{font-weight:700;font-size:13px;color:var(--mute)}
.tk-time{font-weight:700;font-size:13px}.tk-time.crit{color:var(--crit)}.tk-time.warn{color:var(--warn)}.tk-time.ok{color:var(--ok)}.tk-time.mute{color:var(--mute)}
.tk-items{font-size:19px;font-weight:800;letter-spacing:-.02em;line-height:1.15;margin-top:6px}.tk-who{font-weight:600}.tk-addr{color:var(--mute);font-size:13px}
.tk-badges{display:flex;gap:6px;flex-wrap:wrap}.badge{font-size:12px;font-weight:700;padding:3px 8px;border-radius:6px;background:var(--soft);color:var(--mute)}.badge.crit{background:var(--crit-bg);color:var(--crit)}.badge.warn{background:var(--warn-bg);color:var(--warn)}
.tk-foot{margin-top:auto;display:flex;gap:8px;align-items:center;padding-top:8px}
.tk-btn{flex:1;height:44px;border-radius:12px;border:1.5px solid var(--ink);display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:15px}.tk-btn.primary{background:var(--ink);color:#fff}
.tk-more{width:44px;height:44px;border-radius:12px;border:1.5px solid var(--line);display:inline-grid;place-items:center;color:var(--mute);font-weight:800}
.tk-done{color:var(--mute);font-weight:600}
/* timeline */
.tl-wrap{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:24px;flex:1;min-height:0}
.tl{position:relative;display:grid;grid-template-columns:64px 200px minmax(0,1fr);height:830px;overflow:hidden}
.hours{position:relative}.hr{position:absolute;left:0;right:0;font-family:var(--mono);font-size:12px;font-weight:700;color:var(--mute)}.hr::after{content:"";position:absolute;left:60px;width:1200px;top:8px;border-top:1px dashed var(--line)}
.flags{position:relative;border-right:1px solid var(--line)}
.flag{position:absolute;left:8px;right:10px;font-size:12px;font-weight:700;padding:3px 8px 3px 20px;border-radius:7px;background:var(--soft);color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.flag i{position:absolute;left:7px;top:8px;width:7px;height:7px;border-radius:50%;background:var(--info)}.flag.crit{background:var(--crit-bg);color:var(--crit)}.flag.crit i{background:var(--crit)}.flag.warn{background:var(--warn-bg);color:var(--warn)}.flag.warn i{background:var(--warn)}
.lanes{position:relative;padding-left:16px}
.win{position:absolute;left:16px;right:8px;border-radius:14px;background:var(--soft);padding:10px 12px 8px 76px}
.win.past{opacity:.5}.win.cur{background:var(--ok-bg);box-shadow:inset 0 0 0 2px var(--ok)}.win.next{background:var(--warn-bg)}
.win-l{position:absolute;left:12px;top:10px;font-family:var(--mono);font-weight:800;font-size:13px}
.orow{display:grid;grid-template-columns:10px 62px 150px minmax(0,1fr) 110px 70px;gap:10px;align-items:center;height:30px;font-size:13px;font-weight:600}
.ost{width:10px;height:10px;border-radius:50%}.ost.ok{background:var(--ok)}.ost.acc{background:var(--acc)}.ost.info{background:var(--info)}.ost.mute{background:#C9C9C9}
.on{font-family:var(--mono);color:var(--mute)}.oi{color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.os{color:var(--mute)}.oc{color:var(--mute);text-align:right}
.pick{position:absolute;left:16px;right:8px;height:26px;display:flex;align-items:center;gap:6px;padding:0 12px;border-radius:8px;background:var(--info-bg);color:var(--info);font-size:13px;font-weight:600;transform:translateY(-13px)}.pk-t{font-family:var(--mono);font-weight:800}
.now{position:absolute;left:0;right:0;border-top:2px solid var(--crit);z-index:3}.now span{position:absolute;left:-58px;top:-11px;background:var(--crit);color:#fff;font-family:var(--mono);font-weight:800;font-size:12px;padding:2px 6px;border-radius:6px}
.side{display:flex;flex-direction:column;gap:10px}.side-h{font-weight:800;font-size:15px;margin:6px 0 2px;letter-spacing:-.01em}
.sc{border:1px solid var(--line);border-radius:14px;padding:12px 14px;display:flex;flex-wrap:wrap;gap:8px}.sc-t{font-weight:800;width:100%}.sc-s{color:var(--mute);font-size:13px;width:100%}.sc.crit{border-color:var(--crit);background:var(--crit-bg)}.sc.warn{border-color:var(--warn);background:var(--warn-bg)}
"""
DARK="""
:root{--bg:#0E1116;--panel:#161A21;--panel2:#1E232C;--ink:#EEF1F5;--mute:#96A0AF;--line:#262C36;--ok:#34D399;--warn:#FBBF24;--crit:#F87171;--info:#60A5FA;--acc:#C084FC;--now:#22D3EE;--ok-bg:rgba(52,211,153,.14);--warn-bg:rgba(251,191,36,.14);--crit-bg:rgba(248,113,113,.16);--info-bg:rgba(96,165,250,.14);--mono:'JetBrains Mono',ui-monospace,Menlo,monospace}
body{margin:0;background:#0E1116}
.root{width:1440px;height:1000px;background:var(--bg);color:var(--ink);font-family:'Manrope',ui-sans-serif,system-ui,sans-serif;font-size:15px;overflow:hidden;display:grid;grid-template-columns:72px minmax(0,1fr)}
.rail{border-right:1px solid var(--line);display:flex;flex-direction:column;align-items:center;padding:16px 0;gap:6px}
.rail .mark{width:38px;height:38px;border-radius:12px;background:linear-gradient(135deg,#34D399,#22D3EE);margin-bottom:14px}
.rail .ic{width:44px;height:44px;border-radius:12px;display:grid;place-items:center;color:var(--mute)}.rail .ic.on{background:var(--panel2);color:var(--ink)}.rail .ic svg{width:20px;height:20px}
.body{padding:22px 28px 0;display:flex;flex-direction:column;min-height:0}
.hd{display:flex;align-items:flex-end;gap:36px;margin-bottom:16px}
.hd-day{color:var(--mute);font-weight:600}.hd-clock{font-size:46px;font-weight:800;letter-spacing:-.04em;line-height:1;font-family:var(--mono);color:var(--now)}
.hd-nums{display:flex;gap:26px;padding-bottom:4px}.hd-nums div{display:flex;flex-direction:column;color:var(--mute);font-size:13px;font-weight:600}.hd-nums b{font-size:26px;letter-spacing:-.03em;line-height:1.1;color:var(--ink);font-family:var(--mono)}
.hd-nums b.ok{color:var(--ok)}.hd-nums b.warn{color:var(--warn)}.hd-nums b.crit{color:var(--crit)}
.hd-filters{margin-left:auto;display:flex;gap:6px;padding-bottom:6px}.f{padding:8px 14px;border-radius:10px;background:var(--panel);font-weight:700;color:var(--mute);border:1px solid var(--line)}.f.on{background:var(--ink);color:#0E1116;border-color:var(--ink)}.f i{font-style:normal;opacity:.7;margin-left:4px;font-family:var(--mono);font-size:12px}
.strip{display:flex;align-items:center;gap:8px;padding:10px 0 14px;border-top:1px solid var(--line)}.strip-l{color:var(--mute);font-weight:700;font-size:13px;margin-right:6px}
.pin{padding:6px 10px;border-radius:8px;background:var(--panel2);font-weight:700;font-size:13px}.pin.crit{background:var(--crit-bg);color:var(--crit)}.pin.mute{color:var(--mute)}
.wall{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;align-content:start}
.tk{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:6px;min-height:236px;border-top-width:4px}
.tk.crit{border-top-color:var(--crit);background:linear-gradient(180deg,var(--crit-bg),var(--panel) 40%)}.tk.warn{border-top-color:var(--warn)}.tk.ok{border-top-color:var(--ok)}.tk.mute{border-top-color:var(--line)}
.tk.done{opacity:.45}
.tk-top{display:flex;justify-content:space-between;align-items:baseline}.tk-win{font-family:var(--mono);font-weight:800;font-size:20px;letter-spacing:-.02em}.tk-st{font-weight:700;font-size:12px;color:var(--mute);text-transform:uppercase;letter-spacing:.06em}
.tk-time{font-weight:700;font-size:13px;font-family:var(--mono)}.tk-time.crit{color:var(--crit)}.tk-time.warn{color:var(--warn)}.tk-time.ok{color:var(--ok)}.tk-time.mute{color:var(--mute)}
.tk-items{font-size:19px;font-weight:800;letter-spacing:-.02em;line-height:1.15;margin-top:6px}.tk-who{font-weight:600}.tk-addr{color:var(--mute);font-size:13px}
.tk-badges{display:flex;gap:6px;flex-wrap:wrap}.badge{font-size:12px;font-weight:700;padding:3px 8px;border-radius:6px;background:var(--panel2);color:var(--mute)}.badge.crit{background:var(--crit-bg);color:var(--crit)}.badge.warn{background:var(--warn-bg);color:var(--warn)}
.tk-foot{margin-top:auto;display:flex;gap:8px;align-items:center;padding-top:8px}
.tk-btn{flex:1;height:44px;border-radius:12px;border:1.5px solid var(--line);display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:15px;background:var(--panel2)}.tk-btn.primary{background:var(--ok);color:#0E1116;border-color:var(--ok)}
.tk-more{width:44px;height:44px;border-radius:12px;border:1.5px solid var(--line);display:inline-grid;place-items:center;color:var(--mute);font-weight:800}
.tk-done{color:var(--mute);font-weight:600}
.tl-wrap{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:24px;flex:1;min-height:0}
.tl{position:relative;display:grid;grid-template-columns:64px 200px minmax(0,1fr);height:830px;overflow:hidden}
.hours{position:relative}.hr{position:absolute;left:0;right:0;font-family:var(--mono);font-size:12px;font-weight:700;color:var(--mute)}.hr::after{content:"";position:absolute;left:60px;width:1200px;top:8px;border-top:1px dashed var(--line)}
.flags{position:relative;border-right:1px solid var(--line)}
.flag{position:absolute;left:8px;right:10px;font-size:12px;font-weight:700;padding:3px 8px 3px 20px;border-radius:7px;background:var(--panel2);color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.flag i{position:absolute;left:7px;top:8px;width:7px;height:7px;border-radius:50%;background:var(--info)}.flag.crit{background:var(--crit-bg);color:var(--crit)}.flag.crit i{background:var(--crit)}.flag.warn{background:var(--warn-bg);color:var(--warn)}.flag.warn i{background:var(--warn)}
.lanes{position:relative;padding-left:16px}
.win{position:absolute;left:16px;right:8px;border-radius:14px;background:var(--panel);border:1px solid var(--line);padding:10px 12px 8px 76px}
.win.past{opacity:.45}.win.cur{border-color:var(--ok);background:var(--ok-bg)}.win.next{border-color:var(--warn);background:var(--warn-bg)}
.win-l{position:absolute;left:12px;top:10px;font-family:var(--mono);font-weight:800;font-size:13px}
.orow{display:grid;grid-template-columns:10px 62px 150px minmax(0,1fr) 110px 70px;gap:10px;align-items:center;height:30px;font-size:13px;font-weight:600}
.ost{width:10px;height:10px;border-radius:50%}.ost.ok{background:var(--ok)}.ost.acc{background:var(--acc)}.ost.info{background:var(--info)}.ost.mute{background:#4B5563}
.on{font-family:var(--mono);color:var(--mute)}.oi{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.os{color:var(--mute)}.oc{color:var(--mute);text-align:right}
.pick{position:absolute;left:16px;right:8px;height:26px;display:flex;align-items:center;gap:6px;padding:0 12px;border-radius:8px;background:var(--info-bg);color:var(--info);font-size:13px;font-weight:600;transform:translateY(-13px)}.pk-t{font-family:var(--mono);font-weight:800}
.now{position:absolute;left:0;right:0;border-top:2px solid var(--now);z-index:3;box-shadow:0 0 12px rgba(34,211,238,.6)}.now span{position:absolute;left:-58px;top:-11px;background:var(--now);color:#0E1116;font-family:var(--mono);font-weight:800;font-size:12px;padding:2px 6px;border-radius:6px}
.side{display:flex;flex-direction:column;gap:10px}.side-h{font-weight:800;font-size:15px;margin:6px 0 2px}
.sc{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 14px;display:flex;flex-wrap:wrap;gap:8px}.sc-t{font-weight:800;width:100%}.sc-s{color:var(--mute);font-size:13px;width:100%}.sc.crit{border-color:var(--crit);background:var(--crit-bg)}.sc.warn{border-color:var(--warn);background:var(--warn-bg)}
"""
def shell(body,dark):
    fonts='<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&amp;family=Onest:wght@400;500;600;700;800&amp;family=JetBrains+Mono:wght@600;700;800&amp;display=swap">'
    if dark:
        nav=('<div class="rail"><div class="mark"></div>'+''.join('<div class="ic%s">%s</div>'%(' on' if k=='today' else '',ICONS[k]) for k in ['today','orders','clients','reminders','deliveries','settings'])+'</div><div class="body">'+body+'</div>')
    else:
        nav=('<div class="nav"><span class="logo">Tapme Flowers</span><a class="on">Сегодня</a><a>Заказы</a><a>Клиенты</a><a>Напоминания</a><a>Доставка</a><a>Настройки</a><span class="sp"></span><span class="plus">+ Заказ</span><span class="ub">АИ</span></div><div class="body">'+body+'</div>')
    return ('<!doctype html>\n<html>\n<head>\n<meta charset="utf-8">\n<script src="./support.js"></script>\n</head>\n<body>\n<x-dc>\n<helmet>\n'+fonts+'\n<style>'+(DARK if dark else LIGHT)+'</style>\n</helmet>\n<div class="root">'+nav+'</div>\n</x-dc>\n</body>\n</html>\n')
open('WallLight.dc.html','w',encoding='utf-8').write(shell(wall(False),False))
open('WallDark.dc.html','w',encoding='utf-8').write(shell(wall(True),True))
open('TimelineLight.dc.html','w',encoding='utf-8').write(shell(timeline(False),False))
open('TimelineDark.dc.html','w',encoding='utf-8').write(shell(timeline(True),True))
canvas=json.load(open('canvas.json',encoding='utf-8'))
old=[dict(a,page='page-2') for a in canvas['artboards']]
oldn=[dict(n,page='page-2') for n in canvas['annotations']]
new=[
 {"file":"WallLight.dc.html","title":"Стена тикетов · светлая","x":0,"y":0,"w":1440,"h":1000,"page":"page-1"},
 {"file":"WallDark.dc.html","title":"Стена тикетов · тёмная","x":1560,"y":0,"w":1440,"h":1000,"page":"page-1"},
 {"file":"TimelineLight.dc.html","title":"Хронология дня · светлая","x":0,"y":1220,"w":1440,"h":1000,"page":"page-1"},
 {"file":"TimelineDark.dc.html","title":"Хронология дня · тёмная","x":1560,"y":1220,"w":1440,"h":1000,"page":"page-1"}]
newn=[
 {"id":"w-l","x":0,"y":-210,"w":600,"page":"page-1","text":"Стена тикетов. Заказ = плитка, как на кухонных экранах Toast и Square: крупное окно доставки, таймер («опоздание 40 мин», «до 12:00 1 ч 20 м»), состав крупно, получатель и адрес мелко, одна большая кнопка следующего шага. Порядок: опаздывающие, текущее окно, ближайшие, потом остальное, вручённые в конце и приглушены. Задачи вне заказов ужаты в одну строку сверху, ленты нет: события и так видны по плиткам. Светлый стиль: белый фон, чёрный текст, цвет только для состояния, шрифт Onest, таймеры моноширинным JetBrains Mono, навигация сверху вместо тёмной панели."},
 {"id":"w-d","x":1560,"y":-160,"w":600,"page":"page-1","text":"Та же стена в тёмном стиле «пульт»: как настоящие KDS-экраны в тёмных кухнях, меньше бликов на планшете у прилавка, цветная кромка плитки по срочности, зелёная главная кнопка. Узкая иконочная панель слева вместо широкой. Шрифт Manrope."},
 {"id":"t-l","x":0,"y":1010,"w":600,"page":"page-1","text":"Хронология дня. Вертикальная шкала 08:00–20:00 как в Google Calendar и Sunsama, окна доставки как блоки, внутри строки заказов, красная линия «сейчас 10:40». Прошедшие окна гаснут, текущее зелёное, ближайшее жёлтое, самовывозы точками на своём часе. Слева узкая дорожка задач, привязанных ко времени: «09:35 не дозвонился», «11:40 спросить, как букет», «13:00 выдать». Справа панель «Сейчас» и «Дальше» с большими кнопками, чтобы работать, не покидая экран."},
 {"id":"t-d","x":1560,"y":1010,"w":600,"page":"page-1","text":"Та же хронология в тёмном стиле: линия «сейчас» голубая со свечением, окна как панели, тот же принцип цвета по срочности. Хорошо смотрится на большом мониторе в подсобке, хуже на солнце у окна."}]
canvas={"pages":[{"id":"page-1","name":"Стена тикетов и хронология"},{"id":"page-2","name":"Отклонённые компоновки"}],"artboards":new+old,"annotations":newn+oldn,"launch":{"view":"canvas","page":"page-1"}}
json.dump(canvas,open('canvas.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('built metaphors')
