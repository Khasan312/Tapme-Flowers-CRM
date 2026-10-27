import { useEffect, useRef, useState } from "react";
import { Bell, Volume2, VolumeX } from "lucide-react";
import { businessPath, request } from "./api";
import {
  chatNotificationTitle,
  playChatNotification,
} from "./chat-notification-sound";
import "./chat-notifications.css";

type Summary = {
  waiting: number;
  unread: number;
  latest_inbound_id: string;
  items: { id: string; chat_id: string; name: string; text: string }[];
};
function soundPreference(key: string) {
  try {
    return localStorage.getItem(key) === "on";
  } catch {
    return false;
  }
}

export function useChatNotifications(
  businessId: string | null,
  userId: string,
  activeChat: string | null,
) {
  const soundKey = `tapme-chat-sound:${userId}`;
  const [preference, setPreference] = useState(() => ({
    key: soundKey,
    enabled: soundPreference(soundKey),
  }));
  const sound = preference.key === soundKey && preference.enabled;
  const [counts, setCounts] = useState({
    businessId,
    userId,
    unread: 0,
    waiting: 0,
  });
  const [toast, setToast] = useState<Summary["items"][number] | null>(null);
  const [feedback, setFeedback] = useState("");
  const audio = useRef<AudioContext | null>(null);
  const soundRef = useRef(sound),
    activeRef = useRef(activeChat);
  soundRef.current = sound;
  activeRef.current = activeChat;
  useEffect(() => {
    setPreference({ key: soundKey, enabled: soundPreference(soundKey) });
    const sync = (event: StorageEvent) => {
      if (event.key === soundKey)
        setPreference({ key: soundKey, enabled: event.newValue === "on" });
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, [soundKey]);
  async function unlockAudio() {
    try {
      if (!audio.current || audio.current.state === "closed")
        audio.current = new AudioContext();
      if (audio.current.state === "suspended") await audio.current.resume();
      return audio.current;
    } catch {
      return null;
    }
  }
  useEffect(() => {
    const unlock = () => {
      if (soundRef.current) void unlockAudio();
    };
    document.addEventListener("pointerdown", unlock, true);
    document.addEventListener("keydown", unlock, true);
    return () => {
      document.removeEventListener("pointerdown", unlock, true);
      document.removeEventListener("keydown", unlock, true);
      if (audio.current && audio.current.state !== "closed")
        void audio.current.close().catch(() => {});
      audio.current = null;
    };
  }, []);
  useEffect(() => {
    setToast(null);
    if (!businessId) return;
    let cancelled = false,
      inFlight = false,
      initialized = false;
    let cursor = "0",
      unread = 0,
      flashing = false,
      phase = false;
    let timer: number | undefined;
    const controller = new AbortController();
    const baseTitle = document.title.replace(/^\(\d+\)\s*/, "");
    const focused = () => !document.hidden && document.hasFocus();
    const title = () => {
      document.title = chatNotificationTitle(
        baseTitle,
        unread,
        flashing && phase,
      );
    };
    async function notifyOnce(messageId: string) {
      const context = audio.current;
      if (!soundRef.current || !context || context.state !== "running") return;
      const key = `tapme-chat-notified:${userId}:${businessId}`;
      async function play() {
        if (cancelled || !soundRef.current) return;
        try {
          if (BigInt(localStorage.getItem(key) || "0") >= BigInt(messageId))
            return;
        } catch {
          /* Storage may be disabled. */
        }
        if (await playChatNotification(context!)) {
          try {
            localStorage.setItem(key, messageId);
          } catch {
            /* Sound still works without browser storage. */
          }
        }
      }
      try {
        // Several CRM tabs must not play the same incoming notification together.
        if (navigator.locks) await navigator.locks.request(key, play);
        else await play();
      } catch {
        /* A suspended or unavailable audio device must not stop polling. */
      }
    }
    async function poll() {
      if (cancelled || inFlight) return;
      clearTimeout(timer);
      inFlight = true;
      try {
        const data = await request<Summary>(
          businessPath(businessId!, "chats/summary") + `?after=${cursor}`,
          { signal: controller.signal },
        );
        if (cancelled) return;
        unread = data.unread;
        setCounts({ businessId, userId, unread, waiting: data.waiting });
        if (!unread) flashing = false;
        if (initialized && data.items.length) {
          const item = data.items.find(
            (item) => item.chat_id !== activeRef.current || !focused(),
          );
          if (item) setToast(item);
          if (item && unread) {
            flashing = true;
            phase = true;
          }
          void notifyOnce(data.items[0].id);
        }
        if (BigInt(data.latest_inbound_id) > BigInt(cursor))
          cursor = data.latest_inbound_id;
        initialized = true;
        title();
      } catch {
        /* Retry without clearing unread messages or playing old history. */
      } finally {
        inFlight = false;
        if (!cancelled) timer = window.setTimeout(() => void poll(), 10000);
      }
    }
    const wake = () => {
      if (focused()) {
        flashing = false;
        phase = false;
        title();
      }
      if (!document.hidden) void poll();
    };
    const acknowledge = () => {
      flashing = false;
      phase = false;
      title();
    };
    const titleTimer = window.setInterval(() => {
      if (flashing) {
        phase = !phase;
        title();
      }
    }, 1000);
    document.addEventListener("visibilitychange", wake);
    document.addEventListener("pointerdown", acknowledge);
    window.addEventListener("focus", wake);
    window.addEventListener("online", wake);
    void poll();
    return () => {
      cancelled = true;
      controller.abort();
      clearTimeout(timer);
      clearInterval(titleTimer);
      document.removeEventListener("visibilitychange", wake);
      document.removeEventListener("pointerdown", acknowledge);
      window.removeEventListener("focus", wake);
      window.removeEventListener("online", wake);
      document.title = baseTitle;
    };
  }, [businessId, userId]);
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 8000);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    if (!feedback) return;
    const timer = window.setTimeout(() => setFeedback(""), 4000);
    return () => clearTimeout(timer);
  }, [feedback]);
  async function toggle() {
    const enabled = !sound;
    soundRef.current = enabled;
    setPreference({ key: soundKey, enabled });
    try {
      localStorage.setItem(soundKey, enabled ? "on" : "off");
    } catch {
      /* Keep the setting for this session. */
    }
    if (!enabled) {
      setFeedback("Звук уведомлений выключен");
      return;
    }
    const context = await unlockAudio();
    try {
      const played = context && (await playChatNotification(context));
      setFeedback(
        played
          ? "Звук уведомлений включён"
          : "Не удалось включить звук. Нажмите кнопку ещё раз.",
      );
      if (!played) {
        soundRef.current = false;
        setPreference({ key: soundKey, enabled: false });
        try {
          localStorage.setItem(soundKey, "off");
        } catch {
          /* Ignore unavailable storage. */
        }
      }
    } catch {
      soundRef.current = false;
      setPreference({ key: soundKey, enabled: false });
      try {
        localStorage.setItem(soundKey, "off");
      } catch {
        /* Keep the state for this session. */
      }
      setFeedback("Не удалось воспроизвести звук. Проверьте звук браузера.");
    }
  }
  const current = counts.businessId === businessId && counts.userId === userId;
  return {
    waiting: current ? counts.waiting : 0,
    unread: current ? counts.unread : 0,
    toast,
    dismiss: () => setToast(null),
    sound,
    toggle,
    feedback,
  };
}

export function ChatNotificationControls({
  state,
  open,
}: {
  state: ReturnType<typeof useChatNotifications>;
  open: (id: string) => void;
}) {
  return (
    <>
      <button
        className={`chat-icon chat-sound-toggle ${state.sound ? "is-enabled" : ""}`}
        aria-label={
          state.sound ? "Выключить звук чатов" : "Включить звук чатов"
        }
        aria-pressed={state.sound}
        title={
          state.sound
            ? "Звук чатов включён"
            : "Включить звук чатов и прослушать сигнал"
        }
        onClick={() => void state.toggle()}
      >
        {state.sound ? <Volume2 size={18} /> : <VolumeX size={18} />}
      </button>
      {state.feedback && (
        <div className="chat-sound-feedback" role="status">
          {state.feedback}
        </div>
      )}
      {state.toast && (
        <div role="status" className="chat-toast">
          <Bell size={18} />
          <button
            onClick={() => {
              open(state.toast!.chat_id);
              state.dismiss();
            }}
          >
            <strong>{state.toast.name}</strong>
            <span>{state.toast.text}</span>
          </button>
          <button aria-label="Закрыть уведомление" onClick={state.dismiss}>
            ×
          </button>
        </div>
      )}
    </>
  );
}
