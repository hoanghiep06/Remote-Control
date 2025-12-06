# Remote Control Ultimate 🚀

Dự án điều khiển máy tính từ xa sử dụng mô hình Hybrid mạnh mẽ:
- **Server:** C# (Windows Forms) - Quản lý hệ thống, Webcam, Keylog.
- **Backend:** C++ (DLL) - Xử lý socket tốc độ cao, stream video.
- **Frontend:** Python (CustomTkinter) - Giao diện hiện đại, dễ sử dụng.

## Tính năng
- Xem danh sách Apps / Process.
- Kill / Start Process.
- Stream màn hình (Full HD).
- Xem và ghi hình Webcam.
- Keylogger.
- Tắt máy từ xa.

## Cách chạy
1. **Server:** Vào folder `Server_CSharp`, biên dịch và chạy `server.exe` (Admin).
2. **Client:** - Vào folder `Client`, biên dịch ".cpp" ra `client.dll`.
   - Chạy `python main.py`.