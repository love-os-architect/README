import { WebSocketServer } from 'ws';

const wss = new WebSocketServer({ port: 8788 });
function clamp(x, a, b){ return Math.max(a, Math.min(b, x)); }

wss.on('connection', (ws) => {
  let V = 80, R = 40;
  const id = setInterval(() => {
    const hrv = clamp(55 + (Math.random()-0.5)*16, 20, 100);
    const eda = clamp(Math.abs(2.5 + (Math.random()-0.5)*1.6), 0, 8);
    const sync = clamp(0.65 + (Math.random()-0.5)*0.4, 0, 1);
    const delay = clamp(Math.abs(10 + (Math.random()-0.5)*10), 0, 120);
    V = clamp(V + (Math.random()-0.5)*4, 0, 100);

    const Rcalc = Math.min(100, Math.max(1,
      30/Math.max(hrv,1) + 10*Math.log(1+eda) + 8*Math.log(1+delay) - 15*sync
    ));
    R = Rcalc;
    const I = V / Math.max(R, 0.001);
    const r = clamp(0.6*sync + 0.4*(1-R/100), 0, 1);
    const hidden = R * 1.5 * (1 - r);

    ws.send(JSON.stringify({
      timestamp: new Date().toISOString(),
      agent_id: 'demo',
      hrv_ms: hrv,
      eda_microsiemens: eda,
      speech_sync: sync,
      response_delay_sec: delay,
      primary_will_v: V,
      group_id: 'team-42',
      R, I, r, hidden_friction: hidden
    }));
  }, 1000);
  ws.on('close', () => clearInterval(id));
});
console.log('WS server running on ws://localhost:8788');
