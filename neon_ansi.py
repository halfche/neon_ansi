#!/usr/bin/env python3
import math, random, time, argparse, os, sys, shutil, select
from types import SimpleNamespace
from collections import deque
from itertools import groupby
import numpy as np
try:
    import sounddevice as sd
except Exception:
    sd = None
try:
    import psutil
except Exception:
    psutil = None


# ---------------- ترمینال ANSI (بدون curses و بدون وابستگی اضافه) ----------------
# از ANSI برای رنگ و رسم استفاده می‌شود؛ ورودی خام در Linux/macOS و Windows پشتیبانی می‌شود.
class _AnsiScreen:
    def __init__(self):
        self.h, self.w = shutil.get_terminal_size((80, 24))[1], shutil.get_terminal_size((80, 24))[0]
        self.buf = []
        self.nodelay_mode = True
        self._resize()

    def _resize(self):
        size = shutil.get_terminal_size((80, 24))
        self.w, self.h = size.columns, size.lines
        self.buf = [[(" ", 0) for _ in range(self.w)] for _ in range(self.h)]

    def getmaxyx(self):
        size = shutil.get_terminal_size((80, 24))
        if (size.columns, size.lines) != (self.w, self.h):
            self._resize()
        return self.h, self.w

    def nodelay(self, enabled):
        self.nodelay_mode = enabled

    def erase(self):
        h, w = self.getmaxyx()
        self.buf = [[(" ", 0) for _ in range(w)] for _ in range(h)]

    def addstr(self, y, x, s, attr=0):
        h, w = self.getmaxyx()
        if y < 0 or y >= h or x >= w:
            return
        if x < 0:
            s = s[-x:]
            x = 0
        for ch in str(s):
            if x >= w:
                break
            self.buf[y][x] = (ch, attr)
            x += 1

    def getch(self):
        try:
            if os.name == "nt":
                import msvcrt
                if not msvcrt.kbhit():
                    return -1
                ch = msvcrt.getwch()
                return ord(ch) if ch else -1
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if ready:
                data = os.read(sys.stdin.fileno(), 1)
                return data[0] if data else -1
        except (OSError, ValueError):
            return -1
        return -1

    def refresh(self):
        # چاپ کامل فریم با ANSI؛ رنگ هر سلول مطابق جفت‌رنگ تعریف‌شده است.
        out = ["\033[H"]
        last_attr = None
        for row in self.buf:
            for ch, attr in row:
                if attr != last_attr:
                    out.append(_ansi_attr(attr))
                    last_attr = attr
                out.append(ch)
            out.append("\033[0m\n")
            last_attr = None
        sys.stdout.write("".join(out))
        sys.stdout.flush()


_ansi_pairs = {}
_ANSI_BOLD = 1 << 20
_ANSI_REVERSE = 1 << 21

def _ansi_attr(attr):
    pair = attr & 0xFFFF
    fg = _ansi_pairs.get(pair, 7)
    codes = ["0", str(30 + fg) if fg < 8 else "38;5;" + str(fg)]
    if attr & _ANSI_BOLD:
        codes.append("1")
    if attr & _ANSI_REVERSE:
        codes.append("7")
    return "\033[" + ";".join(codes) + "m"

def _init_pair(pair, fg, bg=-1):
    _ansi_pairs[pair] = fg

def _color_pair(pair):
    return pair

def _terminal_wrapper(func, args):
    screen = _AnsiScreen()
    old_settings = None
    try:
        if os.name != "nt" and sys.stdin.isatty():
            import termios, tty
            old_settings = termios.tcgetattr(sys.stdin.fileno())
            tty.setraw(sys.stdin.fileno())
        sys.stdout.write("\033[2J\033[?25l")
        sys.stdout.flush()
        func(screen, args)
    finally:
        if old_settings is not None:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
        sys.stdout.write("\033[0m\033[?25h\033[2J\033[H")
        sys.stdout.flush()

curses = SimpleNamespace(
    COLORS=256, A_BOLD=_ANSI_BOLD, A_REVERSE=_ANSI_REVERSE, error=Exception,
    init_pair=_init_pair, color_pair=_color_pair,
    curs_set=lambda value: None, start_color=lambda: None,
    use_default_colors=lambda: None, wrapper=_terminal_wrapper
)

TAU = 2 * math.pi
MODES = ["mix", "mic", "sim", "cpu", "net"]

