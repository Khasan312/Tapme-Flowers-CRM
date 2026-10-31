const properties = ["--chat-visible-height", "--chat-visible-top"];
const keyboardClass = "tapme-chat-keyboard-open";

/** Keep the chat inside the visible area when a phone keyboard pans/resizes it. */
export function startChatViewport(win: Window, doc: Document) {
  const root = doc.documentElement;
  const viewport = win.visualViewport;
  const mobile = win.matchMedia("(max-width: 700px)");
  const previous = properties.map((name) => ({
    name,
    value: root.style.getPropertyValue(name),
    priority: root.style.getPropertyPriority(name),
  }));
  const wasOpen = root.classList.contains(keyboardClass);
  let frame = 0;
  let baseline = win.innerHeight;
  let width = win.innerWidth;
  let keyboardActive = false;
  const restore = () => {
    for (const { name, value, priority } of previous) {
      if (value) root.style.setProperty(name, value, priority);
      else root.style.removeProperty(name);
    }
    root.classList.toggle(keyboardClass, wasOpen);
  };
  const update = () => {
    frame = 0;
    if (!mobile.matches) {
      keyboardActive = false;
      restore();
      return;
    }
    const height =
      viewport?.height && viewport.height > 0
        ? viewport.height
        : win.innerHeight;
    const top = Math.max(0, viewport?.offsetTop || 0);
    const composing = Boolean(
      doc.activeElement?.matches(".chat-composer textarea"),
    );
    if (
      Math.abs(win.innerWidth - width) > 40 ||
      (!composing && !keyboardActive)
    ) {
      baseline = Math.max(win.innerHeight, height);
      width = win.innerWidth;
    }
    baseline = Math.max(baseline, win.innerHeight, height);
    const keyboardOpen =
      (composing || keyboardActive) &&
      (viewport?.scale || 1) <= 1.05 &&
      baseline - height > 100;
    keyboardActive = keyboardOpen;
    root.style.setProperty(properties[0], `${Math.round(height)}px`);
    root.style.setProperty(properties[1], `${Math.round(top)}px`);
    root.classList.toggle(keyboardClass, keyboardOpen);
  };
  const schedule = () => {
    if (!frame) frame = win.requestAnimationFrame(update);
  };
  const events: [EventTarget, string][] = [
    [win, "resize"],
    [win, "orientationchange"],
    [doc, "focusin"],
    [doc, "focusout"],
    [mobile, "change"],
  ];
  if (viewport) events.push([viewport, "resize"], [viewport, "scroll"]);
  for (const [target, event] of events)
    target.addEventListener(event, schedule, { passive: true });
  update();
  return () => {
    if (frame) win.cancelAnimationFrame(frame);
    for (const [target, event] of events)
      target.removeEventListener(event, schedule);
    restore();
  };
}

export function shouldSendChatOnEnter(
  event: {
    key: string;
    shiftKey: boolean;
    isComposing: boolean;
    repeat?: boolean;
  },
  mobile: boolean,
) {
  return (
    event.key === "Enter" &&
    !event.shiftKey &&
    !event.isComposing &&
    !event.repeat &&
    !mobile
  );
}

/** Resize changes the visible message area without changing the message list. */
export function observeChatThreadResize(
  node: HTMLElement,
  atBottom: () => boolean,
  changed: () => void,
) {
  const observer = new ResizeObserver(() => {
    if (atBottom()) node.scrollTop = node.scrollHeight;
    changed();
  });
  observer.observe(node);
  return () => observer.disconnect();
}
