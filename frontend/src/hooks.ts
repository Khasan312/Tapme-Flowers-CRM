import { useEffect, useState } from "react";
import { ApiError, errorText, request } from "./api";

type RemoteState<T> = {
  path: string | null;
  data: T | null;
  error: string;
  loading: boolean;
};

export function useRemote<T>(path: string | null, revision = 0) {
  const [state, setState] = useState<RemoteState<T>>({
    path,
    data: null,
    error: "",
    loading: Boolean(path),
  });
  useEffect(() => {
    if (!path) {
      setState({ path, data: null, error: "", loading: false });
      return;
    }
    const controller = new AbortController();
    setState((previous) => ({
      path,
      data: previous.path === path ? previous.data : null,
      error: "",
      loading: true,
    }));
    request<T>(path, { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted)
          setState({ path, data: result, error: "", loading: false });
      })
      .catch((e) => {
        if (controller.signal.aborted) return;
        // Keep the last result on a temporary failure, but discard revoked or deleted data.
        const unavailable =
          e instanceof ApiError && [401, 403, 404].includes(e.status);
        setState((previous) => ({
          path,
          data: !unavailable && previous.path === path ? previous.data : null,
          error: errorText(e),
          loading: false,
        }));
      });
    return () => controller.abort();
  }, [path, revision]);
  // Hide another customer's/shop's/filter's result during render, before the effect runs.
  const current = state.path === path;
  const data = path && current ? state.data : null;
  const loading = Boolean(path) && (!current || state.loading);
  return {
    data,
    error: path && current ? state.error : "",
    loading,
    initialLoading: loading && data === null,
    refreshing: loading && data !== null,
  };
}
