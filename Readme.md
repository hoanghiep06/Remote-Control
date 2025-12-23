# 🌐 REMOTE CONTROL SYSTEM

## Next-Generation Remote Administration & Monitoring Ecosystem

---

## 📖 Tổng quan (Executive Summary)

**Remote Control** (tên mã: **Khu Vườn IoT**) là một hệ thống quản trị và giám sát từ xa đa nền tảng, được xây dựng trên kiến trúc **Hybrid Multi-Language** nhằm tối ưu hiệu năng và khả năng mở rộng. Dự án kết nối truy cập hệ thống mức thấp (**Low-level System Access**) với trải nghiệm người dùng hiện đại (**Modern UX**) thông qua giao diện Web trực quan.

Hệ thống cho phép **Administrator** kiểm soát, giám sát tài nguyên và thao tác dữ liệu trên **Target Machine** theo thời gian thực (**Real-time**) thông qua giao thức **TCP/IP** được tối ưu hóa độ trễ.

[![Google Drive](https://img.shields.io/badge/Google%20Drive-Tổng%20Hợp%20Đồ%20Án-4285F4?style=for-the-badge&logo=googledrive&logoColor=white)](https://drive.google.com/drive/folders/19uJcW1mtf-5gq_rPJk1UURX8nxuQ1P8z?usp=sharing)
---

## 🏗️ Kiến trúc Hệ thống (System Architecture)

Dự án áp dụng mô hình **Client–Server phức hợp**, kết hợp 4 ngôn ngữ lập trình để phát huy tối đa thế mạnh của từng phân hệ.

### 1. Target Agent (Server-side | C# .NET)

* Chạy dưới dạng **Background Service** trên máy đích.
* Tương tác trực tiếp với **Windows API** (*User32, Kernel32, GDI+*).
* Thu thập dữ liệu hệ thống và thực thi lệnh điều khiển.
* Hỗ trợ **Multi-threading** để các tác vụ như *Keylogger, Streaming, Remote Shell* hoạt động song song, không gây treo hệ thống.

### 2. Native Middleware (Bridge | C++)

* Đóng vai trò **High-performance Bridge** giữa C# và Python.
* Quản lý **TCP Socket**, đóng gói/giải mã dữ liệu (*Packet Marshaling*).
* Tối ưu **Buffer Management** nhằm truyền tải hình ảnh/video mượt mà, độ trễ thấp.

### 3. Core Controller (Client-side | Python)

* Giao tiếp với Middleware C++ thông qua **ctypes**.
* Vận hành **Web Server (HTTP / WebSocket)**.
* Xử lý logic nghiệp vụ: phân tích log, xử lý ảnh (*OpenCV*), quản lý tập tin.

### 4. Interactive Dashboard (Frontend | HTML / CSS / JavaScript)

* Giao diện **“IoT Garden”** mang tính trực quan cao.
* Kết nối **AJAX / Fetch API / WebSocket** để cập nhật dữ liệu thời gian thực.
* Hiệu ứng động tăng trải nghiệm người dùng.

---

## 🚀 Tính năng Chính (Key Features)

### 👁️ 1. Giám sát Trực quan (Visual Surveillance)

* **Webcam Streaming**: Truyền video trực tiếp với độ trễ thấp, hỗ trợ *Recording* và *Snapshot*.
* **Desktop Monitoring**: Theo dõi màn hình máy đích, sử dụng nén JPEG thông minh để cân bằng chất lượng và băng thông.

### ⚡ 2. Kiểm soát Hệ thống (System Control)

* **Process Manager**: Liệt kê, giám sát và kết thúc (*Kill*) tiến trình.
* **Power Management**: Tắt máy (*Shutdown*) và khởi động lại (*Restart*) từ xa.
* **Meteor Strike Mode**: Hiệu ứng điện ảnh khi thực hiện lệnh tắt hệ thống.

### 📂 3. Quản trị Dữ liệu (Data Administration)

* **File Explorer**: Duyệt ổ đĩa, thư mục; tải file từ máy đích về máy quản trị.
* **Keystroke Telemetry (Keylogger)**:

  * Ghi nhận toàn bộ phím bấm.
  * Thuật toán làm sạch *Backspace*.
  * Hỗ trợ hiển thị tiếng Việt (*Telex / VNI*).
* **Notification History**: Trích xuất lịch sử thông báo từ Windows (Zalo, Messenger, System).

### 📊 4. Theo dõi Hiệu năng (Performance Monitoring)

* Dashboard hiển thị **CPU / RAM / Disk Usage** theo thời gian thực.
* Cảnh báo sớm các bất thường hệ thống.

---

## 🛠️ Cài đặt & Triển khai (Installation)

### 🔧 Yêu cầu Hệ thống

* **Target Machine**: Windows 10 / 11, .NET Framework 4.5+
* **Admin Machine**: Python 3.8+, Trình biên dịch C++ (*MinGW / MSVC*)

---

### 🖥️ Bước 1: Build Target Agent

1. Mở project `server.cs` bằng **Visual Studio**.
2. Build tạo file `server.exe`.
3. Chạy `server.exe` trên máy đích.
4. Đảm bảo **Port 5656** được mở.

---

### 💻 Bước 2: Build Controller

#### Biên dịch Middleware C++

```bash
g++ -shared -o client.dll ClientLib.cpp -lws2_32
```

#### Cài đặt thư viện Python

```bash
pip install opencv-python numpy
```

#### Khởi động Web Server

```bash
python webapp.py
```

---

### 🌐 Bước 3: Vận hành Hệ thống

* Truy cập: `http://localhost:8000`
* Nhập **IP** và **Port** của Target Machine.
* Mặc định khi test local:

  * IP: `127.0.0.1`
  * Port: `5656`

---

## 🎨 Giao diện Người dùng (User Interface)

Giao diện được thiết kế theo phong cách **Glassmorphism**, kết hợp hệ sinh thái ảo sinh động:

* **Dynamic Weather**: Mưa, tuyết, nắng thay đổi ngẫu nhiên.
* **Day / Night Cycle**: Chế độ sáng – tối bảo vệ mắt.
* **Interactive Effects**: Sấm chớp, hộp quà rơi, rung chấn màn hình.

---

## 📌 Ghi chú

* Dự án mang tính **nghiên cứu – học thuật**.
* Không khuyến khích sử dụng cho mục đích xâm phạm quyền riêng tư.

---

**© Remote Control – Khu Vườn IoT**
