# =============================================================
# inspect_fields.py
# =============================================================
# Run this ONCE after placing your template.pdf to see the exact
# AcroForm field names you need to put in the FIELD_MAP in app.py.
#
# Usage (from the project/ folder):
#     python inspect_fields.py
# =============================================================

from pathlib import Path
from pypdf import PdfReader

TEMPLATE = Path("pdf/template.pdf")

def main():
    if not TEMPLATE.exists():
        print(f"[ERROR] File not found: {TEMPLATE}")
        print("        Copy your PDF template to the  pdf/  folder first.")
        return

    reader = PdfReader(str(TEMPLATE))
    fields = reader.get_fields()

    if not fields:
        print("[WARNING] No AcroForm fields found in this PDF.")
        print("          The PDF may be flat (non-fillable). Contact support.")
        return

    print(f"\nFound {len(fields)} AcroForm field(s) in '{TEMPLATE}':\n")
    print(f"{'#':<5} {'Field Name':<45} {'Type':<15} {'Current Value'}")
    print("-" * 85)

    for i, (name, field) in enumerate(sorted(fields.items()), 1):
        ftype = field.get("/FT", "unknown")
        value = field.get("/V", "")
        print(f"{i:<5} {name:<45} {str(ftype):<15} {value}")

    print("\n✅  Copy the field names from the 'Field Name' column into")
    print("    the FIELD_MAP dictionary in app.py  (values on the right side).")

if __name__ == "__main__":
    main()
