# FormFill Pro — Complete Setup Guide
## Windows + VS Code

---

## What This App Does

You paste plain-text business data on the left → click a button →
the app fills your PDF's AcroForm fields and downloads the completed PDF.
The original template design is **never modified**.

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.10 or newer | https://www.python.org/downloads/ |
| pip | bundled with Python | — |
| VS Code | latest | https://code.visualstudio.com/ |

---

## Project Folder Structure

```
project/
│
├── app.py                   ← Flask backend (main entry point)
├── inspect_fields.py        ← Helper to list PDF field names
├── requirements.txt         ← Python dependencies
├── SETUP_GUIDE.md           ← This file
│
├── templates/
│   └── index.html           ← Frontend HTML
│
├── static/
│   ├── css/
│   │   └── style.css        ← All styling
│   └── js/
│       └── script.js        ← All frontend logic
│
├── pdf/
│   └── template.pdf         ← ⚠ YOUR PDF GOES HERE (you provide this)
│
└── generated/               ← Auto-created; filled PDFs are saved here
```

---

## Step 1 — Place Your PDF Template

1. Copy your fillable PDF form to the `pdf/` folder.
2. Rename it exactly to: **`template.pdf`**

> ⚠ The file must have AcroForm interactive fields (not a scanned/flat PDF).

---

## Step 2 — Open the Project in VS Code

1. Open **VS Code**.
2. Go to **File → Open Folder…**
3. Select the `project/` folder.

---

## Step 3 — Open the Integrated Terminal

- Press **Ctrl + `** (backtick)  OR
- Go to **Terminal → New Terminal**

---

## Step 4 — Create a Virtual Environment

```bash
# Create a virtual environment named "venv"
python -m venv venv
```

---

## Step 5 — Activate the Virtual Environment

```bash
# Windows (Command Prompt or PowerShell)
venv\Scripts\activate

# You should see (venv) at the start of your prompt
```

---

## Step 6 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- **Flask** — web framework
- **pypdf** — PDF reading and AcroForm field filling

---

## Step 7 — Inspect Your PDF Field Names

```bash
python inspect_fields.py
```

This prints a table like:

```
Found 12 AcroForm field(s) in 'pdf/template.pdf':

#     Field Name                                    Type            Current Value
---------------------------------------------------------------------------
1     Business Legal Name                           /Tx
2     Business Start Date                           /Tx
3     Business Street Address                       /Tx
...
```

---

## Step 8 — Update the Field Map in app.py

Open `app.py` and find the `FIELD_MAP` dictionary (around line 50).

Update the **values** (right side) to match the exact field names
printed by `inspect_fields.py`:

```python
FIELD_MAP = {
    "business legal name"      : "Business Legal Name",   # ← exact PDF field name
    "type of business entity"  : "Type Of Business Entity",
    "business street address"  : "Business Street Address",
    "city"                     : "City",
    "state"                    : "State",
    "zip code"                 : "Zip",
    "business federal tax id #": "Tax ID",
    "business start date"      : "Business Start Date",
    "owner full name"          : "Owner Name",
    "dob"                      : "Date Of Birth",
    "social security #"        : "Social Security",
    "industry type"            : "Industry Type",
}
```

> **Do not change the keys (left side)** — those match the user's input labels.
> Only update the values (right side) to match your PDF.

---

## Step 9 — Run the Flask App

```bash
python app.py
```

You should see:
```
INFO  * Running on http://127.0.0.1:5000
INFO  * Debug mode: on
```

---

## Step 10 — Open the App in Your Browser

Go to: **http://localhost:5000**

You will see:
- **Left panel** — textarea to paste business data
- **Right panel** — your PDF template preview

---

## Step 11 — Use the App

1. Paste your business data into the left textarea in this format:
   ```
   BUSINESS LEGAL NAME: PRXIMO CAPITAL LLC
   TYPE OF BUSINESS ENTITY: LLC
   CITY: MC LEAN
   STATE: VA
   ...
   ```
2. Click **[ Convert & Download ]**
3. The filled PDF downloads automatically as `completed_form.pdf`

> **Keyboard shortcut:** Press `Ctrl + Enter` inside the textarea to trigger conversion.

---

## Verify Field Names (Debug Endpoint)

Open this URL in your browser while the app is running:

```
http://localhost:5000/fields-info
```

It returns JSON with every AcroForm field name found in your template —
useful for debugging mismatches.

---

## Common Problems & Fixes

### ❌ "template.pdf not found"
→ Make sure your PDF is in `pdf/template.pdf` (exact name, exact folder).

### ❌ "No AcroForm fields found"
→ Your PDF may be flat/scanned. Open it in **Adobe Acrobat** and check
  if fields are interactive. Flat PDFs need a different approach.

### ❌ "None of the labels matched"
→ Run `python inspect_fields.py` and update `FIELD_MAP` in `app.py`.

### ❌ Fields are empty in the output PDF
→ The field names in `FIELD_MAP` don't match your PDF's actual field names.
  They are **case-sensitive**. Run `inspect_fields.py` to check.

### ❌ ModuleNotFoundError
→ Make sure your virtual environment is activated (`venv\Scripts\activate`)
  and you ran `pip install -r requirements.txt`.

### ❌ Port 5000 already in use
→ Change the port at the bottom of `app.py`:
  ```python
  app.run(debug=True, port=5001)
  ```
  Then open http://localhost:5001

---

## Stopping the Server

Press **Ctrl + C** in the terminal.

---

## Restarting After Reboot

```bash
# 1. Open terminal in VS Code (Ctrl + `)
# 2. Activate venv
venv\Scripts\activate

# 3. Start Flask
python app.py
```

---

## Multi-page PDFs

If your form spans more than one page, update the `fill_pdf()` function
in `app.py`. Change `writer.pages[0]` to fill all pages:

```python
# Fill the same fields on every page
for page in writer.pages:
    writer.update_page_form_field_values(page, field_values, auto_regenerate=False)
```

---

*FormFill Pro — the original PDF template is never modified.*
