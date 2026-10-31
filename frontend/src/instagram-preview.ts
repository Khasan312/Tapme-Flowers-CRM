import type { ChatMessage } from "./chat-types";
import { newUuid } from "./uuid";

export type InstagramPreviewChat = {
  id: string;
  name: string;
  handle: string;
  note: string;
  tags: string[];
  folders: string[];
  assigned: string | null;
  unread: number;
  waiting: boolean;
  closed: boolean;
  messages: ChatMessage[];
  nameConfirmed?: boolean;
  draft?: InstagramPreviewOrder;
  orders?: InstagramPreviewOrder[];
};
export type InstagramPreviewFolder = { id: string; name: string };
export type InstagramPreviewOrder = {
  id: string;
  description: string;
  date: string;
  time: string;
  amount: string;
};

export const previewStaff = [
  { id: "aisuluu", name: "Айсулуу" },
  { id: "meerim", name: "Мээрим" },
];

export function previewMessage(
  text: string,
  direction: "in" | "out",
  minutesAgo = 0,
  reply: ChatMessage | null = null,
): ChatMessage {
  const id = newUuid();
  return {
    id,
    request_id: id,
    text,
    direction,
    kind: "text",
    status: direction === "in" ? "received" : minutesAgo ? "read" : "sent",
    sender: direction === "out" ? "Айсулуу" : "",
    automated: false,
    error: "",
    external_id: id,
    context_id: reply?.id || "",
    reply_to: reply,
    happened_at: new Date(Date.now() - minutesAgo * 60000).toISOString(),
    created_at: new Date().toISOString(),
    media_url: null,
    media_type: "",
    media_name: "",
  };
}

export function createInstagramPreview() {
  const folders: InstagramPreviewFolder[] = [
    { id: "clients", name: "Клиенты" },
    { id: "suppliers", name: "Поставщики" },
    { id: "payment", name: "Ждём оплату" },
  ];
  const chats: InstagramPreviewChat[] = [
    {
      id: "alina",
      name: "Алина Садыкова",
      handle: "alina.sadykova",
      note: "Любит нежные оттенки и небольшие букеты. Уточнить адрес перед доставкой.",
      tags: ["Новый клиент", "Доставка"],
      nameConfirmed: false,
      folders: ["clients"],
      assigned: "aisuluu",
      unread: 0,
      waiting: true,
      closed: false,
      messages: [
        previewMessage(
          "Здравствуйте! Очень понравился ваш нежный букет из пионов 🌸",
          "in",
          16,
        ),
        previewMessage(
          "Добрый день, Алина! Спасибо 🤍 Для какого повода подбираете букет?",
          "out",
          14,
        ),
        previewMessage(
          "У мамы завтра день рождения. Хотела бы что-то в светлых оттенках, до 5 000 сом.",
          "in",
          12,
        ),
        previewMessage(
          "Соберём воздушный букет с пионами и маттиолой. Добавим открытку с вашим пожеланием.",
          "out",
          9,
        ),
        previewMessage(
          "Как раз то, что нужно! А завтра к 11:00 сможете доставить?",
          "in",
          2,
        ),
      ],
    },
    {
      id: "maria",
      name: "Мария Ким",
      handle: "maria.kim",
      note: "Букет к годовщине. Ждём подтверждение оплаты.",
      tags: ["Ждём оплату"],
      folders: ["clients", "payment"],
      assigned: "meerim",
      unread: 2,
      waiting: true,
      closed: false,
      messages: [
        previewMessage("Можно заказать 25 белых роз на вечер?", "in", 32),
        previewMessage(
          "Да, подготовим к 18:00. Букет будет стоить 4 500 сом.",
          "out",
          28,
        ),
        previewMessage("Хорошо! Подскажите, как оплатить?", "in", 5),
        previewMessage("И открытку, пожалуйста, без подписи 🤍", "in", 4),
      ],
    },
    {
      id: "diana",
      name: "Диана Оморова",
      nameConfirmed: false,
      handle: "diana.omorova",
      note: "Первое обращение. Подбирает букет для подруги.",
      tags: ["Новый клиент"],
      folders: ["clients"],
      assigned: null,
      unread: 1,
      waiting: true,
      closed: false,
      messages: [
        previewMessage(
          "Добрый день! Какие букеты есть сегодня в наличии? 💐",
          "in",
          7,
        ),
      ],
    },
    {
      id: "supplier",
      name: "Цветочная ферма",
      handle: "flower.farm.example",
      note: "Пример переписки с поставщиком. Поставка по вторникам и пятницам.",
      tags: ["Поставщик"],
      folders: ["suppliers"],
      assigned: "aisuluu",
      unread: 0,
      waiting: false,
      closed: false,
      messages: [
        previewMessage(
          "Добрый день! На пятницу ожидаем свежую маттиолу и эустому.",
          "in",
          56,
        ),
        previewMessage(
          "Спасибо! Пришлите, пожалуйста, список оттенков и цены.",
          "out",
          49,
        ),
      ],
    },
    {
      id: "aizhan",
      name: "Айжан Абдиева",
      handle: "aizhan.abdieva",
      note: "Букет доставлен, клиент остался доволен.",
      tags: ["Заказ выполнен"],
      folders: ["clients"],
      assigned: "meerim",
      unread: 0,
      waiting: false,
      closed: true,
      messages: [
        previewMessage(
          "Ваш букет доставлен. Спасибо, что выбрали нас!",
          "out",
          120,
        ),
        previewMessage("Спасибо большое! Мама в восторге 🥰", "in", 115),
      ],
    },
  ];
  return { folders, chats };
}
