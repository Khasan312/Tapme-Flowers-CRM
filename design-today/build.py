# -*- coding: utf-8 -*-
import json, lib
from lib import ICONS, av, tag, WA_SVG, CHECK_SVG
lib.CSS += """
.task{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:12px;align-items:center;padding:10px 16px;border-top:1px solid var(--border)}.task:first-child{border-top:0}
.task .chk{width:20px;height:20px;border-radius:50%;border:2px solid var(--border-2);background:#fff;display:inline-block}.task.crit .chk{border-color:var(--crit)}.task.warn .chk{border-color:var(--warn)}.task.info .chk{border-color:var(--info)}
.task .t{font-weight:500;color:var(--ink)}.task .s{font-size:12px;color:var(--muted)}.task .acts{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.task-add{padding:10px 16px;border-top:1px solid var(--border)}.task-add div{height:32px;border:1px dashed var(--border-2);border-radius:8px;padding:0 10px;font-size:13px;color:var(--dim);display:flex;align-items:center;background:#fff}
.sel-xs{display:inline-flex;align-items:center;height:26px;border:1px solid var(--border);border-radius:7px;font-size:12px;padding:0 6px;background:#fff;color:var(--ink);gap:6px}
.thumb{width:36px;height:36px;border-radius:8px;overflow:hidden;background:var(--surface-2);flex:none}.thumb svg{width:100%;height:100%;display:block}
.feed-row{min-height:44px;padding:8px 16px}
.lrow .r.row{display:flex;gap:6px}
.tgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.tgrid .task{border-top:1px solid var(--border)}.tgrid .task:nth-child(2){border-top:0}
.root{height:1100px}
"""
_rail0=lib.rail
def rail():
    r=_rail0()
    return r.replace('<div class="nav-item on">'+ICONS['reminders'],'<div class="nav-item">'+ICONS['reminders']).replace('<div class="nav-item">'+ICONS['today'],'<div class="nav-item on">'+ICONS['today'])
lib.rail=rail
_topbar0=lib.topbar
def topbar():
    return _topbar0().replace('<div><h1>Напоминания</h1></div>','<div><h1>Сегодня</h1><div style="font-size:12px;color:var(--muted)">четверг, 19 ноября</div></div>')
lib.topbar=topbar
page=lib.page

def bouquet(seed):
    r=seed*9301+49297
    def rnd():
        nonlocal r
        r=(r*9301+49297)%233280
        return r/233280
    cols=['#F0B6C3','#E39BB2','#D8A4DC','#F5D58F','#F3E4E8','#E8C1D6','#F7C6B3']
    s='<svg viewBox="0 0 120 120" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg"><rect width="120" height="120" fill="#EDEFE8"></rect>'
    for i in range(7):
        x=30+rnd()*60;y=40+rnd()*40;rr=8+rnd()*8
        s+='<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="#6E9B63" transform="rotate(%d %.1f %.1f)"></ellipse>'%(x,y+30,rr*0.6,rr*1.4,(rnd()-0.5)*60,x,y+30)
    for j in range(11):
        cx=28+rnd()*64;cy=28+rnd()*44;cr=9+rnd()*9
        s+='<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"></circle><circle cx="%.1f" cy="%.1f" r="%.1f" fill="rgba(255,255,255,.55)"></circle>'%(cx,cy,cr,cols[int(rnd()*len(cols))%len(cols)],cx,cy,cr*0.35)
    return s+'<path d="M40 118 L52 84 L68 84 L80 118 Z" fill="#DCCBB8"></path></svg>'

HDR='<div class="page-hd"><div><h1>Доброе утро, Айнура</h1><div class="sub">Смена: Айнура, флористы Бермет и Гулия, курьеры Улан и Канат</div></div></div>'
def kpis(cols=4):
    t=[('Заказов сегодня','12','2 вручено'),('В пути','3','1 опаздывает'),('Ждут сборки','5','ближайшее окно 12:00'),('Кому написать','6','даты и давние клиенты')]
    return '<div class="kpis" style="grid-template-columns:repeat(%d,minmax(0,1fr));margin-bottom:16px">'%cols+''.join('<div class="kpi"><div class="kl">%s</div><div class="kv">%s</div><div class="kf">%s</div></div>'%x for x in t)+'</div>'
