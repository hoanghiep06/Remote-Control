let isWebcamRecording = false;
let isScreenRecording = false;
let isKeylogRunning = false;
let recHoverTimer = null;
let webcamAutoStopTimer = null;
let screenAutoStopTimer = null;
let currentViewMode = '';
let isSuperviseOn = false;


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
    // Khởi tạo hiệu ứng nền cũ
    createClouds();
    createStars();

    // LOGIC INTRO -> LOGIN
    const intro = document.getElementById('introOverlay');
    const login = document.getElementById('loginSection');
    
    // Chờ 5 giây (khớp với thanh loading)
    setTimeout(() => {
        if(intro) {
            intro.classList.add('finished'); // Kích hoạt mờ dần
            
            setTimeout(() => {
                intro.style.display = 'none'; // Ẩn hẳn
                
                // Hiện Login Form
                if(login) {
                    login.style.display = 'block'; 
                    // Thêm hiệu ứng hiện ra cho Login
                    login.style.animation = 'popIn 0.8s ease forwards';
                }
            }, 1000); // Chờ 1s để hiệu ứng mờ kết thúc
        }
    }, 5000);
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
    // 1. Lấy thông tin MÁY ĐÍCH (Máy nạn nhân) từ ô nhập
    const targetIP = document.getElementById('ipInput').value.trim();
    const targetPort = document.getElementById('portInput').value.trim();

    if (!targetIP || !targetPort) { 
        alert("Vui lòng nhập IP và Port của máy cần điều khiển!"); 
        return; 
    }

    // 2. Xác định địa chỉ MÁY CHỦ WEB (Máy chạy Python/Bridge)
    // window.location.hostname: Tự động lấy IP của máy đang mở web
    // Nếu bạn mở web trên localhost -> nó là localhost
    // Nếu bạn mở trên điện thoại (truy cập IP máy tính) -> nó là IP máy tính
    const bridgeIP = window.location.hostname || "localhost";
    const bridgePort = "8888"; // Port WebSocket cố định trong webapp.py

    if (socket) { try { socket.close(); } catch(e){} }

    // --- GIAO DIỆN MÀN HÌNH CHỜ ---
    connectStartTime = Date.now();
    document.getElementById('loginSection').style.display = 'none';
    const trans = document.getElementById('transitionScreen');
    
    // Reset nội dung
    document.getElementById('transIcon').innerText = "🌱";
    document.getElementById('transIcon').classList.add('bouncing');
    document.getElementById('transTitle').innerText = "Đang kết nối...";
    document.getElementById('transTitle').style.color = "#86efac";
    // Hiển thị rõ đang gọi tới ai
    document.getElementById('transDesc').innerText = `Đang gọi tới ${targetIP}:${targetPort}...`;
    
    trans.style.display = 'flex';
    trans.style.opacity = '1';

    try {
        // 3. KẾT NỐI WEBSOCKET TỚI BRIDGE (PYTHON)
        console.log(`[WS] Connecting to Bridge at ws://${bridgeIP}:${bridgePort}`);
        socket = new WebSocket(`ws://${bridgeIP}:${bridgePort}`);
        
        socket.onopen = function() { 
            console.log("[WS] Connected to Bridge -> Sending Target Info");
            // [QUAN TRỌNG] Gửi lệnh: CONNECT <IP_NẠN_NHÂN> <PORT_NẠN_NHÂN>
            // Python sẽ nhận lệnh này và thực hiện kết nối TCP thực sự
            socket.send(`CONNECT ${targetIP} ${targetPort}`); 
        };

        socket.onmessage = function(event) {
            // Python trả về kết quả kết nối TCP
            if (event.data.includes("Bridge OK") || event.data.includes("connected") || event.data.includes("OK")) {
                showSuccess(targetIP, targetPort);
            } else if (event.data.includes("error") || event.data.includes("FAIL")) {
                showError(`Không thể kết nối tới ${targetIP} (Kiểm tra IP hoặc Firewall máy đó)`);
            }
        };

        socket.onerror = function() { 
            showError("Lỗi: Không tìm thấy Server Python (Bridge)!"); 
        };
        
        // Timeout 10s
        setTimeout(() => {
            if (trans.style.display !== 'none' && 
                document.getElementById('transTitle').innerText.includes('Đang')) {
                showError("Quá thời gian chờ (Server không phản hồi).");
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
    // 1. Bỏ dòng confirm xác nhận
    // if(!confirm(`Dừng PID ${pid}?`)) return; 
    
    // 2. Hiện thông báo đang xử lý
    showToast(`Đang dừng PID ${pid}...`, "info");
    
    fetch('/api/kill', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({pid: pid})
    })
    .then(res => res.json())
    .then(data => {
        if(data.ok) {
            // 3. Thông báo thành công
            showToast(`✅ Đã diệt xong PID: ${pid}`, "success");
            logMsg(`Đã dừng PID: ${pid}`); // Ghi vào log nhỏ ở dưới nếu có
            
            // 4. Tự động làm mới danh sách (Logic cũ giữ nguyên)
            if (currentViewMode === 'apps') {
                loadRunningApps(); 
            } else if (currentViewMode === 'process') {
                loadInstalledApps(); 
            }
        } else {
            showToast(`❌ Lỗi: Không thể tắt process này`, "error");
        }
    })
    .catch(err => {
        console.error(err);
        showToast("❌ Lỗi kết nối API", "error");
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
    currentViewMode = mode;
    const container = document.getElementById('dynamicContent');
    
    if (mode === 'webcam') {
        isWebcamRecording = false; 
        
        container.innerHTML = `
            <div id="webcamFrame" class="cam-frame">
                <div class="rec-indicator"><div class="rec-dot"></div> REC</div>

                <div id="aiStatus" style="position:absolute; top:10px; left:10px; color:#00ff00; font-weight:bold; display:none; text-shadow: 1px 1px 2px black;">
                    👁️ AI SUPERVISE ACTIVE
                </div>

                <div class="top-right-controls">
                    <button id="btnSupervise" class="icon-btn" onclick="toggleSupervise()" title="Bật/Tắt Giám sát AI" style="margin-right:5px;">
                        👁️
                    </button>

                    <div class="record-wrapper" id="recWrapperWebcam">
                        <input type="number" id="recTimeWebcam" class="rec-timer-input" placeholder="s" min="0">
                        
                        <button id="btnRecordWebcam" class="icon-btn record-btn" onclick="toggleWebcamRecord()" title="Ghi hình">
                            <span>⏺️</span> 
                        </button>
                    </div>

                    <button class="icon-btn" onclick="downloadSnapshot('webcam')" title="Chụp ảnh">
                        📸
                    </button>
                </div>

                <img src="/video_feed" style="width:100%; height:100%; object-fit:contain;">
            </div>`;
    }

    else if (mode === 'screen') {
        isScreenRecording = false;
        
        container.innerHTML = `
            <div id="screenFrame" class="cam-frame">
                <div class="rec-indicator"><div class="rec-dot"></div> REC</div>

                <div class="top-right-controls">
                    <div class="record-wrapper" id="recWrapperScreen">
                        <input type="number" id="recTimeScreen" class="rec-timer-input" placeholder="s" min="0">
                        <button id="btnRecordScreen" class="icon-btn record-btn" onclick="toggleScreenRecord()" title="Quay màn hình">
                            <span>⏺️</span> 
                        </button>
                    </div>

                    <button class="icon-btn" onclick="downloadSnapshot('screen')" title="Chụp ảnh">
                        📸
                    </button>
                </div>

                <img src="/screen_feed" style="width:100%; height:100%; object-fit:contain;">
            </div>
            <div style="text-align:center; color:#93c5fd; margin-top:10px;">🖥️ Đang stream màn hình</div>`;
    }

    else if (mode === 'keylogger') {
        container.innerHTML = `
            <div class="dash-card" style="display:flex; flex-direction:column; height:100%;">
                <div style="margin-bottom:10px; display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
                    
                    <button id="btnKeylogToggle" class="btn-nature" onclick="toggleKeylog()">
                        ▶️ Bắt đầu Ghi
                    </button>

                    <button class="btn-nature" onclick="keylogLoad()">🔄 Tải dữ liệu</button>
                    <button class="btn-nature danger" onclick="clearKeylog()">🗑️ Xóa sạch</button>
                    
                    <span id="keylogStatus" style="font-size:0.8rem; color:#cbd5e1; margin-left:auto; margin-right: 10px;">Sẵn sàng</span>
                </div>
                <textarea id="keylogBox" readonly style="flex:1; width:100%; resize:none; background:rgba(15,23,42,0.9); color:#e5e7eb; border-radius:8px; padding:10px; border:1px solid rgba(148,163,184,0.4); font-family:Consolas,monospace;"></textarea>
            </div>
        `;
        
        // 2. LOGIC TỰ ĐỘNG BẬT KHI VÀO
        if (!isKeylogRunning) {
            // Nếu chưa chạy -> Bật ngay
            toggleKeylog();
        } else {
            // Nếu đang chạy -> Chỉ cập nhật giao diện nút cho đúng
            updateKeylogUI();
        }
        
        // Tự động tải dữ liệu cũ lên khung
        keylogLoad();
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
    else if (mode === 'apps') { 
        container.innerHTML = `
            <div class="apps-container">
                <div class="stats-panel">
                    <h3 style="margin:0; color:#fff; text-align:center; margin-bottom:10px;">📊 Hệ thống</h3>
                    
                    <div class="stat-card">
                        <div class="stat-title">CPU Usage</div>
                        <div id="chart-cpu" class="chart-circle chart-cpu">
                            <span class="chart-value" id="val-cpu">0%</span>
                        </div>
                        <div class="stat-detail" id="det-cpu">Intel/AMD</div>
                    </div>

                    <div class="stat-card">
                        <div class="stat-title">Memory (RAM)</div>
                        <div id="chart-ram" class="chart-circle chart-ram">
                            <span class="chart-value" id="val-ram">0%</span>
                        </div>
                        <div class="stat-detail" id="det-ram">0 / 0 GB</div>
                    </div>

                    <div class="stat-card">
                        <div class="stat-title">Disk (C:)</div>
                        <div id="chart-disk" class="chart-circle chart-disk">
                            <span class="chart-value" id="val-disk">0%</span>
                        </div>
                        <div class="stat-detail" id="det-disk">0 / 0 GB</div>
                    </div>
                </div>

                <div class="apps-table-panel">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; padding:0 10px;">
                        <h3 style="margin:0; color:#86efac;">🔥 Ứng dụng đang chạy</h3>
                        <button class="btn-nature" onclick="loadRunningApps()">🔄 Làm mới</button>
                    </div>
                    <div style="flex:1; overflow-y:auto;">
                        <table class="nature-table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Tên</th>
                                    <th>Threads</th>
                                    <th>Mem</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody id="appListBody">
                                <tr><td colspan="5">Đang tải...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        loadRunningApps();
    }


    else if (mode === 'process') {  
        // Giao diện Processes
        container.innerHTML = `
            <div class="dash-card" style="display:flex; flex-direction:column; height:100%;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h3 style="margin:0; color:#fde68a;">🚀 Quản lý Ứng dụng</h3>
                    <button class="btn-nature" onclick="loadInstalledApps()">🔄 Làm mới</button>
                </div>
                <div style="flex:1; overflow-y:auto;">
                    <table class="nature-table">
                        <thead>
                            <tr>
                                <th>Tên ứng dụng</th>
                                <th style="width:160px; text-align:right;">Hành động</th>
                            </tr>
                        </thead>
                        <tbody id="installedBody">
                            <tr><td colspan="2" style="text-align:center;">Đang phân tích hệ thống...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        // [QUAN TRỌNG] Gọi hàm tải dữ liệu ngay lập tức
        loadInstalledApps();
    }

    else if (mode === 'custom') {
        container.innerHTML = `
            <div class="dash-card" style="display:flex; flex-direction:column; height:100%; justify-content:center; align-items:center;">
                <h2 style="color:#a7f3d0; margin-bottom: 30px;">⚙️ Quản trị Hệ thống</h2>
                
                <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap: 20px; width: 100%; max-width: 600px;">
                    
                    <div class="power-card" onclick="restartServer()">
                        <div class="p-icon">🔄</div>
                        <div class="p-title">Khởi động lại</div>
                        <div class="p-desc">Reboot máy chủ Windows</div>
                    </div>

                    <div class="power-card danger" onclick="shutdownServer()">
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

// --- HÀM HIỂN THỊ THÔNG BÁO (TOAST) ---
function showToast(msg, type = 'success') {
    // Tạo container nếu chưa có
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    // Tạo thẻ thông báo
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Chọn icon tương ứng
    let icon = "✅";
    if (type === 'error') icon = "❌";
    if (type === 'info') icon = "ℹ️";

    toast.innerHTML = `<span class="toast-icon">${icon}</span><span class="toast-msg">${msg}</span>`;
    
    container.appendChild(toast);

    // Tự động xóa khỏi DOM sau 3.5 giây (khớp với CSS fadeOut)
    setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 3500);
}

function downloadSnapshot(type) {
    const url = type === 'webcam' ? '/api/webcam/snapshot' : '/api/screen/snapshot';
    
    showToast("📸 Đang chụp ảnh...", "info");

    fetch(url)
        .then(response => {
            if (response.ok) {
                // [THAY ĐỔI]: Bỏ đoạn code tạo thẻ <a> và click() để không hiện cửa sổ lưu
                // Vì Server Python đã lưu file vào thư mục 'picture' rồi.
                
                // Chỉ hiện thông báo thành công
                showToast(`✅ Đã lưu ảnh vào thư mục 'client/picture'!`, "success");
            } else {
                throw new Error("Lỗi Server");
            }
        })
        .catch(err => {
            showToast("❌ Lỗi: Không thể chụp (Camera/Screen chưa sẵn sàng)", "error");
        });
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
    // Hiển thị thông báo đang tải (dạng info)
    showToast("Đang tải dữ liệu...", "info");

    fetch('/api/keylog/text')
        .then(r => r.json())
        .then(data => {
            const box = document.getElementById('keylogBox');
            if (box) {
                box.value = data.text || "";
                // Cuộn xuống cuối để xem tin mới nhất
                box.scrollTop = box.scrollHeight; 
            }
            showToast("Đã cập nhật nội dung mới!", "success");
        })
        .catch(() => showToast("Lỗi tải dữ liệu Keylog.", "error"));
}

function clearKeylog() {
    // Không dùng confirm() nữa -> Bấm là xóa ngay
    
    fetch('/api/keylog/clear', { method: 'POST' }) 
    .then(r => r.json())
    .then(data => {
        if(data.ok) {
            // Xóa trắng khung hiển thị ngay lập tức
            const box = document.getElementById('keylogBox');
            if(box) box.value = ""; 
            
            showToast("Đã xóa sạch lịch sử!", "success");
        } else {
            showToast("Lỗi Server: Không xóa được file.", "error");
        }
    })
    .catch(() => {
        showToast("Lỗi kết nối Server.", "error");
    });
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
            let rowHtml = "";
            
            if (e.type === "FILE") {
                // --- XỬ LÝ FILE: HIỆN NÚT DOWNLOAD ---
                
                // Xử lý đường dẫn đầy đủ (nối path hiện tại + tên file)
                // Lưu ý: encode tên file để tránh lỗi nháy đơn/kép
                const safeName = e.name.replace(/'/g, "\\'"); 
                let fullPath = (path.endsWith('\\') ? path : path + '\\') + e.name;
                
                // Escape dấu \ để truyền vào hàm JS không bị lỗi
                const jsPath = fullPath.replace(/\\/g, '\\\\').replace(/'/g, "\\'");

                rowHtml = `
                    <tr>
                        <td>📄 ${e.name}</td>
                        <td>${e.type}</td>
                        <td style="display:flex; justify-content:space-between; align-items:center;">
                            <span>${e.size}</span>
                            <button class="btn-nature" style="padding:4px 10px; font-size:0.8rem;" 
                                onclick="downloadFile('${jsPath}')">
                                ⬇ Tải
                            </button>
                        </td>
                    </tr>
                `;
            } else {
                // --- XỬ LÝ FOLDER/DRIVE: CLICK ĐỂ MỞ ---
                const icon = e.type === "DRIVE" ? "💽 " : "📁 ";
                const safeName = e.name.replace(/\\/g,'\\\\').replace(/'/g, "\\'");
                
                rowHtml = `
                    <tr onclick="fileRowClick('${safeName}', '${e.type}')" style="cursor:pointer;">
                        <td>${icon}${e.name}</td>
                        <td>${e.type}</td>
                        <td></td>
                    </tr>
                `;
            }
            tbody.innerHTML += rowHtml;
        });
    })
    .catch(()=> {
        tbody.innerHTML = `<tr><td colspan="3" style="color:#fca5a5;">Lỗi API.</td></tr>`;
    });
}

function downloadFile(fullPath) {
    // 1. Bỏ confirm -> Bấm là chạy luôn
    
    showToast(`Đang kéo file từ máy nạn nhân...`, "info");
    
    fetch('/api/files/download', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path: fullPath})
    })
    .then(r => r.json())
    .then(data => {
        if(data.ok) {
            // 2. Chỉ hiện thông báo, KHÔNG tạo link tải về trình duyệt nữa
            // Vì file đã nằm sẵn trong folder 'client/downloads' của bạn rồi
            showToast(`✅ Tải xong! File đã lưu tại: /downloads/${data.file}`, "success");
            logMsg(`Đã tải file: ${data.file}`);
        } else {
            showToast("❌ Lỗi: " + (data.error || "File rỗng hoặc không quyền"), "error");
        }
    })
    .catch(e => {
        console.error(e);
        showToast("❌ Lỗi kết nối API", "error");
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
    // 1. Tải danh sách Apps (Code cũ, nhưng bỏ render cột CPU)
    const tbody = document.getElementById('appListBody');
    if (tbody) {
        tbody.innerHTML = `<tr><td colspan="5">⏳ Đang tải dữ liệu...</td></tr>`;
        fetch('/api/list_apps')
            .then(r=>r.json())
            .then(list => {
                tbody.innerHTML = "";
                if (!list || list.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="5">Trống.</td></tr>`; return;
                }
                list.forEach(p => {
                    tbody.innerHTML += `
                        <tr>
                            <td>${p.id}</td>
                            <td style="font-weight:bold; color:#e2e8f0; max-width:150px; overflow:hidden; text-overflow:ellipsis;">${p.name}</td>
                            <td>${p.threads}</td>
                            <td style="color:#fde68a;">${p.memory}</td>
                            <td style="text-align:right;">
                                <button class="btn-nature danger" style="padding:4px 10px; font-size:0.75rem;" onclick="killProc('${p.id}')">KILL</button>
                            </td>
                        </tr>`;
                });
            })
            .catch(()=> { tbody.innerHTML = `<tr><td colspan="5" style="color:#fca5a5;">Lỗi API Apps.</td></tr>`; });
    }

    // 2. Tải thông số Hệ thống (Cập nhật thêm text chi tiết)
    fetch('/api/stats')
        .then(r => r.json())
        .then(stats => {
            // Cập nhật biểu đồ (%)
            updateChart('cpu', stats.cpu, '#ef4444');
            updateChart('ram', stats.ram_p, '#f59e0b');
            updateChart('disk', stats.disk_p, '#10b981');

            // Cập nhật text chi tiết (GB)
            setText('det-cpu', stats.cpu + "% Load");
            setText('det-ram', `${stats.ram_u} / ${stats.ram_t} GB`);
            setText('det-disk', `${stats.disk_u} / ${stats.disk_t} GB`);
        })
        .catch(e => console.log("Lỗi Stats:", e));
}

function setText(id, txt) {
    const el = document.getElementById(id);
    if(el) el.innerText = txt;
}

// Hàm vẽ lại biểu đồ tròn
function updateChart(type, value, color) {
    const chart = document.getElementById(`chart-${type}`);
    const valText = document.getElementById(`val-${type}`);
    if (chart && valText) {
        valText.innerText = value + "%";
        // Cập nhật background gradient
        chart.style.background = `conic-gradient(${color} ${value}%, rgba(255,255,255,0.1) ${value}%)`;
    }
}

// ==== INSTALLED APPS (XỬ LÝ THÔNG MINH START/KILL) ====
function loadInstalledApps() {
    const tbody = document.getElementById('installedBody');
    if (!tbody) return;
    
    tbody.innerHTML = `<tr><td colspan="2" style="text-align:center;">⏳ Đang đối chiếu dữ liệu...</td></tr>`;

    // Gọi song song 2 API để lấy dữ liệu
    Promise.all([
        fetch('/api/apps/installed').then(r => r.json()), // List A: Đã cài
        fetch('/api/list_apps').then(r => r.json())       // List B: Đang chạy (có PID)
    ])
    .then(([installedList, runningList]) => {
        tbody.innerHTML = "";
        
        if (!installedList || installedList.length === 0) {
            tbody.innerHTML = `<tr><td colspan="2">Không tìm thấy ứng dụng nào.</td></tr>`;
            return;
        }

        // Tạo Map cho danh sách đang chạy để tìm kiếm nhanh hơn
        // Key: Tên process (chữ thường), Value: PID
        const runningMap = {};
        runningList.forEach(proc => {
            if (proc.name) runningMap[proc.name.toLowerCase()] = proc.id;
        });

        installedList.forEach(app => {
            const appName = app.name; 
            const searchName = appName.toLowerCase();
            
            // LOGIC SO SÁNH:
            // Tìm xem tên App đã cài có xuất hiện trong danh sách process đang chạy không
            // (So sánh tương đối: contains)
            let isRunning = false;
            let targetPid = null;

            for (const [procName, pid] of Object.entries(runningMap)) {
                // Nếu tên process chứa tên app hoặc ngược lại
                if (procName.includes(searchName) || searchName.includes(procName)) {
                    isRunning = true;
                    targetPid = pid;
                    break; 
                }
            }

            // Xử lý trạng thái nút
            // Class 'disabled' sẽ làm nút mờ đi và không bấm được (nhờ CSS ở bước 1)
            const startClass = isRunning ? "btn-nature disabled" : "btn-nature";
            const killClass  = isRunning ? "btn-nature danger" : "btn-nature danger disabled";
            
            // Xử lý hành động onclick
            // Start: Gửi tên app
            // Kill: Gửi PID tìm được (nếu có)
            const startAction = `startInstalledApp('${appName.replace(/'/g,"\\'")}')`;
            const killAction  = targetPid ? `killProc('${targetPid}')` : "";

            tbody.innerHTML += `
                <tr>
                    <td>
                        <span style="${isRunning ? 'color:#86efac; font-weight:bold;' : ''}">
                            ${appName}
                        </span>
                        ${isRunning ? '<small style="color:#cbd5e1; margin-left:5px;">(Đang chạy)</small>' : ''}
                    </td>
                    <td style="text-align:right; white-space:nowrap;">
                        <button class="${startClass}" onclick="${startAction}" style="margin-right:5px;">▶ START</button>
                        <button class="${killClass}" onclick="${killAction}">💀 KILL</button>
                    </td>
                </tr>
            `;
        });
    })
    .catch(err => {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="2" style="color:#fca5a5; text-align:center;">Lỗi kết nối API.</td></tr>`;
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
        if(res.ok) {
            logMsg(`Đã gửi lệnh mở: ${name}`);
            showToast(`Đang khởi động ${name}...`, "info");
            
            // [MỚI] Chờ 1.5 giây cho App kịp chạy lên, rồi refresh lại danh sách
            // Để nút START mờ đi, nút KILL sáng lên
            setTimeout(() => {
                if (currentViewMode === 'process') {
                    loadInstalledApps();
                }
            }, 1500);
        } else {
            logMsg(`Lỗi mở: ${name}`);
            showToast("Không thể khởi động ứng dụng", "error");
        }
    })
    .catch(()=>logMsg("Lỗi API StartProcess."));
}

function shutdownServer() {
    // Hỏi xác nhận trước
    if(!confirm('CẢNH BÁO: Bạn sắp kích hoạt thiên thạch hủy diệt để TẮT MÁY CHỦ.\nHành động này sẽ ngắt kết nối vĩnh viễn.\nTiếp tục?')) return;

    showToast("☄️ Đã phóng thiên thạch...", "info");

    fetch('/api/power', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'shutdown'})
    })
    .then(res => res.json())
    .then(data => {
        if (data.ok) {
            // Hiệu ứng thiên thạch rơi -> Sau đó tự logout
            triggerApocalypse(() => {
                logout(); // Logout sau cú va chạm
            });
        } else {
            showToast("❌ Lỗi: Server từ chối tắt máy.", "error");
        }
    })
    .catch(err => {
        // Vẫn cho chạy hiệu ứng kể cả khi mất kết nối (vì tắt máy là mất kết nối mà)
        triggerMeteorEffect(() => {
             setTimeout(logout, 500);
        });
    });
}

function restartServer() {
    if(!confirm('Bạn muốn triệu hồi thiên thạch để KHỞI ĐỘNG LẠI máy chủ?')) return;

    showToast("☄️ Thiên thạch tái sinh đang đến...", "info");

    fetch('/api/power', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'restart'})
    })
    .then(res => res.json())
    .then(data => {
        if (data.ok) {
            triggerApocalypse(() => {
                logout();
            });
        } else {
            showToast("❌ Lỗi: Không thể restart.", "error");
        }
    })
    .catch(err => {
        triggerMeteorEffect(() => {
             setTimeout(logout, 500);
        });
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

        startNightCycle();
        
        // Đêm thì ngừng tan tuyết (trừ khi đang Mưa)
        if (currentWeather !== WEATHER.RAIN) {
            if(meltingTimer) clearInterval(meltingTimer);
        }
    } else {
        // Chuyển sang SÁNG (Ngày)
        body.classList.remove('dark-mode'); body.classList.add('light-mode');
        if(btn) btn.innerText = "🌙 Chế độ Đêm";
        
        stopNightCycle();

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
    const input = document.getElementById('recTimeWebcam');
    const wrapper = document.getElementById('recWrapperWebcam');

    if (!isWebcamRecording) {
        // --- BẮT ĐẦU ---
        
        // 1. Lấy thời gian từ ô input (nếu có)
        let duration = 0;
        if (input && input.value) {
            duration = parseInt(input.value);
        }

        // 2. Cập nhật giao diện
        btn.classList.add('recording'); 
        frame.classList.add('recording');
        isWebcamRecording = true;
        
        // Ẩn ô input đi cho gọn
        if(wrapper) wrapper.classList.remove('show-input');

        // 3. Gửi lệnh Start kèm duration (POST)
        fetch('/api/webcam/record/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ duration: duration })
        })
        .then(r => r.json())
        .then(res => {
            if(!res.ok) stopUI();
            else {
                // Nếu có hẹn giờ -> JS tự đếm ngược để tắt UI
                if (duration > 0) {
                    console.log(`Hẹn giờ tắt sau ${duration}s`);
                    webcamAutoStopTimer = setTimeout(() => {
                        toggleWebcamRecord(); // Gọi lại hàm để kích hoạt nhánh Dừng
                        showToast("Đã dừng ghi hình (Hết giờ)", "info");
                    }, duration * 1000);
                }
            }
        })
        .catch(() => stopUI());

    } else {
        // --- DỪNG ---
        stopUI();
        // Xóa timer hẹn giờ (nếu người dùng bấm dừng sớm)
        if (webcamAutoStopTimer) clearTimeout(webcamAutoStopTimer);

        fetch('/api/webcam/record/stop').then(() => {
             showToast("Video đã được lưu!", "success");
        });
    }

    function stopUI() {
        btn.classList.remove('recording');
        frame.classList.remove('recording');
        isWebcamRecording = false;
        if(input) input.value = ""; // Reset ô nhập
    }
}


// --- LOGIC QUAY MÀN HÌNH (SCREEN RECORD) ---
function toggleScreenRecord() {
    const btn = document.getElementById('btnRecordScreen');
    const frame = document.getElementById('screenFrame');
    const input = document.getElementById('recTimeScreen');
    const wrapper = document.getElementById('recWrapperScreen');

    if (!isScreenRecording) {
        // --- BẮT ĐẦU GHI ---
        
        // 1. Lấy thời gian hẹn giờ (nếu có)
        let duration = 0;
        if (input && input.value) {
            duration = parseInt(input.value);
        }

        // 2. Cập nhật giao diện ngay lập tức
        btn.classList.add('recording'); 
        frame.classList.add('recording');
        isScreenRecording = true;
        
        // Ẩn ô input đi cho gọn
        if(wrapper) wrapper.classList.remove('show-input');

        // 3. Gọi API Start với method POST
        fetch('/api/screen/record/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ duration: duration })
        })
        .then(r => r.json())
        .then(res => {
            if(!res.ok) {
                stopUI(); // Lỗi thì tắt UI
                showToast("Lỗi: Không thể bắt đầu quay", "error");
            } else {
                // Nếu có hẹn giờ -> Set timeout tự tắt
                if (duration > 0) {
                    console.log(`Screen auto-stop in ${duration}s`);
                    screenAutoStopTimer = setTimeout(() => {
                        toggleScreenRecord(); // Gọi lại chính nó để chạy nhánh Dừng
                        showToast("Đã dừng quay màn hình (Hết giờ)", "info");
                    }, duration * 1000);
                }
            }
        })
        .catch(e => {
            console.error(e);
            stopUI();
        });

    } else {
        // --- DỪNG GHI ---
        stopUI();
        
        // Hủy hẹn giờ (nếu người dùng bấm dừng trước khi hết giờ)
        if (screenAutoStopTimer) clearTimeout(screenAutoStopTimer);

        fetch('/api/screen/record/stop')
            .then(r => r.text())
            .then(msg => {
                 console.log("Đã lưu video màn hình.");
                 showToast("✅ Video màn hình đã được lưu!", "success");
            });
    }

    // Hàm phụ trợ reset UI
    function stopUI() {
        btn.classList.remove('recording');
        frame.classList.remove('recording');
        isScreenRecording = false;
        if(input) input.value = ""; // Reset ô nhập
    }
}

// --- LOGIC KEYLOGGER MỚI (TOGGLE & AUTO) ---

function toggleKeylog() {
    const btn = document.getElementById('btnKeylogToggle');
    
    // Nếu đang tắt -> BẬT (HOOK)
    if (!isKeylogRunning) {
        fetch('/api/keylog/hook', {method:'POST'})
            .then(r => r.json())
            .then(res => {
                if(res.ok) {
                    isKeylogRunning = true;
                    updateKeylogUI();
                    // Hiện thông báo Toast
                    showToast("Đã bật Keylogger (Hook)", "info");
                } else {
                    showToast("Lỗi bật Hook!", "error");
                }
            })
            .catch(() => showToast("Lỗi kết nối API.", "error"));
    } 
    // Nếu đang bật -> TẮT (UNHOOK)
    else {
        fetch('/api/keylog/unhook', {method:'POST'})
            .then(r => r.json())
            .then(res => {
                if(res.ok) {
                    isKeylogRunning = false;
                    updateKeylogUI();
                    // Hiện thông báo Toast
                    showToast("Đã dừng Keylogger", "info");
                } else {
                    showToast("Lỗi tắt Hook!", "error");
                }
            })
            .catch(() => showToast("Lỗi kết nối API.", "error"));
    }
}

function updateKeylogUI() {
    const btn = document.getElementById('btnKeylogToggle');
    const status = document.getElementById('keylogStatus');
    
    if (!btn) return;

    if (isKeylogRunning) {
        // Trạng thái ĐANG CHẠY
        btn.innerHTML = "⏸️ Dừng Ghi";
        btn.classList.add('recording'); // Thêm class đỏ (dùng chung style với nút quay video)
        // Nếu chưa có class recording trong CSS thì thêm: background: #ef4444 !important;
        btn.style.backgroundColor = "#ef4444"; 
        btn.style.borderColor = "#ef4444";
        btn.style.color = "white";
        
        if(status) {
            status.innerText = "● Đang ghi phím...";
            status.style.color = "#ef4444"; 
            status.style.animation = "pulse 1.5s infinite"; // Nhấp nháy nhẹ
        }
    } else {
        // Trạng thái ĐÃ DỪNG
        btn.innerHTML = "▶️ Bắt đầu Ghi";
        btn.classList.remove('recording');
        btn.style.backgroundColor = ""; // Reset về mặc định
        btn.style.borderColor = "";
        btn.style.color = "";
        
        if(status) {
            status.innerText = "Đã dừng.";
            status.style.color = "#cbd5e1";
            status.style.animation = "none";
        }
    }
}

// --- LOGIC HOVER HIỆN Ô NHẬP ---


function startRecHover(type) { // type: 'Webcam' hoặc 'Screen'
    // Nếu đang ghi rồi thì không hiện input làm gì
    if ((type === 'Webcam' && isWebcamRecording) || (type === 'Screen' && isScreenRecording)) return;

    // Đợi 3 giây (3000ms) thì hiện ô input
    recHoverTimer = setTimeout(() => {
        const wrapper = document.getElementById(`recWrapper${type}`);
        if(wrapper) wrapper.classList.add('show-input');
    }, 3000); 
}

function endRecHover(type) {
    if (recHoverTimer) clearTimeout(recHoverTimer); // Hủy đếm nếu chuột rời đi sớm
    
    // Nếu chưa nhập gì (input rỗng) thì ẩn đi cho gọn
    const input = document.getElementById(`recTime${type}`);
    const wrapper = document.getElementById(`recWrapper${type}`);
    
    // Nếu đang focus vào ô input thì đừng ẩn vội
    if (document.activeElement !== input) {
        if(wrapper) wrapper.classList.remove('show-input');
    }
}

// --- HIỆU ỨNG KHẢI HUYỀN (MƯA THIÊN THẠCH CHẬM) ---
function triggerApocalypse(callback) {
    // 1. Tạo lớp phủ đỏ (Atmosphere)
    let overlay = document.querySelector('.apocalypse-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'apocalypse-overlay';
        document.body.appendChild(overlay);
    }

    // 2. Tạo container chứa thiên thạch
    let stormContainer = document.querySelector('.meteor-storm-container');
    if (!stormContainer) {
        stormContainer = document.createElement('div');
        stormContainer.className = 'meteor-storm-container';
        document.body.appendChild(stormContainer);
    }

    setTimeout(() => { overlay.classList.add('active'); }, 100);

    // --- HÀM TẠO VỤ NỔ TẠI MẶT ĐẤT ---
    function spawnExplosion(xPercent) {
        const boom = document.createElement('div');
        boom.className = 'impact-explosion';
        boom.style.left = xPercent + '%'; // Nổ tại vị trí X
        document.body.appendChild(boom);
        
        // Xóa sau khi nổ xong
        setTimeout(() => boom.remove(), 1000);
    }

    // --- HÀM SINH THIÊN THẠCH ---
    function spawnMeteor() {
        const m = document.createElement('div');
        m.classList.add('meteor-slow');
        
        // Vị trí xuất phát X (từ 20% đến 140% chiều ngang)
        // Vì bay chéo sang trái nên cần xuất phát tít bên phải mới bay vào giữa màn hình được
        const startX = Math.random() * 120 + 20; 
        m.style.left = startX + '%';
        m.style.top = Math.random() * -20 - 10 + '%';

        // Tốc độ ngẫu nhiên (3s - 5s)
        const durationSec = Math.random() * 2 + 3; 
        m.style.animation = `meteorFallSlow ${durationSec}s linear forwards`;
        
        // Kích thước ngẫu nhiên
        const scale = Math.random() * 0.5 + 0.6;
        m.style.transform = `rotate(-45deg) scale(${scale})`;

        stormContainer.appendChild(m);

        // --- TÍNH TOÁN VỤ NỔ (IMPACT LOGIC) ---
        // Thiên thạch đi quãng đường dọc (Y) là 150vh (trong CSS)
        // Mặt đất nằm ở 100vh.
        // => Thời gian chạm đất = Tổng thời gian * (100 / 150)
        const impactTimeMs = (durationSec * 1000) * (100 / 150);

        // Vị trí X khi chạm đất:
        // Thiên thạch di chuyển ngang (X) là -150vw (trong CSS)
        // => Tại thời điểm chạm đất, nó đã đi được -100vw
        const endX = startX - 100; 

        // Nếu điểm rơi nằm trong màn hình (0% đến 100%) -> Cho nổ
        if (endX > 0 && endX < 100) {
            setTimeout(() => {
                spawnExplosion(endX);
            }, impactTimeMs);
        }

        // Xóa thiên thạch
        setTimeout(() => m.remove(), durationSec * 1000);
    }

    // Tạo thiên thạch liên tục
    const meteorInterval = setInterval(spawnMeteor, 150); // Mật độ dày hơn xíu

    // KẾT THÚC SAU 5 GIÂY -> CHỚP TRẮNG -> LOGOUT
    setTimeout(() => {
        clearInterval(meteorInterval);
        
        const flash = document.createElement('div');
        flash.className = 'final-flash';
        document.body.appendChild(flash);
        
        setTimeout(() => flash.style.opacity = '1', 50);

        setTimeout(() => {
            if (callback) callback();
            
            // Dọn dẹp sạch sẽ sau khi logout
            setTimeout(() => {
                overlay.remove();
                stormContainer.remove();
                flash.remove();
                // Xóa hết các vụ nổ còn sót lại
                document.querySelectorAll('.impact-explosion').forEach(e => e.remove());
            }, 2000);
        }, 1500);

    }, 5000);
}

function toggleSupervise() {
    const btn = document.getElementById('btnSupervise');
    const status = document.getElementById('aiStatus');
    
    // Đảo trạng thái
    isSuperviseOn = !isSuperviseOn;

    // Cập nhật UI ngay lập tức
    if (isSuperviseOn) {
        btn.classList.add('recording'); // Tái sử dụng class đỏ hoặc tạo class mới
        btn.style.color = "#00ff00";    // Icon màu xanh lá
        btn.style.border = "1px solid #00ff00";
        if(status) status.style.display = "block";
        showToast("👁️ Đã BẬT giám sát thông minh!", "info");
    } else {
        btn.classList.remove('recording');
        btn.style.color = "";
        btn.style.border = "";
        if(status) status.style.display = "none";
        showToast("Đã tắt giám sát.", "info");
    }

    // Gọi API Server
    fetch('/api/webcam/supervise', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ enable: isSuperviseOn })
    })
    .catch(err => console.error(err));
}

// ============================================================
// 5. HIỆU ỨNG ĐÊM (NIGHT AMBIENCE) - Đom đóm & Sao băng
// ============================================================

let nightEffectTimer = null;

// --- HÀM KHỞI TẠO (GỌI KHI CHUYỂN SANG DARK MODE) ---
function startNightCycle() {
    if (nightEffectTimer) clearTimeout(nightEffectTimer);
    scheduleRandomNightEvent();
}

function stopNightCycle() {
    if (nightEffectTimer) clearTimeout(nightEffectTimer);
    
    // Xóa ngay các phần tử đang bay để màn hình sạch sẽ
    document.querySelectorAll('.firefly-container').forEach(e => e.remove());
    document.querySelectorAll('.meteor-shower-container').forEach(e => e.remove());
}

// --- BỘ ĐIỀU PHỐI NGẪU NHIÊN ---
function scheduleRandomNightEvent() {
    // Chỉ chạy nếu đang ở Dark Mode
    if (!document.body.classList.contains('dark-mode')) return;

    // Random thời gian nghỉ giữa các sự kiện (5s đến 15s)
    const nextTime = Math.random() * 10000 + 5000;

    nightEffectTimer = setTimeout(() => {
        // Random chọn sự kiện:
        // 0-40%: Đom đóm (Nếu không mưa)
        // 40-70%: Sao băng lẻ tẻ
        // 70-90%: Mưa sao băng (Nhiều)
        // 90-100%: Nghỉ ngơi (Không có gì)
        
        const chance = Math.random() * 100;

        if (chance < 40) {
            // Đom đóm chỉ bay khi trời tạnh ráo (Không mưa)
            if (currentWeather !== WEATHER.RAIN) { 
                spawnFireflies(); 
            }
        } 
        else if (chance < 70) {
            spawnShootingStars(1); // 1 ngôi sao lẻ loi
        }
        else if (chance < 90) {
            spawnShootingStars(Math.floor(Math.random() * 5) + 3); // Mưa sao băng (3-8 ngôi)
        }
        
        // Loop tiếp tục
        scheduleRandomNightEvent();

    }, nextTime);
}

// --- 1. HIỆU ỨNG ĐOM ĐÓM ---
function spawnFireflies() {
    let container = document.querySelector('.firefly-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'firefly-container';
        document.body.appendChild(container);
    }

    // [TĂNG SỐ LƯỢNG] Cũ: 5-12 -> Mới: 12-25 con
    const count = Math.floor(Math.random() * 14) + 12;
    
    for (let i = 0; i < count; i++) {
        const fly = document.createElement('div');
        fly.classList.add('firefly');
        
        fly.style.left = Math.random() * 100 + '%';
        fly.style.bottom = Math.random() * 35 + '%'; // Bay cao hơn một chút (tầm 35% dưới)

        // Random chuyển động bay lượn
        const moveX = (Math.random() * 250 - 125) + 'px'; // Phạm vi bay rộng hơn xíu
        const moveY = (Math.random() * 120 - 60) + 'px';
        fly.style.setProperty('--move-x', moveX);
        fly.style.setProperty('--move-y', moveY);
        
        fly.style.setProperty('--fly-duration', (Math.random() * 6 + 6) + 's'); // 6-12s
        fly.style.setProperty('--flash-duration', (Math.random() * 2.5 + 1.5) + 's'); // 1.5-4s

        container.appendChild(fly);
        setTimeout(() => { fly.remove(); }, 18000); // Tăng thời gian sống lên 18s
    }
}

// --- 2. HIỆU ỨNG SAO BĂNG ---
function spawnShootingStars(amount) {
    let container = document.querySelector('.meteor-shower-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'meteor-shower-container';
        document.body.appendChild(container);
    }

    for (let i = 0; i < amount; i++) {
        setTimeout(() => {
            const star = document.createElement('div');
            star.classList.add('shooting-star-v2');

            // 1. Tính toán vị trí xuất phát (Bên trái hoặc phía trên)
            // startX từ -10% (ngoài mép trái) đến 80% màn hình
            const startXVal = (Math.random() * 90 - 10); 
            star.style.setProperty('--start-x', startXVal + '%');

            // 2. Tính toán khoảng cách bay ngang (Luôn dương để bay sang phải)
            // Bay thêm từ 30vw đến 60vw sang phải
            const destDistVal = (Math.random() * 30 + 30);
            star.style.setProperty('--dest-dist', destDistVal + 'vw');
            
            // 3. [CHẬM LẠI] Thời gian bay: 2.5s đến 4.5s (Cũ là 1-2s)
            const durationSec = (Math.random() * 2 + 2.5);
            star.style.setProperty('--fall-duration', durationSec + 's');

            container.appendChild(star);

            // 4. Lên lịch tạo hiệu ứng LẤP LÁNH khi sao bay xong
            setTimeout(() => {
                // Ước lượng vị trí kết thúc để đặt hiệu ứng lấp lánh
                // Vị trí X cuối = X đầu + khoảng cách bay
                const endXEstimate = startXVal + destDistVal;
                // Vị trí Y cuối = khoảng 85-90% chiều cao màn hình (gần đáy)
                spawnSparkle(endXEstimate + '%', '85%');
                
                star.remove(); // Xóa sao băng
            }, durationSec * 1000 - 200); // Kích hoạt sớm 200ms trước khi sao biến mất hẳn cho mượt

        }, Math.random() * 3000); // Rải rác trong 3 giây
    }
}

// --- HÀM PHỤ TRỢ: TẠO ĐỐM SÁNG LẤP LÁNH ---
function spawnSparkle(x, y) {
    const sparkle = document.createElement('div');
    sparkle.className = 'star-sparkle';
    sparkle.style.left = x;
    sparkle.style.top = y;
    document.body.appendChild(sparkle);

    // Tự xóa sau khi animation kết thúc (0.8s)
    setTimeout(() => sparkle.remove(), 800);
}

// Bắt đầu chu trình sau 2 giây
setTimeout(scheduleNextWeather, 2000);