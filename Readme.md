🌐 REMOTE CONTROL SYSTEM
Next-Generation Remote Administration & Monitoring Ecosystem
📖 Tổng quan (Executive Summary)
Nexus Remote Control (tên mã: Khu Vườn IoT) là một hệ thống quản trị và giám sát từ xa đa nền tảng, được xây dựng dựa trên kiến trúc Hybrid Multi-Language tiên tiến. Dự án phá vỡ rào cản giữa việc truy cập hệ thống mức thấp (Low-level System Access) và trải nghiệm người dùng hiện đại (Modern UX) thông qua giao diện Web trực quan.

Hệ thống cho phép người quản trị (Administrator) thực hiện các tác vụ kiểm soát, theo dõi tài nguyên và thao tác tập tin trên máy trạm (Target Machine) theo thời gian thực (Real-time) thông qua giao thức TCP/IP được tối ưu hóa độ trễ.

🏗️ Kiến trúc Hệ thống (System Architecture)
Dự án sử dụng mô hình Client-Server phức hợp, kết hợp sức mạnh của 4 ngôn ngữ lập trình để tối ưu hóa hiệu năng từng phân hệ:

Target Agent (Server-side | C# .NET):

Hoạt động như một Service ngầm trên máy nạn nhân.

Chịu trách nhiệm tương tác sâu với Windows API (User32, Kernel32, GDI+) để thu thập dữ liệu và thực thi lệnh.

Xử lý đa luồng (Multi-threading) để đảm bảo các tác vụ (Keylog, Stream, Shell) chạy song song không gây treo máy.

Native Middleware (Bridge | C++):

Đóng vai trò là lớp trung gian hiệu năng cao (High-performance Bridge).

Quản lý kết nối Socket TCP, đóng gói/giải mã gói tin (Packet Marshaling) và tối ưu hóa bộ đệm (Buffer management) để truyền tải hình ảnh/video mượt mà.

Core Controller (Client-side | Python):

Sử dụng thư viện ctypes để giao tiếp trực tiếp với Middleware C++.

Vận hành Web Server (HTTP/WebSocket) để phục vụ giao diện điều khiển.

Xử lý logic nghiệp vụ: Phân tích log, xử lý ảnh (OpenCV), quản lý file.

Interactive Dashboard (Frontend | HTML/JS/CSS):

Giao diện "IoT Garden" với hiệu ứng thời tiết động (Mưa, Tuyết, Ngày/Đêm).

Sử dụng AJAX/Fetch API và WebSocket để cập nhật dữ liệu thời gian thực (Real-time Telemetry).

🚀 Tính năng Đột phá (Key Features)
1. 👁️ Giám sát Trực quan (Visual Surveillance)
Webcam Streaming: Truyền hình ảnh trực tiếp từ Camera với độ trễ thấp. Hỗ trợ ghi hình (Recording) và chụp ảnh nhanh (Snapshot).

Desktop Monitoring: Theo dõi toàn bộ hoạt động màn hình của máy trạm. Thuật toán nén ảnh JPEG thông minh giúp cân bằng giữa chất lượng và băng thông.

2. ⚡ Kiểm soát Hệ thống (System Control)
Process Manager: Liệt kê, theo dõi và tiêu diệt (Kill) các tiến trình đang chạy. Tự động nhận diện ứng dụng rác.

Power Management: Thực hiện lệnh Tắt máy (Shutdown) hoặc Khởi động lại (Restart) từ xa.

Hiệu ứng "Meteor Strike": Giao diện kích hoạt hiệu ứng thiên thạch rơi đậm chất điện ảnh khi thực hiện lệnh tắt máy chủ.

3. 📂 Quản trị Dữ liệu (Data Administration)
File Explorer: Duyệt toàn bộ ổ đĩa, thư mục. Hỗ trợ tải file (Download) từ máy trạm về máy quản trị với tốc độ cao.

Keystroke Telemetry (Keylogger): Ghi lại toàn bộ lịch sử phím bấm.

Cải tiến: Thuật toán xử lý ngôn ngữ tự nhiên giúp "làm sạch" các phím xóa (Backspace) và hiển thị chính xác tiếng Việt (Telex/VNI).

Notification History: Trích xuất và đọc lịch sử thông báo (Zalo, Messenger, System) từ cơ sở dữ liệu hệ thống Windows.

4. 📊 Theo dõi Hiệu năng (Performance Monitoring)
Dashboard hiển thị biểu đồ trực quan về mức độ tiêu thụ CPU, RAM, và Disk Usage theo thời gian thực.

Cảnh báo sớm các bất thường của hệ thống.

🛠️ Cài đặt & Triển khai (Installation)
Yêu cầu hệ thống
Target Machine: Windows 10/11 (.NET Framework 4.5+).

Admin Machine: Python 3.8+, C++ Compiler (MinGW/MSVC).

Bước 1: Build Target (Máy bị điều khiển)
Mở project server.cs bằng Visual Studio.

Build ra file server.exe.

Chạy server.exe trên máy đích. (Đảm bảo Port 5656 được mở).

Bước 2: Build Controller (Máy điều khiển)
Biên dịch file thư viện liên kết động:

Bash

g++ -shared -o client.dll ClientLib.cpp -lws2_32
Cài đặt thư viện Python cần thiết:

Bash

pip install opencv-python numpy
Khởi động Web Server:

Bash

python webapp.py
Bước 3: Vận hành
Truy cập trình duyệt tại địa chỉ: http://localhost:8000.

Nhập IP của máy Target và bấm "Kết nối ngay".
Thông thường, mặc định 127.0.0.1 và 5656 là IP và port mặc định khi thao tác trên chính máy tính cá nhân

🎨 Giao diện Người dùng (User Interface)
Giao diện được thiết kế theo phong cách Glassmorphism hiện đại, tích hợp hệ thống môi trường ảo:

Dynamic Weather: Hệ thống tự động thay đổi thời tiết (Mưa, Tuyết rơi, Nắng) ngẫu nhiên.

Day/Night Cycle: Chế độ Sáng/Tối giúp bảo vệ mắt và tăng tính thẩm mỹ.

Interactive Elements: Các hiệu ứng tương tác như hộp quà rơi, sấm chớp, và rung chấn màn hình.
