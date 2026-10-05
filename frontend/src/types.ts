export type User = { id: string; username: string };
export type Business = {
  id: string;
  name: string;
  currency: string;
  timezone: string;
  role: string;
};
export type Page<T> = { count: number; results: T[] };
export type Customer = {
  id: string;
  name: string;
  phone: string;
  notes: string;
  consent: boolean;
  source?: string;
  tags?: string[];
};
export type Product = {
  active?: boolean;
  id: string;
  name: string;
  price: string;
  version?: number;
};
export type Order = {
  occasion: string;
  source: string;
  relation: string;
  id: string;
  number: number;
  customer_id: string;
  customer_name: string;
  customer_phone: string;
  recipient_name: string;
  recipient_phone: string;
  fulfillment: "pickup" | "courier";
  delivery_date: string;
  window_start: string;
  window_end: string;
  address: string;
  notes: string;
  card: string;
  status: string;
  version: number;
  florist_id: string | null;
  courier_id: string | null;
  completed_at: string | null;
  cancellation_reason: string;
  delivery_issue: string;
  delivery_fee: string;
  paid_amount: string;
  total: string;
  created_at: string;
  lines: {
    product_id: string;
    name: string;
    quantity: number;
    unit_price: string;
    total: string;
  }[];
};

export type Staff = {
  id: string;
  name: string;
  username: string;
  role: string;
  is_active: boolean;
  phone: string;
};
export type ShopSettings = {
  name: string;
  address: string;
  phone: string;
  timezone: string;
  windows: { start: string; end: string; capacity: number; price: string }[];
  city: string;
  whatsapp: string;
  opening_hours: string;
  pickup_unlimited: boolean;
  enforce_capacity: boolean;
};
export type Payment = {
  id: string;
  amount: string;
  kind: string;
  method: string;
  note: string;
  created_at: string;
};
export type Photo = { id: string; kind: string; created_at: string };
export type HistoryEvent = {
  id: number;
  kind: string;
  detail: string;
  created_at: string;
  actor__username: string;
};
export type Feedback = {
  id: string;
  kind: string;
  message: string;
  rating: number | null;
  status: string;
  outcome: string;
  created_at: string;
};
export type Recipient = {
  id: string;
  name: string;
  relation: string;
  phone: string;
  address: string;
  notes: string;
};
export type ImportantDate = {
  id: string;
  label: string;
  person: string;
  month: number;
  day: number;
};
export type CustomerProfile = Customer & {
  code: number;
  created_at: string;
  version: number;
  recipients: Recipient[];
  dates: ImportantDate[];
};
export type ReminderRules = {
  enabled: boolean;
  offsets: number[];
  inactive_days: number;
  start_hour: number;
  end_hour: number;
  template: string;
  inactive_template: string;
  templates: Record<string, string>;
};
export type Reminder = {
  kind: "date" | "inactive";
  id: string;
  customer_id: string;
  customer_name: string;
  phone: string;
  event: string;
  person: string;
  due_date: string;
  state: string;
  message: string;
  paused: boolean;
  preview?: string;
};
export type Task = Pick<
  Order,
  | "id"
  | "number"
  | "status"
  | "version"
  | "fulfillment"
  | "delivery_date"
  | "window_start"
  | "window_end"
  | "recipient_name"
  | "florist_id"
  | "courier_id"
  | "card"
> & {
  items: { name: string; quantity: number }[];
  delivery_issue?: string;
  address?: string;
  recipient_phone?: string;
};
