rule Mirage_AutoVaccine_8cd15f13 {
    meta:
        author = "Blue Team"
        description = "Detects access attempt to aws_prod_keys.env captured by deception honeypot"
        attacker_ip = "127.0.0.1"
        timestamp = "2026-10-16T14:46:11.105764+00:00"
    strings:
        $cmd = "cat aws_prod_keys.env" ascii wide
        $target = "aws_prod_keys.env" ascii wide
    condition:
        $cmd or $target
}
