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
    const statusText = document.getElementById('statusDesc'); // Hoặc id text nhỏ ở header
    
    // 1. Báo UI đang chuyển
    container.innerHTML = '<div style="text-align:center; margin-top:50px;">⏳ Đang chuyển chế độ...</div>';
    
    // 2. Gọi API set_mode (Python sẽ tự Stop cái cũ -> Wait -> Start cái mới)
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
            <div style="text-align:center; color:#6ee7b7; margin-top:10px;">🔴 Đang xem trực tiếp</div>
        `;
    } 
    else if (mode === 'apps') {
        container.innerHTML = `
            <h3 style="margin:0 0 10px 0; color:#86efac;">Danh sách Apps</h3>
            <div style="overflow-y:auto; flex:1;">
                <table class="nature-table">
                    <thead><tr><th>ID</th><th>Tên</th><th>Thread</th></tr></thead>
                    <tbody id="appListBody"><tr><td colspan="3">Đang tải...</td></tr></tbody>
                </table>
            </div>
        `;
        // Đợi 1.5s để Python kịp tạo file apps.txt rồi mới fetch
        setTimeout(() => {
            fetch('/api/list_apps').then(r=>r.json()).then(apps => {
                const tbody = document.getElementById('appListBody');
                tbody.innerHTML = "";
                if(apps.length==0) tbody.innerHTML="<tr><td colspan='3'>Trống</td></tr>";
                apps.forEach(a => {
                    tbody.innerHTML += `<tr><td>${a.id}</td><td>${a.name}</td><td>${a.threads}</td></tr>`;
                });
            });
        }, 1500);
    }
    else {
        // Các mode khác chưa code hiển thị thì hiện tạm dòng này
        container.innerHTML = `
            <div style="text-align:center; margin-top:50px;">
                <h3>Chế độ: ${mode.toUpperCase()}</h3>
                <p>Đã gửi lệnh kích hoạt. Server đang xử lý...</p>
            </div>`;
    }
}
