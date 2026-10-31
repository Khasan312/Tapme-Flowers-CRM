import { readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";
import ts from "typescript";
import vm from "node:vm";

const source = readFileSync(
  new URL("../src/chat-notification-sound.ts", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.ES2022,
  },
}).outputText;
const { chatNotificationTitle, playChatNotification } = await import(
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
);

function audio(state = "running", resumeBlocked = false) {
  const notes = [];
  const context = {
    state,
    currentTime: 2,
    destination: {},
    resumes: 0,
    async resume() {
      this.resumes++;
      if (resumeBlocked) throw new Error("Autoplay blocked");
      this.state = "running";
    },
    createOscillator() {
      const note = {
        envelope: [],
        disconnected: false,
        frequency: {
          setValueAtTime(value, time) {
            note.hz = value;
            note.at = time;
          },
        },
        connect(gain) {
          note.gain = gain;
        },
        start(time) {
          note.start = time;
        },
        stop(time) {
          note.stop = time;
        },
        disconnect() {
          note.disconnected = true;
        },
      };
      notes.push(note);
      return note;
    },
    createGain() {
      const note = notes.at(-1);
      return {
        gain: {
          setValueAtTime(value, time) {
            note.envelope.push([value, time]);
          },
          exponentialRampToValueAtTime(value, time) {
            note.envelope.push([value, time]);
          },
        },
        connect() {},
        disconnect() {
          note.gainDisconnected = true;
        },
      };
    },
  };
  return { context, notes };
}

test("notification signal schedules two bounded, softly faded notes and releases nodes", async () => {
  const { context, notes } = audio();
  assert.equal(await playChatNotification(context), true);
  assert.equal(notes.length, 2);
  assert.deepEqual(
    notes.map((note) => note.hz),
    [880, 1174.66],
  );
  assert.equal(notes[0].start, 2);
  assert.ok(notes[1].start > notes[0].start);
  for (const note of notes) {
    assert.ok(note.stop - note.start <= 0.211);
    assert.equal(note.envelope[0][0], 0.001);
    assert.equal(note.envelope[2][0], 0.001);
    assert.ok(note.envelope[1][0] <= 0.1);
    note.onended();
    assert.equal(note.disconnected, true);
    assert.equal(note.gainDisconnected, true);
  }
});
test("a suspended context resumes before playing, a closed context never plays", async () => {
  const suspended = audio("suspended");
  assert.equal(await playChatNotification(suspended.context), true);
  assert.equal(suspended.context.resumes, 1);
  const closed = audio("closed");
  assert.equal(await playChatNotification(closed.context), false);
  assert.equal(closed.notes.length, 0);
});
test("blocked autoplay is reported without scheduling a silent signal", async () => {
  const blocked = audio("suspended", true);
  await assert.rejects(
    playChatNotification(blocked.context),
    /Autoplay blocked/,
  );
  assert.equal(blocked.notes.length, 0);
});
test("tab title alternates the alert and unread counter, clearing to the app title", () => {
  assert.equal(
    chatNotificationTitle("Tapme Flowers", 1, false),
    "(1) Tapme Flowers",
  );
  assert.equal(
    chatNotificationTitle("Tapme Flowers", 1, true),
    "● (1) Новое сообщение — Tapme Flowers",
  );
  assert.equal(
    chatNotificationTitle("Tapme Flowers", 0, true),
    "Tapme Flowers",
  );
});

