# =============================================================
# app.py — FormFill Pro  (All Points Capital Group PDF)
# Backend: Flask + PyMuPDF (fitz)
# =============================================================

import os
import uuid
import logging
from datetime import date
from pathlib import Path

import fitz                          # PyMuPDF
from flask import (
    Flask, render_template, request,
    send_file, jsonify, send_from_directory
)

# ── App setup ─────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

BASE_DIR = Path(__file__).parent
PDF_DIR  = BASE_DIR / "pdf"
GEN_DIR  = Path("/tmp/generated")
TEMPLATE = PDF_DIR  / "template.pdf"

GEN_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# =============================================================
# FIELD MAP
# Keys (left)  = exact AcroForm widget names inside template.pdf
# Values (right)= logical slot names used in the fill logic below
# =============================================================
WIDGET_SLOTS = {
    "TEXT_WIDGET_01JSMJEAM26NKH4WDX8CYK5B1T":                                                   "BUSINESS_LEGAL_NAME",
    "TEXT_WIDGET_01JSMJEAM26NKH4WDX8CYK5B1T copy":                                              "TYPE_OF_BUSINESS_ENTITY",
    "TEXT_WIDGET_01JSMJEAM26NKH4WDX8CYK5B1T copy copy":                                         "INDUSTRY_TYPE",
    "TEXT_WIDGET_01JSMJEAM26NKH4WDX8CYK5B1T copy copy copy copy":                               "STATE_OF_INCORPORATION",   # same as STATE
    "TEXT_WIDGET_01JSMJEAM26NKH4WDX8CYK5B1T copy copy copy copy copy":                          "BUSINESS_STREET_ADDRESS",
    "TEXT_WIDGET_01JSMJEAM26NKH4WDX8CYK5B1T copy copy copy copy copy copy":                     "CITY",                     # business city
    "TEXT_WIDGET_01JSMJEAM26NKH4WDX8CYK5B1T copy copy copy copy copy copy copy":                "STATE",                    # business state
    "TEXT_WIDGET_01JSMJEAM26NKH4WDX8CYK5B1T copy copy copy copy copy copy copy copy":           "ZIP_CODE",                 # business zip
    "TEXT_WIDGET_01JSMJEAM26NKH4WDX8CYK5B1T copy copy copy copy copy copy copy copy copy":      "BUSINESS_FEDERAL_TAX_ID",
    "TEXT_WIDGET_01JSMJEAM26NKH4WDX8CYK5B1T copy copy copy copy copy copy copy copy copy copy": "BUSINESS_START_DATE",
    "TEXT_WIDGET_01JSMM9C7QZER9C11GE3BHK4KY":                                                   "FIRST_NAME",
    "TEXT_WIDGET_01JSMM9H64ZWPAQKGTFX9VFMYY":                                                   "LAST_NAME",
    "TEXT_WIDGET_01JSMM9TD36ZSDGZ56CC3TMC9T":                                                   "DOB",
    "TEXT_WIDGET_01JSMMA0G8YT2T8DTDDW9XWEN2":                                                   "HOME_STREET_ADDRESS",      # same as business address
    "TEXT_WIDGET_01JSMMA56T0XWSFFKTJS7YKGZE":                                                   "CITY_OWNER",               # owner city  = CITY
    "TEXT_WIDGET_01JSMMAJN9BAKYN7T6T1QNNQJM":                                                   "STATE_OWNER",              # owner state = STATE
    "TEXT_WIDGET_01JSMMARBXEGFN1F847RD9JMH9":                                                   "ZIP_OWNER",                # owner zip   = ZIP_CODE
    "TEXT_WIDGET_01JSMMAW5QDGF7HMZB7NRRRHW0":                                                   "SOCIAL_SECURITY",
    "TEXT_WIDGET_01JSMMB81AD3YW0A3HBASQX5VH":                                                   "OWNER_NAME_PRINT",         # full name #1
    "TEXT_WIDGET_01JSMMBFH54ZKR0AHK2HE7SVM7":                                                   "DATE_SIGNED",              # today's date
    "TEXT_WIDGET_01JSMMCAG2A0FRY0BG598GAMS5":                                                   "OWNER_SIGNATURE_FIELD",    # full name #2
}

# =============================================================
# INPUT LABEL → SLOT mapping
# Keys = what the user types in the textarea (lower-cased)
# =============================================================
LABEL_TO_SLOT = {
    "business legal name"      : "BUSINESS_LEGAL_NAME",
    "type of business entity"  : "TYPE_OF_BUSINESS_ENTITY",
    "business street address"  : "BUSINESS_STREET_ADDRESS",
    "city"                     : "CITY",
    "state"                    : "STATE",
    "zip code"                 : "ZIP_CODE",
    "business federal tax id #": "BUSINESS_FEDERAL_TAX_ID",
    "business start date"      : "BUSINESS_START_DATE",
    "owner full name"          : "OWNER_FULL_NAME",       # split into first/last
    "dob"                      : "DOB",
    "social security #"        : "SOCIAL_SECURITY",
    "industry type"            : "INDUSTRY_TYPE",
}


# ── Parse textarea input ──────────────────────────────────────
def parse_input(raw: str) -> dict:
    """Return {slot: value} from the pasted text block."""
    result = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        label, _, value = line.partition(":")
        slot = LABEL_TO_SLOT.get(label.strip().lower())
        if slot:
            result[slot] = value.strip()
    return result


