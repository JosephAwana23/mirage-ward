# 🛡️ Project Mirage-Ward: Autonomous Multimodal Cyber Defense & Deception Suite

Project Mirage-Ward is an enterprise-grade, local EDR (Endpoint Detection and Response) and deception platform built from scratch in Python. It bridges the gap between active host protection, multimodal AI threat analysis (Powered by Google Gemini), active directory honeypots, and automated YARA rule forging.

---

## 🚀 Key Architectural Modules

1. **`mirage_dashboard.py` (The Command Center)**
   * A centralized Tkinter "Single Pane of Glass" SOC dashboard.
   * Features real-time host telemetry (CPU/RAM tracking), live forensic incident streams, an interactive **MITRE ATT&CK Matrix Heatmap**, and a **Distributed Peer Immunity Mesh Network** visualization.
   * Includes one-click encrypted forensic `.zip` bundle export and automated **Executive PDF Incident Report** generation.

2. **`visual_aegis.py` (Sub-Second Anti-Scam Shield)**
   * Inspects foreground window telemetry and process metadata every 0.3 seconds.
   * Flags Process-to-Pixel Impersonation (e.g., untrusted scripts rendering fake Microsoft/Windows Security login popups).
   * Automatically destroys window handles (`WM_CLOSE`) and terminates rogue PIDs in under **0.3 seconds** before credential entry can occur.

3. **`trapdoor_shunt.py` (C2 Guard & Session Shunt)**
   * Traps unauthorized command-and-control network sockets and redirects suspicious attacker sessions into a local cognitive sandbox.

4. **`mirage_weaver.py` (AI Deception Engine)**
   * Uses Gemini to generate dynamic deception responses and honey-token tripwires that monitor for unauthorized file access.

5. **`vaccine_forge.py` (Auto-Vaccine Forge)**
   * Automatically compiles YARA rules and cryptographically signed SHA-256 immunity manifests the moment a canary or threat telemetry event is triggered.

6. **`ldap_honeypot.py` (Active Directory LDAP Honey-Schema)**
   * Listens on internal LDAP ports to intercept attacker reconnaissance and lateral movement tools (like BloodHound), poisoning enumeration queries with deceptive high-privilege honey-accounts.

---

## 🛠️ Tech Stack
* **Language:** Python (`asyncio`, `tkinter`, `psutil`, `subprocess`)
* **AI Integration:** Google Gemini SDK (`gemini-3.8-flash` for multimodal vision inspection and SOC threat briefings)
* **Reporting:** ReportLab (for programmatic executive PDF generation)
* **Security Standards:** MITRE ATT&CK Framework, YARA Rules, Win32 API Interception (`ctypes`)

---
*Built with passion for defensive cybersecurity and autonomous AI collaboration.*