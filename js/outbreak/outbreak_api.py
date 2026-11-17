"""API HTTP local para o Outbreak Engine do Radar-Simulator.

Execute dentro desta pasta com:
    python outbreak_api.py

A API é para desenvolvimento/local; GitHub Pages não executa este servidor Python.
"""
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from outbreak_engine import make_day, run_forecaster, score

HOST = os.environ.get("OUTBREAK_HOST", "127.0.0.1")
PORT = int(os.environ.get("OUTBREAK_PORT", "8000"))

simulation = {
    "day": None,
    "score": None,
    "running": False,
    "paused": False,
    "started_at": None,
    "elapsed_before_pause": 0.0,
    "risk": None,
    "seed": None,
}


def current_minute():
    if simulation["day"] is None:
        return 0
    elapsed = simulation["elapsed_before_pause"]
    if simulation["running"] and not simulation["paused"]:
        elapsed += time.monotonic() - simulation["started_at"]
    return min(simulation["day"].minutes, int(elapsed * 60))


def snapshot():
    day = simulation["day"]
    if day is None:
        return {"available": True, "running": False, "paused": False, "message": "Motor Python conectado; nenhuma simulação iniciada."}

    minute = current_minute()
    storms = []
    for storm in day.storms:
        if storm.active(minute):
            x, y = storm.pos(minute)
            storms.append({
                "id": storm.id, "x_km": round(x, 2), "y_km": round(y, 2),
                "dbz": round(storm.peak, 1), "rotation": round(storm.rot(minute), 2)
            })

    tornadoes = []
    for tornado in day.tornadoes:
        if tornado.active(minute):
            x, y = tornado.pos(minute)
            tornadoes.append({
                "storm": tornado.storm, "ef": tornado.ef,
                "x_km": round(x, 2), "y_km": round(y, 2)
            })

    warnings = []
    for warning in day.warnings:
        if warning.t_issue <= minute <= warning.t_exp:
            warnings.append({
                "storm": warning.storm, "issued": warning.t_issue,
                "expires": warning.t_exp, "polygon_km": warning.poly,
                "verified": warning.verified
            })

    return {
        "available": True,
        "running": simulation["running"],
        "paused": simulation["paused"],
        "finished": minute >= day.minutes,
        "minute": minute,
        "duration": day.minutes,
        "risk": day.risk,
        "seed": simulation["seed"],
        "storms": storms,
        "tornadoes_active": tornadoes,
        "warnings_active": warnings,
        "score": simulation["score"]
    }


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_json(200, {"ok": True})

    def do_GET(self):
        if self.path == "/api/outbreak/status":
            self.send_json(200, {
                "available": True,
                "running": simulation["running"],
                "message": "Backend Python conectado."
            })
        elif self.path == "/api/outbreak/state":
            self.send_json(200, snapshot())
        else:
            self.send_json(404, {"error": "Endpoint não encontrado."})

    def do_POST(self):
        if self.path not in {
            "/api/outbreak/start", "/api/outbreak/pause",
            "/api/outbreak/resume", "/api/outbreak/reset"
        }:
            self.send_json(404, {"error": "Endpoint não encontrado."})
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_json(400, {"error": "JSON inválido."})
            return

        if self.path.endswith("/start"):
            risk = payload.get("risk", "Slight")
            if risk not in {"Marginal", "Slight", "Enhanced", "Moderate", "High"}:
                self.send_json(400, {"error": "Nível de risco inválido."})
                return
            try:
                seed = int(payload.get("seed", 7))
            except (TypeError, ValueError):
                self.send_json(400, {"error": "Seed precisa ser um número inteiro."})
                return
            day = run_forecaster(make_day(seed=seed, risk=risk), seed=seed + 1)
            simulation.update({
                "day": day, "score": score(day), "running": True,
                "paused": False, "started_at": time.monotonic(),
                "elapsed_before_pause": 0.0, "risk": risk, "seed": seed
            })
            result = snapshot()
            result["message"] = "Dia sintético iniciado."
            self.send_json(200, result)

        elif self.path.endswith("/pause"):
            if simulation["day"] is not None and simulation["running"] and not simulation["paused"]:
                simulation["elapsed_before_pause"] += time.monotonic() - simulation["started_at"]
                simulation["paused"] = True
            result = snapshot()
            result["message"] = "Simulação pausada."
            self.send_json(200, result)

        elif self.path.endswith("/resume"):
            if simulation["day"] is not None and simulation["paused"]:
                simulation["started_at"] = time.monotonic()
                simulation["paused"] = False
            result = snapshot()
            result["message"] = "Simulação retomada."
            self.send_json(200, result)

        else:
            simulation.update({
                "day": None, "score": None, "running": False,
                "paused": False, "started_at": None,
                "elapsed_before_pause": 0.0, "risk": None, "seed": None
            })
            self.send_json(200, {
                "available": True, "running": False,
                "message": "Simulação reiniciada."
            })

    def log_message(self, fmt, *args):
        print("[Outbreak API] " + fmt % args)


if __name__ == "__main__":
    print(f"Outbreak API disponível em http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
