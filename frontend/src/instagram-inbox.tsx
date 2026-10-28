import { Chats, type ChatsProps } from "./chats";
import { InstagramChats } from "./instagram-chats";
import { businessPath } from "./api";
import { Notice } from "./components";
import { useRemote } from "./hooks";
import type { InstagramChannel } from "./chat-types";

export function InstagramInbox(props: ChatsProps) {
  const channel = useRemote<InstagramChannel>(
    businessPath(props.business.id, "channels/instagram"),
  );
  if (!channel.data)
    return (
      <div className="stack">
        <Notice>{channel.error || "Загружаем подключение Instagram…"}</Notice>
        {channel.error && (
          <button className="btn" onClick={props.settings}>
            Открыть настройки каналов
          </button>
        )}
      </div>
    );
  if (channel.data.version > 0)
    return <Chats {...props} channelKind="instagram" />;
  return (
    <>
      <div className="chat-test-banner">
        <span>Instagram ещё не подключён. Ниже — пример интерфейса.</span>
        <button className="btn" onClick={props.settings}>
          Подключить Instagram
        </button>
      </div>
      <InstagramChats timezone={props.business.timezone} />
    </>
  );
}
