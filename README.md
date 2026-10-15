# NEON ANSI Telemetry

> A real-time terminal visualization and system telemetry dashboard built with Python, ANSI graphics, live hardware metrics, and audio-reactive effects.

**NEON ANSI Telemetry** یک داشبورد و موتور Visualizer مبتنی بر ترمینال است که اطلاعات زنده‌ی سیستم را دریافت کرده و آن‌ها را به شکل گرافیک‌های ANSI، انیمیشن‌های سایبری و داشبورد مانیتورینگ نمایش می‌دهد.

این پروژه با هدف ترکیب **System Monitoring + Terminal Graphics + Audio Visualization** ساخته شده و بدون نیاز به محیط گرافیکی اختصاصی، مستقیماً داخل Terminal اجرا می‌شود.

---

## Features

### Live System Telemetry

پروژه می‌تواند اطلاعات زنده‌ی سیستم را دریافت و نمایش دهد، از جمله:

- CPU Usage
- Per-Core CPU Usage
- RAM Usage
- Network RX / TX
- Network Activity
- Network Peak
- Disk Usage
- Disk Activity
- CPU Frequency
- CPU Load
- System Uptime
- Process Count
- Network Interfaces
- Battery Status
- Charging Status
- Temperature Sensors
- Audio / Microphone Level

اطلاعاتی که توسط سخت‌افزار یا سیستم‌عامل پشتیبانی نشوند، به‌صورت `N/A` نمایش داده می‌شوند و مقدار جعلی تولید نمی‌شود.

---

## Terminal Visualizations

پروژه شامل چندین Scene مختلف است که هرکدام یک سبک متفاوت از Visualizer را ارائه می‌کنند:

| Scene | Description                     |
| ----- | ------------------------------- |
| `1`   | Matrix-style digital rain       |
| `2`   | Animated cyber grid             |
| `3`   | Audio spectrum visualizer       |
| `4`   | Reactive waveform               |
| `5`   | Perspective tunnel              |
| `6`   | Procedural plasma               |
| `7`   | Radar / scanning visualization  |
| `8`   | Live system telemetry dashboard |
| `0`   | Automatic scene mode            |

هر Scene به‌صورت real-time رندر می‌شود و می‌تواند با داده‌های سیستم و Audio تغییر کند.

---

## Telemetry Dashboard

Scene شماره‌ی `8` به‌عنوان مرکز مانیتورینگ سیستم طراحی شده است.

این صفحه اطلاعاتی مانند موارد زیر را نمایش می‌دهد:

```text
CPU
MEMORY
DISK
THERMAL
POWER
NETWORK
CPU HISTORY
NETWORK ACTIVITY
UPTIME
LOAD
PROCESSES
AUDIO LEVEL
NETWORK INTERFACES
```

همچنین Dashboard از یک طراحی pseudo-3D در محیط ANSI استفاده می‌کند تا پنل‌ها عمق بصری بیشتری داشته باشند.

---

## Audio Reactive Mode

پروژه می‌تواند ورودی صوتی را دریافت کرده و از آن برای کنترل Visualizer استفاده کند.

Audio analyzer شامل:

- Bass detection
- Mid frequencies
- High frequencies
- Overall level
- Frequency bands
- Beat detection

است.

بنابراین صدا می‌تواند روی شدت و رفتار برخی از افکت‌های بصری تأثیر بگذارد.

### Audio Sources

منبع Audio قابل تغییر است:

```text
mic
sim
cpu
net
mix
```

برای مثال:

```bash
python neon_ansi.py --source mic
```

یا:

```bash
python neon_ansi.py --source mix
```

---

## Installation

### Requirements

پروژه با Python ساخته شده و به کتابخانه‌های زیر نیاز دارد:

```text
numpy
psutil
sounddevice
```

نسخه‌های مورد نیاز در `requirements.txt` قرار گرفته‌اند.

### Install Dependencies

```bash
python -m pip install -r requirements.txt
```

سپس برنامه را اجرا کنید:

```bash
python neon_ansi.py
```

---

## Running the Dashboard

برای اجرای مستقیم Dashboard:

```bash
python neon_ansi.py --scene dash
```

یا:

```bash
python neon_ansi.py --scene 8
```

---

## Command Line Options

می‌توان تنظیمات اولیه‌ی برنامه را از طریق CLI کنترل کرد.

### Scene

```bash
python neon_ansi.py --scene 3
```

### Theme

```bash
python neon_ansi.py --theme cyber
```

Themeهای موجود:

```text
cyber
matrix
synth
fire
```

### Audio Source

```bash
python neon_ansi.py --source mic
```

### Sensitivity

```bash
python neon_ansi.py --sensitivity 1.5
```

### Animation Speed

```bash
python neon_ansi.py --speed 1.2
```

### Glitch Effect

```bash
python neon_ansi.py --glitch 0.3
```

### FPS

```bash
python neon_ansi.py --fps 30
```

---

## Keyboard Controls

پس از اجرای برنامه می‌توان با کیبورد کنترل کرد:

| Key     | Action                        |
| ------- | ----------------------------- |
| `1-8`   | تغییر Scene                   |
| `0`     | Auto Scene                    |
| `T`     | تغییر Theme                   |
| `+ / -` | افزایش / کاهش Sensitivity     |
| `[ / ]` | کاهش / افزایش Animation Speed |
| `G`     | کنترل Glitch                  |
| `M`     | تغییر Audio Source            |
| `Q`     | خروج                          |
| `ESC`   | خروج                          |

