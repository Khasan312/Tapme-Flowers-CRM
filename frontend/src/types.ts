export type User = {
  id: string;
  username: string;
  is_platform_admin?: boolean;
  must_change_password?: boolean;
};
export type Business = {
  id: string;
  name: string;
  point_id?: string;
  currency: string;
  timezone: string;
  role: string;
};
export type Page<T> = { count: number; results: T[] };
export type Customer = {
  id: string;
  name: string;
  phone: string;
  additional_phones?: string[];
  notes: string;
  consent: boolean;
  source?: string;
  tags?: string[];
};
export type Product = {
  photo_url?: string;
  active?: boolean;
  id: string;
  name: string;
  price: string;
  version?: number;
};
export type Point = {
  windows: ShopSettings["windows"];
  id: string;
  name: string;
  short_name: string;
  address: string;
  city: string;
  active: boolean;
  is_primary: boolean;
  version: number;
  sort: number;
};
export type Order = {
  point_id: string;
  point_name: string;
  prepayment_percent: number;
  prepayment_required: string;
  payment_due_at: string | null;
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
    photo_url?: string;
    product_id: string;
    name: string;
    quantity: number;
    unit_price: string;
    total: string;
  }[];
};

export type Staff = {
  point_ids?: string[];
  id: string;
  name: string;
  username: string;
  role: string;
  is_active: boolean;
  phone: string;
};
export type ShopSettings = {
  version: number;
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
export type Photo = {
  id: string;
  kind: string;
  created_at: string;
  can_delete: boolean;
};
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
  version: number;
  enabled: boolean;
  offsets: number[];
  inactive_days: number;
  start_hour: number;
  end_hour: number;
  template: string;
  inactive_template: string;
  templates: Record<string, string>;
  custom_templates: { id: string; name: string; text: string }[];
};
export type Reminder = {
  point_id: string | null;
  point_name: string;
  kind: "before_event" | "after_last_order" | "after_delivery" | "holiday";
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
  recovered: boolean;
  preview?: string;
  event_date: string | null;
  scenario_id: string | null;
  scenario_name: string;
  pause_reason: string;
  sent_at: string | null;
  order_id: string | null;
  last_order: ReminderOrder | null;
  last_year_hint: ReminderOrder | null;
};
export type ReminderOrder = {
  id: string;
  number: number;
  date: string;
  total: string;
  items: string;
};
export type ReminderStep = {
  id: string;
  offset_days: number;
  template: string;
  enabled: boolean;
};
export type ReminderScenario = {
  id: string;
  name: string;
  kind: Reminder["kind"];
  enabled: boolean;
  event_labels: string[];
  holiday_month: number;
  holiday_day: number;
  audience: "consented_all" | "ordered_last_year";
  daily_cap: number;
  steps: ReminderStep[];
};
export type ReminderConfiguration = {
  version: number;
  enabled: boolean;
  start_hour: number;
  end_hour: number;
  min_days_between: number;
  scenarios: ReminderScenario[];
};
export type ReminderPage = Page<Reminder> & {
  stats: Record<string, number>;
  summary: {
    sent_today: number;
    total_today: number;
    ordered_week: number;
    revenue_week: string;
  };
  scenarios: { id: string; name: string }[];
  rules: Pick<
    ReminderConfiguration,
    "enabled" | "start_hour" | "end_hour" | "min_days_between"
  >;
};
export type Task = Pick<
  Order,
  | "point_id"
  | "point_name"
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
  items: { name: string; quantity: number; photo_url?: string }[];
  delivery_issue?: string;
  address?: string;
  recipient_phone?: string;
};
