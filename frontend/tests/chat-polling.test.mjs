import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { test } from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = readFileSync(
  new URL("../src/chat-polling.ts", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.CommonJS,
  },
}).outputText;
function clock() {
  const timers = new Map(),
    exports = {};
  let now = 0,
    sequence = 0;
  const window = {
    setTimeout(fn, delay) {
      const id = ++sequence;
      timers.set(id, { at: now + delay, fn });
      return id;
    },
    clearTimeout(id) {
      timers.delete(id);
    },
  };
  vm.runInNewContext(compiled, { exports, window });
  const flush = async () => {
    await Promise.resolve();
    await Promise.resolve();
  };
  return {
    start: exports.startChatPolling,
    now: () => now,
    flush,
    async advance(ms) {
      const target = now + ms;
      for (;;) {
        await flush();
        const next = [...timers].sort((a, b) => a[1].at - b[1].at)[0];
        if (!next || next[1].at > target) break;
        now = next[1].at;
        timers.delete(next[0]);
        next[1].fn();
      }
      now = target;
      await flush();
    },
  };
}
test("a quiet chat polls eight times in the first minute instead of twenty", async () => {
  const time = clock(),
    calls = [];
  const polling = time.start(
    async () => {
      calls.push(time.now());
      return calls.length === 1;
    },
    { canPoll: () => true },
  );
  await time.advance(60000);
  assert.deepEqual(calls, [0, 3000, 9000, 19000, 29000, 39000, 49000, 59000]);
  polling.stop();
  await time.advance(60000);
  assert.equal(calls.length, 8);
});
test("hidden/offline chats do not poll and wake immediately when visible again", async () => {
  const time = clock();
  let visible = false,
    calls = 0;
  const polling = time.start(
    async () => {
      calls++;
      return false;
    },
    { canPoll: () => visible },
  );
  await time.advance(60000);
  assert.equal(calls, 0);
  visible = true;
  polling.wake();
  await time.flush();
  assert.equal(calls, 1);
  visible = false;
  await time.advance(60000);
  assert.equal(calls, 1);
  visible = true;
  polling.wake();
  await time.flush();
  assert.equal(calls, 2);
  polling.stop();
});
test("focus and notification events share one in-flight request and one follow-up", async () => {
  const time = clock();
  let calls = 0,
    finish;
  const pending = new Promise((resolve) => {
    finish = resolve;
  });
  const polling = time.start(
    async () => {
      calls++;
      return calls === 1 ? await pending : false;
    },
    { canPoll: () => true },
  );
  polling.wake();
  polling.wake();
  polling.wake();
  assert.equal(calls, 1);
  finish(false);
  await time.advance(0);
  assert.equal(calls, 2);
  await time.advance(6000);
  assert.equal(calls, 2);
  await time.advance(4000);
  assert.equal(calls, 3);
  polling.stop();
});
test("temporary errors retry and real activity restores fast updates", async () => {
  const time = clock(),
    calls = [];
  const polling = time.start(
    async () => {
      calls.push(time.now());
      if (calls.length === 1) throw new Error("offline");
      return true;
    },
    { canPoll: () => true },
  );
  await time.advance(9000);
  assert.deepEqual(calls, [0, 6000, 9000]);
  polling.stop();
});
