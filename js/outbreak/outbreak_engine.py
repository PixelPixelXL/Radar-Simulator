"""outbreak_engine.py — motor de um "dia de outbreak" SINTÉTICO (simulação, não é tempo real).

Tempestades se movem, produzem tornados, um "previsor" automático emite polígonos de alerta
e o dia é pontuado (antecedência, alarmes falsos, tornados sem aviso).
Coordenadas em km (x = leste, y = norte) com origem no radar; a conversão para lat/lon é opcional.
Os parâmetros de risco e de EF são do JOGO, não estatísticas reais.
"""

import math
import random
from dataclasses import dataclass, field

import numpy as np

R_EARTH = 6371.0
RISK = {
    "Marginal": (0, 3),
    "Slight": (3, 9),
    "Enhanced": (8, 20),
    "Moderate": (15, 40),
    "High": (30, 70),
}
EF = [("EF0", 0.50), ("EF1", 0.30), ("EF2", 0.14), ("EF3", 0.05), ("EF4", 0.01)]


# ---------- geometria ----------

def km_to_latlon(x, y, lat0, lon0):
    """Inverso da projeção azimutal equidistante centrada no radar."""
    rho = math.hypot(x, y)
    if rho < 1e-9:
        return lat0, lon0

    c, p0 = rho / R_EARTH, math.radians(lat0)
    lat = math.asin(
        math.cos(c) * math.sin(p0)
        + y * math.sin(c) * math.cos(p0) / rho
    )
    lon = math.radians(lon0) + math.atan2(
        x * math.sin(c),
        rho * math.cos(p0) * math.cos(c)
        - y * math.sin(p0) * math.sin(c),
    )
    return math.degrees(lat), math.degrees(lon)


def inside(poly, x, y):
    """Ponto em polígono (ray casting)."""
    n, c = len(poly), False
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def warning_polygon(x, y, vx, vy, minutes=30.0, half_width=9.0, back=4.0, spread_deg=10.0):
    """Polígono de 4 vértices ao longo da trajetória prevista (km, vx/vy em km/min)."""
    sp = math.hypot(vx, vy) or 1e-6
    ux, uy = vx / sp, vy / sp
    nx, ny = -uy, ux
    bx, by = x - ux * back, y - uy * back
    ex, ey = x + vx * minutes, y + vy * minutes
    w2 = half_width + math.tan(math.radians(spread_deg)) * sp * minutes
    return [
        (bx + nx * half_width, by + ny * half_width),
        (ex + nx * w2, ey + ny * w2),
        (ex - nx * w2, ey - ny * w2),
        (bx - nx * half_width, by - ny * half_width),
    ]


# ---------- entidades ----------

@dataclass
class Tornado:
    storm: int
    t0: float
    t1: float
    ef: str
    p0: tuple
    p1: tuple
    lead: float = 14.0  # minutos entre o início da assinatura de rotação e o tornado

    def pos(self, t):
        f = min(1.0, max(0.0, (t - self.t0) / max(1e-6, self.t1 - self.t0)))
        return (
            self.p0[0] + (self.p1[0] - self.p0[0]) * f,
            self.p0[1] + (self.p1[1] - self.p0[1]) * f,
        )

    def active(self, t):
        return self.t0 <= t <= self.t1


@dataclass
class Storm:
    id: int
    x0: float
    y0: float
    vx: float  # km/min
    vy: float
    born: float
    dies: float
    peak: float  # dBZ
    bump_t: float  # centro de um pico de rotação sem tornado (isca de alarme falso)
    bump_a: float
    tornadoes: list = field(default_factory=list)

    def pos(self, t):
        return self.x0 + self.vx * (t - self.born), self.y0 + self.vy * (t - self.born)

    def active(self, t):
        return self.born <= t <= self.dies

    def rot(self, t):
        """Assinatura de rotação (0..1): sobe antes do tornado, fica alta durante e decai depois."""
        r = self.bump_a * math.exp(-0.5 * ((t - self.bump_t) / 6.0) ** 2)
        for tor in self.tornadoes:
            if t < tor.t0:
                r = max(r, max(0.0, 1 - (tor.t0 - t) / max(tor.lead, 0.5)) * 0.9)
            elif t <= tor.t1:
                r = max(r, 0.95)
            else:
                r = max(r, 0.95 * math.exp(-(t - tor.t1) / 6.0))
        return r


