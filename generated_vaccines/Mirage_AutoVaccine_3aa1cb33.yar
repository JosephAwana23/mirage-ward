rule Mirage_AutoVaccine_3aa1cb33
{
    meta:
        author = "Blue Team"
        description = "Detects visual spoofing artifacts mimicking Windows Security and Microsoft Online OAuth login prompts"
        attacker_ip = "127.0.0.1"
        captured_timestamp = "2026-10-16T15:57:53.416484+00:00"
        threat_type = "Credential Harvesting / UI Spoofing"

    strings:
        $url = "https://login.microsoftonline.com" ascii wide nocase
        $spoof_title1 = "Windows Security" ascii wide
        $spoof_title2 = "Microsoft Online OAuth Login" ascii wide nocase
        $py_indicator1 = "tkinter" ascii wide nocase
        $py_indicator2 = "PyQt" ascii wide nocase
        $py_indicator3 = "webview" ascii wide nocase

    condition:
        ($url and ($spoof_title1 or $spoof_title2)) or
        ($spoof_title2 and (any of ($py_indicator*)))
}
