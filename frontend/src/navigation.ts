import { useCallback, useEffect, useState } from "react";
import type { SettingsTab } from "./settings";
import type { Business } from "./types";

export type View =
  "orders" | "chats" | "customers" | "reminders" | "deliveries" | "settings";
export type WorkspaceRoute = {
  view: View;
  settingsTab: SettingsTab;
  businessId: string;
  pointId: string;
  customerId: string | null;
  orderId: string | null;
  chatId: string | null;
};
export const homeRoute: WorkspaceRoute = {
  view: "orders",
  settingsTab: "staff",
  businessId: "",
  pointId: "",
  customerId: null,
  orderId: null,
  chatId: null,
};
const views: View[] = [
  "orders",
  "chats",
  "customers",
  "reminders",
  "deliveries",
  "settings",
];
const settingsTabs: SettingsTab[] = [
  "staff",
  "channels",
  "windows",
  "points",
  "templates",
  "reminders",
  "prices",
  "shop",
];
const uuid = (value: string | null) =>
  value &&
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
    ? value.toLowerCase()
    : null;

export function readRoute(): WorkspaceRoute {
  const params = new URLSearchParams(location.search);
  const candidate = params.get("view") as View;
  const view = views.includes(candidate) ? candidate : "orders";
  const tab = params.get("tab") as SettingsTab;
  return {
    view,
    settingsTab: settingsTabs.includes(tab) ? tab : "staff",
    businessId: uuid(params.get("business")) || "",
    pointId:
      uuid(params.get("point")) || (params.get("point") === "all" ? "all" : ""),
    customerId: view === "customers" ? uuid(params.get("customer")) : null,
    orderId: uuid(params.get("order")),
    chatId: view === "chats" ? uuid(params.get("chat")) : null,
  };
}

export function routeUrl(route: WorkspaceRoute) {
  const params = new URLSearchParams({ view: route.view });
  if (route.businessId) params.set("business", route.businessId);
  if (route.pointId) params.set("point", route.pointId);
  if (route.view === "settings") params.set("tab", route.settingsTab);
  if (route.view === "customers" && route.customerId)
    params.set("customer", route.customerId);
  if (route.orderId) params.set("order", route.orderId);
  if (route.view === "chats" && route.chatId) params.set("chat", route.chatId);
  return `${import.meta.env.BASE_URL}?${params}`;
}

export function accessibleRoute(
  route: WorkspaceRoute,
  businesses: Business[],
): WorkspaceRoute {
  const selected = businesses.find((b) => b.id === route.businessId);
  const business = selected || businesses[0];
  const office = business && ["owner", "manager"].includes(business.role);
  const unavailable = Boolean(route.businessId) && !selected;
  const next = {
    ...route,
    businessId: business?.id || "",
    pointId: unavailable ? "" : route.pointId,
    view: office ? route.view : ("orders" as const),
    settingsTab: office ? route.settingsTab : ("staff" as const),
    customerId: office && !unavailable ? route.customerId : null,
    orderId: office && !unavailable ? route.orderId : null,
    chatId: office && !unavailable ? route.chatId : null,
  };
  return Object.keys(next).every(
    (key) =>
      next[key as keyof WorkspaceRoute] === route[key as keyof WorkspaceRoute],
  )
    ? route
    : next;
}

export function useWorkspaceRoute() {
  const [route, setRoute] = useState(readRoute);
  const go = useCallback(
    (next: WorkspaceRoute, mode: "push" | "replace" = "push") => {
      const url = routeUrl(next);
      if (url !== location.pathname + location.search + location.hash) {
        // Keep sections in the query string under the configured application base.
        if (mode === "replace") history.replaceState(null, "", url);
        else history.pushState(null, "", url);
      }
      setRoute(next);
    },
    [],
  );
  useEffect(() => {
    const pop = () => setRoute(readRoute());
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);
  return { route, go };
}
