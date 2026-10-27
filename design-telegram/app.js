(() => {
  'use strict';

  const paths = {
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/>',
    close: '<path d="m6 6 12 12M18 6 6 18"/>',
    back: '<path d="m10 5-7 7 7 7M3 12h18"/>',
    more: '<circle cx="12" cy="5" r="1" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="12" cy="19" r="1" fill="currentColor" stroke="none"/>',
    edit: '<path d="m15 4 5 5M4 20l1.2-5.2L16 4a2.1 2.1 0 0 1 3 0l1 1a2.1 2.1 0 0 1 0 3L9.2 18.8 4 20Z"/>',
    send: '<path d="m3 11 18-8-7.5 18-3-7-7.5-3Z"/><path d="m10.5 14 5-5"/>',
    attach: '<path d="m8 12 6.5-6.5a3.2 3.2 0 0 1 4.5 4.5l-9 9a5 5 0 0 1-7-7l9-9M7 14l7.5-7.5"/>',
    smile: '<circle cx="12" cy="12" r="9"/><path d="M8 14.5a4.5 4.5 0 0 0 8 0"/><circle cx="8.5" cy="9" r=".7" fill="currentColor"/><circle cx="15.5" cy="9" r=".7" fill="currentColor"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    checks: '<path d="m2 12 4 4L16 6m-4 10L22 6"/>',
    bookmark: '<path d="M6 4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v17l-6-4-6 4V4Z"/>',
    users: '<circle cx="9" cy="8" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M17 5a3 3 0 0 1 0 6m1 3a5 5 0 0 1 3 4v2"/>',
    settings: '<path d="m9.5 3-.7 2-2 .9-2-.4L3 8.5l1.4 1.6v3.8L3 15.5l1.8 3 2-.4 2 .9.7 2h5l.7-2 2-.9 2 .4 1.8-3-1.4-1.6v-3.8L21 8.5l-1.8-3-2 .4-2-.9-.7-2h-5Z"/><circle cx="12" cy="12" r="3"/>',
    palette: '<path d="M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 1.5-3.3 1.7 1.7 0 0 1 1.4-2.8H18a3 3 0 0 0 3-3A9 9 0 0 0 12 3Z"/><circle cx="7" cy="11" r=".8"/><circle cx="9" cy="7" r=".8"/><circle cx="14" cy="6.5" r=".8"/><circle cx="17.5" cy="10" r=".8"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.2"/>',
    bell: '<path d="M5 17h14l-2-3V9a5 5 0 0 0-10 0v5l-2 3Zm5 3h4"/>',
    file: '<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8l-5-5Zm0 0v5h5M8 12h8m-8 4h6"/>',
    image: '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 6-6 4 4 3-3 5 5"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
    folder: '<path d="M3 6a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6Z"/>',
    globe: '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    keyboard: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M5 9h1m3 0h1m3 0h1m3 0h1M5 12h1m3 0h1m3 0h1m3 0h1m-12 4h10"/>',
    storage: '<path d="M4 5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5ZM4 15h16M7 18h1"/>',
    phone: '<path d="M8 3H4a1 1 0 0 0-1 1 17 17 0 0 0 17 17 1 1 0 0 0 1-1v-4l-5-2-2 3a14 14 0 0 1-7-7l3-2-2-5Z"/>',
    chevron: '<path d="m9 5 7 7-7 7"/>',
    download: '<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',
  };
  const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.info}</svg>`;
  const drawIcons = (root = document) => root.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); });
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const $ = id => document.getElementById(id);
  const chats = [
    {id:'design', title:'Дизайн-команда', initials:'ДК', color:'purple', status:'5 участников', preview:'Вы: Отлично, оставим этот вариант.', time:'14:32', count:0},
    {id:'maria', title:'Мария', initials:'М', color:'pink', status:'была недавно', preview:'Отправила тебе обновлённые макеты', time:'14:20', count:2},
    {id:'product', title:'Продуктовые заметки', initials:'ПЗ', color:'blue', status:'канал · 248 подписчиков', preview:'Как сделать интерфейс понятнее', time:'13:48', count:12},
    {id:'daniil', title:'Даниил', initials:'Д', color:'orange', status:'в сети', preview:'Спасибо! Уже посмотрел 🙌', time:'13:16', count:0},
    {id:'weekend', title:'Планы на выходные', initials:'ПВ', color:'green', status:'4 участника', preview:'Аня: Давайте встретимся в 11?', time:'12:45', count:4, muted:true},
    {id:'saved', title:'Избранное', initials:'', color:'saved', status:'ваши заметки', preview:'Палитра и заметки к макету', time:'11:30', count:0},
    {id:'reading', title:'Что почитать', initials:'ЧП', color:'red', status:'канал · 126 подписчиков', preview:'Подборка на эту неделю', time:'10:54', count:7, muted:true},
    {id:'alex', title:'Александр', initials:'А', color:'blue', status:'был недавно', preview:'Да, договорились', time:'Вчера', count:0},
    {id:'photos', title:'Фотография', initials:'Ф', color:'purple', status:'12 участников', preview:'Новый альбом с прогулки', time:'Вчера', count:0},
    {id:'ideas', title:'Идеи', initials:'И', color:'orange', status:'ваши заметки', preview:'Сохранил, вернусь вечером', time:'Пн', count:0},
  ];
  const initialMessages = [
    {side:'in', sender:'Мария', time:'14:24', text:'Привет! Собрала основные экраны в одном месте.'},
    {side:'in', time:'14:24', text:'Посмотрите на отступы, поиск и состояния выбранного чата. Всё должно ощущаться спокойно и привычно.'},
    {side:'out', time:'14:26', text:'Очень нравится, как смотрятся плавающая шапка и скруглённые панели.', read:true},
    {side:'in', sender:'Даниил', orange:true, time:'14:28', type:'palette', text:'И вот палитра для тёмной темы. Фиолетовый — для акцентов и исходящих сообщений.'},
    {side:'out', time:'14:30', text:'Да, и хорошо, что второстепенный текст не перетягивает внимание.', read:true},
    {side:'in', sender:'Мария', time:'14:31', type:'file', filename:'Заметки к интерфейсу.pdf', size:'128 КБ · PDF', reaction:1},
    {side:'out', time:'14:32', text:'Отлично, оставим этот вариант.', read:true},
  ];
  const histories = new Map([['design', initialMessages], ['saved', [{side:'out',time:'11:30',text:'Проверить состояния поиска, выбранного чата и меню.',read:true}]]]);
  const drafts = new Map();
  const preferences = {notifications:true, sounds:true, preview:true, animations:true, rounded:true};
  let active = 'design';
  let settingsPage = null;
  let toastTimer;

  function renderChats() {
    const query = $('chat-search').value.trim().toLocaleLowerCase('ru');
    const visible = chats.filter(chat => `${chat.title} ${chat.preview}`.toLocaleLowerCase('ru').includes(query));
    $('chat-list').innerHTML = visible.map(chat => `<button class="chat-row" data-chat="${chat.id}" aria-current="${chat.id===active}" aria-label="${esc(chat.title)}"><span class="avatar gradient-${chat.color}" aria-hidden="true">${chat.id==='saved'?icon('bookmark'):esc(chat.initials)}</span><span class="chat-row-content"><span class="chat-row-top"><span class="chat-row-name">${esc(chat.title)}</span><span class="chat-row-time">${chat.time}</span></span><span class="chat-row-bottom"><span class="chat-row-preview">${esc(chat.preview)}</span>${chat.count?`<span class="unread-badge${chat.muted?' muted':''}">${chat.count}</span>`:chat.id===active?`<span class="row-check">${icon('checks')}</span>`:''}</span></span></button>`).join('');
    $('empty-search').hidden = visible.length > 0;
  }
  function messageHtml(message, index) {
    const attachment = message.type==='palette'?'<div class="palette-attachment"><div class="palette-attachment-art" aria-label="Пять цветов тёмной темы"><i></i><i></i><i></i><i></i><i></i></div><div class="palette-attachment-label">DARK · PALETTE</div></div>':message.type==='file'?`<div class="document-card"><span class="file-symbol">${icon('file')}</span><div><div class="document-name">${esc(message.filename)}</div><div class="document-meta">${esc(message.size)}</div></div></div>`:'';
    return `<div class="bubble" data-message="${index}">${message.sender?`<div class="sender${message.orange?' orange':''}">${esc(message.sender)}</div>`:''}${attachment}${message.text?`<p class="message-copy">${esc(message.text)}</p>`:''}<span class="message-time">${esc(message.time)}${message.side==='out'?icon('checks'):''}</span>${message.reaction!==undefined?`<button class="reaction" aria-label="Нравится" aria-pressed="${!!message.liked}" data-reaction="${index}">👍 ${message.reaction}</button>`:''}</div>`;
  }
  function renderMessages(scrollToEnd = true) {
    const messages = histories.get(active) || [];
    const groups = [];
    messages.forEach((message,index) => {
      const key = `${message.side}/${message.sender||''}`;
      const previous = groups.at(-1);
      if(previous && previous.key===key && !message.sender) previous.items.push({message,index});
      else groups.push({key,side:message.side,items:[{message,index}]});
    });
    $('messages').innerHTML = '<div class="day-label">27 октября</div>'+groups.map(group=>`<div class="message-group ${group.side==='out'?'outgoing':'incoming'}">${group.items.map(({message,index})=>messageHtml(message,index)).join('')}</div>`).join('');
    if(scrollToEnd) requestAnimationFrame(() => { $('messages-scroll').scrollTop = $('messages-scroll').scrollHeight; });
  }
  function selectChat(id) {
    if(!chats.some(chat=>chat.id===id))return;
    drafts.set(active,$('message-input').value);
    active=id;
    const chat=chats.find(item=>item.id===active);
    if(!histories.has(active)) histories.set(active,[{side:'in',sender:chat.title,time:chat.time,text:chat.preview},{side:'out',time:'14:32',text:'Хорошо, спасибо! Вернусь с ответом чуть позже.',read:true}]);
    $('chat-title').textContent=chat.title;
    $('chat-status').textContent=chat.status;
    $('header-avatar').className=`avatar header-avatar gradient-${chat.color}`;
    $('header-avatar').innerHTML=active==='saved'?icon('bookmark'):esc(chat.initials);
    $('message-input').value=drafts.get(active)||'';
    $('app').classList.add('show-chat');
    closePopups(); closeSettings(); closeProfile();
    $('conversation-search').hidden=true;
    renderChats();renderMessages();resizeInput();
  }
  function closePopups() {
    ['main-menu','chat-menu','emoji-picker','attachment-picker'].forEach(id=>$(id).hidden=true);
    ['main-menu-button','chat-menu-button','emoji-button','attach-button'].forEach(id=>$(id).setAttribute('aria-expanded','false'));
  }
  function togglePopup(id,trigger) {
    const open=$(id).hidden;
    closePopups(); $(id).hidden=!open;
    $(trigger).setAttribute('aria-expanded',String(open));
  }
  function notify(text) {
    clearTimeout(toastTimer);$('sample-toast').textContent=text;$('sample-toast').hidden=false;
    toastTimer=setTimeout(()=>$('sample-toast').hidden=true,2600);
  }
  function settingsRow(label,name,detail='') {
    return `<button class="settings-row" data-page="${name}"><span>${icon(({notifications:'bell',storage:'storage',privacy:'lock',general:'settings',folders:'folder',language:'globe',shortcuts:'keyboard'})[name]||'info')}</span><span class="row-label">${label}</span>${detail?`<span class="row-detail">${detail}</span>`:''}</button>`;
  }
  function toggleRow(label,key) {
    return `<button class="settings-row setting-toggle" role="switch" aria-checked="${preferences[key]}" data-preference="${key}"><span class="row-label">${label}</span><span class="switch${preferences[key]?' is-on':''}" aria-hidden="true"></span></button>`;
  }
  function openSettings(page='main') {
    closePopups();settingsPage=page;$('settings-panel').hidden=false;
    const names={main:'Настройки',notifications:'Уведомления',general:'Общие настройки',shortcuts:'Горячие клавиши',storage:'Данные и память',privacy:'Конфиденциальность',folders:'Папки с чатами',language:'Язык'};
    let content='';
    if(page==='main') content=`<div class="settings-identity"><span class="avatar gradient-purple">Д</span><strong>Демо-профиль</strong><span>в сети</span></div><div class="settings-section">${settingsRow('Уведомления и звуки','notifications')}${settingsRow('Данные и память','storage')}${settingsRow('Конфиденциальность','privacy')}${settingsRow('Общие настройки','general')}${settingsRow('Папки с чатами','folders')}${settingsRow('Язык','language','Русский')}${settingsRow('Горячие клавиши','shortcuts')}</div><p class="settings-help">Локальный образец оформления. Все имена и сообщения вымышлены.</p><p class="settings-help"><a href="system.html">Посмотреть измерения и компоненты</a></p>`;
    else if(page==='notifications') content=`<div class="settings-section"><h2>Уведомления</h2>${toggleRow('Показывать уведомления','notifications')}${toggleRow('Звук сообщения','sounds')}${toggleRow('Предпросмотр сообщения','preview')}</div><p class="settings-help">Переключатели меняют состояние только в этом образце.</p>`;
    else if(page==='general') content=`<div class="settings-section"><h2>Оформление</h2><div class="settings-row"><span class="row-label">Тема</span><span class="row-detail">Тёмная</span></div>${toggleRow('Скруглённые панели','rounded')}${toggleRow('Анимации','animations')}</div><div class="settings-section"><h2>Сообщения</h2><div class="settings-row"><span class="row-label">Размер текста</span><span class="row-detail">16 px</span></div><div class="settings-row"><span class="row-label">Отправка сообщения</span><kbd>Enter</kbd></div></div><p class="settings-help">Воспроизведена тема из открытой вкладки Telegram Web K.</p>`;
    else if(page==='shortcuts') content=`<div class="settings-section"><h2>Форматирование текста</h2>${[['Полужирный','Ctrl + B'],['Курсив','Ctrl + I'],['Подчёркнутый','Ctrl + U'],['Зачёркнутый','Ctrl + S'],['Моноширинный','Ctrl + M'],['Спойлер','Ctrl + P'],['Добавить ссылку','Ctrl + K']].map(([label,key])=>`<div class="settings-row"><span class="row-label">${label}</span><kbd>${key}</kbd></div>`).join('')}</div><p class="settings-help">Выделите текст в поле ввода, чтобы применить форматирование. Здесь показано оформление справки.</p><div class="settings-section"><h2>Сообщения</h2><div class="settings-row"><span class="row-label">Отправить сообщение</span><kbd>Enter</kbd></div><div class="settings-row"><span class="row-label">Новая строка</span><kbd>Shift + Enter</kbd></div></div>`;
    else if(page==='storage') content=`<div class="settings-section"><h2>Автозагрузка медиа</h2>${toggleRow('Фотографии','preview')}<div class="settings-row"><span class="row-label">Видео</span><span class="row-detail">До 10 МБ</span></div><div class="settings-row"><span class="row-label">Файлы</span><span class="row-detail">До 3 МБ</span></div></div><p class="settings-help">Образец показывает только визуальные состояния настроек.</p>`;
    else if(page==='privacy') content=`<div class="settings-section"><h2>Конфиденциальность</h2>${[['Номер телефона','Мои контакты'],['Последняя активность','Все'],['Фотографии профиля','Все'],['Пересылка сообщений','Мои контакты'],['Звонки','Мои контакты']].map(([a,b])=>`<div class="settings-row"><span class="row-label">${a}</span><span class="row-detail">${b}</span></div>`).join('')}</div><p class="settings-help">Значения вымышлены и не связаны с настройками вашего аккаунта.</p>`;
    else if(page==='folders') content=`<div class="settings-section"><h2>Папки с чатами</h2><div class="settings-row"><span>${icon('folder')}</span><span class="row-label">Работа</span><span class="row-detail">3 чата</span></div><div class="settings-row"><span>${icon('folder')}</span><span class="row-label">Личное</span><span class="row-detail">4 чата</span></div></div>`;
    else content=`<div class="settings-section"><h2>Язык интерфейса</h2><div class="settings-row"><span class="row-label">Русский</span><span style="color:var(--tg-primary)">${icon('check')}</span></div><div class="settings-row"><span class="row-label">English</span></div></div>`;
    $('settings-panel').innerHTML=`<header class="settings-header"><button class="icon-button" id="settings-back" aria-label="Назад">${icon('back')}</button><h1>${names[page]||names.main}</h1>${page==='main'?`<button class="icon-button" id="settings-search" aria-label="Горячие клавиши">${icon('search')}</button>`:''}</header><div class="settings-scroll">${content}</div>`;
    $('settings-back').onclick=()=>page==='main'?closeSettings():openSettings('main');
    if($('settings-search'))$('settings-search').onclick=()=>openSettings('shortcuts');
  }
  function closeSettings() {settingsPage=null;$('settings-panel').hidden=true;}
  function openProfile() {
    closePopups();const chat=chats.find(c=>c.id===active);
    $('app').classList.add('profile-open');$('profile-panel').hidden=false;
    $('profile-panel').innerHTML=`<header class="settings-header"><button class="icon-button" id="close-profile" aria-label="Закрыть информацию">${icon('close')}</button><h1>Информация</h1></header><div class="profile-cover"><span class="avatar gradient-${chat.color}">${chat.id==='saved'?icon('bookmark'):esc(chat.initials)}</span><strong>${esc(chat.title)}</strong><p>${esc(chat.status)}</p></div><div class="settings-section profile-members"><h2>О чате</h2><div class="settings-row"><span class="row-label">Заметки, обсуждения и хорошие идеи.</span></div>${toggleRow('Уведомления','notifications')}</div><div class="settings-section profile-members"><h2>Участники</h2>${[['Мария','М','pink','была недавно'],['Даниил','Д','orange','в сети'],['Анна','А','green','была недавно']].map(([name,initials,color,status])=>`<div class="member-row"><span class="avatar gradient-${color}">${initials}</span><div><strong>${name}</strong><small>${status}</small></div></div>`).join('')}</div>`;
    $('close-profile').onclick=closeProfile;
  }
  function closeProfile() {$('app').classList.remove('profile-open');$('profile-panel').hidden=true;}
  function resizeInput() {const input=$('message-input');input.style.height='40px';input.style.height=`${Math.min(Math.max(40,input.scrollHeight),160)}px`;}
  function appendMessage(message) {histories.get(active).push(message);renderMessages();}
  function showMessageSearch() {closePopups();$('conversation-search').hidden=false;$('message-search').focus();}

  $('chat-list').addEventListener('click',event=>{const row=event.target.closest('[data-chat]');if(row)selectChat(row.dataset.chat);});
  $('chat-search').addEventListener('input',renderChats);
  $('main-menu-button').onclick=()=>togglePopup('main-menu','main-menu-button');
  $('chat-menu-button').onclick=()=>togglePopup('chat-menu','chat-menu-button');
  $('settings-button').onclick=()=>openSettings();
  $('saved-messages').onclick=()=>selectChat('saved');
  $('contacts-button').onclick=()=>{closePopups();$('chat-search').value='';renderChats();$('chat-search').focus();notify('Выберите контакт в списке чатов');};
  $('dismiss-banner').onclick=()=>$('notification-banner').hidden=true;
  $('new-chat-button').onclick=()=>{$('chat-search').value='';renderChats();$('chat-search').focus();};
  $('back-to-chats').onclick=()=>{$('app').classList.remove('show-chat');closePopups();closeProfile();};
  $('open-profile').onclick=openProfile;
  $('chat-menu-info').onclick=openProfile;
  $('chat-menu-search').onclick=showMessageSearch;
  $('chat-menu-mute').onclick=()=>{preferences.notifications=!preferences.notifications;$('chat-menu-mute').querySelector('.switch').classList.toggle('is-on',preferences.notifications);};
  $('search-in-chat').onclick=showMessageSearch;
  $('close-message-search').onclick=()=>{$('conversation-search').hidden=true;$('message-search').value='';$('messages').querySelectorAll('.message-highlight').forEach(el=>el.classList.remove('message-highlight'));};
  $('message-search').addEventListener('input',()=>{const query=$('message-search').value.toLocaleLowerCase('ru').trim();$('messages').querySelectorAll('.bubble').forEach(el=>el.classList.toggle('message-highlight',!!query&&el.textContent.toLocaleLowerCase('ru').includes(query)));});
  $('attach-button').onclick=()=>togglePopup('attachment-picker','attach-button');
  $('emoji-button').onclick=()=>togglePopup('emoji-picker','emoji-button');
  $('emoji-picker').innerHTML=['🙂','😊','✨','👍','❤️','🙌','🎉','🔥','👌','💜','🤝','☀️','🌿','💬','🚀','👏','💡','✅'].map(e=>`<button type="button" data-emoji="${e}" aria-label="${e}">${e}</button>`).join('');
  $('emoji-picker').onclick=event=>{const button=event.target.closest('[data-emoji]');if(button){$('message-input').value+=button.dataset.emoji;resizeInput();$('message-input').focus();closePopups();}};
  $('insert-example-file').onclick=()=>{appendMessage({side:'out',type:'file',filename:'Заметки.pdf',size:'128 КБ · PDF',time:'14:33',read:true});closePopups();};
  $('insert-example-image').onclick=()=>{appendMessage({side:'out',type:'palette',text:'Палитра для обсуждения',time:'14:33',read:true});closePopups();};
  $('message-input').addEventListener('input',resizeInput);
  $('message-input').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();$('composer').requestSubmit();}});
  $('composer').addEventListener('submit',event=>{event.preventDefault();const text=$('message-input').value.trim();if(!text)return;appendMessage({side:'out',text,time:'14:33',read:true});const chat=chats.find(c=>c.id===active);chat.preview=`Вы: ${text}`;chat.time='14:33';$('message-input').value='';drafts.set(active,'');resizeInput();renderChats();closePopups();});
  $('messages').addEventListener('click',event=>{const button=event.target.closest('[data-reaction]');if(!button)return;const message=histories.get(active)[Number(button.dataset.reaction)];message.liked=!message.liked;message.reaction+=message.liked?1:-1;renderMessages(false);});
  document.addEventListener('click',event=>{const pageButton=event.target.closest('[data-page]');if(pageButton)openSettings(pageButton.dataset.page);const toggle=event.target.closest('[data-preference]');if(toggle){const key=toggle.dataset.preference;preferences[key]=!preferences[key];toggle.setAttribute('aria-checked',String(preferences[key]));toggle.querySelector('.switch').classList.toggle('is-on',preferences[key]);if(key==='rounded')document.documentElement.style.setProperty('--tg-panel-radius',preferences[key]?'24px':'0px');if(key==='animations')document.documentElement.style.setProperty('--tg-menu-motion',preferences[key]?'.2s var(--tg-ease)':'0s');}if(!event.target.closest('.popup-menu,.emoji-picker,#main-menu-button,#chat-menu-button,#emoji-button,#attach-button'))closePopups();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'){closePopups();if(!$('conversation-search').hidden)$('close-message-search').click();else if(!$('profile-panel').hidden)closeProfile();else if(settingsPage)settingsPage==='main'?closeSettings():openSettings('main');}if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='f'){event.preventDefault();showMessageSearch();}});

  drawIcons();renderChats();renderMessages();$('app').classList.add('show-chat');
})();
