rule Mirage_AutoVaccine_5834fb31 {
    meta:
        description = "Detects execution of command accessing decoy credential file"
        attacker_ip = "127.0.0.1"
        captured_command = "cat network_passwords.txt"
        timestamp = "2026-10-16T14:46:22.554014+00:00"
        author = "Blue Team"
    strings:
        $cmd1 = "cat network_passwords.txt" ascii wide
        $file1 = "network_passwords.txt" ascii wide
    condition:
        any of them
}