TASKS=[
 ('crit','Связаться с получателем №2494, курьер не дозвонился','Эльмира Касымова · ул. Байтик Баатыра 41','<span class="btn xs">Позвонить</span><span class="btn xs wa">Написать</span><span class="btn xs">Связались</span>'),
 ('crit','Разобрать жалобу №2482: «Букет не такой, как на фото, две розы вялые»','Данияр Осмонов · флорист Бермет · курьер Канат · 19.11 10:20','<span class="btn xs">Позвонить</span><span class="btn xs wa">Извиниться</span><span class="btn xs primary">Решить</span>'),
 ('warn','Выдать №2492 в 13:00, собран','Мээрим Жолдошева · 5 500 сом · перевод mbank','<span class="btn xs ok">Выдан</span>'),
 ('warn','Напомнить об оплате №2490, завтра 10:00–12:00','Асель Жумабекова · 2 800 сом','<span class="btn xs wa">Напомнить</span><span class="btn xs">Оплачен</span>'),
 ('info','Отправить счёт бухгалтерии: Счёт №118 от 18.11','Эркин Абдыраимов · №2485 · 11 300 сом','<span class="btn xs wa">Отправить</span><span class="btn xs">Оплачен</span>'),
 ('info','Передать флористу №2488 к 16:00–18:00','Коробка шляпная · Асель','<span class="sel-xs">Флорист…</span>'),
 ('info','Передать флористу №2486 к 17:00','Букет дня · Айсулуу Токтосунова','<span class="sel-xs">Флорист…</span>'),
 ('info','Передать флористу №2493 к 18:00–20:00','Букет дня, Упаковка премиум · Салтанат Орозова','<span class="sel-xs">Флорист…</span>'),
 ('info','Назначить курьера на завтра №2490, 10:00–12:00','ул. Ленина 312 · Бурул','<span class="sel-xs">Курьер…</span>'),
 ('info','Спросить, как букет №2477','Айдай Сулайманова · вручён в 08:20 · Улан','<span class="btn xs wa">Спросить</span><span class="btn xs ok">Доволен</span><span class="btn xs">Нейтрально</span><span class="btn xs crit" style="background:var(--crit-bg);color:var(--crit);border-color:transparent">Жалоба</span>'),
 ('','Написать 6 клиентам по напоминаниям','даты и давние клиенты','<span class="btn xs">Открыть</span>'),
]
def task_rows(n,grid=False):
    rows=''.join('<div class="task %s"><span class="chk"></span><div style="min-width:0"><div class="t">%s</div><div class="s">%s</div></div><div class="acts">%s</div></div>'%x for x in TASKS[:n])
    return ('<div class="tgrid">'+rows+'</div>') if grid else rows
def tasks(n,grid=False,add=True):
    return ('<div class="card"><div class="card-hd"><h2>Задачи</h2>'+tag(str(len(TASKS)),'crit')+'<span class="small muted">сделано 0</span></div><div class="card-bd tight">'+task_rows(n,grid)+(('<div class="task-add"><div>Своя задача, Enter чтобы добавить</div></div>') if add else ('<div class="empty small" style="padding:8px 16px;text-align:left">и ещё %d</div>'%(len(TASKS)-n) if len(TASKS)>n else ''))+'</div></div>')
ORDERS=[
 (2494,'08:00–10:00','Эльмира Касымова','','Букет из тюльпанов','3 100','ул. Байтик Баатыра 41','route','В пути','Канат','Вручён',True),
 (2482,'08:00–10:00','Данияр Осмонов','Нургуль','Букет дня','2 800','пр. Чуй 155, БЦ «Аврора», 5 этаж','done','Вручён','Канат','',False),
 (2477,'08:00–10:00','Айдай Сулайманова','','Букет дня','2 800','ул. Медерова 44, кв. 9','done','Вручён','Улан','',False),
 (2483,'10:00–12:00','Айгерим Ниязова','Салтанат','Авторский букет','3 300','ул. Киевская 95, кв. 12','route','В пути','Улан','Вручён',False),
 (2487,'10:00–12:00','Гульнара Асанова','Офис, ул. Ахунбаева 119','Авторский букет','3 500','ул. Ахунбаева 119','route','В пути','Яндекс','Вручён',False),
 (2484,'12:00–14:00','Айбек Токтосунов','Айгуль','25 роз 60 см','6 550','ул. Исанова 105, офис 4','ready','Собран','Улан','Курьер забрал',False),
 (2491,'12:00–14:00','Бакыт Жээнбеков','','Букет из хризантем','2 500','ул. Панфилова 42, роддом №2','work','У флориста','Канат','Собран',False),
 (2492,'13:00','Мээрим Жолдошева','','Корзина фрукты и цветы','5 500','самовывоз','ready','Собран',None,'Выдан',False),
 (2485,'14:00–16:00','Эркин Абдыраимов','Приёмная ОсОО «Азия Трейд»','Композиция в корзине ×2','11 300','пр. Чуй 155, БЦ «Аврора», 3 этаж','work','У флориста','Канат','Собран',False),
 (2488,'16:00–18:00','Данияр Осмонов','Асель','Коробка шляпная','5 100','мкр. Джал 23, д. 7','new','Новый','Улан','Передать флористу',False),
 (2486,'17:00','Айсулуу Токтосунова','','Букет дня','2 500','самовывоз','new','Новый',None,'Передать флористу',False),
 (2493,'18:00–20:00','Салтанат Орозова','','Букет дня, Упаковка премиум','3 200','мкр. Асанбай 24/1','new','Новый','Улан','Передать флористу',False),
]
STCLS={'new':'info','work':'acc','ready':'warn','route':'acc','done':'ok'}
def orow(o):
    id,win,c,rec,items,sm,addr,st,stn,cour,nxt,late=o
    r='<span class="tag %s"><i class="dot"></i>%s</span>'%(STCLS[st],stn)
    if cour is not None and st!='done': r+='<span class="sel-xs">%s ▾</span>'%cour
    if nxt: r+='<span class="btn xs%s">%s</span>'%(' ok' if nxt in('Вручён','Выдан') else '',nxt)
    return ('<div class="lrow"><div class="thumb">'+bouquet(id)+'</div><div style="min-width:0"><div class="t"><span class="mono">'+win+'</span> · '+c+(' → '+rec if rec else '')+(' <span class="tag crit">опаздывает</span>' if late else '')+'</div><div class="s">№%d · %s · %s сом · %s</div></div><div class="r row">%s</div></div>'%(id,items,sm,addr,r))
