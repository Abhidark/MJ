import { useEffect, useRef, useCallback } from 'react';

export function useSSE(url, onMessage, { onError, enabled = true } = {}) {
  const sourceRef = useRef(null);

  const close = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!enabled || !url) return;
    const es = new EventSource(url);
    sourceRef.current = es;
    es.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)); }
      catch { onMessage(e.data); }
    };
    es.onerror = () => {
      onError?.();
      es.close();
      setTimeout(() => {
        if (sourceRef.current === es) sourceRef.current = new EventSource(url);
      }, 5000);
    };
    return () => es.close();
  }, [url, enabled]);

  return { close };
}