---

## Architecture

ساختار کلی پروژه به چند بخش اصلی تقسیم شده است:

```text
neon_ansi.py
│
├── ANSI Terminal Engine
│
├── System Telemetry
│   ├── CPU
│   ├── Memory
│   ├── Network
│   ├── Disk
│   ├── Temperature
│   ├── Battery
│   └── Processes
│
├── Audio Analyzer
│   ├── Microphone
│   ├── Spectrum
│   ├── Bass
│   ├── Mid
│   ├── High
│   └── Beat Detection
│
├── Scene Engine
│   ├── Rain
│   ├── Grid
│   ├── Spectrum
│   ├── Wave
│   ├── Tunnel
│   ├── Plasma
│   ├── Radar
│   └── Dashboard
│
└── Main Render Loop
```

---

## Technology Stack

- **Python**
- **NumPy**
- **psutil**
- **SoundDevice**
- ANSI Escape Sequences
- Terminal Rendering
- Real-time Data Processing
- Procedural Graphics
- Audio Signal Analysis

---

## Cross-Platform Support

این پروژه تا حد زیادی به قابلیت‌های سیستم‌عامل و سخت‌افزار وابسته است.

به‌طور کلی می‌تواند روی محیط‌هایی مانند موارد زیر اجرا شود:

- Windows
- Linux
- macOS

با این حال، در دسترس بودن برخی Telemetryها به سیستم‌عامل و سخت‌افزار بستگی دارد.

برای مثال:

```text
Temperature → ممکن است روی بعضی سیستم‌ها در دسترس نباشد
Battery     → روی Desktop ممکن است وجود نداشته باشد
Microphone  → نیازمند دسترسی Audio است
```

در صورت عدم پشتیبانی، برنامه به‌جای ایجاد مقدار جعلی، وضعیت را به‌صورت `N/A` نمایش می‌دهد.

---

## Performance

NEON ANSI برای اجرای real-time طراحی شده است.

برای سیستم‌های ضعیف‌تر می‌توان FPS را کاهش داد:

```bash
python neon_ansi.py --fps 20
```

و برای سیستم‌های قدرتمندتر:

```bash
python neon_ansi.py --fps 60
```

همچنین می‌توان سرعت Animation و Sensitivity را کنترل کرد.

---

## Example

یک اجرای ساده:

```bash
python neon_ansi.py
```

اجرای Dashboard:

```bash
python neon_ansi.py --scene dash
```

اجرای Audio Visualizer:

```bash
python neon_ansi.py --scene 3 --source mic
```

اجرای Tunnel:

```bash
python neon_ansi.py --scene 5 --speed 1.5
```

اجرای یک Theme خاص:

```bash
python neon_ansi.py --theme matrix
```

---

## Project Structure

```text
neon-ansi-telemetry/
│
├── neon_ansi.py
├── requirements.txt
├── README.md
└── LICENSE
```

---

## Use Cases

این پروژه می‌تواند برای موارد مختلفی استفاده شود:

- Terminal System Monitor
- Developer Dashboard
- Hardware Monitoring
- Server Monitoring
- Cyberpunk Terminal UI
- Audio Visualizer
- Linux Terminal Dashboard
- CLI Experiments
- Procedural Graphics
- Real-time Telemetry Visualization
- Desktop / Server Diagnostics

---

## Design Philosophy

هدف پروژه صرفاً نمایش اعداد CPU و RAM نیست.

ایده‌ی اصلی این است که **داده‌ی واقعی سیستم به یک محیط بصری زنده تبدیل شود.**

به‌جای یک Dashboard سنتی:

```text
CPU: 42%
RAM: 61%
NET: 2.4 MB/s
```

داده‌ها می‌توانند مستقیماً به رفتار گرافیکی سیستم تبدیل شوند:

```text
System Telemetry
       ↓
Data Processing
       ↓
Visual Parameters
       ↓
ANSI Rendering
       ↓
Real-time Terminal Visualization
```

---

## Contributing

Pull Request و پیشنهادهای فنی برای توسعه‌ی پروژه آزاد است.

برای مشارکت:

```bash
git clone <repository-url>
cd neon-ansi-telemetry

python -m pip install -r requirements.txt
python neon_ansi.py
```

سپس تغییرات خود را ایجاد کرده و یک Pull Request ارسال کنید.

---

## Roadmap

برنامه‌ی توسعه‌ی پروژه می‌تواند شامل موارد زیر باشد:

- [ ] Advanced GPU monitoring
- [ ] GPU temperature and utilization
- [ ] More detailed disk telemetry
- [ ] Process-level monitoring
- [ ] Network packet visualization
- [ ] Per-interface traffic graphs
- [ ] More advanced 3D terminal scenes
- [ ] True telemetry-driven scene physics
- [ ] Custom user themes
- [ ] Configuration file
- [ ] Plugin system
- [ ] Remote monitoring
- [ ] Server mode
- [ ] WebSocket telemetry input
- [ ] Multi-machine monitoring
- [ ] More advanced audio analysis

---

## License

این پروژه را می‌توانید تحت لایسنس موردنظر خود منتشر کنید.

در صورت استفاده از این Repository، شرایط مندرج در فایل `LICENSE` را رعایت کنید.

---

## Author

Developed with Python, ANSI graphics and real-time system telemetry.

**NEON ANSI Telemetry**

> Turn your system metrics into motion.
