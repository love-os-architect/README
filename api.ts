export type MetricPacket = {
  timestamp: string;
  agent_id: string;
  hrv_ms: number;
  eda_microsiemens: number;
  speech_sync: number;
  response_delay_sec: number;
  primary_will_v: number;
  group_id: string;
  R?: number;
  I?: number;
  r?: number;
  hidden_friction?: number;
};

export function connectSSE(
  url: string,
  onData: (data: MetricPacket) => void,
  onError?: (e: any) => void
) {
  const es = new EventSource(url, { withCredentials: false });
  es.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      onData(data);
    } catch (e) {
      onError?.(e);
    }
  };
  es.onerror = (e) => onError?.(e);
  return () => es.close();
}
