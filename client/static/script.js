// --- 1. HIỆU ỨNG THIÊN NHIÊN (Giữ nguyên) ---
const cloudContainer = document.getElementById('cloudContainer');
const clouds = [];

function createClouds() {
    cloudContainer.innerHTML = ''; clouds.length = 0; 
    for (let i = 0; i < 5; i++) {
        const cloud = document.createElement('div');
        cloud.classList.add('cloud');
        cloud.style.top = Math.random() * 40 + 5 + '%';
        cloud.style.transform = `scale(${Math.random() * 0.5 + 0.8})`;
        cloud.style.animationDuration = Math.random() * 20 + 25 + 's';
        cloud.style.animationDelay = Math.random() * -30 + 's'; 
        cloudContainer.appendChild(cloud);
        clouds.push(cloud);
    }
}
function createStars() {
    const container = document.getElementById('starContainer'); container.innerHTML = '';
    for (let i = 0; i < 50; i++) {
        const star = document.createElement('div'); star.classList.add('star');
        const size = Math.random() * 3 + 'px'; star.style.width = size; star.style.height = size;
        star.style.top = Math.random() * 100 + '%'; star.style.left = Math.random() * 100 + '%';
        star.style.animationDuration = Math.random() * 3 + 2 + 's'; star.style.animationDelay = Math.random() * 5 + 's';
        container.appendChild(star);
    }
}
function createRain() {
    const container = document.getElementById('rainContainer'); container.innerHTML = '';
    for (let i = 0; i < 80; i++) {
        const drop = document.createElement('div'); drop.classList.add('raindrop');
        drop.style.left = Math.random() * 100 + '%'; drop.style.animationDuration = Math.random() * 0.4 + 0.4 + 's';
        drop.style.animationDelay = Math.random() * 2 + 's';
        container.appendChild(drop);
    }
}

// Chạy khởi tạo
createClouds(); createStars(); createRain(); 

// Logic Mưa/Nắng
let stormTimer;
function startWeatherCycle() {
    const randomTime = Math.floor(Math.random() * (45000 - 30000 + 1) + 30000);
    stormTimer = setTimeout(activateStorm, randomTime);
}
function activateStorm() {
    document.body.classList.add('storm-active');
    document.getElementById('rainContainer').style.display = 'block';
    document.body.classList.remove('is-dimmed');
    setTimeout(() => {
        document.body.classList.remove('storm-active');
        document.getElementById('rainContainer').style.display = 'none';
        startWeatherCycle();
    }, 15000);
}
startWeatherCycle();

function toggleTheme() {
    const body = document.body;
    const btn = document.querySelector('.theme-toggle');
    if (body.classList.contains('light-mode')) {
        body.classList.remove('light-mode'); body.classList.add('dark-mode');
        if(btn) btn.innerText = "☀️ Chế độ Ngày";
    } else {
        body.classList.remove('dark-mode'); body.classList.add('light-mode');
        if(btn) btn.innerText = "🌙 Chế độ Đêm";
    }
}

// --- 2. LOGIC LOGIN (WEBSOCKET) ---
let socket = null;
const ipInput = document.getElementById('ipInput');
const portInput = document.getElementById('portInput');
// Tự điền IP nếu có thể
ipInput.value = window.location.hostname; 
portInput.value = "8888";

