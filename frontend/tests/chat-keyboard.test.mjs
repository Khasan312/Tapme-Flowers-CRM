import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { test } from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = readFileSync(
  new URL("../src/chat-keyboard.ts", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.CommonJS,
  },
}).outputText;

function phone(visual = true) {
  const exports = {};
  vm.runInNewContext(compiled, { exports });
  class Target extends EventTarget {
    listeners = 0;
    addEventListener(...args) {
      this.listeners++;
      super.addEventListener(...args);
    }
    removeEventListener(...args) {
      this.listeners--;
      super.removeEventListener(...args);
    }
    fire(name) {
      this.dispatchEvent(new Event(name));
    }
  }
  const frames = new Map(),
    styles = new Map(),
    classes = new Set();
  const win = new Target(),
    doc = new Target(),
    media = new Target(),
    viewport = new Target();
  let sequence = 0;
  Object.assign(viewport, { height: 844, offsetTop: 0, scale: 1 });
  Object.assign(media, { matches: true });
  Object.assign(win, {
    innerHeight: 844,
    innerWidth: 390,
    visualViewport: visual ? viewport : null,
    matchMedia: () => media,
    requestAnimationFrame: (fn) => {
      const id = ++sequence;
      frames.set(id, fn);
      return id;
    },
    cancelAnimationFrame: (id) => frames.delete(id),
  });
  let focused = false;
  doc.activeElement = { matches: () => focused };
  doc.documentElement = {
    style: {
      getPropertyValue: (key) => styles.get(key)?.value || "",
      getPropertyPriority: (key) => styles.get(key)?.priority || "",
      setProperty: (key, value, priority = "") =>
        styles.set(key, { value, priority }),
      removeProperty: (key) => styles.delete(key),
    },
    classList: {
      contains: (key) => classes.has(key),
      toggle: (key, value) => (value ? classes.add(key) : classes.delete(key)),
    },
  };
  return {
    win,
    doc,
    media,
    viewport,
    frames,
    styles,
    classes,
    api: exports,
    start: () => exports.startChatViewport(win, doc),
    focus: (value) => {
      focused = value;
      doc.fire(value ? "focusin" : "focusout");
    },
    flush: () => {
      const pending = [...frames.values()];
      frames.clear();
      pending.forEach((fn) => fn());
    },
    height: () => styles.get("--chat-visible-height")?.value,
    keyboard: () => classes.has("tapme-chat-keyboard-open"),
  };
}

test("keyboard shrink and Safari viewport panning keep the composer in the visible area", () => {
  const p = phone(),
    stop = p.start();
  assert.equal(p.height(), "844px");
  p.focus(true);
  p.flush();
  Object.assign(p.viewport, { height: 350, offsetTop: 44 });
  p.viewport.fire("resize");
  p.viewport.fire("scroll");
  assert.equal(p.frames.size, 1);
  p.flush();
  assert.equal(p.height(), "350px");
  assert.equal(p.styles.get("--chat-visible-top").value, "44px");
  assert.equal(p.keyboard(), true);
  Object.assign(p.viewport, { height: 844, offsetTop: 0 });
  p.viewport.fire("resize");
  p.flush();
  assert.equal(p.keyboard(), false); // iOS may leave textarea focused after dismissing the keyboard.
  stop();
});

test("sending does not expand the toolbar before the keyboard closes", () => {
  const p = phone(),
    stop = p.start();
  p.focus(true);
  p.flush();
  p.win.innerHeight = 430;
  p.viewport.height = 430;
  p.viewport.fire("resize");
  p.flush();
  assert.equal(p.keyboard(), true);
  p.focus(false);
  p.flush();
  assert.equal(p.keyboard(), true);
  p.win.innerHeight = 844;
  p.viewport.height = 844;
  p.viewport.fire("resize");
  p.flush();
  assert.equal(p.keyboard(), false);
  stop();
});

