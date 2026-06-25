import { useEffect, useRef, useState } from "react";

/** Poll an async fetcher on an interval; returns latest data + loading/error. */
export function usePoll<T>(fetcher: () => Promise<T>, intervalMs = 2000, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const savedFetcher = useRef(fetcher);
  savedFetcher.current = fetcher;

  useEffect(() => {
    let alive = true;
    const run = async () => {
      try {
        const d = await savedFetcher.current();
        if (alive) {
          setData(d);
          setError(null);
        }
      } catch (e: any) {
        if (alive) setError(e?.message ?? "request failed");
      } finally {
        if (alive) setLoading(false);
      }
    };
    run();
    const id = setInterval(run, intervalMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, ...deps]);

  return { data, error, loading };
}