function handleConnection() {
    const targetIP = ipInput.value.trim();
    const targetPort = portInput.value.trim();
    const mainBtn = document.getElementById('mainBtn');
    const statusDesc = document.getElementById('statusDesc');

    if (!targetIP || !targetPort) { alert("Thiếu IP/Port!"); return; }
    if (socket) { try { socket.close(); } catch(e){} }

    mainBtn.innerHTML = '⏳ Đang kết nối...'; mainBtn.style.opacity = "0.8";
    statusDesc.innerText = `Connecting to ws://${targetIP}:${targetPort}...`;

    try {
        socket = new WebSocket(`ws://${targetIP}:${targetPort}`);
        
        // [SỬA 1] Gửi lệnh "CONNECT" chuẩn thay vì "HELLO_FROM_WEB"
        socket.onopen = function() { 
            console.log("Socket Open -> Sending CONNECT");
            socket.send("CONNECT"); 
        };

        socket.onmessage = function(event) {
            console.log("Nhan duoc tu Server:", event.data);
            
            // [SỬA 2] Logic kiểm tra tin nhắn linh hoạt hơn
            // Python gửi: {"status": "connected", "msg": "Bridge OK"}
            let isConnected = false;

            // Cách 1: Kiểm tra chuỗi JSON
            if (event.data.includes("Bridge OK") || event.data.includes("connected")) {
                isConnected = true;
            }
            // Cách 2: Nếu Server C++ trả về chữ "OK" hoặc "1"
            else if (event.data.includes("OK") || event.data.trim() === "1") {
                isConnected = true;
            } 
            // Cách 3: Logic cũ (để phòng hờ)
            else if (event.data.includes("CONNECTED_TO_EXE")) {
                isConnected = true;
            }

            if (isConnected) {
                showSuccess(targetIP, targetPort);
            } 
            else if (event.data.includes("error") || event.data.includes("Offline")) {
                showError("Lỗi: Server C++ chưa bật!");
            }
        };

        socket.onerror = function() { showError("Lỗi kết nối Socket (Bridge chưa chạy)!"); };
        
        // Thêm timeout: Nếu 5 giây mà không thấy gì thì báo lỗi
        setTimeout(() => {
            if (document.getElementById('loginSection').style.display !== 'none' && 
                mainBtn.innerHTML.includes('Đang')) {
                showError("Quá thời gian chờ (Server C++ không trả lời)");
            }
        }, 5000);

    } catch (err) { showError(err.message); }
}

function showError(msg) {
    const mainBtn = document.getElementById('mainBtn');
    mainBtn.innerHTML = "Thử lại"; mainBtn.classList.add('error');
    setTimeout(() => mainBtn.classList.remove('error'), 500);
    document.getElementById('statusDesc').innerText = msg;
}

function showSuccess(ip, port) {
    document.getElementById('statusTitle').innerText = "Đã kết nối!";
    document.getElementById('statusDesc').innerText = `Thành công: ${ip}:${port}`;
    document.getElementById('statusDesc').style.color = "#22c55e";
    document.getElementById('iconStatus').innerText = "🌿";
    
    document.getElementById('mainBtn').innerHTML = "Đang vào vườn...";
    
    // Chuyển cảnh sang Dashboard
    setTimeout(() => {
        document.getElementById('loginSection').style.display = 'none';
        const app = document.getElementById('appSection');
        app.style.display = 'flex'; // Hiện Dashboard (Flex)
        app.classList.add('active'); // Kích hoạt animation
    }, 1500);
}

function logout() {
    if(socket) socket.close();
    document.getElementById('appSection').style.display = 'none';
    document.getElementById('appSection').classList.remove('active');
    document.getElementById('loginSection').style.display = 'block';
    document.getElementById('mainBtn').innerHTML = "Kết nối ngay";
    document.getElementById('statusDesc').innerText = "Sẵn sàng kết nối.";
    document.getElementById('statusDesc').style.color = "inherit";
}

// --- 3. LOGIC DASHBOARD (WEBCAM + APPS) ---

function logMsg(msg) {
    const el = document.getElementById('mini-log');
    if(el) el.innerText = "> " + msg;
}

function toggleWebcam(action) {
    const img = document.getElementById('video-feed');
    const dot = document.getElementById('recDot');
    
    if (action === 'start') {
        fetch('/api/webcam/start', {method: 'POST'}).catch(e=>console.log(e));
        img.src = "/video_feed"; 
        img.style.opacity = "1";
        dot.style.display = "block";
        logMsg("Đang kết nối Camera...");
    } else {
        fetch('/api/webcam/stop', {method: 'POST'}).catch(e=>console.log(e));
        img.src = "";
        img.style.opacity = "0.2";
        dot.style.display = "none";
        logMsg("Đã tắt Camera.");
    }
}

