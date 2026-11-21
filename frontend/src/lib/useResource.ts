import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";

export interface Resource<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  /** Fetch again, keeping the current data on screen while loading. */
  reload: () => void;
}

/**
 * Load data with a fetcher and expose loading/error state.
 * Refetches whenever ``deps`` change; stale responses are ignored so a slow
 * request can never overwrite a newer one.
 */
export function useResource<T>(fetcher: () => Promise<T>, deps: readonly unknown[]): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const latest = useRef(0);
  // The fetcher is intentionally read through a ref: callers pass inline closures.
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const ticket = ++latest.current;
    setLoading(true);
    fetcherRef
      .current()
      .then((result) => {
        if (ticket !== latest.current) return;
        setData(result);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (ticket !== latest.current) return;
        setError(caught instanceof ApiError ? caught : new ApiError(String(caught), null));
      })
      .finally(() => {
        if (ticket === latest.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((value) => value + 1), []);
  return { data, error, loading, reload };
}