@dataclass
class Warning:
    storm: int
    t_issue: float
    t_exp: float
    poly: list
    verified: bool = False


@dataclass
class Day:
    risk: str
    minutes: int
    storms: list
    warnings: list = field(default_factory=list)
    news: list = field(default_factory=list)

    @property
    def tornadoes(self):
        return [t for s in self.storms for t in s.tornadoes]


# ---------- geração do dia ----------

def make_day(seed, risk="Slight", minutes=420, range_km=140.0):
    rng = random.Random(seed)
    lo, hi = RISK[risk]
    n_tor = rng.randint(lo, hi)
    n_tornadic = max(1 if n_tor else 0, round(n_tor / 1.5))
    n_storms = n_tornadic + rng.randint(2, 4 + n_tor // 3)
    storms, left = [], n_tor

    for i in range(n_storms):
        ang = math.radians(rng.uniform(40, 80))  # as tempestades vão para ENE
        sp = rng.uniform(0.7, 1.2)  # km/min (~26 a 45 mph)
        vx, vy = sp * math.sin(ang), sp * math.cos(ang)
        born = rng.uniform(0, minutes * 0.55)
        dur = rng.uniform(90, 200)

        # Ponto de partida a sudoeste, de modo que a trilha cruze a área do radar.
        cross = rng.uniform(-60, 60)
        ux, uy = math.sin(ang), math.cos(ang)
        mid = born + rng.uniform(35, 70)
        mx, my = cross * -uy, cross * ux
        x0 = mx - ux * sp * (mid - born)
        y0 = my - uy * sp * (mid - born)

        s = Storm(
            i, x0, y0, vx, vy, born, born + dur,
            rng.uniform(50, 66),
            rng.uniform(born + 20, born + dur - 10),
            rng.uniform(0.25, 0.75),
        )

        if i < n_tornadic and left > 0:
            k = min(left, rng.choice([1, 1, 1, 2, 3]))
            t = born + rng.uniform(30, 60)

            for _ in range(k):
                ef = rng.choices(
                    [e for e, _ in EF],
                    [p for _, p in EF],
                )[0]
                d = rng.uniform(3, 8) + {
                    "EF0": 0, "EF1": 4, "EF2": 9, "EF3": 14, "EF4": 18
                }[ef]
                if t + d >= s.dies:
                    break

                p0, p1 = s.pos(t), s.pos(t + d)
                s.tornadoes.append(
                    Tornado(
                        i, t, t + d, ef, p0,
                        (p1[0] + rng.uniform(-1, 1), p1[1] + rng.uniform(-1, 1)),
                        rng.uniform(0, 4) if rng.random() < 0.3 else rng.uniform(8, 22),
                    )
                )
                t += d + rng.uniform(8, 25)

            left -= len(s.tornadoes)

        storms.append(s)

    return Day(risk, minutes, storms)


# ---------- previsor automático ----------

def run_forecaster(day, seed=0, threshold=0.5, duration=30.0):
    """Emite alertas de tornado com base na assinatura de rotação (com ruído e atraso de detecção)."""
    rng = random.Random(seed)
    active = {}

    for t in range(day.minutes + 1):
        for s in day.storms:
            if not s.active(t):
                continue

            w = active.get(s.id)
            if w and t < w.t_exp:
                continue

            if s.rot(t) + rng.gauss(0, 0.08) > threshold:
                x, y = s.pos(t)
                vx = s.vx * rng.uniform(0.9, 1.1)
                vy = s.vy * rng.uniform(0.9, 1.1)
                w = Warning(s.id, t, t + duration, warning_polygon(x, y, vx, vy, duration))
                active[s.id] = w
                day.warnings.append(w)
                day.news.append(
                    (t, "Tornado Warning (simulado) emitido para a tempestade %d" % s.id)
                )

        for tor in day.tornadoes:
            if int(tor.t0) == t:
                day.news.append((t, "Tornado %s (simulado) começou" % tor.ef))

    return day


# ---------- pontuação ----------

def score(day):
    tors = day.tornadoes
    for w in day.warnings:
        w.verified = False

    ahead, never, leads = 0, 0, []
    for tor in tors:
        t_start_pt = tor.pos(tor.t0)
        best = None

        for w in day.warnings:
            if w.t_issue <= tor.t0 <= w.t_exp and inside(w.poly, *t_start_pt):
                best = w if best is None or w.t_issue < best.t_issue else best

        covered = False
        for w in day.warnings:
            for t in np.arange(max(tor.t0, w.t_issue), min(tor.t1, w.t_exp) + 1e-9, 1.0):
                if inside(w.poly, *tor.pos(t)):
                    w.verified, covered = True, True

        if best is not None:
            ahead += 1
            leads.append(tor.t0 - best.t_issue)
        elif not covered:
            never += 1

    return {
        "tornados": len(tors),
        "alertas": len(day.warnings),
        "avisados_antes": ahead,
        "antecedência_média_min": round(sum(leads) / len(leads), 1) if leads else 0.0,
        "sem_aviso": never,
        "alarmes_falsos": sum(1 for w in day.warnings if not w.verified),
    }


# ---------- renderização de um quadro (radar sintético em grade cartesiana) ----------

def render_frame(day, t, path, radar_id="KDIX", half=140.0, res=1.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    n = int(2 * half / res)
    xs = np.linspace(-half, half, n)
    X, Y = np.meshgrid(xs, xs)
    Z = np.full(X.shape, -99.0)
    rng = np.random.default_rng(int(t))

    for s in day.storms:
        if not s.active(t):
            continue

        sx, sy = s.pos(t)
        r2 = (X - sx) ** 2 + (Y - sy) ** 2
        fade = min(1.0, (t - s.born) / 20.0, (s.dies - t) / 20.0)
        Z = np.maximum(Z, s.peak * fade - 12 * r2 / 7.0 ** 2)

        if s.rot(t) > 0.4:  # eco de gancho a sudoeste
            hx, hy = sx - 7, sy - 7
            Z = np.maximum(
                Z,
                s.peak * fade * 0.9
                - 12 * ((X - hx) ** 2 + (Y - hy) ** 2) / 3.0 ** 2,
            )

    Z = np.where(Z > 5, Z + rng.normal(0, 1.5, Z.shape), np.nan)
    stops = [
        (0, "#3a5a88"), (0.17, "#3cb44b"), (0.27, "#1e8c2a"),
        (0.4, "#e6e02a"), (0.5, "#f08a10"), (0.6, "#e03010"),
        (0.68, "#b00a0a"), (0.76, "#d83a8c"), (0.84, "#b04ad0"),
        (1, "#ffffff"),
    ]
    cmap = LinearSegmentedColormap.from_list("nws", stops)

    fig, ax = plt.subplots(figsize=(9, 9), dpi=100)
    fig.patch.set_facecolor("#05080b")
    ax.set_facecolor("#05080b")
    ax.imshow(
        Z, origin="lower", extent=[-half, half, -half, half],
        cmap=cmap, vmin=0, vmax=75,
    )

    for r in (50, 100):
        ax.add_patch(plt.Circle((0, 0), r, fill=False, ec="#8fa2b8", lw=0.6, alpha=0.5))

    for w in day.warnings:
        if w.t_issue <= t <= w.t_exp:
            xs_, ys_ = zip(*(w.poly + [w.poly[0]]))
            ax.plot(xs_, ys_, color="#ff3030", lw=2)

    for tor in day.tornadoes:
        if tor.active(t):
            px, py = tor.pos(t)
            ax.plot(px, py, "x", color="white", ms=10, mew=2)
            ax.text(px + 3, py + 3, tor.ef, color="white", fontsize=9)

    ax.set_xlim(-half, half)
    ax.set_ylim(-half, half)
    ax.set_xticks([])
    ax.set_yticks([])

    nact = sum(1 for tor in day.tornadoes if tor.active(t))
    ax.text(
        -half + 4, half - 8,
        "%s  |  %s risk  |  tornados ativos: %d" % (radar_id, day.risk, nact),
        color="#ffd23f", fontsize=12, weight="bold",
    )
    ax.text(
        0, -half + 6, "SIMULAÇÃO • NÃO É TEMPO REAL",
        color="#ffffff", fontsize=12, ha="center", weight="bold",
    )
    ax.text(
        half - 4, -half + 6, "t = %d min" % t,
        color="#cfe9cf", fontsize=10, ha="right",
    )
    fig.savefig(path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    day = run_forecaster(make_day(seed=7, risk="Slight"), seed=1)
    print(score(day))
    best = max(
        range(day.minutes),
        key=lambda t: sum(1 for tor in day.tornadoes if tor.active(t)),
    )
    render_frame(day, best, "frame.png")
    print("quadro em t =", best, "min")
