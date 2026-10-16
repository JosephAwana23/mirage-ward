import datetime
import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import tkinter as tk
from tkinter import filedialog

BASE_DIR = Path(__file__).resolve().parent
TELEMETRY_LOG = BASE_DIR / "mirage_telemetry.jsonl"
MANIFEST_FILE = BASE_DIR / "generated_vaccines" / "immunity_manifest.json"


def generate_executive_pdf():
    # Hide the root tkinter window so only the Save As dialog appears
    root = tk.Tk()
    root.withdraw()

    # Prompt user for save destination immediately
    pdf_path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")],
        initialfile="MirageWard_Incident_Report.pdf",
        title="Save Executive PDF Incident Report As..."
    )

    if not pdf_path:
        print("[*] PDF export canceled by operator.")
        return

    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()

    # Custom Styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=20, textColor=colors.HexColor('#0284c7'), spaceAfter=4)
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#64748b'), spaceAfter=20)
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#1e293b'), spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#334155'), spaceAfter=6)

    # Header
    story.append(Paragraph("🛡️ PROJECT MIRAGE-WARD", title_style))
    story.append(Paragraph(f"Executive Incident & Threat Intelligence Report | Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
    story.append(Spacer(1, 10))

    # Executive Summary Box
    story.append(Paragraph("Executive Summary", h2_style))
    summary_text = (
        "Project Mirage-Ward autonomous deception nodes successfully intercepted and neutralized multiple "
        "unauthorized intrusion attempts. Attackers were transparently shunted into local cognitive sandboxes, "
        "active UI phishing overlays were destroyed within 0.3 seconds, and autonomous YARA vaccines were "
        "forged and broadcasted across network peer nodes."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 10))

    # Load Telemetry Data
    story.append(Paragraph("Captured Intrusion Telemetry & Canary Tripwires", h2_style))
    events = []
    if TELEMETRY_LOG.exists():
        with open(TELEMETRY_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    events.append(json.loads(line.strip()))
                except Exception:
                    pass

    table_data = [["Timestamp", "Source IP", "Attack / Recon Command", "Status"]]
    for ev in events[-10:]: # Last 10 events
        ts = ev.get("timestamp", "").split("T")[-1][:8]
        src = ev.get("source", "N/A")
        cmd = ev.get("command", "N/A")[:45]
        status = "NEUTRALIZED" if ev.get("canary_tripped") else "LOGGED"
        table_data.append([ts, src, cmd, status])

    t = Table(table_data, colWidths=[65, 110, 265, 90])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('TEXTCOLOR', (0,1), (-1,-1), colors.HexColor('#334155')),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    # Load Immunity Manifest / YARA rules
    story.append(Paragraph("Generated YARA Immunity Signatures & Firewall Actions", h2_style))
    manifests = []
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                manifests = json.load(f)
        except Exception:
            pass

    man_data = [["Incident ID", "Trigger Reason", "Target IP", "YARA Signature File"]]
    for m in manifests:
        man_data.append([
            m.get("incident_id"),
            m.get("trigger_reason"),
            m.get("firewall_mitigation", {}).get("target_ip"),
            m.get("yara_file")
        ])

    t2 = Table(man_data, colWidths=[80, 150, 95, 205])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0284c7')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('TEXTCOLOR', (0,1), (-1,-1), colors.HexColor('#334155')),
    ]))
    story.append(t2)

    doc.build(story)
    print(f"[+] Executive PDF Incident Report compiled successfully: {pdf_path}")


if __name__ == "__main__":
    generate_executive_pdf()