function loadApps() {
    const tbody = document.getElementById('app-list-body');
    tbody.innerHTML = "<tr><td colspan='3' style='text-align:center'>Đang tìm kiếm...</td></tr>";
    
    fetch('/api/list_apps')
    .then(res => res.json())
    .then(data => {
        tbody.innerHTML = "";
        if(data.length === 0) {
                tbody.innerHTML = "<tr><td colspan='3' style='text-align:center'>Trống.</td></tr>";
                return;
        }
        data.forEach(app => {
            tbody.innerHTML += `
                <tr>
                    <td>${app.id}</td>
                    <td>${app.name}</td>
                    <td style="text-align: right;">
                        <button class="btn-nature danger" style="padding: 2px 8px; font-size: 0.7rem;" onclick="killProc('${app.id}')">KILL</button>
                    </td>
                </tr>
            `;
        });
        logMsg(`Tìm thấy ${data.length} tiến trình.`);
    })
    .catch(err => {
        tbody.innerHTML = "<tr><td colspan='3' style='text-align:center; color:#fca5a5'>Lỗi API!</td></tr>";
        logMsg("Lỗi kết nối Server API.");
    });
}

function killProc(pid) {
    if(!confirm(`Dừng PID ${pid}?`)) return;
    fetch('/api/kill', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({pid: pid})
    }).then(res => res.json()).then(data => {
        logMsg(`Đã dừng PID: ${pid}`);
        loadApps();
    });
}

// Đồng hồ
setInterval(() => {
    const c = document.getElementById('clock');
    if(c) c.innerText = new Date().toLocaleTimeString();
}, 1000);

function switchMode(mode) {
    const container = document.getElementById('dynamicContent');
    const statusText = document.getElementById('statusDesc');
    
    container.innerHTML = '<div style="text-align:center; margin-top:50px;">⏳ Đang chuyển chế độ...</div>';
    
    fetch('/api/set_mode', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ mode: mode })
    })
    .then(res => res.json())
    .then(data => {
        if(data.status === 'ok') {
            renderContent(mode);
        } else {
            container.innerHTML = '<p style="color:#fca5a5; text-align:center;">Lỗi server không phản hồi.</p>';
        }
    })
    .catch(err => {
        console.error(err);
        container.innerHTML = '<p style="color:#fca5a5; text-align:center;">Mất kết nối!</p>';
    });
}

