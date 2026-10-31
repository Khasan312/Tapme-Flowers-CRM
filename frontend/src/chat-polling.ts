export type ChatPolling = { wake: () => void; stop: () => void };

/** Fast after activity; back off while unchanged. Pause entirely in a hidden tab. */
export function startChatPolling(
  load: () => Promise<boolean>,
  {
    canPoll = () => document.visibilityState === "visible" && navigator.onLine,
    fast = 3000,
    idle = 10000,
  }: { canPoll?: () => boolean; fast?: number; idle?: number } = {},
): ChatPolling {
  let stopped = false,
    running = false,
    again = false,
    quiet = 0;
  let timer: number | undefined;
  async function poll() {
    if (stopped || !canPoll()) return;
    if (running) {
      again = true;
      return;
    }
    running = true;
    window.clearTimeout(timer);
    try {
      quiet = (await load()) ? 0 : Math.min(quiet + 1, 4);
    } catch {
      quiet = Math.min(quiet + 1, 4);
    } finally {
      running = false;
      const catchUp = again;
      again = false;
      if (!stopped && canPoll()) {
        const delay = catchUp ? 0 : Math.min(idle, fast * 2 ** quiet);
        timer = window.setTimeout(() => void poll(), delay);
      }
    }
  }
  void poll();
  return {
    wake() {
      quiet = 0;
      window.clearTimeout(timer);
      void poll();
    },
    stop() {
      stopped = true;
      window.clearTimeout(timer);
    },
  };
}
