from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import time, json, math, random, datetime

app = FastAPI()

def clamp(x, a, b): return max(a, min(b, x))

def sse_stream():
    V, R = 80.0, 40.0
    while True:
        # 
        hrv = clamp(random.gauss(55, 8), 20, 100)
        eda = clamp(abs(random.gauss(2.5, 0.8)), 0, 8)
        sync = clamp(random.uniform(0.4, 0.9), 0, 1)
        delay = clamp(abs(random.gauss(10, 5)), 0, 120)
        V = clamp(V + (random.random() - 0.5) * 4, 0, 100)

        # Proxy Metrics
        hrvTerm = 30 / max(hrv, 1)
        edaTerm = 10 * math.log(1 + eda)
        latTerm = 8 * math.log(1 + delay)
        syncTerm = -15 * sync
        R = clamp(hrvTerm + edaTerm + latTerm + syncTerm, 1, 100)

        I = V / max(R, 0.001)
        r_base = sync
        r_adj = clamp(1 - R/100, 0, 1)
        r = clamp(0.6 * r_base + 0.4 * r_adj, 0, 1)
        hidden = R * 1.5 * (1 - r)

        pkt = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "agent_id": "demo",
            "hrv_ms": hrv,
            "eda_microsiemens": eda,
            "speech_sync": sync,
            "response_delay_sec": delay,
            "primary_will_v": V,
            "group_id": "team-42",
            "R": R, "I": I, "r": r, "hidden_friction": hidden
        }
        yield f"data: {json.dumps(pkt)}\n\n"
        time.sleep(1)

@app.get("/stream")
def stream():
    return StreamingResponse(sse_stream(), media_type="text/event-stream")
