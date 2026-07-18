"""Generate SYNTHETIC demo assets — no real PII, ever.

  demo-data/sample-foia.png     : a records doc with planted PII for REDACT
  demo-data/leaked-creds.txt     : a planted AWS key for SECURE -> Redactor bridge
  demo-data/messy/*              : ~14 junk-named files for ORGANIZE
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DD = HERE / "demo-data"
(DD / "messy").mkdir(parents=True, exist_ok=True)


def font(sz):
    for f in ["arial.ttf", "DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"]:
        try:
            return ImageFont.truetype(f, sz)
        except Exception:
            continue
    return ImageFont.load_default()


def sample_doc():
    W, H = 1000, 1294
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 70], fill=(20, 40, 60))
    d.text((40, 24), "COUNTY SHERIFF — INCIDENT REPORT  (SYNTHETIC / DEMO)", font=font(22), fill="white")
    lines = [
        ("Case No: 2026-04471", 130),
        ("Reporting Officer: Jane A. Doe", 175),
        ("Complainant: Robert M. Sanchez", 210),
        ("SSN: 431-88-2190", 245),
        ("Date of Birth: 04/12/1979", 280),
        ("Home Address: 22 Ivy Lane, Irvine CA 92602", 315),
        ("Phone: (949) 555-0173", 350),
        ("Email: r.sanchez@example.com", 385),
        ("Credit Card on file: 4111 1111 1111 1111", 420),
        ("", 455),
        ("NARRATIVE:", 490),
        ("On 03/14/2026 the complainant reported a burglary at the above", 525),
        ("address. The complainant, a 47-year-old male with a documented", 555),
        ("heart condition, stated that several items were taken. Officer", 585),
        ("Doe responded and interviewed the only left-handed pitcher on", 615),
        ("the 1998 county team, who now lives two houses down.", 645),
        ("", 675),
        ("Signature on file:", 720),
    ]
    for t, y in lines:
        d.text((45, y), t, font=font(21), fill=(15, 15, 15))
    # a fake "signature"
    d.line([(230, 745), (260, 725), (290, 755), (330, 720), (380, 750)], fill=(20, 20, 120), width=3)
    d.text((45, 900), "This document contains information exempt under FOIA", font=font(16), fill=(120, 120, 120))
    d.text((45, 924), "Exemptions 6 and 7(C) (personal privacy).", font=font(16), fill=(120, 120, 120))
    img.save(DD / "sample-foia.png")
    print("wrote", DD / "sample-foia.png")


def leaked_creds():
    (DD / "leaked-creds.txt").write_text(
        "# personal notes - do not commit (SYNTHETIC DEMO)\n"
        "aws_access_key_id = AKIAIOSFODNN7EXAMPLE\n"
        "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n"
        "db_password = 'hunter2demo'\n", encoding="utf-8")
    print("wrote", DD / "leaked-creds.txt")


def messy():
    files = {
        "IMG_20260312_final FINAL v2.txt": "Invoice #8841 from Acme Roofing. Amount due $4,200. Terms net 30.",
        "scan0007.txt": "EMPLOYMENT AGREEMENT between Cenergy Power and contractor. Confidential.",
        "Document (3).txt": "Q1 2026 quarterly report. Revenue up 18%. Prepared for the board.",
        "asdf.txt": "Grocery list: milk, eggs, coffee, batteries.",
        "untitled.txt": "Resume - John Smith - Software Engineer - 8 years experience.",
        "receipt.txt": "Receipt Whole Foods 03/14/2026 total $63.20 card ****1111.",
        "notes2.txt": "Meeting notes with Bill re: solar siting hearing prep. Action items.",
        "photo backup.txt": "[binary photo placeholder] beach trip july",
        "New Text Document.txt": "Health insurance EOB - claim processed - patient responsibility $40.",
        "copy of copy final.txt": "Lease agreement 22 Ivy Lane term 12 months rent $2400/mo.",
        "xyz123.txt": "Bank statement March 2026 balance $12,405.77 account ****8890.",
        "todo.txt": "TODO: file taxes, renew registration, call dentist.",
        "presentation draft.txt": "Slide deck outline: problem, solution, market, ask.",
        "misc.txt": "Warranty card for refrigerator model RF28. Keep for 5 years.",
    }
    for name, body in files.items():
        (DD / "messy" / name).write_text(body, encoding="utf-8")
    print(f"wrote {len(files)} files to", DD / "messy")


if __name__ == "__main__":
    sample_doc()
    leaked_creds()
    messy()
    print("\nDemo data ready in", DD)
