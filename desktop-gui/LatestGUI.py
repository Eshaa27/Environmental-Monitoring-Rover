#!/usr/bin/env python3

import sys, json, math, socket, threading

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QTextEdit, QFrame, QGridLayout,
    QSizePolicy, QTabWidget, QSpacerItem
)
from PySide6.QtCore  import Qt, Signal, QObject, QTimer, QPointF
from PySide6.QtGui   import (
    QFont, QKeyEvent, QPainter, QColor, QPen, QBrush, QPolygonF,
    QLinearGradient
)

# ============================================================
# SETTINGS
# ============================================================

ROVER_HOST  = "lorarover.local"
ROVER_PORT  = 5000
DRIVE_SPEED = 100

# ============================================================
# PALETTE
# ============================================================

BG        = "#0d1117"
SURFACE   = "#161b22"
SURFACE2  = "#1c2333"
SURFACE3  = "#21262d"
BORDER    = "#30363d"
TEXT      = "#c9d1d9"
TEXT2     = "#8b949e"
ACCENT    = "#58a6ff"
ACCENT2   = "#1f6feb"
GREEN     = "#3fb950"
GREEN2    = "#196c2e"
RED       = "#f85149"
RED2      = "#8b1a1a"
YELLOW    = "#e3b341"

# ============================================================
# GLOBAL STYLESHEET
# ============================================================