def orders(n=12,grouped=False,hd='Заказы на сегодня'):
    body=''
    if grouped:
        cur=None
        for o in ORDERS[:n]:
            if o[1]!=cur:
                cur=o[1];body+='<div class="qhead">%s</div>'%cur
            body+=orow(o)
    else:
        body=''.join(orow(o) for o in ORDERS[:n])
    return '<div class="card"><div class="card-hd"><h2>'+hd+'</h2><span class="small muted">статус и курьер меняются прямо здесь</span><div class="spacer"></div><span class="btn sm">Доска</span></div><div class="card-bd tight">'+body+'</div></div>'
FEED=[('10:32','Заказ принят','№2493 · Салтанат Орозова','АИ'),('10:30','Передан флористу','№2491 · Бакыт Жээнбеков','АИ'),('10:25','Заказ принят','№2486 · Айсулуу Токтосунова','АИ'),('10:20','Жалоба со страницы заказа: две розы вялые','№2482 · Нургуль','АИ'),('10:20','Передан Яндекс Доставке','№2487 · Офис, ул. Ахунбаева 119','АИ'),('10:15','Собран, фото','№2492 · Мээрим Жолдошева','ГТ'),('10:12','Курьер забрал','№2483 · Салтанат','УМ'),('10:05','Собран, фото','№2484 · Айгуль','БС'),('09:55','Заказ принят','№2488 · Асель','АИ'),('09:50','Собран','№2487 · Офис','ГТ'),('09:40','Вручён, фото','№2482 · Нургуль','КА'),('09:35','Не дозвонился, ждёт','№2494 · Эльмира Касымова','КА'),('09:30','Собран, фото','№2483 · Салтанат','БС'),('09:20','Курьер забрал','№2494 · Эльмира Касымова','КА'),('09:15','Дата через 7 дней','Данияр Осмонов · WhatsApp','АИ'),('09:05','Курьер забрал','№2482 · Нургуль','КА'),('09:00','Передан флористу','№2485 · Приёмная ОсОО «Азия Трейд»','АИ'),('08:50','Собран, фото','№2494 · Эльмира Касымова','БС'),('08:35','Собран, фото','№2482 · Нургуль','БС'),('08:20','Вручён, фото','№2477 · Айдай Сулайманова','УМ')]
def feed(n=16):
    rows=''.join('<div class="lrow feed-row"><span class="mono small muted">%s</span><div style="min-width:0"><div class="t">%s <span class="muted" style="font-weight:400">%s</span></div></div><div class="r"><span class="av sm">%s</span></div></div>'%x for x in FEED[:n])
    more=('<div class="empty small">ещё %d раньше</div>'%(len(FEED)-n)) if len(FEED)>n else ''
    return '<div class="card"><div class="card-hd"><h2>Лента дня</h2><span class="small muted">%d событий</span></div><div class="card-bd tight">'%len(FEED)+rows+more+'</div></div>'
def grid(cols,*items):
    return '<div style="display:grid;grid-template-columns:%s;gap:16px;align-items:start">'%cols+''.join(items)+'</div>'
def stack(*items):
    return '<div class="stack">'+''.join(items)+'</div>'

