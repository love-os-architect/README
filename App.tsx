import { useEffect, useMemo, useState } from 'react';
import { Activity, Zap, ShieldAlert, Heart, Orbit } from 'lucide-react';
import { connectSSE, MetricPacket } from './api';

type MetricState = {
  V: number;
  R: number;
  I: number;
  r: number;
  hiddenFriction: number;
};

function clamp(x: number, a: number, b: number) {
  return Math.max(a, Math.min(b, x));
}

// 
function estimateR(pkt: MetricPacket) {
  const hrvTerm = 30 / Math.max(pkt.hrv_ms, 1);
  const edaTerm = 10 * Math.log(1 + Math.max(pkt.eda_microsiemens, 0));
  const latTerm = 8 * Math.log(1 + Math.max(pkt.response_delay_sec, 0));
  const syncTerm = -15 * clamp(pkt.speech_sync, 0, 1);
  return clamp(hrvTerm + edaTerm + latTerm + syncTerm, 1, 100);
}

function estimateRsync(pkt: MetricPacket, R: number) {
  const base = clamp(pkt.speech_sync, 0, 1);
  const adj = clamp(1 - R / 100, 0, 1);
  return clamp(0.6 * base + 0.4 * adj, 0, 1);
}

function Panel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-[#0f1620] p-6 rounded-xl border border-gray-800 shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg text-gray-300">{title}</h2>
        {icon}
      </div>
      {children}
    </div>
  );
}

export default function App() {
  const [metrics, setMetrics] = useState<MetricState>({
    V: 80, R: 40, I: 2, r: 0.35, hiddenFriction: 60
  });

  useEffect(() => {
    const stop = connectSSE('http://localhost:8787/stream', (pkt) => {
      const V = clamp(pkt.primary_will_v, 0, 100);
      const R = pkt.R ?? estimateR(pkt);
      const I = V / Math.max(R, 0.001);
      const r = clamp(pkt.r ?? estimateRsync(pkt, R), 0, 1);
      const hiddenFriction = R * 1.5 * (1 - r);

      setMetrics({ V, R, I, r, hiddenFriction });
    }, console.error);
    return () => stop();
  }, []);

  const resonanceColor = useMemo(() => (metrics.r > 0.8 ? 'text-green-400' : metrics.r > 0.5 ? 'text-yellow-400' : 'text-red-500'), [metrics.r]);
  const frictionColor = useMemo(() => (metrics.hiddenFriction > 50 ? 'text-red-500' : metrics.hiddenFriction > 20 ? 'text-yellow-400' : 'text-green-400'), [metrics.hiddenFriction]);

  return (
    <div className="min-h-screen text-white p-8 font-mono bg-black">
      <header className="mb-8 border-b border-gray-800 pb-4">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Orbit className="text-blue-400" size={36} />
          Love-OS: Resonance Dashboard
        </h1>
        <p className="text-gray-400 mt-2 text-sm">Real-time Phase Synchronization & Ego-Resistance Monitor</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Panel title="Resonance (r)" icon={<Activity className={resonanceColor} size={24} />}>
          <div className={`text-5xl font-bold ${resonanceColor}`}>{metrics.r.toFixed(3)}</div>
          <p className="text-xs text-gray-500 mt-2">Target: 1.000</p>
        </Panel>

        <Panel title="Resistance (R)" icon={<ShieldAlert className="text-yellow-500" size={24} />}>
          <div className="text-5xl font-bold text-yellow-500">{metrics.R.toFixed(1)} <span className="text-2xl">Ω</span></div>
          <p className="text-xs text-gray-500 mt-2">Ego defense / Calculation</p>
        </Panel>

        <Panel title="Primary Will (V)" icon={<Heart className="text-pink-500" size={24} />}>
          <div className="text-5xl font-bold text-pink-500">{metrics.V.toFixed(1)} <span className="text-2xl">V</span></div>
          <p className="text-xs text-gray-500 mt-2">Cosmic attraction / Root drive</p>
        </Panel>

        <Panel title="Hidden Friction" icon={<Zap className={frictionColor} size={24} />}>
          <div className={`text-5xl font-bold ${frictionColor}`}>{metrics.hiddenFriction.toFixed(1)} <span className="text-2xl">J</span></div>
          <p className="text-xs text-gray-500 mt-2">Heat loss due to Fake Resonance</p>
        </Panel>
      </div>

      <div className="bg-[#0f1620] p-6 rounded-xl border border-gray-800 shadow-lg">
        <h2 className="text-xl text-gray-300 mb-4 border-b border-gray-800 pb-2">System Output: I = V / R</h2>
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="text-left">
            <p className="text-gray-400 mb-1">Soul Current (I) — Vitality</p>
            <div className="text-6xl font-extrabold text-blue-400">{metrics.I.toFixed(2)} <span className="text-3xl">A</span></div>
          </div>
          <div className="bg-[#0b1118] p-4 rounded-lg text-sm text-green-400 font-mono w-full md:w-1/2">
            <p>{`> SYSTEM CHECK...`}</p>
            <p>{`> V: ${metrics.V.toFixed(2)} | R: ${metrics.R.toFixed(2)}`}</p>
            {metrics.I > 5 ? (
              <p className="text-pink-400 mt-2">{`> HIGH FLOW. TRUE RESONANCE ACHIEVED.`}</p>
            ) : (
              <p className="text-yellow-400 mt-2">{`> CAUTION: RESISTANCE ELEVATED. SURRENDER REQUIRED.`}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
