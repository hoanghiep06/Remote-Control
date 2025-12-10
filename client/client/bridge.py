import socket
import threading
import base64
import hashlib
import struct
import time

# --- CẤU HÌNH ---
EXE_IP = '127.0.0.1'
EXE_PORT = 5656     # Cổng của server.exe
WEB_PORT = 8888     # Cổng cho Web kết nối

def create_handshake_response(key):
    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    accept_key = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
    return (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept_key}\r\n"
        "\r\n"
    ).encode()

def send_websocket_message(client_socket, message):
    # Đóng gói tin nhắn Text frame gửi về Web
    msg_bytes = message.encode('utf-8')
    header = bytearray()
    header.append(0x81) # Fin + Text Opcode
    length = len(msg_bytes)
    
    if length <= 125:
        header.append(length)
    elif length <= 65535:
        header.append(126)
        header.extend(struct.pack("!H", length))
    else:
        header.append(127)
        header.extend(struct.pack("!Q", length))
        
    client_socket.sendall(header + msg_bytes)

def decode_websocket_frame(data):
    # Giải mã tin nhắn từ Web gửi lên (Masked)
    if len(data) < 2: return None
    
    second_byte = data[1]
    is_masked = second_byte & 128
    payload_len = second_byte & 127
    
    start_idx = 2
    if payload_len == 126: start_idx = 4
    elif payload_len == 127: start_idx = 10
    
    if is_masked:
        mask = data[start_idx:start_idx+4]
        start_idx += 4
        encrypted_data = data[start_idx:]
        decoded = bytearray()
        for i in range(len(encrypted_data)):
            decoded.append(encrypted_data[i] ^ mask[i % 4])
        return decoded.decode('utf-8', errors='ignore')
    return None

def handle_web_client(web_conn):
    print("-> Web đã kết nối. Đang bắt tay...")
    try:
        # 1. Bắt tay WebSocket thủ công
        req = web_conn.recv(1024).decode()
        key_start = req.find("Sec-WebSocket-Key: ") + 19
        key_end = req.find("\r\n", key_start)
        key = req[key_start:key_end]
        
        web_conn.sendall(create_handshake_response(key))
        print("-> Bắt tay WebSocket thành công!")

        # 2. Kết nối tới EXE
        exe_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        exe_sock.connect((EXE_IP, EXE_PORT))
        print("-> Đã nối thông với Server.exe")
        
        send_websocket_message(web_conn, "Connected to EXE via SimpleBridge")

        # 3. Chạy luồng đọc từ EXE gửi về Web
        def listen_exe():
            while True:
                try:
                    data = exe_sock.recv(1024)
                    if not data: break
                    send_websocket_message(web_conn, data.decode())
                except: break
            web_conn.close()

        threading.Thread(target=listen_exe, daemon=True).start()

        # 4. Luồng chính: Đọc từ Web gửi sang EXE
        while True:
            data = web_conn.recv(1024) # Nhận raw frame
            if not data: break
            
            msg = decode_websocket_frame(data)
            if msg:
                print(f"Web gửi: {msg}")
                exe_sock.sendall(msg.encode())

    except Exception as e:
        print(f"Lỗi xử lý: {e}")
    finally:
        web_conn.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", WEB_PORT))
    server.listen(1)
    print(f"SIMPLE BRIDGE đang chạy tại ws://127.0.0.1:{WEB_PORT}")
    print(f"Đang chờ Web kết nối...")
    
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_web_client, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    main()