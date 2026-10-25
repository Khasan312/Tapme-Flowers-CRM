let csrfToken = "";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

function messages(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(messages);
  if (value && typeof value === "object")
    return Object.values(value).flatMap(messages);
  return [];
}

export async function request<T>(
  path: string,
  options: RequestInit & { point?: string } = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  const point =
    options.point ?? new URLSearchParams(location.search).get("point");
  if (point && path.startsWith("/businesses/"))
    headers.set("X-Tapme-Point", point);
  const write = options.method && options.method !== "GET";
  if (write) {
    if (!csrfToken)
      csrfToken = (await request<{ csrf_token: string }>("/auth/csrf/"))
        .csrf_token;
    headers.set("X-CSRFToken", csrfToken);
    if (!(options.body instanceof FormData))
      headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch("/api/v1" + path, {
      ...options,
      headers,
      credentials: "same-origin",
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw new ApiError(
      "Не удалось связаться с сервером. Проверьте соединение и повторите.",
      0,
    );
  }
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 403) csrfToken = "";
    throw new ApiError(
      response.status >= 500
        ? "Сервер не смог выполнить запрос. Попробуйте ещё раз."
        : messages(data).join(" ") || "Не удалось выполнить запрос.",
      response.status,
    );
  }
  if (data?.csrf_token) csrfToken = data.csrf_token;
  return data as T;
}

export function errorText(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Произошла ошибка. Попробуйте ещё раз.";
}

export function businessPath(id: string, resource: string): string {
  return `/businesses/${id}/${resource}/`;
}

export function price(value: string | number): string {
  return (
    new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(
      Number(value),
    ) + " сом"
  );
}