MAIN = HDR+kpis()+grid('minmax(0,1.6fr) minmax(300px,1fr)',stack(tasks(7),orders(12)),feed(16))
T1 = HDR+kpis()+grid('340px minmax(0,1fr) 340px',tasks(9,add=False),orders(12),feed(16))
T2 = HDR+kpis()+grid('minmax(0,1fr) 380px',orders(12,grouped=True,hd='Заказы по окнам доставки'),stack(tasks(6,add=False),feed(9)))
T3 = HDR+tasks(11,grid=True,add=False)+'<div style="height:16px"></div>'+kpis()+grid('minmax(0,1fr) 360px',orders(12),feed(12))
T4 = HDR+kpis()+grid('minmax(0,1fr) 400px',orders(12),stack(tasks(7,add=False),feed(8)))
T5 = HDR+kpis()+grid('minmax(0,1fr) 440px',feed(20),stack(tasks(6,add=False),orders(6,hd='Ближайшие заказы')))

for name,body in [('Main',MAIN),('T1Columns',T1),('T2Windows',T2),('T3TasksFirst',T3),('T4OrdersFirst',T4),('T5FeedFirst',T5)]:
    open(name+'.dc.html','w',encoding='utf-8').write(page(body))
H=1100
canvas={
 "artboards":[
  {"file":"Main.dc.html","title":"Как сейчас","x":0,"y":0,"w":1440,"h":H},
  {"file":"T1Columns.dc.html","title":"T1 · Диспетчерская, три колонки","x":1560,"y":0,"w":1440,"h":H},
  {"file":"T2Windows.dc.html","title":"T2 · По окнам доставки","x":3120,"y":0,"w":1440,"h":H},
  {"file":"T3TasksFirst.dc.html","title":"T3 · Сначала задачи","x":0,"y":1320,"w":1440,"h":H},
  {"file":"T4OrdersFirst.dc.html","title":"T4 · Сначала заказы","x":1560,"y":1320,"w":1440,"h":H},
  {"file":"T5FeedFirst.dc.html","title":"T5 · Лента для владельца","x":3120,"y":1320,"w":1440,"h":H}
 ],
 "annotations":[
  {"id":"n-main","x":0,"y":-150,"w":560,"text":"Как сейчас: задачи и заказы слева, лента справа. Компоненты во всех вариантах одни и те же: приветствие, четыре плитки, задачи, заказы дня со сменой статуса и курьера в строке, лента. Меняются только порядок, ширина и группировка."},
  {"id":"n-t1","x":1560,"y":-190,"w":560,"text":"T1 · Диспетчерская. Три колонки без прокрутки между ними, как доски диспетчера в Onfleet и Bringg: слева что сделать, в центре что везём, справа что произошло. Плюс: всё видно одним взглядом на большом мониторе. Минус: на ноутбуке 13″ колонки тесные, действия в строках заказов переносятся."},
  {"id":"n-t2","x":3120,"y":-190,"w":560,"text":"T2 · По окнам доставки. Заказы сгруппированы заголовками окон, как таймлайн доставки и кухонные экраны в ресторанных системах: менеджер читает день сверху вниз по времени. Задачи и лента компактно справа. Плюс: видно, какое окно горит. Минус: задачи ниже по приоритету, на них смотрят реже."},
  {"id":"n-t3","x":0,"y":1170,"w":560,"text":"T3 · Сначала задачи. Как «Сегодня» в Todoist и очередь задач в HubSpot: первым идёт чек-лист во всю ширину в две колонки, цифры и заказы ниже. Плюс: утро начинается с «что сделать», ничего не пропустишь. Минус: заказы уезжают ниже сгиба, для быстрого «где заказ» нужен второй взгляд."},
  {"id":"n-t4","x":1560,"y":1170,"w":560,"text":"T4 · Сначала заказы. Как главная Shopify: метрики сверху, главная колонка про деньги, то есть заказы, справа стопкой задачи и лента. Плюс: заказ ищется быстрее всего, действия в строке помещаются. Минус: задачи справа читаются как второстепенные, красные жалобы легко проглядеть."},
  {"id":"n-t5","x":3120,"y":1170,"w":560,"text":"T5 · Лента для владельца. Лента событий как главная колонка, по образцу ленты активности в Intercom и Shopify: владелец, который заходит на пять минут, видит, как дышит магазин. Плюс: наглядно и живо. Минус: для менеджера это не рабочее место, задачи и заказы ужаты. Годится как режим по роли, а не по умолчанию."}
 ],
 "launch":{"view":"canvas"}
}
json.dump(canvas,open('canvas.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('built today variants')