# ---------------- رنگ ----------------
THEMES = {
    "cyber":  ([17, 19, 25, 31, 37, 44, 51, 159], 201),
    "matrix": ([22, 28, 34, 40, 46, 82, 118, 157], 231),
    "synth":  ([53, 90, 127, 164, 201, 207, 213, 219], 51),
    "fire":   ([52, 88, 124, 160, 196, 202, 214, 226], 231),
}
FALLBACK = {
    "cyber":  ([4, 4, 4, 6, 6, 6, 7, 7], 5),
    "matrix": ([2, 2, 2, 2, 2, 2, 7, 7], 6),
    "synth":  ([4, 4, 5, 5, 5, 6, 6, 7], 3),
    "fire":   ([1, 1, 1, 1, 3, 3, 3, 7], 5),
}

def apply_theme(name):
    cols, acc = THEMES[name] if curses.COLORS >= 256 else FALLBACK[name]
    for i, c in enumerate(cols):
        curses.init_pair(i + 1, c, -1)
    curses.init_pair(9, acc, -1)
    curses.init_pair(10, cols[-1], -1)

def G(f):
    i = min(7, max(0, int(f * 8)))
    a = curses.color_pair(i + 1)
    return (a | curses.A_BOLD) if i >= 6 else a

def ACC():
    return curses.color_pair(9) | curses.A_BOLD

def put(scr, y, x, s, attr=0):
    h, w = scr.getmaxyx()
    if y < 0 or y >= h or x >= w or not s:
        return
    if x < 0:
        s = s[-x:]
        x = 0
        if not s:
            return
    s = s[:w - x]
    try:
        scr.addstr(y, x, s, attr)
    except curses.error:
        pass