function renderContent(mode) {
    const container = document.getElementById('dynamicContent');
    
    if (mode === 'webcam') {
        container.innerHTML = `
            <div class="cam-frame" style="height:100%; flex:1;">
                <img src="/video_feed" style="width:100%; height:100%; object-fit:contain;">
            </div>
            <div style="text-align:center; color:#6ee7b7; margin-top:10px;">🎥 Đang xem Webcam</div>
        `;
    } 
    else if (mode === 'screen') {
        container.innerHTML = `
            <div class="cam-frame" style="height:100%; flex:1;">
                <img src="/video_feed" style="width:100%; height:100%; object-fit:contain;">
            </div>
            <div style="text-align:center; color:#93c5fd; margin-top:10px;">🖥️ Đang stream màn hình</div>
        `;
    }
    else if (mode === 'keylogger') {
        container.innerHTML = `
            <div class="dash-card" style="display:flex; flex-direction:column; height:100%;">
                <div style="margin-bottom:10px; display:flex; gap:8px; flex-wrap:wrap;">
                    <button class="btn-nature" onclick="keylogHook()">Bắt đầu Ghi (Hook)</button>
                    <button class="btn-nature" onclick="keylogUnhook()">Dừng Ghi (Unhook)</button>
                    <button class="btn-nature" onclick="keylogLoad()">Tải Keylog</button>
                </div>
                <textarea id="keylogBox" style="flex:1; width:100%; resize:none; background:rgba(15,23,42,0.9); color:#e5e7eb; border-radius:8px; padding:10px; border:1px solid rgba(148,163,184,0.4); font-family:Consolas,monospace;"></textarea>
            </div>
        `;
    }
    else if (mode === 'notify') {
        container.innerHTML = `
            <div class="dash-card" style="display:flex; flex-direction:column; height:100%;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h3 style="margin:0; color:#a5b4fc;">🔔 Lịch sử Thông báo</h3>
                    <button class="btn-nature" onclick="loadNotify()">Tải lại</button>
                </div>
                <div style="flex:1; overflow-y:auto;">
                    <table class="nature-table">
                        <thead>
                            <tr><th>App</th><th>Thời gian</th><th>Nội dung</th></tr>
                        </thead>
                        <tbody id="notifyBody">
                            <tr><td colspan="3">Đang tải...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        loadNotify();
    }
    else if (mode === 'files') {
        container.innerHTML = `
            <div class="dash-card" style="display:flex; flex-direction:column; height:100%;">
                <div style="display:flex; gap:8px; margin-bottom:10px; align-items:center;">
                    <button class="btn-nature" onclick="loadDrives()">🏠 Drives</button>
                    <button class="btn-nature" onclick="goBackPath()">⬅ Back</button>
                    <input id="currentPath" class="custom-input" style="background:rgba(15,23,42,0.7); color:#e5e7eb; border-radius:10px; border:1px solid rgba(148,163,184,0.4);" readonly value="My Computer">
                </div>
                <div style="flex:1; overflow-y:auto;">
                    <table class="nature-table">
                        <thead>
                            <tr><th>Tên</th><th>Loại</th><th>Kích thước</th></tr>
                        </thead>
                        <tbody id="fileBody">
                            <tr><td colspan="3">Đang tải...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        window._currentPath = "";  // global state
        loadDrives();
    }
    else if (mode === 'apps') { // Đang chạy + KILL
        container.innerHTML = `
            <div class="dash-card" style="display:flex; flex-direction:column; height:100%;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h3 style="margin:0; color:#86efac;">🔥 Ứng dụng đang chạy</h3>
                    <button class="btn-nature" onclick="loadRunningApps()">Làm mới</button>
                </div>
                <div style="flex:1; overflow-y:auto;">
                    <table class="nature-table">
                        <thead>
                            <tr><th>ID</th><th>Tên</th><th>Threads</th><th></th></tr>
                        </thead>
                        <tbody id="appListBody">
                            <tr><td colspan="4">Đang tải...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        loadRunningApps();
    }
    else if (mode === 'process') {  // Ứng dụng đã cài + START
        container.innerHTML = `
            <div class="dash-card" style="display:flex; flex-direction:column; height:100%;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h3 style="margin:0; color:#fde68a;">🚀 Ứng dụng đã cài</h3>
                    <button class="btn-nature" onclick="loadInstalledApps()">Lấy DS Ứng dụng</button>
                </div>
                <div style="flex:1; overflow-y:auto;">
                    <table class="nature-table">
                        <thead>
                            <tr><th>Tên ứng dụng</th><th style="width:120px;"></th></tr>
                        </thead>
                        <tbody id="installedBody">
                            <tr><td colspan="2">Chưa tải.</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    else {
        container.innerHTML = `
            <div style="text-align:center; margin-top:50px;">
                <h3>Chế độ: ${mode.toUpperCase()}</h3>
                <p>Đã gửi lệnh kích hoạt. Server đang xử lý...</p>
            </div>`;
    }
}


// ==== KEYLOGGER ====
function keylogHook() {
    fetch('/api/keylog/hook', {method:'POST'})
        .then(r=>r.json()).then(res => {
            logMsg(res.ok ? "Đã bật Hook Keylogger." : "Lỗi bật Hook.");
        }).catch(()=>logMsg("Lỗi API Keylog."));
}
function keylogUnhook() {
    fetch('/api/keylog/unhook', {method:'POST'})
        .then(r=>r.json()).then(res => {
            logMsg(res.ok ? "Đã tắt Hook Keylogger." : "Lỗi tắt Hook.");
        }).catch(()=>logMsg("Lỗi API Keylog."));
}
function keylogLoad() {
    fetch('/api/keylog/text')
        .then(r=>r.json())
        .then(data => {
            const box = document.getElementById('keylogBox');
            if (box) box.value = data.text || "";
            logMsg("Đã tải keylog.");
        })
        .catch(()=>logMsg("Lỗi tải keylog."));
}

// ==== NOTIFICATIONS ====
function loadNotify() {
    const tbody = document.getElementById('notifyBody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="3">Đang tải...</td></tr>`;
    fetch('/api/notify/list')
        .then(r=>r.json())
        .then(list => {
            tbody.innerHTML = "";
            if (!list || list.length === 0) {
                tbody.innerHTML = `<tr><td colspan="3">Không có dữ liệu.</td></tr>`;
                return;
            }
            list.forEach(n => {
                tbody.innerHTML += `
                    <tr>
                        <td>${n.app}</td>
                        <td>${n.time}</td>
                        <td>${n.content}</td>
                    </tr>
                `;
            });
            logMsg(`Đã tải ${list.length} thông báo.`);
        })
        .catch(()=> {
            tbody.innerHTML = `<tr><td colspan="3" style="color:#fca5a5;">Lỗi API.</td></tr>`;
            logMsg("Lỗi tải thông báo.");
        });
}

// ==== FILE MANAGER ====
function loadDrives() {
    const tbody = document.getElementById('fileBody');
    const pathInput = document.getElementById('currentPath');
    if (!tbody || !pathInput) return;

    pathInput.value = "My Computer";
    window._currentPath = "";
    tbody.innerHTML = `<tr><td colspan="3">Đang tải...</td></tr>`;

    fetch('/api/files/drives')
        .then(r=>r.json())
        .then(list => {
            tbody.innerHTML = "";
            if (!list || list.length === 0) {
                tbody.innerHTML = `<tr><td colspan="3">Không có dữ liệu.</td></tr>`;
                return;
            }
            list.forEach(e => {
                const icon = e.type === "DRIVE" ? "💽 " : e.type === "FOLDER" ? "📁 " : "📄 ";
                tbody.innerHTML += `
                    <tr onclick="fileRowClick('${e.name.replace(/\\/g,'\\\\')}', '${e.type}')">
                        <td>${icon}${e.name}</td>
                        <td>${e.type}</td>
                        <td>${e.size}</td>
                    </tr>
                `;
            });
        })
        .catch(()=> {
            tbody.innerHTML = `<tr><td colspan="3" style="color:#fca5a5;">Lỗi API.</td></tr>`;
        });
}

function fileRowClick(name, type) {
    if (type === "DRIVE") {
        openPath(name);
    } else if (type === "FOLDER") {
        let base = window._currentPath || "";
        let newPath = base ? (base + name + "\\") : name;
        openPath(newPath);
    } else {
        logMsg(`File: ${name} (chưa hỗ trợ tải về Web)`);
    }
}

function openPath(path) {
    const tbody = document.getElementById('fileBody');
    const pathInput = document.getElementById('currentPath');
    if (!tbody || !pathInput) return;

    tbody.innerHTML = `<tr><td colspan="3">Đang tải...</td></tr>`;

    fetch('/api/files/list', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({path: path})
    })
    .then(r=>r.json())
    .then(list => {
        window._currentPath = path;
        pathInput.value = path;
        tbody.innerHTML = "";
        if (!list || list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="3">Thư mục trống.</td></tr>`;
            return;
        }
        list.forEach(e => {
            const icon = e.type === "DRIVE" ? "💽 " : e.type === "FOLDER" ? "📁 " : "📄 ";
            tbody.innerHTML += `
                <tr onclick="fileRowClick('${e.name.replace(/\\/g,'\\\\')}', '${e.type}')">
                    <td>${icon}${e.name}</td>
                    <td>${e.type}</td>
                    <td>${e.size}</td>
                </tr>
            `;
        });
    })
    .catch(()=> {
        tbody.innerHTML = `<tr><td colspan="3" style="color:#fca5a5;">Lỗi API.</td></tr>`;
    });
}

function goBackPath() {
    let cur = window._currentPath || "";
    if (!cur || cur.length <= 3) {
        loadDrives();
        return;
    }
    let parent = cur.replace(/\\+$/,'');
    const lastSlash = parent.lastIndexOf('\\');
    if (lastSlash > 2) {
        parent = parent.substring(0, lastSlash+1);
    } else {
        parent = parent.substring(0, 3);
    }
    openPath(parent);
}

// ==== RUNNING APPS (Apps block) ====
function loadRunningApps() {
    const tbody = document.getElementById('appListBody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="4">Đang tải...</td></tr>`;
    fetch('/api/list_apps')
        .then(r=>r.json())
        .then(list => {
            tbody.innerHTML = "";
            if (!list || list.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4">Trống.</td></tr>`;
                return;
            }
            list.forEach(p => {
                tbody.innerHTML += `
                    <tr>
                        <td>${p.id}</td>
                        <td>${p.name}</td>
                        <td>${p.threads}</td>
                        <td style="text-align:right;">
                            <button class="btn-nature danger" onclick="killProc('${p.id}')">KILL</button>
                        </td>
                    </tr>
                `;
            });
        })
        .catch(()=> {
            tbody.innerHTML = `<tr><td colspan="4" style="color:#fca5a5;">Lỗi API.</td></tr>`;
        });
}

// ==== INSTALLED APPS (Processes block) ====
function loadInstalledApps() {
    const tbody = document.getElementById('installedBody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="2">Đang tải...</td></tr>`;
    fetch('/api/apps/installed')
        .then(r=>r.json())
        .then(list => {
            tbody.innerHTML = "";
            if (!list || list.length === 0) {
                tbody.innerHTML = `<tr><td colspan="2">Không có dữ liệu.</td></tr>`;
                return;
            }
            list.forEach(a => {
                const name = a.name;
                tbody.innerHTML += `
                    <tr>
                        <td>${name}</td>
                        <td style="text-align:right;">
                            <button class="btn-nature" onclick="startInstalledApp('${name.replace(/'/g,"\\'")}')">START</button>
                        </td>
                    </tr>
                `;
            });
        })
        .catch(()=> {
            tbody.innerHTML = `<tr><td colspan="2" style="color:#fca5a5;">Lỗi API.</td></tr>`;
        });
}

function startInstalledApp(name) {
    fetch('/api/process/start', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({name: name})
    })
    .then(r=>r.json())
    .then(res => {
        logMsg(res.ok ? `Đã gửi lệnh mở: ${name}` : `Lỗi mở: ${name}`);
    })
    .catch(()=>logMsg("Lỗi API StartProcess."));
}

function shutdownServer() {
    fetch('/api/power', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'shutdown'})
    })
    .then(res => res.json())
    .then(data => {
        if (data.ok) {
            alert('Máy chủ đang tắt...');
        } else {
            alert('Không thể tắt máy.');
        }
    })
    .catch(err => {
        console.error(err);
        alert('Lỗi kết nối khi shutdown.');
    });
}

function restartServer() {
    fetch('/api/power', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'restart'})
    })
    .then(res => res.json())
    .then(data => {
        if (data.ok) {
            alert('Máy chủ đang khởi động lại...');
        } else {
            alert('Không thể restart máy.');
        }
    })
    .catch(err => {
        console.error(err);
        alert('Lỗi kết nối khi restart.');
    });
}
