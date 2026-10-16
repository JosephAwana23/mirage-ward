rule Mirage_AutoVaccine_79d8cbe2
{
    meta:
        author = "Blue Team"
        description = "Detects visual spoofing artifacts mimicking Microsoft Windows Security and login.microsoftonline.com OAuth dialogs via Python"
        date = "2026-10-16"
        attacker_ip = "127.0.0.1"
        captured_command = "[VISUAL-SPOOF] python.exe rendered 'Microsoft Windows Security / login.microsoftonline.com OAuth dialog'"

    strings:
        $spoof_host = "login.microsoftonline.com" ascii wide nocase
        $spoof_title = "Microsoft Windows Security" ascii wide nocase
        $spoof_oauth = "OAuth" ascii wide nocase
        $py_indicator1 = "python.exe" ascii wide nocase
        $py_indicator2 = "tkinter" ascii wide nocase
        $py_indicator3 = "PyQt" ascii wide nocase
        $py_indicator4 = "webview" ascii wide nocase

    condition:
        $spoof_host and ($spoof_title or $spoof_oauth) and (1 of ($py_indicator*))
}
