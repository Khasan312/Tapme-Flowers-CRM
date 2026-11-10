const base = import.meta.env.BASE_URL;

export const siteUrl = (path = "") => base + path;

export function marketingPath(location: Location): string | null {
  if (!location.pathname.startsWith(base)) return null;
  const path = location.pathname.slice(base.length).replace(/\/$/, "");
  if (path === "login" || path === "platform") return null;
  const params = new URLSearchParams(location.search);
  const workspaceKeys = [
    "view",
    "tab",
    "business",
    "point",
    "customer",
    "order",
    "chat",
    "channel",
  ];
  if (!path && workspaceKeys.some((key) => params.has(key))) return null;
  return path;
}
