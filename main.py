import platform
import socket
import psutil
import subprocess
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

def get_windows_version_info():
    """استخراج دقیق نسخه و بیلد ویندوز از رجیستری"""
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            display_version = winreg.QueryValueEx(key, "DisplayVersion")[0]
            build = winreg.QueryValueEx(key, "CurrentBuild")[0]
            return f"Windows {platform.release()} (Version: {display_version}, Build: {build})"
        except Exception:
            pass
    return f"{platform.system()} {platform.release()} (Build: {platform.version()})"

def get_physical_disks():
    """استخراج سخت‌افزار فیزیکی هارد دیسک‌ها و تفکیک برند از مدل"""
    disks = []
    if platform.system() == "Windows":
        try:
            cmd = 'wmic diskdrive get model,size,mediatype /format:csv'
            output = subprocess.check_output(cmd, shell=True, text=True)
            lines = output.strip().split('\n')[1:]
            for line in lines:
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 4:
                        media = parts[1].strip()
                        full_model = parts[2].strip()
                        
                        # تفکیک برند (کلمه اول) از مدل
                        model_words = full_model.split(' ')
                        brand = model_words[0] if len(model_words) > 0 else "Unknown"
                        model = " ".join(model_words[1:]) if len(model_words) > 1 else full_model

                        try:
                            size_gb = round(int(parts[3].strip()) / (1024**3), 2)
                        except:
                            size_gb = 0
                            
                        # حدس نوع دیسک بر اساس نام مدل
                        if "SSD" in full_model.upper() or "NVME" in full_model.upper():
                            media = "SSD / NVMe"
                        elif "Fixed" in media:
                            media = "HDD / Solid State"
                            
                        disks.append({"brand": brand, "model": model, "type": media, "size": size_gb})
        except Exception:
            pass
    return disks

def get_logical_partitions():
    """استخراج فضای درگیر درایوهای منطقی"""
    partitions = []
    for part in psutil.disk_partitions(all=False):
        if part.fstype != "" and "cdrom" not in part.opts:
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append({
                    "device": part.device,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "percent": usage.percent
                })
            except PermissionError:
                continue
    return partitions

@app.route('/api/v1/stats')
def get_stats():
    svmem = psutil.virtual_memory()
    stats = {
        "cpu": {
            "usage_percent": psutil.cpu_percent(interval=0.1),
            "frequency_mhz": round(psutil.cpu_freq().current if psutil.cpu_freq() else 0)
        },
        "ram": {
            "total_gb": round(svmem.total / (1024**3), 2),
            "used_gb": round(svmem.used / (1024**3), 2),
            "percent": svmem.percent
        },
        "partitions": get_logical_partitions()
    }
    return jsonify(stats)