GLOBAL_QSS = f"""
QMainWindow, QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {SURFACE};
    border-radius: 0 8px 8px 8px;
}}
QTabBar::tab {{
    background: {SURFACE3};
    color: {TEXT2};
    border: 1px solid {BORDER};
    border-bottom: none;
    padding: 8px 20px;
    margin-right: 2px;
    border-radius: 6px 6px 0 0;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 1px;
}}
QTabBar::tab:selected {{
    background: {SURFACE};
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    background: {SURFACE2};
    color: {TEXT};
}}
QTextEdit {{
    background: {SURFACE3};
    color: #39d353;
    border: 1px solid {BORDER};
    border-radius: 6px;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    padding: 6px;
}}
QScrollBar:vertical {{
    background: {SURFACE2};
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""

# ============================================================
# SIGNALS
# ============================================================

class Signals(QObject):
    log       = Signal(str)
    status    = Signal(bool)
    pi_status = Signal(bool)
    sensors   = Signal(dict)

signals = Signals()

# ============================================================
# HELPERS
# ============================================================

def card(title="", accent_bar=True):
    """Returns (frame, inner_layout). frame has dark card styling."""
    f = QFrame()
    f.setObjectName("card")
    f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    f.setStyleSheet(
        "QFrame#card { "
        "background: " + SURFACE + "; "
        "border: 1px solid " + BORDER + "; "
        "border-radius: 10px; }"
    )
    vl = QVBoxLayout(f)
    vl.setContentsMargins(0, 0, 0, 0)
    vl.setSpacing(0)

    if accent_bar:
        bar = QFrame()
        bar.setFixedHeight(2)
        bar.setStyleSheet(
            "background: qlineargradient("
            "x1:0,y1:0,x2:1,y2:0,"
            "stop:0 " + ACCENT2 + ",stop:1 " + ACCENT + ");"
            "border-radius: 10px 10px 0 0;"
        )
        vl.addWidget(bar)

    inner_widget = QWidget()
    inner_widget.setStyleSheet("background: transparent;")
    inner = QVBoxLayout(inner_widget)
    inner.setContentsMargins(18, 14, 18, 16)
    inner.setSpacing(10)

    if title:
        h_row = QHBoxLayout()
        t = QLabel(title.upper())
        t.setStyleSheet(
            "color: " + TEXT2 + ";"
            "font-size: 10px;"
            "font-weight: 700;"
            "letter-spacing: 2px;"
        )
        h_row.addWidget(t)
        h_row.addStretch()
        inner.addLayout(h_row)
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: " + BORDER + ";")
        inner.addWidget(div)

    vl.addWidget(inner_widget, 1)
    return f, inner


def pill_label(text, color=None):
    """Small badge label."""
    lbl = QLabel(text)
    c = color or ACCENT
    lbl.setStyleSheet(
        "color: " + c + ";"
        "background: transparent;"
        "border: 1px solid " + c + ";"
        "border-radius: 8px;"
        "padding: 2px 8px;"
        "font-size: 9px;"
        "font-weight: 700;"
        "letter-spacing: 1px;"
    )
    return lbl


def section_label(text):
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "color: " + TEXT2 + ";"
        "font-size: 9px;"
        "font-weight: 700;"
        "letter-spacing: 2px;"
    )
    return lbl


def divider():
    d = QFrame()
    d.setFixedHeight(1)
    d.setStyleSheet("background: " + BORDER + ";")
    return d


def btn_primary(text, height=36):
    b = QPushButton(text)
    b.setFixedHeight(height)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(
        "QPushButton {"
        "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        "stop:0 " + ACCENT2 + ",stop:1 " + ACCENT + ");"
        "color: #0d1117;"
        "font-weight: 800;"
        "border: none;"
        "border-radius: 8px;"
        "padding: 0 18px;"
        "font-size: 11px;"
        "letter-spacing: 1px;"
        "}"
        "QPushButton:hover { background: " + ACCENT + "; }"
        "QPushButton:pressed { background: " + ACCENT2 + "; }"
    )
    return b


def btn_ghost(text, height=32):
    b = QPushButton(text)
    b.setFixedHeight(height)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(
        "QPushButton {"
        "background: transparent;"
        "color: " + TEXT2 + ";"
        "border: 1px solid " + BORDER + ";"
        "border-radius: 7px;"
        "padding: 0 14px;"
        "font-size: 11px;"
        "font-weight: 600;"
        "}"
        "QPushButton:hover { border-color: " + ACCENT + "; color: " + ACCENT + "; }"
        "QPushButton:pressed { background: " + SURFACE2 + "; }"
    )
    return b


def btn_danger(text, height=44):
    b = QPushButton(text)
    b.setFixedHeight(height)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(
        "QPushButton {"
        "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        "stop:0 " + RED2 + ",stop:1 " + RED + ");"
        "color: #fff;"
        "font-weight: 900;"
        "border: none;"
        "border-radius: 9px;"
        "font-size: 13px;"
        "letter-spacing: 1px;"
        "}"
        "QPushButton:hover { background: " + RED + "; }"
        "QPushButton:pressed { background: " + RED2 + "; }"
    )
    return b


# ============================================================
# RADAR WIDGET
# ============================================================

class RadarWidget(QWidget):
    MAX_DIST  = 100
    CONE_HALF = 28

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._front = -1
        self._right = -1
        self._left  = -1
        self._obs_dots = {}

    def update_sensors(self, front, right, left):
        self._front = front
        self._right = right
        self._left  = left
        self.update()

    def paintEvent(self, _):
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(0, 0, w, h, QColor("#0b1117"))

        ox       = w // 2
        oy       = int(h * 0.87)
        beam_len = int(min(w, h) * 0.78)

        for frac, label_cm in [(0.25, 25), (0.5, 50), (0.75, 75), (1.0, 100)]:
            rr = int(beam_len * frac)
            p.setPen(QPen(QColor(30, 55, 80, 150), 1, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawArc(ox - rr, oy - rr, rr * 2, rr * 2, 30 * 16, 120 * 16)
            p.setPen(QColor(50, 80, 110))
            p.setFont(QFont("monospace", 7))
            p.drawText(ox + 4, oy - rr + 10, f"{label_cm}cm")

        self._draw_beam(p, ox, oy, beam_len, self._front, -90,  "FRONT")
        self._draw_beam(p, ox, oy, beam_len, self._left,  -135, "LEFT")
        self._draw_beam(p, ox, oy, beam_len, self._right, -45,  "RIGHT")
        self._draw_obs_dots(p)
        self._draw_rover(p, ox, oy)

        p.setPen(QColor(50, 80, 110))
        p.setFont(QFont("monospace", 7))
        p.drawText(ox + 6, oy + 14, "0")
        p.end()

    def _beam_clear_r(self, dist_cm, beam_len):
        if dist_cm < 0 or dist_cm >= self.MAX_DIST:
            return beam_len
        return max(4, int(beam_len * dist_cm / self.MAX_DIST))

    def _draw_beam(self, p, ox, oy, beam_len, dist_cm, centre_deg, label):
        half     = self.CONE_HALF
        qt_start = -(centre_deg + half)
        qt_span  = half * 2
        clear_r  = self._beam_clear_r(dist_cm, beam_len)
        obstacle = (0 <= dist_cm < self.MAX_DIST)

        if obstacle:
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(180, 30, 30, 80)))
            p.drawPie(ox - beam_len, oy - beam_len,
                      beam_len * 2, beam_len * 2,
                      int(qt_start * 16), int(qt_span * 16))

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(31, 111, 235, 90)))
        p.drawPie(ox - clear_r, oy - clear_r,
                  clear_r * 2, clear_r * 2,
                  int(qt_start * 16), int(qt_span * 16))

        edge_col = QColor(248, 81, 73, 200) if obstacle else QColor(88, 166, 255, 200)
        p.setPen(QPen(edge_col, 1))
        p.setBrush(Qt.NoBrush)
        for edge in [centre_deg - half, centre_deg + half]:
            er = math.radians(edge)
            p.drawLine(ox, oy,
                       int(ox + beam_len * math.cos(er)),
                       int(oy + beam_len * math.sin(er)))
        p.drawArc(ox - beam_len, oy - beam_len,
                  beam_len * 2, beam_len * 2,
                  int(qt_start * 16), int(qt_span * 16))

        cr = math.radians(centre_deg)
        if obstacle and clear_r > 6:
            dx = int(ox + clear_r * math.cos(cr))
            dy = int(oy + clear_r * math.sin(cr))
            self._obs_dots[label] = (dx, dy, dist_cm)
        elif not obstacle:
            self._obs_dots.pop(label, None)

        txt_r = clear_r * 0.52
        tx = int(ox + txt_r * math.cos(cr))
        ty = int(oy + txt_r * math.sin(cr))
        p.setPen(QColor(180, 190, 200, 200))
        p.setFont(QFont("monospace", 7, QFont.Bold))
        val = f"{dist_cm}cm" if obstacle else "--"
        p.drawText(tx - 12, ty + 4, val)

        tip_r = beam_len + 18
        lx = int(ox + tip_r * math.cos(cr))
        ly = int(oy + tip_r * math.sin(cr))
        p.setPen(edge_col)
        p.setFont(QFont("monospace", 8, QFont.Bold))
        p.drawText(lx - len(label) * 3, ly + 4, label)

    def _draw_obs_dots(self, p):
        for label, (dx, dy, dist_cm) in self._obs_dots.items():
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(248, 81, 73, 50)))
            p.drawEllipse(dx - 10, dy - 10, 20, 20)
            p.setBrush(QBrush(QColor(248, 81, 73, 240)))
            p.drawEllipse(dx - 4, dy - 4, 8, 8)
            p.setPen(QColor(255, 130, 120))
            p.setFont(QFont("monospace", 7, QFont.Bold))
            p.drawText(dx + 8, dy - 2, f"{dist_cm}cm")

    def _draw_rover(self, p, cx, cy):
        top = cy - 30
        bw, bh = 22, 30
        p.setPen(QPen(QColor(88, 166, 255), 2))
        p.setBrush(QBrush(QColor(15, 55, 120, 220)))
        p.drawRoundedRect(cx - bw // 2, top, bw, bh, 4, 4)
        tri = QPolygonF([
            QPointF(cx, top + 5),
            QPointF(cx - 7, top + 18),
            QPointF(cx + 7, top + 18),
        ])
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(88, 166, 255, 220)))
        p.drawPolygon(tri)
        ww, wh = 6, 10
        p.setPen(QPen(QColor(88, 166, 255), 1))
        p.setBrush(QBrush(QColor(30, 80, 180, 200)))
        for wx, wy in [
            (cx - bw // 2 - ww + 1, top + 2),
            (cx + bw // 2 - 1,      top + 2),
            (cx - bw // 2 - ww + 1, top + bh - wh - 2),
            (cx + bw // 2 - 1,      top + bh - wh - 2),
        ]:
            p.drawRoundedRect(wx, wy, ww, wh, 2, 2)
        p.setPen(QPen(QColor(227, 179, 65, 150), 1, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        pad = 20
        p.drawEllipse(cx - pad, cy - pad, pad * 2, pad * 2)


# ============================================================
# MAP WIDGET
# ============================================================

class MapWidget(QWidget):
    """
    Dead-reckoning LIDAR-style map.

    Position model
    ──────────────
    Every sensor packet carries a Pi timestamp (ts).  We measure
    Δt between packets, then:
        distance = ROVER_SPEED_CMS * Δt * (|vy| / 100)   [manual]
        distance = ROVER_SPEED_CMS * Δt                   [autonomous, always moving]
    Heading integrates from vx (steering ratio).

    Render style
    ────────────
    Dark background, concentric scan rings, obstacle points plotted
    as cyan dots that fade with age — looks like a LIDAR scan.
    Rover sits at centre; world scrolls around it.
    Sweep line rotates continuously for the radar feel.
    """

    SCALE          = 3.0     # pixels per cm
    MAX_OBS        = 2000    # obstacle history
    MAX_PATH       = 4000    # path history
    ROVER_SPEED    = 28.0    # cm/s at full throttle (calibrate to your rover)
    FADE_SECS      = 12.0    # obstacle dots fade over this many seconds
    SWEEP_RPM      = 20.0    # visual sweep line rotations per minute

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Dead-reckoning state
        self._rx   = 0.0      # world X (cm)
        self._ry   = 0.0      # world Y (cm)
        self._head = 0.0      # heading degrees, 0=up CW

        # Drive command (set by GUI every 100 ms)
        self._vx   = 0.0
        self._vy   = 0.0
        self._auto = False

        # Timestamping
        self._prev_ts   = None   # Pi timestamp of previous packet
        self._local_t0  = None   # local time when first packet arrived

        # History
        self._path:      list = [(0.0, 0.0)]   # [(x,y), ...]
        self._obstacles: list = []              # [(x, y, age_secs), ...]

        # Sweep angle (visual only)
        self._sweep_angle = 0.0

        # Repaint timer for sweep animation
        self._anim_timer = QTimer()
        self._anim_timer.setInterval(33)   # ~30 fps
        self._anim_timer.timeout.connect(self._tick_sweep)
        self._anim_timer.start()

    # ──────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────

    def reset(self):
        self._rx = self._ry = self._head = 0.0
        self._prev_ts = self._local_t0 = None
        self._path      = [(0.0, 0.0)]
        self._obstacles = []
        self._vx = self._vy = 0.0
        self.update()

    def set_drive(self, vx, vy):
        self._vx, self._vy = float(vx), float(vy)

    def set_auto(self, auto: bool):
        self._auto = auto

    # ──────────────────────────────────────────────────────────
    # SENSOR UPDATE  (called from main thread via Signal)
    # ──────────────────────────────────────────────────────────

    def update_sensors(self, front_cm, right_cm, left_cm, ts=None):
        import time as _time
        now = _time.monotonic()

        # ── Δt ────────────────────────────────────────────────
        if self._prev_ts is None or ts is None:
            dt = 0.08          # assume 80 ms for first packet
        else:
            dt = max(0.01, min(ts - self._prev_ts, 0.5))
        self._prev_ts = ts

        # ── Dead reckoning ────────────────────────────────────
        if self._auto:
            # Autonomous: rover always moving forward unless front blocked
            if 0 <= front_cm < 15:
                speed = -self.ROVER_SPEED * 0.6   # reversing
            else:
                speed = self.ROVER_SPEED

            # Infer turning from side sensors
            if 0 <= right_cm < 25 and (left_cm < 0 or left_cm > right_cm + 15):
                self._head = (self._head - 5.0) % 360   # steer left
            elif 0 <= left_cm < 25 and (right_cm < 0 or right_cm > left_cm + 15):
                self._head = (self._head + 5.0) % 360   # steer right

            dist = speed * dt

        else:
            # Manual: scale by vy magnitude and Δt
            if abs(self._vy) < 5:
                dist = 0.0
            else:
                sign = 1 if self._vy > 0 else -1
                dist = sign * self.ROVER_SPEED * (abs(self._vy) / 100.0) * dt

            # Heading from vx
            if abs(self._vy) > 5 and abs(self._vx) > 5:
                turn = (self._vx / 100.0) * 8.0
                self._head = (self._head + turn) % 360

        # Advance position
        if abs(dist) > 0.1:
            hr = math.radians(self._head - 90)
            self._rx += dist * math.cos(hr)
            self._ry += dist * math.sin(hr)
            self._path.append((self._rx, self._ry))
            if len(self._path) > self.MAX_PATH:
                self._path.pop(0)

        # ── Plot obstacles ────────────────────────────────────
        def plot(d, offset_deg):
            if 0 <= d < 300:
                ar = math.radians(self._head - 90 + offset_deg)
                ox = self._rx + d * math.cos(ar)
                oy = self._ry + d * math.sin(ar)
                self._obstacles.append([ox, oy, 0.0])   # [x, y, age]
                if len(self._obstacles) > self.MAX_OBS:
                    self._obstacles.pop(0)

        plot(front_cm,  0)
        plot(left_cm,  -90)
        plot(right_cm,  90)

        self.update()

    # ──────────────────────────────────────────────────────────
    # SWEEP ANIMATION
    # ──────────────────────────────────────────────────────────

    def _tick_sweep(self):
        dt_s = 33 / 1000.0
        self._sweep_angle = (self._sweep_angle + self.SWEEP_RPM * 6 * dt_s) % 360
        # Age obstacle dots
        for obs in self._obstacles:
            obs[2] += dt_s
        # Remove fully faded dots
        self._obstacles = [o for o in self._obstacles if o[2] < self.FADE_SECS]
        self.update()

    # ──────────────────────────────────────────────────────────
    # COORDINATE TRANSFORM  (world cm → screen px, rover centred)
    # ──────────────────────────────────────────────────────────

    def _w2s(self, x_cm, y_cm):
        scx = self.width()  // 2
        scy = self.height() // 2
        sx  = int(scx + (x_cm - self._rx) * self.SCALE)
        sy  = int(scy - (y_cm - self._ry) * self.SCALE)
        return sx, sy

    # ──────────────────────────────────────────────────────────
    # PAINT
    # ──────────────────────────────────────────────────────────

    def paintEvent(self, _):
        w, h = self.width(), self.height()
        cx   = w // 2
        cy   = h // 2
        R    = int(min(w, h) * 0.46)   # radius of outer scan ring

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # ── Background ─────────────────────────────────────────
        p.fillRect(0, 0, w, h, QColor("#050d14"))

        # ── Scan rings ─────────────────────────────────────────
        ring_cm = [50, 100, 150, 200]
        for i, dist_cm in enumerate(ring_cm):
            rr = int(dist_cm * self.SCALE)
            alpha = 60 - i * 12
            p.setPen(QPen(QColor(0, 180, 120, alpha), 1))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(cx - rr, cy - rr, rr * 2, rr * 2)
            # Label
            p.setPen(QColor(0, 120, 80, 140))
            p.setFont(QFont("monospace", 7))
            p.drawText(cx + rr + 3, cy + 10, f"{dist_cm}cm")

        # ── Cross-hair grid lines ──────────────────────────────
        p.setPen(QPen(QColor(0, 80, 50, 60), 1))
        p.drawLine(cx, 0, cx, h)
        p.drawLine(0, cy, w, cy)

        # ── Sweep line (visual only, doesn't represent real data) ──
        sa_rad = math.radians(self._sweep_angle - 90)
        p.save()
        # Gradient fade from centre outward
        for step in range(0, R, 4):
            alpha = max(0, 80 - int(step * 80 / R))
            p.setPen(QPen(QColor(0, 255, 150, alpha), 2))
            ex = int(cx + step * math.cos(sa_rad))
            ey = int(cy + step * math.sin(sa_rad))
            nx = int(cx + (step + 4) * math.cos(sa_rad))
            ny = int(cy + (step + 4) * math.sin(sa_rad))
            p.drawLine(ex, ey, nx, ny)
        p.restore()

        # ── Path trace ─────────────────────────────────────────
        if len(self._path) > 1:
            total = len(self._path)
            for i in range(1, total):
                # Fade older segments
                t     = i / total
                alpha = int(40 + 160 * t)
                green = int(120 + 100 * t)
                p.setPen(QPen(QColor(0, green, 80, alpha), 1))
                ax, ay = self._w2s(*self._path[i - 1])
                bx, by = self._w2s(*self._path[i])
                p.drawLine(ax, ay, bx, by)

        # ── Obstacle dots — LIDAR-style, fade with age ─────────
        for ox, oy, age in self._obstacles:
            sx, sy = self._w2s(ox, oy)
            if not (0 <= sx < w and 0 <= sy < h):
                continue
            t     = age / self.FADE_SECS          # 0.0=fresh → 1.0=gone
            alpha = int(255 * (1.0 - t ** 0.5))   # sqrt fade
            size  = 3 if t < 0.3 else 2

            # Outer glow
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(0, 255, 200, max(0, alpha // 4))))
            p.drawEllipse(sx - size - 2, sy - size - 2, (size + 2) * 2, (size + 2) * 2)
            # Inner dot
            p.setBrush(QBrush(QColor(80, 255, 220, max(0, alpha))))
            p.drawEllipse(sx - size, sy - size, size * 2, size * 2)

        # ── START marker ───────────────────────────────────────
        sx0, sy0 = self._w2s(0, 0)
        if 0 <= sx0 < w and 0 <= sy0 < h:
            p.setPen(QPen(QColor(255, 200, 0), 2))
            p.setBrush(QBrush(QColor(255, 200, 0, 160)))
            p.drawEllipse(sx0 - 6, sy0 - 6, 12, 12)
            p.setPen(QColor(0, 0, 0))
            p.setFont(QFont("monospace", 7, QFont.Bold))
            p.drawText(sx0 - 4, sy0 + 4, "S")

        # ── Rover — always at screen centre ────────────────────
        p.save()
        p.translate(cx, cy)
        p.rotate(self._head)   # heading: 0=up, CW

        # Body
        p.setPen(QPen(QColor(0, 220, 160), 2))
        p.setBrush(QBrush(QColor(0, 60, 50, 220)))
        p.drawRoundedRect(-8, -12, 16, 24, 3, 3)

        # Forward triangle
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 255, 180, 230)))
        tri = QPolygonF([QPointF(0, -12), QPointF(-6, -3), QPointF(6, -3)])
        p.drawPolygon(tri)

        # Wheels
        p.setPen(QPen(QColor(0, 180, 130), 1))
        p.setBrush(QBrush(QColor(0, 80, 60, 220)))
        for wx, wy in [(-12, -10), (8, -10), (-12, 4), (8, 4)]:
            p.drawRoundedRect(wx, wy, 4, 8, 1, 1)

        # Centre dot
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 255, 180)))
        p.drawEllipse(-2, -2, 4, 4)

        p.restore()

        # ── HUD overlay ────────────────────────────────────────
        p.setPen(QColor(0, 180, 120, 180))
        p.setFont(QFont("monospace", 8, QFont.Bold))
        p.drawText(8, 16, f"POS  {self._rx:+7.1f}, {self._ry:+7.1f} cm")
        p.drawText(8, 30, f"HDG  {self._head:6.1f}°")
        p.drawText(8, 44, f"PATH {len(self._path):4d} pts")
        p.drawText(8, 58, f"OBS  {len(self._obstacles):4d}")

        # Mode badge
        mode_txt = "AUTO" if self._auto else "MANUAL"
        mode_col = QColor(0, 255, 120) if self._auto else QColor(88, 166, 255)
        p.setPen(mode_col)
        p.setFont(QFont("monospace", 8, QFont.Bold))
        p.drawText(w - 70, 16, mode_txt)

        p.end()



class DirButton(QPushButton):
    def __init__(self, label, parent=None):
        super().__init__(label, parent)
        self.setMinimumSize(72, 72)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)
        self._set(False)

    def _set(self, active):
        if active:
            self.setStyleSheet(
                "QPushButton {"
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                "stop:0 " + ACCENT2 + ",stop:1 " + ACCENT + ");"
                "color: #0d1117;"
                "font-size: 22px;"
                "font-weight: 900;"
                "border: none;"
                "border-radius: 12px;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QPushButton {"
                "background: " + SURFACE3 + ";"
                "color: " + TEXT2 + ";"
                "font-size: 22px;"
                "border: 1px solid " + BORDER + ";"
                "border-radius: 12px;"
                "}"
                "QPushButton:hover { border-color: " + ACCENT + "; color: " + ACCENT + "; }"
            )

    def set_active(self, active):
        self._set(active)


# ============================================================
# MODE BUTTON (toggle pair)
# ============================================================

class ModeBtn(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(32)
        self.setCursor(Qt.PointingHandCursor)
        self.set_active(False)

    def set_active(self, active):
        if active:
            self.setStyleSheet(
                "QPushButton {"
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 " + ACCENT2 + ",stop:1 " + ACCENT + ");"
                "color: #0d1117;"
                "font-weight: 800;"
                "border: none;"
                "border-radius: 7px;"
                "padding: 0 16px;"
                "font-size: 11px;"
                "letter-spacing: 1px;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QPushButton {"
                "background: transparent;"
                "color: " + TEXT2 + ";"
                "border: 1px solid " + BORDER + ";"
                "border-radius: 7px;"
                "padding: 0 16px;"
                "font-size: 11px;"
                "font-weight: 600;"
                "}"
                "QPushButton:hover { border-color: " + ACCENT + "; color: " + ACCENT + "; }"
            )


# ============================================================
# OBSTACLE TOGGLE BUTTON
# ============================================================

class ObsBtn(QPushButton):
    def __init__(self, parent=None):
        super().__init__("AVOIDANCE OFF", parent)
        self.setFixedHeight(32)
        self.setCursor(Qt.PointingHandCursor)
        self._on = False
        self._refresh()
        self.clicked.connect(self._toggle)

    def _toggle(self):
        self._on = not self._on
        self._refresh()

    def _refresh(self):
        self.setText("AVOIDANCE ON" if self._on else "AVOIDANCE OFF")
        if self._on:
            self.setStyleSheet(
                "QPushButton {"
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 " + GREEN2 + ",stop:1 " + GREEN + ");"
                "color: #0d1117;"
                "font-weight: 800;"
                "border: none;"
                "border-radius: 7px;"
                "padding: 0 14px;"
                "font-size: 11px;"
                "letter-spacing: 1px;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QPushButton {"
                "background: transparent;"
                "color: " + TEXT2 + ";"
                "border: 1px solid " + BORDER + ";"
                "border-radius: 7px;"
                "padding: 0 14px;"
                "font-size: 11px;"
                "font-weight: 600;"
                "}"
                "QPushButton:hover { border-color: " + GREEN + "; color: " + GREEN + "; }"
            )

    def set_state(self, on):
        self._on = on
        self._refresh()

    @property
    def is_on(self):
        return self._on


# ============================================================
# STATUS DOT
# ============================================================

class StatusDot(QLabel):
    def __init__(self, parent=None):
        super().__init__("●", parent)
        self.setStyleSheet("color: " + TEXT2 + "; font-size: 10px;")

    def set_online(self, online):
        self.setStyleSheet(
            "color: " + (GREEN if online else TEXT2) + "; font-size: 10px;"
        )


# ============================================================
# MAIN WINDOW
# ============================================================

class RoverGUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("4WD Rover — Base Station")
        self.setStyleSheet(GLOBAL_QSS)
        self.setMinimumSize(1100, 700)

        self.socket     = None
        self._held      = set()
        self._auto_mode = False

        self._build_ui()

        # Fit to screen
        screen = QApplication.primaryScreen()
        if screen:
            ag = screen.availableGeometry()
            mw, mh = int(ag.width() * 0.03), int(ag.height() * 0.03)
            self.setGeometry(ag.x() + mw, ag.y() + mh,
                             ag.width() - mw * 2, ag.height() - mh * 2)

        self._drive_timer = QTimer(self)
        self._drive_timer.setInterval(100)
        self._drive_timer.timeout.connect(self._send_current)
        self._drive_timer.start()

        signals.log.connect(self._log)
        signals.status.connect(self._set_status)
        signals.pi_status.connect(self._set_pi_status)
        signals.sensors.connect(self._on_sensors)

        self.setFocusPolicy(Qt.StrongFocus)

    # --------------------------------------------------------
    # BUILD UI
    # --------------------------------------------------------

    def _build_ui(self):
        root_w = QWidget()
        self.setCentralWidget(root_w)
        root = QVBoxLayout(root_w)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_titlebar())
        root.addWidget(self._build_toolbar())

        # ── Tabs ──
        self._tabs = QTabWidget()
        self._tabs.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._tabs, 1)

        self._tabs.addTab(self._build_control_tab(), "⬛  CONTROL")
        self._tabs.addTab(self._build_sensors_tab(), "📡  SENSORS")
        self._tabs.addTab(self._build_map_tab(),     "🗺  MAP")
        self._tabs.addTab(self._build_log_tab(),     "📋  CONSOLE")

    # ── TITLE BAR ──────────────────────────────────────────

    def _build_titlebar(self):
        bar = QFrame()
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            "QFrame { "
            "background: " + SURFACE + "; "
            "border-bottom: 1px solid " + BORDER + "; "
            "}"
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(24, 0, 24, 0)
        h.setSpacing(12)

        # Icon
        ico = QLabel("🚗")
        ico.setFixedSize(36, 36)
        ico.setAlignment(Qt.AlignCenter)
        ico.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 " + ACCENT2 + ",stop:1 " + ACCENT + ");"
            "border-radius: 9px; font-size: 17px;"
        )
        h.addWidget(ico)

        # Title
        vl = QVBoxLayout()
        vl.setSpacing(1)
        t1 = QLabel("4WD ROVER CONTROL")
        t1.setStyleSheet(
            "color: " + TEXT + ";"
            "font-weight: 800; font-size: 14px; letter-spacing: 3px;"
        )
        t2 = QLabel("Raspberry Pi  ·  Arduino Uno  ·  Live Telemetry")
        t2.setStyleSheet(
            "color: " + TEXT2 + ";"
            "font-size: 10px; letter-spacing: 1px;"
        )
        vl.addWidget(t1)
        vl.addWidget(t2)
        h.addLayout(vl)
        h.addStretch()

        # Status pill
        pill = QFrame()
        pill.setStyleSheet(
            "QFrame { "
            "background: " + SURFACE3 + "; "
            "border: 1px solid " + BORDER + "; "
            "border-radius: 14px; "
            "}"
        )
        pl = QHBoxLayout(pill)
        pl.setContentsMargins(12, 5, 16, 5)
        pl.setSpacing(6)
        self._hdr_dot = StatusDot()
        self._hdr_lbl = QLabel("Disconnected")
        self._hdr_lbl.setStyleSheet("color: " + TEXT2 + "; font-size: 11px;")
        pl.addWidget(self._hdr_dot)
        pl.addWidget(self._hdr_lbl)
        h.addWidget(pill)
        return bar

    # ── TOOLBAR ────────────────────────────────────────────

    def _build_toolbar(self):
        tb = QFrame()
        tb.setFixedHeight(48)
        tb.setStyleSheet(
            "QFrame { "
            "background: " + SURFACE + "; "
            "border-bottom: 1px solid " + BORDER + "; "
            "}"
        )
        h = QHBoxLayout(tb)
        h.setContentsMargins(24, 0, 24, 0)
        h.setSpacing(10)

        lbl = QLabel("ROVER")
        lbl.setStyleSheet(
            "color: " + TEXT2 + "; font-size: 9px; font-weight: 700; letter-spacing: 2px;"
        )
        h.addWidget(lbl)

        self._addr_lbl = QLabel(f"{ROVER_HOST}:{ROVER_PORT}")
        self._addr_lbl.setStyleSheet(
            "color: " + ACCENT + ";"
            "background: " + SURFACE3 + ";"
            "border: 1px solid " + BORDER + ";"
            "border-radius: 6px;"
            "font-family: monospace; font-size: 12px; font-weight: 700;"
            "padding: 3px 10px;"
        )
        h.addWidget(self._addr_lbl)
        h.addStretch()

        self._connect_btn = btn_primary("⚡  CONNECT")
        self._connect_btn.clicked.connect(self._connect)
        h.addWidget(self._connect_btn)
        return tb

    # ── CONTROL TAB ────────────────────────────────────────

    def _build_control_tab(self):
        tab = QWidget()
        tab.setStyleSheet("background: " + BG + ";")
        grid = QGridLayout(tab)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(16)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)

        # ── Drive card (left, tall) ──
        drive_f, drive_l = card("Drive Control")
        grid.addWidget(drive_f, 0, 0, 2, 1)

        # Mode row
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_row.addWidget(section_label("Mode"))

        self.btn_manual = ModeBtn("MANUAL")
        self.btn_manual.clicked.connect(self._set_manual)
        self.btn_manual.set_active(True)
        mode_row.addWidget(self.btn_manual)

        self.btn_auto = ModeBtn("AUTONOMOUS")
        self.btn_auto.clicked.connect(self._set_autonomous)
        mode_row.addWidget(self.btn_auto)

        mode_row.addSpacing(20)
        mode_row.addWidget(section_label("Avoidance"))

        self.btn_obstacle = ObsBtn()
        self.btn_obstacle.clicked.connect(self._toggle_obstacle)
        mode_row.addWidget(self.btn_obstacle)
        mode_row.addStretch()

        drive_l.addLayout(mode_row)
        drive_l.addWidget(divider())

        # D-pad
        self.dpad_widget = QWidget()
        self.dpad_widget.setStyleSheet("background: transparent;")
        pad_vl = QVBoxLayout(self.dpad_widget)
        pad_vl.setContentsMargins(0, 10, 0, 10)

        hint = QLabel("Arrow keys  ↑ ↓ ← →  or click & hold buttons")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: " + TEXT2 + "; font-size: 10px; letter-spacing: 1px;")
        pad_vl.addWidget(hint)
        pad_vl.addSpacing(8)

        self.btn_fwd   = DirButton("↑")
        self.btn_back  = DirButton("↓")
        self.btn_left  = DirButton("←")
        self.btn_right = DirButton("→")

        for b, d in [(self.btn_fwd,"up"),(self.btn_back,"down"),
                     (self.btn_left,"left"),(self.btn_right,"right")]:
            b.pressed.connect(lambda _d=d, _b=b: self._btn_press(_d, _b))
            b.released.connect(lambda _d=d, _b=b: self._btn_release(_d, _b))

        g = QGridLayout()
        g.setSpacing(10)

        centre = QLabel()
        centre.setFixedSize(72, 72)
        centre.setAlignment(Qt.AlignCenter)
        centre.setStyleSheet(
            "background: " + SURFACE3 + ";"
            "border: 1px solid " + BORDER + ";"
            "border-radius: 12px;"
        )
        g.addWidget(self.btn_fwd,  0, 1)
        g.addWidget(self.btn_left, 1, 0)
        g.addWidget(centre,        1, 1)
        g.addWidget(self.btn_right,1, 2)
        g.addWidget(self.btn_back, 2, 1)

        pw = QWidget()
        pw.setStyleSheet("background: transparent;")
        pw.setLayout(g)
        pw.setMaximumWidth(300)

        cr = QHBoxLayout()
        cr.addStretch()
        cr.addWidget(pw)
        cr.addStretch()
        pad_vl.addLayout(cr)

        drive_l.addWidget(self.dpad_widget, 1)

        # Auto label
        self.auto_label = QLabel("🤖  Rover is operating autonomously")
        self.auto_label.setAlignment(Qt.AlignCenter)
        self.auto_label.setStyleSheet(
            "color: " + GREEN + "; font-size: 13px; font-weight: 700; letter-spacing: 1px;"
        )
        self.auto_label.setVisible(False)
        drive_l.addWidget(self.auto_label)
        drive_l.addStretch()

        # E-stop
        self.stop_button = btn_danger("⛔   EMERGENCY STOP   (Space)", 48)
        self.stop_button.clicked.connect(self._emergency_stop)
        drive_l.addWidget(self.stop_button)

        # ── Link status card (top-right) ──
        link_f, link_l = card("Link Status")
        grid.addWidget(link_f, 0, 1)

        def link_row(label_text, dot=True):
            rw = QHBoxLayout()
            lb = QLabel(label_text)
            lb.setStyleSheet("color: " + TEXT2 + "; font-size: 11px;")
            rw.addWidget(lb)
            rw.addStretch()
            if dot:
                d  = StatusDot()
                vl = QLabel("Offline")
                vl.setStyleSheet("color: " + TEXT2 + "; font-size: 11px; font-weight: 700;")
                rw.addWidget(d)
                rw.addWidget(vl)
                return rw, d, vl
            else:
                vl = QLabel()
                vl.setStyleSheet("color: " + TEXT + "; font-size: 11px; font-weight: 700; font-family: monospace;")
                rw.addWidget(vl)
                return rw, vl

        r1, self._pi_dot,      self._pi_lbl      = link_row("Raspberry Pi")
        r2, self._arduino_dot, self._arduino_lbl = link_row("Arduino")
        r3, self._target_lbl                     = link_row("Target", dot=False)
        self._target_lbl.setText(f"{ROVER_HOST}:{ROVER_PORT}")

        link_l.addLayout(r1)
        link_l.addLayout(r2)
        link_l.addWidget(divider())
        link_l.addLayout(r3)
        link_l.addStretch()

        note = QLabel(
            "Pi connects via mDNS hostname — works even if the Pi's IP changes."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: " + TEXT2 + "; font-size: 10px;")
        link_l.addWidget(note)

        # ── Quick sensor readout card (bottom-right) ──
        sens_f, sens_l = card("Sensor Snapshot")
        grid.addWidget(sens_f, 1, 1)

        def sensor_row(icon, name):
            rw  = QHBoxLayout()
            ico = QLabel(icon)
            ico.setStyleSheet("font-size: 16px;")
            nm  = QLabel(name)
            nm.setStyleSheet("color: " + TEXT2 + "; font-size: 11px;")
            val = QLabel("--")
            val.setStyleSheet(
                "color: " + ACCENT + ";"
                "font-family: monospace; font-size: 13px; font-weight: 700;"
            )
            rw.addWidget(ico)
            rw.addWidget(nm)
            rw.addStretch()
            rw.addWidget(val)
            return rw, val

        rf, self._sf = sensor_row("⬆", "Front")
        rr, self._sr = sensor_row("➡", "Right")
        rl, self._sl = sensor_row("⬅", "Left")
        sens_l.addLayout(rf)
        sens_l.addLayout(rr)
        sens_l.addLayout(rl)
        sens_l.addStretch()

        return tab

    # ── SENSORS TAB ────────────────────────────────────────

    def _build_sensors_tab(self):
        tab = QWidget()
        tab.setStyleSheet("background: " + BG + ";")
        grid = QGridLayout(tab)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)

        # Radar card
        radar_f, radar_l = card("Proximity Radar")
        self.radar = RadarWidget()
        radar_l.addWidget(self.radar, 1)

        sr = QHBoxLayout()
        self._lbl_f = QLabel("F: --")
        self._lbl_r = QLabel("R: --")
        self._lbl_l = QLabel("L: --")
        for lbl in (self._lbl_f, self._lbl_r, self._lbl_l):
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "color: " + TEXT2 + ";"
                "font-family: monospace; font-size: 12px; font-weight: 700;"
            )
            sr.addWidget(lbl)
        radar_l.addLayout(sr)
        grid.addWidget(radar_f, 0, 0)

        # Sensor details card
        detail_f, detail_l = card("Sensor Details")
        grid.addWidget(detail_f, 0, 1)

        def big_sensor(name):
            vl = QVBoxLayout()
            nm = QLabel(name)
            nm.setStyleSheet("color: " + TEXT2 + "; font-size: 10px; letter-spacing: 2px; font-weight: 700;")
            val = QLabel("-- cm")
            val.setStyleSheet(
                "color: " + ACCENT + ";"
                "font-family: monospace; font-size: 32px; font-weight: 700;"
            )
            bar_frame = QFrame()
            bar_frame.setFixedHeight(6)
            bar_frame.setStyleSheet(
                "background: " + SURFACE3 + "; border-radius: 3px;"
            )
            bar_inner = QFrame(bar_frame)
            bar_inner.setGeometry(0, 0, 0, 6)
            bar_inner.setStyleSheet(
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 " + ACCENT2 + ",stop:1 " + ACCENT + ");"
                "border-radius: 3px;"
            )
            vl.addWidget(nm)
            vl.addWidget(val)
            vl.addWidget(bar_frame)
            return vl, val, bar_inner

        vf, self._dv_f, self._bar_f = big_sensor("FRONT")
        vr, self._dv_r, self._bar_r = big_sensor("RIGHT")
        vl2, self._dv_l, self._bar_l = big_sensor("LEFT")

        detail_l.addLayout(vf)
        detail_l.addWidget(divider())
        detail_l.addLayout(vr)
        detail_l.addWidget(divider())
        detail_l.addLayout(vl2)
        detail_l.addStretch()

        return tab

    # ── MAP TAB ────────────────────────────────────────────

    def _build_map_tab(self):
        tab = QWidget()
        tab.setStyleSheet("background: " + BG + ";")
        vl = QVBoxLayout(tab)
        vl.setContentsMargins(20, 20, 20, 20)
        vl.setSpacing(12)

        # Toolbar row
        tr = QHBoxLayout()
        tr.addWidget(section_label("Live Route Trace + Obstacle Map"))
        tr.addStretch()

        self._map_reset_btn = btn_ghost("↺  RESET MAP")
        self._map_reset_btn.clicked.connect(self._reset_map)
        tr.addWidget(self._map_reset_btn)

        legend_obs = QLabel("● Obstacle")
        legend_obs.setStyleSheet("color: " + RED + "; font-size: 10px; font-weight: 700;")
        legend_path = QLabel("— Path")
        legend_path.setStyleSheet("color: " + GREEN + "; font-size: 10px; font-weight: 700;")
        tr.addSpacing(10)
        tr.addWidget(legend_obs)
        tr.addSpacing(12)
        tr.addWidget(legend_path)

        vl.addLayout(tr)

        # Map card
        map_f, map_l = card("", accent_bar=False)
        self.map_widget = MapWidget()
        map_l.setContentsMargins(4, 4, 4, 4)
        map_l.addWidget(self.map_widget)
        vl.addWidget(map_f, 1)

        return tab

    # ── LOG TAB ─────────────────────────────────────────────

    def _build_log_tab(self):
        tab = QWidget()
        tab.setStyleSheet("background: " + BG + ";")
        vl = QVBoxLayout(tab)
        vl.setContentsMargins(20, 20, 20, 20)
        vl.setSpacing(12)

        tr = QHBoxLayout()
        tr.addWidget(section_label("System Console"))
        tr.addStretch()
        clr = btn_ghost("Clear")
        vl.addLayout(tr)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        clr.clicked.connect(self.log_box.clear)
        tr.addWidget(clr)
        vl.addWidget(self.log_box)

        return tab

    # --------------------------------------------------------
    # MODE SWITCHING
    # --------------------------------------------------------

    def _set_manual(self):
        self._auto_mode = False
        self.map_widget.set_auto(False)
        self.btn_manual.set_active(True)
        self.btn_auto.set_active(False)
        self.dpad_widget.setVisible(True)
        self.auto_label.setVisible(False)
        self.btn_obstacle.set_state(False)
        self._send({"type": "mode", "mode": "manual"})
        self._send({"type": "obstacle", "enabled": False})
        signals.log.emit("Mode → MANUAL")

    def _set_autonomous(self):
        self._auto_mode = True
        self.map_widget.set_auto(True)
        self.btn_auto.set_active(True)
        self.btn_manual.set_active(False)
        self.dpad_widget.setVisible(False)
        self.auto_label.setVisible(True)
        self.btn_obstacle.set_state(True)
        self._send({"type": "mode", "mode": "autonomous"})
        self._send({"type": "obstacle", "enabled": True})
        signals.log.emit("Mode → AUTONOMOUS  (obstacle avoidance ON)")

    def _toggle_obstacle(self):
        enabled = self.btn_obstacle.is_on
        self._send({"type": "obstacle", "enabled": enabled})
        signals.log.emit(f"Obstacle avoidance → {'ON' if enabled else 'OFF'}")

    def _reset_map(self):
        self.map_widget.reset()
        signals.log.emit("Map reset")

    # --------------------------------------------------------
    # KEYS
    # --------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent):
        if event.isAutoRepeat() or self._auto_mode:
            return
        k = event.key()
        if   k == Qt.Key_Up:    self._key_press("up",    self.btn_fwd)
        elif k == Qt.Key_Down:  self._key_press("down",  self.btn_back)
        elif k == Qt.Key_Left:  self._key_press("left",  self.btn_left)
        elif k == Qt.Key_Right: self._key_press("right", self.btn_right)
        elif k == Qt.Key_Space: self._emergency_stop()
        else: super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.isAutoRepeat() or self._auto_mode:
            return
        k = event.key()
        if   k == Qt.Key_Up:    self._key_release("up",    self.btn_fwd)
        elif k == Qt.Key_Down:  self._key_release("down",  self.btn_back)
        elif k == Qt.Key_Left:  self._key_release("left",  self.btn_left)
        elif k == Qt.Key_Right: self._key_release("right", self.btn_right)
        else: super().keyReleaseEvent(event)

    def _key_press(self, d, b):   self._held.add(d);    b.set_active(True)
    def _key_release(self, d, b): self._held.discard(d); b.set_active(False)
    def _btn_press(self, d, b):   self._held.add(d);    b.set_active(True)
    def _btn_release(self, d, b): self._held.discard(d); b.set_active(False)

    def _emergency_stop(self):
        self._held.clear()
        for b in (self.btn_fwd, self.btn_back, self.btn_left, self.btn_right):
            b.set_active(False)
        self._send({"type": "stop"})
        signals.log.emit("⛔ EMERGENCY STOP")

    # --------------------------------------------------------
    # DRIVE REPEAT
    # --------------------------------------------------------

    def _send_current(self):
        if self._auto_mode:
            return
        vx = vy = 0
        if "up"    in self._held: vy += DRIVE_SPEED
        if "down"  in self._held: vy -= DRIVE_SPEED
        if "left"  in self._held: vx -= DRIVE_SPEED
        if "right" in self._held: vx += DRIVE_SPEED
        vx = max(-100, min(100, vx))
        vy = max(-100, min(100, vy))
        self.map_widget.set_drive(vx, vy)
        if vx == 0 and vy == 0:
            self._send({"type": "stop"})
        else:
            self._send({"type": "drive", "vx": vx, "vy": vy})

    # --------------------------------------------------------
    # SENSORS
    # --------------------------------------------------------

    def _on_sensors(self, obj):
        f = obj.get("front", -1)
        r = obj.get("right", -1)
        l = obj.get("left",  -1)

        self.radar.update_sensors(f, r, l)
        self.map_widget.update_sensors(f, r, l, ts=obj.get("ts"))

        def fmt(v): return f"{v} cm" if v >= 0 else "--"

        # Control tab quick readout
        self._sf.setText(fmt(f))
        self._sr.setText(fmt(r))
        self._sl.setText(fmt(l))

        # Sensors tab
        self._lbl_f.setText(f"F: {fmt(f)}")
        self._lbl_r.setText(f"R: {fmt(r)}")
        self._lbl_l.setText(f"L: {fmt(l)}")

        danger = 15
        for lbl, val in ((self._lbl_f, f), (self._lbl_r, r), (self._lbl_l, l)):
            c = RED if (0 <= val < danger) else TEXT2
            lbl.setStyleSheet(
                "color: " + c + ";"
                "font-family: monospace; font-size: 12px; font-weight: 700;"
            )

        # Big sensor values + colour
        MAX_D = 100
        for dv, bar, val in (
            (self._dv_f, self._bar_f, f),
            (self._dv_r, self._bar_r, r),
            (self._dv_l, self._bar_l, l),
        ):
            if val < 0:
                dv.setText("-- cm")
                dv.setStyleSheet(
                    "color: " + TEXT2 + ";"
                    "font-family: monospace; font-size: 32px; font-weight: 700;"
                )
            else:
                dv.setText(f"{val} cm")
                c = RED if val < danger else (YELLOW if val < 40 else ACCENT)
                dv.setStyleSheet(
                    "color: " + c + ";"
                    "font-family: monospace; font-size: 32px; font-weight: 700;"
                )
                pct = max(0.05, min(1.0, val / MAX_D))
                bar.setGeometry(0, 0, int(bar.parent().width() * pct), 6)

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    def _log(self, msg):
        self.log_box.append(msg)

    def _set_status(self, online):
        self._hdr_dot.set_online(online)
        self._hdr_lbl.setText("Arduino Online" if online else "Arduino Offline")
        self._hdr_lbl.setStyleSheet(
            "color: " + (GREEN if online else TEXT2) + "; font-size: 11px;"
        )
        self._arduino_dot.set_online(online)
        self._arduino_lbl.setText("Online" if online else "Offline")
        self._arduino_lbl.setStyleSheet(
            "color: " + (GREEN if online else TEXT2) + "; font-size: 11px; font-weight: 700;"
        )

    def _set_pi_status(self, connected):
        self._pi_dot.set_online(connected)
        self._pi_lbl.setText("Online" if connected else "Offline")
        self._pi_lbl.setStyleSheet(
            "color: " + (GREEN if connected else TEXT2) + "; font-size: 11px; font-weight: 700;"
        )
        if not connected:
            self._set_status(False)
            self._connect_btn.setText("⚡  CONNECT")

    # --------------------------------------------------------
    # NETWORK
    # --------------------------------------------------------

    def _connect(self):
        if self.socket:
            try: self.socket.close()
            except Exception: pass
            self.socket = None

        signals.log.emit(f"Connecting to {ROVER_HOST}:{ROVER_PORT} …")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((ROVER_HOST, ROVER_PORT))
            s.settimeout(None)
            self.socket = s
            self._send({"type": "hello"})
            self._connect_btn.setText("✓  CONNECTED")
            threading.Thread(target=self._receiver, daemon=True).start()
        except socket.gaierror:
            self.socket = None
            signals.log.emit(f"Cannot resolve {ROVER_HOST} — check network / mDNS")
            self._connect_btn.setText("⚡  CONNECT")
        except Exception as e:
            self.socket = None
            signals.log.emit(f"Connection failed: {e}")
            self._connect_btn.setText("⚡  CONNECT")

    def _receiver(self):
        sock = self.socket
        buf  = ""
        try:
            while True:
                data = sock.recv(4096)
                if not data: break
                buf += data.decode(errors="ignore")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line: continue
                    try: obj = json.loads(line)
                    except Exception: continue
                    t = obj.get("type")
                    if t == "hello_ack":
                        signals.log.emit("Handshake complete ✓")
                        signals.pi_status.emit(True)
                    elif t == "rover_status":
                        signals.status.emit(bool(obj.get("online", False)))
                    elif t == "sensors":
                        signals.sensors.emit(obj)
                    elif t == "error":
                        signals.log.emit(f"Arduino error: {obj}")
        except Exception as e:
            signals.log.emit(f"Connection lost: {e}")
        finally:
            if self.socket == sock: self.socket = None
            signals.pi_status.emit(False)

    def _send(self, obj):
        s = self.socket
        if not s: return False
        try:
            s.sendall((json.dumps(obj) + "\n").encode())
            return True
        except Exception as e:
            signals.log.emit(f"Send failed: {e}")
            return False


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = RoverGUI()
    win.show()
    sys.exit(app.exec())