# ---------------- سیستم (CPU / RAM / شبکه) ----------------
class Sys:
    """Live hardware/OS telemetry. Unsupported sensors remain unavailable."""
    def __init__(self):
        self.ok = psutil is not None
        self.cpu = 0.0
        self.cores = []
        self.ram = 0.0
        self.net = 0.0
        self.net_rx = self.net_tx = 0
        self.netpeak = 1e5
        self.disk = 0.0
        self.disk_rate = 0.0
        self.load = 0.0
        self.battery = None
        self.charging = None
        self.temp = None
        self.freq = 0.0
        self.uptime = None
        self.procs = 0
        self.ifaces = []
        self.cpuhist = deque([0.0] * 60, maxlen=60)
        self.nethist = deque([0.0] * 60, maxlen=60)
        self.diskhist = deque([0.0] * 60, maxlen=60)
        self.temphist = deque([0.0] * 60, maxlen=60)
        self.last_net = None
        self.last_disk = None
        self.last = 0.0
        self.last_temp_scan = 0.0
        if self.ok:
            try:
                psutil.cpu_percent(percpu=True)
            except Exception:
                self.ok = False

    def _temperature(self):
        if psutil is None or not hasattr(psutil, "sensors_temperatures"):
            return None
        try:
            vals = []
            for entries in (psutil.sensors_temperatures(fahrenheit=False) or {}).values():
                vals.extend(float(x.current) for x in entries
                            if getattr(x, "current", None) is not None)
            return sum(vals) / len(vals) if vals else None
        except Exception:
            return None

    def update(self):
        if not self.ok:
            return
        now = time.time()
        if now - self.last < 0.2:
            return
        self.last = now
        try:
            self.cores = [x / 100 for x in psutil.cpu_percent(percpu=True)]
            self.cpu = sum(self.cores) / max(1, len(self.cores))
            self.ram = psutil.virtual_memory().percent / 100

            io = psutil.net_io_counters()
            total = io.bytes_sent + io.bytes_recv
            rate = 0.0
            if self.last_net:
                rate = (total - self.last_net[0]) / max(0.001, now - self.last_net[1])
            self.last_net = (total, now)
            self.net_rx, self.net_tx = io.bytes_recv, io.bytes_sent
            self.netpeak = max(self.netpeak * 0.98, rate, 1e5)
            self.net = math.sqrt(min(1.0, rate / self.netpeak))

            try:
                self.disk = psutil.disk_usage(os.path.abspath(os.sep)).percent / 100
            except Exception:
                self.disk = 0.0

            try:
                dio = psutil.disk_io_counters()
                if dio:
                    total_d = dio.read_bytes + dio.write_bytes
                    self.disk_rate = (
                        (total_d - self.last_disk[0]) /
                        max(0.001, now - self.last_disk[1])
                        if self.last_disk else 0.0
                    )
                    self.last_disk = (total_d, now)
            except Exception:
                self.disk_rate = 0.0

            try:
                self.load = psutil.getloadavg()[0]
            except Exception:
                self.load = self.cpu

            try:
                battery = psutil.sensors_battery()
                if battery:
                    self.battery = battery.percent / 100
                    self.charging = bool(battery.power_plugged)
                else:
                    self.battery = None
                    self.charging = None
            except Exception:
                self.battery = None
                self.charging = None

            if now - self.last_temp_scan > 2:
                self.temp = self._temperature()
                self.last_temp_scan = now

            try:
                freq = psutil.cpu_freq()
                self.freq = float(freq.current) if freq else 0.0
            except Exception:
                self.freq = 0.0

            try:
                self.uptime = max(0, now - psutil.boot_time())
            except Exception:
                self.uptime = None

            try:
                self.procs = len(psutil.pids())
            except Exception:
                self.procs = 0

            try:
                self.ifaces = [name for name, addrs in psutil.net_if_addrs().items()
                               if addrs][:8]
            except Exception:
                self.ifaces = []

            self.cpuhist.append(self.cpu)
            self.nethist.append(self.net)
            self.diskhist.append(self.disk)
            if self.temp is not None:
                self.temphist.append(max(0.0, min(1.0, (self.temp - 20) / 80)))
        except Exception:
            pass

    @staticmethod
    def fmt_bytes(value):
        value = float(max(0, value))
        for unit in ("B", "K", "M", "G", "T"):
            if value < 1024 or unit == "T":
                return f"{value:.1f}{unit}"
            value /= 1024

    @staticmethod
    def fmt_uptime(seconds):
        if seconds is None:
            return "--:--:--"
        days, rem = divmod(int(seconds), 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        return (f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
                if days else f"{hours:02d}:{minutes:02d}:{seconds:02d}")

# ---------------- صدا / سیگنال ----------------
class Audio:
    def __init__(self, mode, sens):
        self.mode = mode
        self.sens = sens
        self.use_mic = False
        self.stream = None
        self._buf = np.zeros(1024)
        self.bands = np.zeros(32)
        self.bass = self.mid = self.high = self.level = self.beat = 0.0
        self.peak = 0.6
        self.avg_bass = 0.1
        self.cool = 0
        self.lastsec = 0
        edges = [2]
        for i in range(32):
            edges.append(max(edges[-1] + 1, int(2 * (150 ** ((i + 1) / 32)))))
        self.edges = edges
        self.set_mode(mode)

    def set_mode(self, mode):
        self.mode = mode
        if mode in ("mic", "mix"):
            if not self.use_mic:
                self.start_mic()
        else:
            self.stop_mic()

    def start_mic(self):
        if sd is None:
            return False
        try:
            self.stream = sd.InputStream(channels=1, samplerate=44100,
                                         blocksize=1024, callback=self._cb)
            self.stream.start()
            self.use_mic = True
        except Exception:
            self.stream = None
            self.use_mic = False
        return self.use_mic

    def stop_mic(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
        self.stream = None
        self.use_mic = False

    def _cb(self, indata, frames, ti, status):
        self._buf = indata[:, 0].copy()

    def mic_bands(self):
        x = self._buf
        spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
        b = np.array([spec[self.edges[i]:self.edges[i + 1]].mean() for i in range(32)])
        b = np.log1p(b * 20)
        self.peak = max(self.peak * 0.995, float(b.max()), 0.6)
        return np.clip(b / self.peak, 0, 1)

    def sim_bands(self, t):
        beat = (t * 2.1) % 1
        kick = math.exp(-beat * 6)
        return np.array([
            (0.5 + 0.5 * math.sin(t * (1 + i * 0.25) + i)) *
            ((0.35 + 0.65 * kick) if i < 8 else (0.25 + 0.4 * random.random()))
            for i in range(32)])

    def cpu_bands(self, sy):
        cores = sy.cores or [sy.cpu]
        if len(cores) > 1:
            v = np.interp(np.linspace(0, len(cores) - 1, 32), np.arange(len(cores)), cores)
        else:
            v = np.full(32, cores[0])
        v = np.sqrt(np.clip(v, 0, 1)) * (1 - 0.3 * np.linspace(0, 1, 32))
        return np.clip(v + np.random.rand(32) * 0.08, 0, 1)

    def net_bands(self, sy):
        return np.array(list(sy.nethist)[-32:])

    def update(self, t, sy):
        m = self.mode
        if m == "mic":
            new = self.mic_bands() if self.use_mic else self.sim_bands(t)
        elif m == "sim":
            new = self.sim_bands(t)
        elif m == "cpu":
            new = self.cpu_bands(sy) if sy.ok else self.sim_bands(t)
        elif m == "net":
            new = self.net_bands(sy) if sy.ok else self.sim_bands(t)
        else:
            base = self.mic_bands() if self.use_mic else self.sim_bands(t)
            new = np.maximum(base, self.cpu_bands(sy) * 0.7) if sy.ok else base
        new = np.clip(new * self.sens, 0, 1)
        self.bands = np.maximum(new, self.bands * 0.86)
        self.bass = float(self.bands[:6].mean())
        self.mid = float(self.bands[6:18].mean())
        self.high = float(self.bands[18:].mean())
        self.level = float(self.bands.mean())
        self.avg_bass = self.avg_bass * 0.95 + self.bass * 0.05
        self.cool = max(0, self.cool - 1)
        if self.bass > self.avg_bass * 1.35 and self.bass > 0.3 and self.cool == 0:
            self.beat = 1.0
            self.cool = 6
        sec = int(time.time())
        if m in ("cpu", "net") and sec != self.lastsec:
            self.beat = max(self.beat, 0.7)
        self.lastsec = sec
        self.beat *= 0.85

# ---------------- صحنه‌ها ----------------
class Rain:
    name = "rain"
    CH = "01ABCDEF<>/\\|=+*#$%&░▒"
    def __init__(self):
        self.drops = []
    def draw(self, scr, h, w, st):
        a = st.audio
        n = int(w * (0.02 + a.level * 0.12) * st.dt * 30)
        if a.beat > 0.8:
            n += int(w * 0.15)
        for _ in range(n):
            if len(self.drops) < 450:
                self.drops.append([random.randrange(w), 0.0, random.uniform(8, 25),
                                   random.randint(6, max(8, h // 2 + 6))])
        alive = []
        for d in self.drops:
            d[1] += d[2] * st.dt * (0.6 + a.level * 2.5)
            y = int(d[1])
            if y - d[3] > h:
                continue
            alive.append(d)
            for k in range(d[3]):
                attr = G(1) if k == 0 else G((1 - k / d[3]) * 0.8)
                if k == 0 and a.beat > 0.5:
                    attr = ACC()
                put(scr, y - k, d[0], random.choice(self.CH), attr)
        self.drops = alive

class Grid:
    name = "grid"
    def draw(self, scr, h, w, st):
        a = st.audio
        cx = w // 2
        y0 = int(h * 0.55)
        r = h * 0.32 * (0.85 + a.bass * 0.35)
        cy = y0 - r * 0.4
        for yy in range(max(1, int(cy - r)), y0):
            dy = yy - cy
            if abs(dy) >= r or (yy > cy and yy % 3 == 0):
                continue
            hw = int(2 * math.sqrt(r * r - dy * dy))
            put(scr, yy, cx - hw, "▓" * (2 * hw), ACC() if yy < cy else G(0.75))
        hot = a.beat > 0.5
        put(scr, y0, 0, "─" * w, G(1))
        for k in range(-12, 13):
            for yy in range(y0 + 1, h - 1):
                f = (yy - y0) / max(1, h - y0)
                x = int(cx + k * f * w * 0.09)
                ch = "|" if k == 0 else ("/" if k < 0 else "\\")
                put(scr, yy, x, ch, ACC() if hot else G(0.2 + f * 0.7))
        for i in range(10):
            z = ((i / 10) + st.t * (0.15 + a.level * 0.5)) % 1
            y = y0 + 1 + int((h - y0 - 2) * z * z)
            put(scr, y, 0, "─" * w, ACC() if hot else G(0.15 + z * 0.8))

class Spectrum:
    name = "spectrum"
    def __init__(self):
        self.peaks = np.zeros(32)
    def draw(self, scr, h, w, st):
        a = st.audio
        bw = max(2, w // 32)
        mid = h // 2
        maxh = max(1, mid - 3)
        self.peaks = np.maximum(a.bands, self.peaks - 0.015)
        for i in range(32):
            bh = int(a.bands[i] * maxh)
            x = i * bw
            for r in range(bh):
                put(scr, mid - r, x, "█" * (bw - 1), G(r / maxh))
                if r < bh * 0.6:
                    put(scr, mid + 1 + r, x, "▒" * (bw - 1), G(0.15))
            pk = int(self.peaks[i] * maxh)
            put(scr, mid - pk - 1, x, "▀" * (bw - 1), ACC())
        put(scr, mid, 0, "━" * w, G(1))

class Wave:
    name = "wave"
    def draw(self, scr, h, w, st):
        a = st.audio
        mid = h / 2
        t = st.t
        layers = [
            (a.bass, 0.05, 2.0, 0.28, G(0.6), "█"),
            (a.mid, 0.15, -3.0, 0.18, G(1), "▓"),
            (a.high, 0.40, 6.0, 0.10, ACC(), "░"),
        ]
        for x in range(w):
            for amp, fr, sp, sc, attr, ch in layers:
                y = mid + math.sin(x * fr + t * sp) * (0.1 + amp) * h * sc * 1.6
                put(scr, int(y), x, ch, attr)
            put(scr, int(mid), x, "·", G(0.2))

class Tunnel:
    name = "tunnel"
    def __init__(self):
        self.stars = [[random.uniform(-1, 1), random.uniform(-1, 1), random.random()]
                      for _ in range(220)]
    def draw(self, scr, h, w, st):
        a = st.audio
        cx, cy = w / 2, h / 2
        for i in range(9):
            z = ((i / 9) + st.t * 0.25 * (0.5 + a.level * 2)) % 1
            r = z * z
            k_ = 1 + a.bass * 0.4
            rx, ry = r * w * 0.55 * k_, r * h * 0.55 * k_
            n = int(40 + r * 160)
            ch = "█" if r > 0.5 else ("▒" if r > 0.2 else "░")
            attr = ACC() if (a.beat > 0.5 and i % 3 == 0) else G(r)
            for k in range(n):
                ang = k / n * TAU + st.t * 0.4 * (1 if i % 2 else -1)
                wob = 1 + a.mid * 0.25 * math.sin(ang * 3 + st.t * 3)
                put(scr, int(cy + math.sin(ang) * ry * wob),
                    int(cx + math.cos(ang) * rx * wob), ch, attr)
        sp = 0.25 + a.level * 1.6 + a.beat * 0.8
        for s in self.stars:
            s[2] -= sp * st.dt
            if s[2] <= 0.03:
                s[0], s[1], s[2] = random.uniform(-1, 1), random.uniform(-1, 1), 1.0
            sx = int(cx + s[0] / s[2] * w * 0.1)
            sy = int(cy + s[1] / s[2] * h * 0.2)
            c = min(5, int((1 - s[2]) * 6))
            put(scr, sy, sx, "·.:+*#"[c], G(1 - s[2]))

class Plasma:
    name = "plasma"
    SH = "  ░▒▒▓▓█"
    def draw(self, scr, h, w, st):
        a = st.audio
        t = st.t * (0.6 + a.level)
        ys = np.arange(h)[:, None].astype(float)
        xs = np.arange(w)[None, :] / 2.0
        v = (np.sin(xs * 0.35 * (1 + a.bass * 2) + t) +
             np.sin(ys * 0.45 + t * 1.3) +
             np.sin((xs + ys) * 0.25 + t * 0.7) +
             np.sin(np.hypot(xs - w / 4, ys - h / 2) * 0.5 * (1 + a.mid) - t * 2))
        v = np.clip((v + 4) / 8 + a.beat * 0.25, 0, 0.999)
        lv = (v * 8).astype(int)
        for y in range(1, h - 1):
            x = 0
            for key, grp in groupby(lv[y].tolist()):
                n = len(list(grp))
                if key > 0:
                    put(scr, y, x, self.SH[key] * n, G(key / 8 + 0.01))
                x += n

class Radar:
    name = "radar"
    def __init__(self):
        self.b = np.zeros(32)
        self.rad = np.zeros(32)
    def draw(self, scr, h, w, st):
        a = st.audio
        cx, cy = w // 2, h // 2
        R = max(4.0, min(h / 2 - 3, w / 4 - 3))
        def pt(ang, rad):
            return (int(round(cy + math.sin(ang) * rad)),
                    int(round(cx + math.cos(ang) * rad * 2)))
        for rr in (0.33, 0.66, 1.0):
            n = int(40 + 120 * rr)
            for k in range(n):
                y, x = pt(k / n * TAU, R * rr)
                put(scr, y, x, "·", G(0.3))
        for r in range(-int(R), int(R) + 1):
            put(scr, cy + r, cx, "│", G(0.2))
            put(scr, cy, cx + r * 2, "─", G(0.2))
        sweep = (st.t * 1.8) % TAU
        for i in range(32):
            if (sweep - i / 32 * TAU) % TAU < 0.3:
                self.b[i] = 1.0
                self.rad[i] = 0.12 + 0.88 * a.bands[i]
        self.b *= 0.975
        for i in range(32):
            if self.b[i] > 0.08:
                ang = i / 32 * TAU
                for r in range(1, int(R * self.rad[i]) + 1):
                    y, x = pt(ang, r)
                    put(scr, y, x, "·", G(self.b[i] * 0.5))
                y, x = pt(ang, R * self.rad[i])
                put(scr, y, x, "◆", ACC() if self.rad[i] > 0.8 else G(self.b[i]))
        for j in range(12):
            ang = sweep - j * 0.05
            ch = "█" if j == 0 else ("▒" if j < 4 else "░")
            attr = ACC() if (j == 0 and a.beat > 0.5) else G(1 - j / 12)
            for r in range(1, int(R) + 1):
                y, x = pt(ang, r)
                put(scr, y, x, ch, attr)
        for i, (lab, v) in enumerate((("BASS", a.bass), ("MID ", a.mid), ("HIGH", a.high))):
            put(scr, 3 + i, 3, f"{lab} {'█' * int(v * 14):<14}", G(0.4 + v * 0.6))

FONT = {
    "0": ["███", "█ █", "█ █", "█ █", "███"], "1": ["  █", "  █", "  █", "  █", "  █"],
    "2": ["███", "  █", "███", "█  ", "███"], "3": ["███", "  █", "███", "  █", "███"],
    "4": ["█ █", "█ █", "███", "  █", "  █"], "5": ["███", "█  ", "███", "  █", "███"],
    "6": ["███", "█  ", "███", "█ █", "███"], "7": ["███", "  █", "  █", "  █", "  █"],
    "8": ["███", "█ █", "███", "█ █", "███"], "9": ["███", "█ █", "███", "  █", "███"],
    ":": [" ", "█", " ", "█", " "],
}
SPARK = " ▁▂▃▄▅▆▇█"

def spark(hist, n):
    vals = list(hist)[-n:]
    return "".join(SPARK[min(8, int(v * 8.99))] for v in vals)

class Dash:
    """Scene 8: live device telemetry center."""
    name = "dash"

    def _panel(self, scr, y, x, width, height, title, value, sub, level, st):
        if width < 12 or height < 4:
            return
        edge = ACC() if st.audio.beat > 0.5 else G(0.42)
        put(scr, y, x, "┌" + "─" * (width - 2) + "┐", edge)
        put(scr, y + 1, x, "│" + title[:width - 2].center(width - 2) + "│", G(0.55))
        put(scr, y + height - 1, x, "└" + "─" * (width - 2) + "┘", edge)
        if y + height < scr.getmaxyx()[0]:
            put(scr, y + height, x + 2, "╲" * max(1, min(6, width - 4)), G(0.18))
        put(scr, y + max(2, height // 2 - 1), x + 2,
            str(value)[:width - 4].center(width - 4),
            ACC() if level > 0.8 else G(0.9))
        if height >= 5:
            put(scr, y + height - 2, x + 2, sub[:width - 4], G(0.35))

    def draw(self, scr, h, w, st):
        a, s = st.audio, st.sys
        gap = 2
        col = max(15, (w - 4 - gap) // 2)
        y = 2

        put(scr, y, 2, "SYSTEM TELEMETRY // LIVE", ACC())
        put(scr, y, max(2, w - 11), time.strftime("%H:%M:%S"), G(0.75))
        put(scr, y + 1, 2,
            f"SOURCE {a.mode.upper():4}  MIC {'ON' if a.use_mic else 'OFF'}  "
            f"PROCS {s.procs:04d}  IFACES {len(s.ifaces):02d}", G(0.38))
        y += 3

        self._panel(scr, y, 2, col, 6, "CPU", f"{s.cpu * 100:5.1f}%",
                    f"{len(s.cores)} cores  {s.freq:.0f}MHz", s.cpu, st)
        self._panel(scr, y, 2 + col + gap, col, 6, "MEMORY",
                    f"{s.ram * 100:5.1f}%", "RAM utilization", s.ram, st)

        y += 7
        self._panel(scr, y, 2, col, 6, "DISK", f"{s.disk * 100:5.1f}%",
                    f"I/O {s.disk_rate / 1048576:.1f} MB/s", s.disk, st)

        temp_text = f"{s.temp:.1f} C" if s.temp is not None else "N/A"
        temp_level = max(0.0, min(1.0, (s.temp - 30) / 70)) if s.temp is not None else 0
        self._panel(scr, y, 2 + col + gap, col, 6, "THERMAL", temp_text,
                    "hardware sensor" if s.temp is not None else "sensor unavailable",
                    temp_level, st)

        y += 7
        battery_text = "N/A" if s.battery is None else f"{s.battery * 100:5.1f}%"
        battery_sub = ("AC / CHARGING" if s.charging else "BATTERY") if s.battery is not None else "OS sensor unavailable"
        self._panel(scr, y, 2, col, 6, "POWER", battery_text, battery_sub, s.battery or 0, st)

        rate = s.netpeak * s.net * s.net
        self._panel(scr, y, 2 + col + gap, col, 6, "NETWORK",
                    f"{Sys.fmt_bytes(rate)}/s",
                    f"RX {Sys.fmt_bytes(s.net_rx)} TX {Sys.fmt_bytes(s.net_tx)}",
                    s.net, st)

        y += 7
        graph_h = max(5, h - y - 5)
        half = max(18, (w - 5) // 2)

        if graph_h >= 5:
            put(scr, y, 2, "CPU HISTORY", G(0.55))
            put(scr, y, 3 + half, "NETWORK ACTIVITY", G(0.55))
            for row in range(1, graph_h):
                put(scr, y + row, 2, "│", G(0.18))
                put(scr, y + row, 2 + half, "│", G(0.18))

            for i, value in enumerate(list(s.cpuhist)[-(half - 2):]):
                yy = y + graph_h - 2 - int(value * max(1, graph_h - 3))
                put(scr, yy, 3 + i, "█", ACC() if value > 0.8 else G(0.35 + value * 0.65))

            for i, value in enumerate(list(s.nethist)[-(half - 2):]):
                yy = y + graph_h - 2 - int(value * max(1, graph_h - 3))
                put(scr, yy, 3 + half + i, "◆" if value > 0.8 else "·",
                    ACC() if value > 0.8 else G(0.35 + value * 0.65))

        footer = max(y + graph_h, h - 3)
        put(scr, footer, 2,
            f"UPTIME {Sys.fmt_uptime(s.uptime)}  LOAD {s.load:.2f}  PROCS {s.procs}  MIC {a.level:.2f}",
            G(0.42))
        if s.ifaces:
            put(scr, footer + 1, 2, "NET IFACES: " + ", ".join(s.ifaces)[:w - 14], G(0.28))

# ---------------- گلیچ، قاب و HUD ----------------
def glitch(scr, h, w, st):
    a = st.audio
    if st.glitch <= 0:
        return
    if a.beat > 0.5 or random.random() < 0.01 * st.glitch:
        for _ in range(int(3 * st.glitch * (1 + a.beat * 3))):
            ln = random.randint(5, 30)
            s = "".join(random.choice("█▓▒░#@%&01") for _ in range(ln))
            attr = ACC() | (curses.A_REVERSE if random.random() < 0.3 else 0)
            put(scr, random.randrange(1, max(2, h - 1)), random.randrange(w), s, attr)

def frame(scr, h, w, st):
    attr = ACC() if st.audio.beat > 0.5 else G(0.5)
    L = min(8, w // 4)
    put(scr, 1, 0, "┏" + "━" * (L - 1), attr)
    put(scr, 1, w - L, "━" * (L - 1) + "┓", attr)
    put(scr, h - 2, 0, "┗" + "━" * (L - 1), attr)
    put(scr, h - 2, w - L, "━" * (L - 1) + "┛", attr)

def hud(scr, h, w, st, name):
    a = st.audio
    src = a.mode + ("!" if a.mode in ("mic", "mix") and not a.use_mic else "")
    bar = "█" * int(a.level * 12)
    line = (f" NEON//GRID v2 [{name}{'*' if st.auto else ''}] src:{src} "
            f"cpu:{st.sys.cpu * 100:.0f}% sens:{a.sens:.1f} spd:{st.speed:.1f} "
            f"glitch:{st.glitch} theme:{st.theme} temp:{st.sys.temp if st.sys.temp is not None else "N/A"}C |{bar:<12}| ")
    put(scr, 0, 0, line.ljust(w), curses.color_pair(10) | curses.A_REVERSE)
    put(scr, h - 1, 0, " 1-8 scene | 0 auto | t theme | +/- sens | [ ] speed | g glitch | m source | q quit "[:w - 1],
        G(0.3))

# ---------------- main ----------------
def run(scr, args):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    curses.start_color()
    curses.use_default_colors()
    scr.nodelay(True)

    class St:
        pass
    st = St()
    st.sys = Sys()
    st.audio = Audio(args.source, args.sens)
    st.speed, st.glitch, st.theme = args.speed, args.glitch, args.theme
    st.t, st.dt, st.auto = 0.0, 0.03, args.scene == "auto"
    apply_theme(st.theme)

    scenes = [Rain(), Grid(), Spectrum(), Wave(), Tunnel(), Plasma(), Radar(), Dash()]
    names = [s.name for s in scenes]
    idx = names.index(args.scene) if args.scene in names else 0
    theme_names = list(THEMES)
    last = time.time()
    switch_t = last

    while True:
        k = scr.getch()
        if k in (ord("q"), 27):
            break
        elif ord("1") <= k <= ord("8"):
            idx = k - ord("1")
            st.auto = False
        elif k == ord("0"):
            st.auto = not st.auto
        elif k == ord("t"):
            st.theme = theme_names[(theme_names.index(st.theme) + 1) % len(theme_names)]
            apply_theme(st.theme)
        elif k in (ord("+"), ord("=")):
            st.audio.sens = min(5.0, st.audio.sens + 0.1)
        elif k == ord("-"):
            st.audio.sens = max(0.1, st.audio.sens - 0.1)
        elif k == ord("]"):
            st.speed = min(4.0, st.speed + 0.1)
        elif k == ord("["):
            st.speed = max(0.1, st.speed - 0.1)
        elif k == ord("g"):
            st.glitch = (st.glitch + 1) % 4
        elif k == ord("m"):
            st.audio.set_mode(MODES[(MODES.index(st.audio.mode) + 1) % len(MODES)])

        now = time.time()
        st.dt = (now - last) * st.speed
        last = now
        st.t += st.dt
        if st.auto and now - switch_t > 12:
            idx = (idx + 1) % len(scenes)
            switch_t = now

        st.sys.update()
        st.audio.update(st.t, st.sys)
        # Real device telemetry drives visual intensity across every scene.
        if st.sys.ok:
            telemetry_boost = 0.75 + st.sys.cpu * 0.8 + st.sys.net * 0.45
            st.visual_intensity = max(0.25, min(2.5, telemetry_boost + st.audio.level * 0.5))
        else:
            st.visual_intensity = 0.75 + st.audio.level * 0.5
        scr.erase()
        h, w = scr.getmaxyx()
        if h > 8 and w > 40:
            scenes[idx].draw(scr, h, w, st)
            frame(scr, h, w, st)
            glitch(scr, h, w, st)
            hud(scr, h, w, st, scenes[idx].name)
        else:
            put(scr, 0, 0, "terminal too small")
        scr.refresh()
        time.sleep(max(0, 1 / args.fps - (time.time() - now)))

    st.audio.stop_mic()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--scene", default="tunnel",
                   choices=["rain", "grid", "spectrum", "wave", "tunnel", "plasma", "radar", "dash", "auto"])
    p.add_argument("--theme", choices=list(THEMES), default="cyber")
    p.add_argument("--source", choices=MODES, default="mix")
    p.add_argument("--sens", type=float, default=1.0)
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--glitch", type=int, default=1, choices=[0, 1, 2, 3])
    p.add_argument("--fps", type=int, default=30)
    curses.wrapper(run, p.parse_args())


