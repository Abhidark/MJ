import { useState, useEffect } from 'react';
import { systemAPI } from '@/services/api';

export function useSystemStats(intervalMs = 5000) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const { data } = await systemAPI.getStats();
        if (!cancelled) { setStats(data); setLoading(false); }
      } catch { if (!cancelled) setLoading(false); }
    };
    poll();
    const id = setInterval(poll, intervalMs);
    return () => { cancelled = true; clearInterval(id); };
  }, [intervalMs]);

  return { stats, loading };
}