test("keyboard is detected when the browser resizes both layout and visual viewport", () => {
  const p = phone(),
    stop = p.start();
  p.focus(true);
  p.flush();
  p.win.innerHeight = 420;
  p.viewport.height = 420;
  p.win.fire("resize");
  p.flush();
  assert.equal(p.height(), "420px");
  assert.equal(p.keyboard(), true);
  stop();
});

test("pinch zoom and ordinary browser chrome changes do not hide chat actions", () => {
  const p = phone(),
    stop = p.start();
  p.focus(true);
  p.flush();
  p.viewport.height = 780;
  p.viewport.fire("resize");
  p.flush();
  assert.equal(p.keyboard(), false);
  Object.assign(p.viewport, { height: 450, scale: 1.6 });
  p.viewport.fire("resize");
  p.flush();
  assert.equal(p.keyboard(), false);
  stop();
});

test("desktop switch and cleanup restore styles, cancel frames and remove listeners", () => {
  const p = phone();
  p.doc.documentElement.style.setProperty(
    "--chat-visible-height",
    "90vh",
    "important",
  );
  const stop = p.start();
  p.media.matches = false;
  p.media.fire("change");
  p.flush();
  assert.equal(p.height(), "90vh");
  p.media.matches = true;
  p.media.fire("change");
  p.flush();
  p.viewport.fire("resize");
  assert.equal(p.frames.size, 1);
  stop();
  assert.equal(p.frames.size, 0);
  assert.equal(p.height(), "90vh");
  assert.equal(p.styles.get("--chat-visible-height").priority, "important");
  assert.equal(p.keyboard(), false);
  for (const target of [p.win, p.doc, p.media, p.viewport])
    assert.equal(target.listeners, 0);
  p.viewport.fire("resize");
  assert.equal(p.frames.size, 0);
});

test("without VisualViewport the chat falls back to the window height", () => {
  const p = phone(false),
    stop = p.start();
  assert.equal(p.height(), "844px");
  p.win.innerHeight = 600;
  p.win.fire("resize");
  p.flush();
  assert.equal(p.height(), "600px");
  stop();
});

test("mobile Enter keeps a newline; desktop Enter sends except Shift, IME or held keys", () => {
  const send = phone().api.shouldSendChatOnEnter;
  const enter = { key: "Enter", shiftKey: false, isComposing: false };
  assert.equal(send(enter, true), false);
  assert.equal(send(enter, false), true);
  for (const patch of [
    { shiftKey: true },
    { isComposing: true },
    { repeat: true },
    { key: "a" },
  ])
    assert.equal(send({ ...enter, ...patch }, false), false);
});

for (const pinned of [true, false]) {
  test(
    pinned
      ? "viewport resize keeps the latest message visible"
      : "viewport resize preserves position while reading older messages",
    () => {
      const exports = {};
      let resize,
        disconnected = false,
        synced = 0;
      class Observer {
        constructor(callback) {
          resize = callback;
        }
        observe() {}
        disconnect() {
          disconnected = true;
        }
      }
      vm.runInNewContext(compiled, { exports, ResizeObserver: Observer });
      let top = pinned ? 1500 : 600;
      const node = {
        scrollHeight: 2000,
        clientHeight: 500,
        get scrollTop() {
          return top;
        },
        set scrollTop(value) {
          top = Math.max(
            0,
            Math.min(value, this.scrollHeight - this.clientHeight),
          );
        },
      };
      const stop = exports.observeChatThreadResize(
        node,
        () => pinned,
        () => synced++,
      );
      node.clientHeight = 300;
      resize();
      assert.equal(node.scrollTop, pinned ? 1700 : 600);
      node.clientHeight = 700;
      resize();
      assert.equal(node.scrollTop, pinned ? 1300 : 600);
      assert.equal(synced, 2);
      stop();
      assert.equal(disconnected, true);
    },
  );
}
