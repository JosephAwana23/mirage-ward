rule Mirage_AutoVaccine_401addec {
    meta:
        description = "Detects visual spoofing artifacts mimicking Microsoft OAuth or Windows Security dialogs via Python"
        author = "Blue Team YARA Engineer"
        date = "2026-10-16"
        attacker_ip = "127.0.0.1"
        captured_command = "[VISUAL-SPOOF] python.exe rendered 'Microsoft Online OAuth Login / Windows Security dialog (https://login.microsoftonline.com)'"
        severity = "high"

    strings:
        $login_url = "login.microsoftonline.com" ascii wide nocase
        $str_ms = "Microsoft Online" ascii wide nocase
        $str_winsec = "Windows Security" ascii wide nocase
        $str_oauth = "OAuth" ascii wide nocase
        $py_exe = "python.exe" ascii wide nocase
        $py_gui1 = "tkinter" ascii wide nocase
        $py_gui2 = "PyQt5" ascii wide nocase
        $py_gui3 = "PySide" ascii wide nocase
        $py_gui4 = "webview" ascii wide nocase

    condition:
        $login_url and (1 of ($str_*)) and ($py_exe or 1 of ($py_gui*))
}