# ── Build the final widget→value dict ────────────────────────
def build_widget_values(slots: dict) -> dict:
    """
    Expand slot values into every widget that needs them.

    Special logic:
      - OWNER_FULL_NAME is split into FIRST_NAME / LAST_NAME
      - STATE, CITY, ZIP_CODE are reused for both business and owner rows
      - BUSINESS_STREET_ADDRESS is also used as HOME_STREET_ADDRESS
      - STATE is also used as STATE_OF_INCORPORATION
      - OWNER_NAME_PRINT and OWNER_SIGNATURE_FIELD both get the full name
      - DATE_SIGNED gets today's date in M/D/YYYY format
    """
    s = slots  # shorthand

    # Split owner full name into first / last
    full_name = s.get("OWNER_FULL_NAME", "")
    parts = full_name.split(None, 1)          # split on first whitespace
    first_name = parts[0] if len(parts) > 0 else ""
    last_name  = parts[1] if len(parts) > 1 else ""

    # Today's date M/D/YYYY  (no leading zeros — e.g. 6/1/2026)
    today = date.today()
    today_str = f"{today.month}/{today.day}/{today.year}"

    # Build the slot→value lookup (many-to-one expansions done here)
    slot_values = {
        "BUSINESS_LEGAL_NAME"    : s.get("BUSINESS_LEGAL_NAME", ""),
        "TYPE_OF_BUSINESS_ENTITY": s.get("TYPE_OF_BUSINESS_ENTITY", ""),
        "INDUSTRY_TYPE"          : s.get("INDUSTRY_TYPE", ""),
        "STATE_OF_INCORPORATION" : s.get("STATE", ""),           # same as STATE
        "BUSINESS_STREET_ADDRESS": s.get("BUSINESS_STREET_ADDRESS", ""),
        "CITY"                   : s.get("CITY", ""),
        "STATE"                  : s.get("STATE", ""),
        "ZIP_CODE"               : s.get("ZIP_CODE", ""),
        "BUSINESS_FEDERAL_TAX_ID": s.get("BUSINESS_FEDERAL_TAX_ID", ""),
        "BUSINESS_START_DATE"    : s.get("BUSINESS_START_DATE", ""),
        "FIRST_NAME"             : first_name,
        "LAST_NAME"              : last_name,
        "DOB"                    : s.get("DOB", ""),
        "HOME_STREET_ADDRESS"    : s.get("BUSINESS_STREET_ADDRESS", ""),  # same street
        "CITY_OWNER"             : s.get("CITY", ""),            # same city
        "STATE_OWNER"            : s.get("STATE", ""),           # same state
        "ZIP_OWNER"              : s.get("ZIP_CODE", ""),        # same zip
        "SOCIAL_SECURITY"        : s.get("SOCIAL_SECURITY", ""),
        "OWNER_NAME_PRINT"       : full_name,                    # full name print #1
        "DATE_SIGNED"            : today_str,                    # auto today
        "OWNER_SIGNATURE_FIELD"  : full_name,                    # full name print #2
    }

    # Now map every widget name to its value
    widget_values = {}
    for widget_name, slot in WIDGET_SLOTS.items():
        widget_values[widget_name] = slot_values.get(slot, "")

    return widget_values


# ── Fill the PDF with fitz ────────────────────────────────────
def fill_pdf(widget_values: dict) -> Path:
    """Open template, write all field values, save to generated/."""
    if not TEMPLATE.exists():
        raise FileNotFoundError(
            f"template.pdf not found at {TEMPLATE}. "
            "Copy your PDF form into the pdf/ folder."
        )

    doc  = fitz.open(str(TEMPLATE))
    page = doc[0]

    filled = 0
    for widget in page.widgets():
        val = widget_values.get(widget.field_name)
        if val is not None:
            widget.field_value = val
            widget.update()
            filled += 1

    log.info("Filled %d/%d widgets", filled, len(widget_values))

    out_name = f"filled_{uuid.uuid4().hex[:8]}.pdf"
    out_path = GEN_DIR / out_name
    doc.save(str(out_path), deflate=True, garbage=4)
    doc.close()

    return out_path


# ── Routes ────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/template-pdf")
def template_pdf():
    if not TEMPLATE.exists():
        return jsonify({"error": "template.pdf not found"}), 404
    return send_from_directory(str(PDF_DIR), "template.pdf",
                               mimetype="application/pdf")


@app.route("/fill", methods=["POST"])
def fill():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body received."}), 400

    raw = data.get("raw_text", "").strip()
    if not raw:
        return jsonify({"error": "Input text is empty."}), 400

    # 1. Parse
    slots = parse_input(raw)
    if not slots:
        return jsonify({
            "error": "No recognised fields found.",
            "hint" : "Each line must be  LABEL: VALUE  — e.g.  CITY: MC LEAN"
        }), 400

    log.info("Parsed slots: %s", list(slots.keys()))

    # 2. Build widget values
    widget_values = build_widget_values(slots)

    # 3. Fill PDF
    try:
        out_path = fill_pdf(widget_values)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        log.exception("PDF fill error")
        return jsonify({"error": f"PDF generation failed: {e}"}), 500

    # 4. Download — set filename using BUSINESS_LEGAL_NAME if present
    business_name = slots.get("BUSINESS_LEGAL_NAME", "").strip()
    if business_name:
        # remove characters not allowed in filenames
        safe_name = "".join(c for c in business_name if c not in '/\\?%*:|"<>').strip()
        download_name = f"APCG-{safe_name}.pdf"
    else:
        download_name = "APCG-completed_form.pdf"
    return send_file(
        str(out_path),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


@app.route("/fields-info")
def fields_info():
    """Debug: list all widget names in the template."""
    if not TEMPLATE.exists():
        return jsonify({"error": "template.pdf not found"}), 404
    doc     = fitz.open(str(TEMPLATE))
    widgets = [{"widget": w.field_name, "slot": WIDGET_SLOTS.get(w.field_name, "UNMAPPED")}
               for w in doc[0].widgets()]
    doc.close()
    return jsonify({"total": len(widgets), "fields": widgets})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
