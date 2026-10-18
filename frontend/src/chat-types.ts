export type Channel = {
  configured: boolean;
  version: number;
  provider_mode: "fake" | "live";
  server_mode: "fake" | "live";
  simulator: boolean;
  waba_id: string;
  verify_token?: string;
  quality_rating: string;
  connection_error: string;
  checks: Record<string, boolean>;
  main_phone: string;
  autoreply: AutoReply | null;
  payment: PaymentSettings;
  status: "active" | "disconnected";
  display_name: string;
  display_phone: string;
  phone_number_id: string;
  last_webhook_at: string | null;
  webhook_path: string;
};
export type Conversation = {
  id: string;
  customer_id: string | null;
  name: string;
  phone: string;
  channel_phone: string;
  provider_mode: "fake" | "live";
  preview: string;
  last_message_at: string;
  last_inbound_at: string | null;
  waiting_since: string | null;
  unread: number;
  mode: "human" | "closed";
  version: number;
  assigned_to: string | null;
  assigned_name: string;
  needs_customer_link: boolean;
  can_reply: boolean;
  reply_reason: string;
  tags: string[];
  new_customer: boolean;
  origin: string;
};
export type ChatDetail = Conversation & {
  staff: { id: string; name: string }[];
  link_candidates: { id: string; name: string; phone: string }[];
  customer: null | {
    notes: string;
    created_at: string;
    consent: boolean;
    orders_count: number;
    dates: {
      id: string;
      label: string;
      person: string;
      month: number;
      day: number;
    }[];
    orders: {
      id: string;
      number: number;
      total: string;
      status: string;
      date: string;
    }[];
  };
};
export type ChatMessage = {
  id: string;
  request_id: string;
  direction: "in" | "out" | "system";
  text: string;
  kind: string;
  status:
    | "queued"
    | "sending"
    | "unknown"
    | "sent"
    | "delivered"
    | "read"
    | "failed"
    | "received";
  error: string;
  sender: string;
  automated: boolean;
  context_id: string;
  external_id: string | null;
  happened_at: string;
  created_at: string;
  media_url: string | null;
  media_type: string;
  media_name: string;
};

export type AutoReply = {
  enabled: boolean;
  start: string;
  end: string;
  open_text: string;
  closed_text: string;
};
export type PaymentSettings = {
  version: number;
  note: string;
  text: string;
  image_url: string | null;
};
export type QuickReply = {
  id: string;
  title: string;
  text: string;
  version: number;
};
