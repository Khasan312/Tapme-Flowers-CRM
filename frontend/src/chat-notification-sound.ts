export function chatNotificationTitle(
  base: string,
  unread: number,
  flash: boolean,
) {
  if (!unread) return base;
  return flash
    ? `● (${unread}) Новое сообщение — ${base}`
    : `(${unread}) ${base}`;
}

export async function playChatNotification(context: AudioContext) {
  if (context.state === "suspended") await context.resume();
  if (context.state !== "running") return false;
  // Two short notes with a soft envelope avoid a harsh click at either end.
  for (const [offset, frequency] of [
    [0, 880],
    [0.13, 1174.66],
  ]) {
    const start = context.currentTime + offset;
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(frequency, start);
    gain.gain.setValueAtTime(0.001, start);
    gain.gain.exponentialRampToValueAtTime(0.07, start + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.001, start + 0.2);
    oscillator.onended = () => {
      oscillator.disconnect();
      gain.disconnect();
    };
    oscillator.start(start);
    oscillator.stop(start + 0.21);
  }
  return true;
}