@app.route('/')
def index():
    static_info = {
        "os_full": get_windows_version_info(),
        "architecture": platform.machine(),
        "hostname": socket.gethostname(),
        "cpu_model": platform.processor(),
        "cpu_cores": psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(logical=True),
        "physical_disks": get_physical_disks()
    }

    HTML_TEMPLATE = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TechNodeZ | TechInspector</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <style>
            /* متغیرهای اصلی تم دارک و لایت */
            :root {
                --bg-main: #0b0f19;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --card-bg: rgba(30, 41, 59, 0.6);
                --card-border: rgba(255, 255, 255, 0.08);
                --accent-blue: #38bdf8;
                --progress-bg: #334155;
                --table-row-bg: rgba(0, 0, 0, 0.2);
            }

            [data-theme="light"] {
                --bg-main: #f8fafc;
                --text-main: #0f172a;
                --text-muted: #475569;
                --card-bg: rgba(255, 255, 255, 0.9);
                --card-border: rgba(0, 0, 0, 0.08);
                --accent-blue: #0284c7;
                --progress-bg: #e2e8f0;
                --table-row-bg: rgba(255, 255, 255, 0.6);
            }

            body {
                background-color: var(--bg-main);
                color: var(--text-main);
                font-family: 'Inter', sans-serif;
                transition: background-color 0.4s ease, color 0.4s ease;
                overflow-x: hidden;
            }

            /* افکت نئون موس */
            .cursor-glow {
                position: absolute;
                width: 350px;
                height: 350px;
                border-radius: 50%;
                pointer-events: none;
                transform: translate(-50%, -50%);
                z-index: 0;
                mix-blend-mode: screen;
                opacity: 0.12;
                filter: blur(50px);
                transition: background 0.4s ease;
            }
            [data-theme="dark"] .cursor-glow { background: #4ade80; }
            [data-theme="light"] .cursor-glow { background: #1e3a8a; }

            .content-wrapper { position: relative; z-index: 1; }
            .font-mono { font-family: 'JetBrains Mono', monospace; }

            /* برند و هدر */
            .navbar-brand { font-weight: 800; letter-spacing: 1px; color: var(--accent-blue) !important; }
            
            /* دکمه ستاره گیت هاب */
            .btn-github-star {
                background: rgba(250, 204, 21, 0.1);
                border: 1px solid rgba(250, 204, 21, 0.5);
                color: #facc15;
                font-weight: 600;
                transition: all 0.3s ease;
                border-radius: 8px;
            }
            .btn-github-star:hover {
                background: rgba(250, 204, 21, 0.2);
                color: #fde047;
                box-shadow: 0 0 15px rgba(250, 204, 21, 0.3);
                transform: translateY(-1px);
            }
            [data-theme="light"] .btn-github-star {
                color: #ca8a04; border-color: #ca8a04;
            }
            [data-theme="light"] .btn-github-star:hover { color: #a16207; }

            /* کارت‌ها (رفع باگ پرش) */
            .card-stat {
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 16px;
                backdrop-filter: blur(12px);
                transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s ease, border-color 0.3s ease;
                color: var(--text-main);
                will-change: transform;
            }
            /* به جای translateY از scale استفاده کردیم تا ابعاد کادر به هم نریزد و پرش اتفاق نیفتد */
            .card-stat:hover { 
                transform: scale(1.015); 
                border-color: var(--accent-blue); 
                box-shadow: 0 10px 30px rgba(0,0,0,0.08); 
            }
            
            .text-secondary-custom { color: var(--text-muted); font-weight: 500; }
            
            /* پروگرس بار */
            .progress { background-color: var(--progress-bg); height: 8px; border-radius: 4px; overflow: hidden;}
            .progress-bar { transition: width 0.3s ease; }

            .pulse-dot {
                width: 8px; height: 8px; background-color: #10b981; border-radius: 50%;
                display: inline-block; animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
                70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
                100% { transform: scale(0.9); }
            }

            /* استایل اختصاصی جدول هاردها */
            .storage-table {
                width: 100%;
                border-collapse: separate;
                border-spacing: 0 8px;
            }
            .storage-table th {
                color: var(--text-muted);
                font-weight: 600;
                padding: 0 15px 10px 15px;
                border-bottom: 1px solid var(--card-border);
                text-transform: uppercase;
                font-size: 0.85rem;
                letter-spacing: 0.5px;
            }
            .storage-table td {
                background: var(--table-row-bg);
                padding: 15px;
                vertical-align: middle;
                color: var(--text-main);
            }
            .storage-table tr td:first-child { border-top-left-radius: 8px; border-bottom-left-radius: 8px; }
            .storage-table tr td:last-child { border-top-right-radius: 8px; border-bottom-right-radius: 8px; }

            /* برند هارد */
            .brand-badge {
                font-weight: 800;
                color: var(--accent-blue);
                text-transform: uppercase;
                font-size: 0.9rem;
            }

            /* دکمه سوییچ تم */
            .theme-switch { position: relative; display: inline-block; width: 60px; height: 30px; }
            .theme-switch input { opacity: 0; width: 0; height: 0; }
            .slider {
                position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
                background-color: #334155; transition: .4s; border-radius: 34px;
            }
            .slider:before {
                position: absolute; content: "🌙"; height: 22px; width: 22px; left: 4px; bottom: 4px;
                background-color: white; transition: .4s; border-radius: 50%;
                display: flex; align-items: center; justify-content: center; font-size: 12px;
            }
            input:checked + .slider { background-color: #cbd5e1; }
            input:checked + .slider:before { transform: translateX(30px); content: "☀️"; }

            /* فوتر */
            footer {
                border-top: 1px solid var(--card-border);
                margin-top: 60px; padding: 40px 0; text-align: center;
            }
            .social-icons a {
                display: inline-flex; justify-content: center; align-items: center;
                width: 40px; height: 40px; border-radius: 50%;
                background: var(--card-bg); border: 1px solid var(--card-border);
                color: var(--text-muted); font-size: 1.2rem; margin: 0 8px; transition: all 0.3s;
                text-decoration: none;
            }
            .social-icons a:hover {
                color: var(--accent-blue);
                border-color: var(--accent-blue);
                transform: translateY(-3px);
                box-shadow: 0 5px 15px rgba(56, 189, 248, 0.2);
            }
        </style>
    </head>
    <body data-theme="dark">
        <div class="cursor-glow" id="cursorGlow"></div>

        <div class="content-wrapper">
            <nav class="navbar bg-transparent py-4">
                <div class="container d-flex justify-content-between align-items-center">
                    <a class="navbar-brand text-decoration-none fs-4" href="#">
                        <i class="fa-solid fa-layer-group me-2"></i>TechNodeZ <span class="text-secondary-custom fs-5 fw-normal">// TechInspector</span>
                    </a>
                    
                    <div class="d-flex align-items-center gap-3">
                        <a href="https://github.com/TechNodeZ/TechInspector" target="_blank" class="btn btn-sm btn-github-star d-flex align-items-center gap-2 px-3 py-2">
                            <i class="fa-solid fa-star"></i> Star on GitHub
                        </a>

                        <span class="badge bg-dark border border-secondary text-light d-flex align-items-center gap-2 p-2 px-3 rounded-3">
                            <span class="pulse-dot"></span> Live 500ms
                        </span>
                        
                        <div class="d-flex align-items-center ms-2">
                            <label class="theme-switch" for="checkbox">
                                <input type="checkbox" id="checkbox" />
                                <div class="slider"></div>
                            </label>
                        </div>
                    </div>
                </div>
            </nav>

            <div class="container py-2">
                <div class="row g-4 mb-5">
                    <div class="col-md-6">
                        <div class="card p-4 card-stat h-100">
                            <h5 class="text-secondary-custom mb-4"><i class="fa-brands fa-windows me-2"></i>OS Specification</h5>
                            <div class="d-flex justify-content-between mb-3"><span class="text-secondary-custom">Windows Detail:</span><strong class="font-mono text-end">{{ static_info.os_full }}</strong></div>
                            <div class="d-flex justify-content-between mb-3"><span class="text-secondary-custom">Architecture:</span><strong class="font-mono">{{ static_info.architecture }}</strong></div>
                            <div class="d-flex justify-content-between"><span class="text-secondary-custom">Hostname:</span><strong class="font-mono">{{ static_info.hostname }}</strong></div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card p-4 card-stat h-100">
                            <h5 class="text-secondary-custom mb-4"><i class="fa-solid fa-microchip me-2"></i>Processor Profile</h5>
                            <div class="d-flex justify-content-between mb-3"><span class="text-secondary-custom">Model:</span><strong class="font-mono text-truncate text-end" style="max-width: 250px;">{{ static_info.cpu_model }}</strong></div>
                            <div class="d-flex justify-content-between mb-3"><span class="text-secondary-custom">Physical Cores:</span><strong class="font-mono">{{ static_info.cpu_cores }}</strong></div>
                            <div class="d-flex justify-content-between"><span class="text-secondary-custom">Logical Threads:</span><strong class="font-mono">{{ static_info.cpu_threads }}</strong></div>
                        </div>
                    </div>
                </div>

                <h4 class="mb-4 fw-bold">Live Telemetry</h4>
                <div class="row g-4 mb-5">
                    <div class="col-md-6">
                        <div class="card p-4 card-stat">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="m-0 font-weight-bold">CPU Load</h5>
                                <i class="fa-solid fa-gauge-high text-info fs-4"></i>
                            </div>
                            <h1 class="mb-3 font-mono fw-bold" id="cpu-text">--%</h1>
                            <div class="progress mb-3"><div id="cpu-bar" class="progress-bar bg-info" style="width: 0%"></div></div>
                            <div class="d-flex justify-content-between">
                                <small class="text-secondary-custom">Core Frequency</small>
                                <small class="font-mono fw-bold"><span id="cpu-freq">--</span> MHz</small>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-6">
                        <div class="card p-4 card-stat">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="m-0 font-weight-bold">Memory (RAM)</h5>
                                <i class="fa-solid fa-memory text-success fs-4"></i>
                            </div>
                            <h1 class="mb-3 font-mono fw-bold" id="ram-text">--%</h1>
                            <div class="progress mb-3"><div id="ram-bar" class="progress-bar bg-success" style="width: 0%"></div></div>
                            <div class="d-flex justify-content-between">
                                <small class="text-secondary-custom">Utilization</small>
                                <small class="font-mono fw-bold"><span id="ram-used">--</span> GB / <span id="ram-total">--</span> GB</small>
                            </div>
                        </div>
                    </div>
                </div>

                <h4 class="mb-4 fw-bold">Storage Diagnostics</h4>
                
                <div class="card p-4 card-stat mb-4">
                    <h6 class="text-secondary-custom mb-4"><i class="fa-solid fa-hard-drive me-2"></i>Physical Storage Hardware</h6>
                    <div class="table-responsive">
                        <table class="storage-table font-mono">
                            <thead>
                                <tr>
                                    <th>Brand</th>
                                    <th>Hardware Model</th>
                                    <th>Media Type</th>
                                    <th>Capacity</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for disk in static_info.physical_disks %}
                                <tr>
                                    <td><span class="brand-badge">{{ disk.brand }}</span></td>
                                    <td>{{ disk.model }}</td>
                                    <td><span class="badge bg-secondary px-2 py-1">{{ disk.type }}</span></td>
                                    <td class="fw-bold">{{ disk.size }} GB</td>
                                </tr>
                                {% endfor %}
                                {% if not static_info.physical_disks %}
                                <tr><td colspan="4" class="text-center text-secondary-custom py-4">Hardware level details require Admin rights on Windows.</td></tr>
                                {% endif %}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="row g-4" id="partitions-container">
                    </div>
            </div>

            <footer>
                <div class="container">
                    <div class="social-icons mb-4">
                        <a href="https://github.com/technodez" title="GitHub"><i class="fa-brands fa-github"></i></a>
                        <a href="https://t.me/technodez" title="Telegram"><i class="fa-brands fa-telegram"></i></a>
                        <a href="https://www.youtube.com/@technodez" title="YouTube"><i class="fa-brands fa-youtube"></i></a>
                        <a href="https://www.aparat.com/TechNodeZ" title="Aparat"><i class="fa-solid fa-video"></i></a>
                    </div>
                    <p class="text-secondary-custom font-mono small mb-0">Developed By <strong style="color: var(--text-main);">TechNodeZ Team</strong></p>
                </div>
            </footer>
        </div>

        <script>
            // سیستم تغییر تم
            const toggleSwitch = document.querySelector('.theme-switch input[type="checkbox"]');
            const currentTheme = localStorage.getItem('theme');

            if (currentTheme) {
                document.body.setAttribute('data-theme', currentTheme);
                if (currentTheme === 'light') toggleSwitch.checked = true;
            }

            function switchTheme(e) {
                if (e.target.checked) {
                    document.body.setAttribute('data-theme', 'light');
                    localStorage.setItem('theme', 'light');
                } else {
                    document.body.setAttribute('data-theme', 'dark');
                    localStorage.setItem('theme', 'dark');
                }    
            }
            toggleSwitch.addEventListener('change', switchTheme, false);

            // افکت موس نئون با پرفورمنس بالا
            const cursorGlow = document.getElementById('cursorGlow');
            document.addEventListener('mousemove', (e) => {
                requestAnimationFrame(() => {
                    cursorGlow.style.left = e.pageX + 'px';
                    cursorGlow.style.top = e.pageY + 'px';
                });
            });

            // موتور واکشی اطلاعات زنده
            async function updateDashboard() {
                try {
                    const response = await fetch('/api/v1/stats');
                    const data = await response.json();
                    
                    // Update CPU
                    document.getElementById('cpu-text').innerText = data.cpu.usage_percent + '%';
                    document.getElementById('cpu-bar').style.width = data.cpu.usage_percent + '%';
                    document.getElementById('cpu-freq').innerText = data.cpu.frequency_mhz;

                    // Update RAM
                    document.getElementById('ram-text').innerText = data.ram.percent + '%';
                    document.getElementById('ram-bar').style.width = data.ram.percent + '%';
                    document.getElementById('ram-used').innerText = data.ram.used_gb;
                    document.getElementById('ram-total').innerText = data.ram.total_gb;

                    // Update Disks (Partitions)
                    const partitionsContainer = document.getElementById('partitions-container');
                    partitionsContainer.innerHTML = ''; 
                    
                    data.partitions.forEach(part => {
                        let barColor = part.percent > 85 ? 'bg-danger' : 'bg-warning';
                        const cardHtml = `
                            <div class="col-md-4">
                                <div class="card p-4 card-stat h-100">
                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                        <h5 class="m-0 fw-bold">Drive ${part.device}</h5>
                                    </div>
                                    <h2 class="mb-3 font-mono">${part.percent}%</h2>
                                    <div class="progress mb-3"><div class="progress-bar ${barColor}" style="width: ${part.percent}%"></div></div>
                                    <div class="d-flex justify-content-between">
                                        <small class="text-secondary-custom">Space Used</small>
                                        <small class="font-mono fw-bold">${part.used_gb} GB / ${part.total_gb} GB</small>
                                    </div>
                                </div>
                            </div>
                        `;
                        partitionsContainer.insertAdjacentHTML('beforeend', cardHtml);
                    });

                } catch (error) {
                    console.error("Error fetching stats:", error);
                }
            }

            setInterval(updateDashboard, 500);
            updateDashboard();
        </script>
    </body>
    </html>
    '''
    return render_template_string(HTML_TEMPLATE, static_info=static_info)

if __name__ == '__main__':
    app.run(debug=True, threaded=True)