const hookSource = readFileSync(
  new URL("../src/chat-notifications.tsx", import.meta.url),
  "utf8",
);
const hookCompiled = ts.transpileModule(hookSource, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.CommonJS,
    jsx: ts.JsxEmit.ReactJSX,
  },
}).outputText;
async function notificationHarness(enabled = true) {
  const effects = [],
    state = [],
    timers = new Map(),
    intervals = new Map(),
    storage = new Map([["tapme-chat-sound:user", enabled ? "on" : "off"]]);
  const listeners = { document: new Map(), window: new Map() },
    calls = [],
    played = [];
  let sequence = 0,
    focused = true;
  const queue = [
    { waiting: 1, unread: 3, latest_inbound_id: "100", items: [] },
    {
      waiting: 1,
      unread: 4,
      latest_inbound_id: "101",
      items: [
        { id: "101", chat_id: "other", name: "Тест", text: "Новое сообщение" },
      ],
    },
  ];
  const eventSurface = (name) => ({
    addEventListener(type, fn) {
      if (!listeners[name].has(type)) listeners[name].set(type, new Set());
      listeners[name].get(type).add(fn);
    },
    removeEventListener(type, fn) {
      listeners[name].get(type)?.delete(fn);
    },
  });
  const document = {
    ...eventSurface("document"),
    title: "Tapme Flowers",
    hidden: false,
    hasFocus: () => focused,
  };
  const window = {
    ...eventSurface("window"),
    setTimeout(fn, delay) {
      const id = ++sequence;
      timers.set(id, { fn, delay });
      return id;
    },
    setInterval(fn) {
      const id = ++sequence;
      intervals.set(id, fn);
      return id;
    },
  };
  const exports = {};
  vm.runInNewContext(hookCompiled, {
    exports,
    AbortController,
    AudioContext: class {
      state = "running";
      async resume() {
        this.state = "running";
      }
      async close() {
        this.state = "closed";
      }
    },
    window,
    document,
    navigator: { locks: { request: async (_key, fn) => fn() } },
    localStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
    },
    clearTimeout: (id) => timers.delete(id),
    clearInterval: (id) => intervals.delete(id),
    require(name) {
      if (name === "react")
        return {
          useState(initial) {
            const index = state.length;
            state.push(typeof initial === "function" ? initial() : initial);
            return [
              state[index],
              (value) => {
                state[index] =
                  typeof value === "function" ? value(state[index]) : value;
              },
            ];
          },
          useRef: (value) => ({ current: value }),
          useEffect: (fn) => effects.push(fn),
        };
      if (name === "./api")
        return {
          businessPath: (id, suffix) => `/${id}/${suffix}/`,
          request: async (path) => {
            calls.push(path);
            return (
              queue.shift() ?? {
                waiting: 1,
                unread: 4,
                latest_inbound_id: "101",
                items: [],
              }
            );
          },
        };
      if (name === "./chat-notification-sound")
        return {
          chatNotificationTitle,
          playChatNotification: async (context) => {
            assert.equal(context.state, "running");
            played.push(true);
            return true;
          },
        };
      return {};
    },
  });
  const hook = exports.useChatNotifications("shop", "user", "current");
  const cleanup = effects.map((effect) => effect());
  const flush = () => new Promise((resolve) => setImmediate(resolve));
  await flush();
  return {
    hook,
    state,
    document,
    storage,
    calls,
    played,
    async poll() {
      const entry = [...timers].find(([, timer]) => timer.delay === 10000);
      assert.ok(entry, "polling should schedule its next request");
      timers.delete(entry[0]);
      entry[1].fn();
      await flush();
    },
    async emit(surface, type) {
      if (type === "focus") focused = true;
      for (const fn of listeners[surface].get(type) ?? []) fn({});
      await flush();
    },
    tick() {
      for (const fn of intervals.values()) fn();
    },
    close() {
      for (const fn of cleanup) if (typeof fn === "function") fn();
    },
  };
}
test("new inbound flashes the tab, plays once and shows a toast; old unread history stays quiet", async () => {
  const app = await notificationHarness();
  assert.equal(app.document.title, "(3) Tapme Flowers");
  assert.equal(app.played.length, 0);
  await app.emit("document", "pointerdown");
  await app.poll();
  assert.match(app.document.title, /Новое сообщение/);
  assert.equal(app.state[2].chat_id, "other");
  assert.equal(app.played.length, 1);
  assert.match(app.calls[1], /after=100/);
  assert.equal(app.state[4].revision, 1);
  app.tick();
  assert.equal(app.document.title, "(4) Tapme Flowers");
  app.tick();
  assert.match(app.document.title, /Новое сообщение/);
  await app.emit("window", "focus");
  app.tick();
  assert.equal(app.document.title, "(4) Tapme Flowers");
  assert.equal(app.played.length, 1);
  app.close();
  assert.equal(app.document.title, "Tapme Flowers");
});
test("muting still shows incoming notifications and tab alerts without playing sound", async () => {
  const app = await notificationHarness(false);
  await app.emit("document", "pointerdown");
  await app.poll();
  assert.match(app.document.title, /Новое сообщение/);
  assert.equal(app.played.length, 0);
  app.close();
});
test("enabling sound persists the preference and plays a test signal", async () => {
  const app = await notificationHarness(false);
  await app.hook.toggle();
  assert.equal(app.storage.get("tapme-chat-sound:user"), "on");
  assert.equal(app.played.length, 1);
  assert.equal(app.state[3], "Звук уведомлений включён");
  app.close();
});
