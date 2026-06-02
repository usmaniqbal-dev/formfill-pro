/* =============================================================
   script.js — FormFill Pro Frontend Logic
   =============================================================
   Responsibilities:
     1. Load the PDF template into the right-panel iframe
     2. Live textarea analysis (line/char count + field detection)
     3. Send data to /fill endpoint on button click
     4. Handle the binary PDF response and trigger browser download
     5. Show success / error toast messages
   ============================================================= */

"use strict";

// ── Utility: debounce ─────────────────────────────────────────
function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

// ── Known labels (must match FIELD_MAP keys in app.py) ────────
// Used to detect which fields are present in the textarea
const KNOWN_LABELS = [
  "BUSINESS LEGAL NAME",
  "TYPE OF BUSINESS ENTITY",
  "BUSINESS STREET ADDRESS",
  "CITY",
  "STATE",
  "ZIP CODE",
  "BUSINESS FEDERAL TAX ID #",
  "BUSINESS START DATE",
  "OWNER FULL NAME",
  "DOB",
  "SOCIAL SECURITY #",
  "INDUSTRY TYPE",
];

// ── DOM references ─────────────────────────────────────────────
const inputData      = document.getElementById("inputData");
const convertBtn     = document.getElementById("convertBtn");
const clearBtn       = document.getElementById("clearBtn");
const btnSpinner     = document.getElementById("btnSpinner");
const btnText        = convertBtn.querySelector(".btn-text");
const btnIcon        = convertBtn.querySelector(".btn-icon");
const lineCount      = document.getElementById("lineCount");
const charCount      = document.getElementById("charCount");
const detectedSection= document.getElementById("detectedSection");
const chipList       = document.getElementById("chipList");
const toastEl        = document.getElementById("toast");
const pdfLoading     = document.getElementById("pdfLoading");
const pdfPreview     = document.getElementById("pdfPreview");
const pdfError       = document.getElementById("pdfError");

// ── 1. Load PDF template on page load ─────────────────────────
(function loadTemplate() {
  // We set the iframe src to our Flask route that serves the PDF.
  // If the file is missing the route returns 404 and we show an error.
  pdfPreview.addEventListener("load", () => {
    // The iframe loaded something — check if it contains an error
    // by checking the URL still points to our template route
    pdfLoading.hidden = true;
    pdfPreview.hidden = false;
  });

  pdfPreview.addEventListener("error", () => {
    showPdfError();
  });

  // Attempt to verify the template exists before setting the src
  fetch("/template-pdf", { method: "HEAD" })
    .then(res => {
      if (!res.ok) throw new Error("not found");
      // Append a cache-buster so refreshing always shows current file
      pdfPreview.src = `/template-pdf?t=${Date.now()}`;
    })
    .catch(() => showPdfError());
})();

function showPdfError() {
  pdfLoading.hidden = true;
  pdfError.hidden   = false;
  pdfPreview.hidden = true;
}

// ── 2. Live textarea stats + field detection ───────────────────
function updateStats() {
  const text  = inputData.value;
  const lines = text.split("\n").filter(l => l.trim()).length;
  const chars = text.length;

  lineCount.textContent = `${lines} line${lines !== 1 ? "s" : ""}`;
  charCount.textContent = `${chars} char${chars !== 1 ? "s" : ""}`;

  // Detect which known labels appear in the text
  const upperText = text.toUpperCase();
  const found = KNOWN_LABELS.filter(label => upperText.includes(label + ":"));

  if (found.length > 0) {
    detectedSection.hidden = false;
    chipList.innerHTML = "";
    found.forEach(label => {
      const chip       = document.createElement("span");
      chip.className   = "chip";
      chip.textContent = label;
      chipList.appendChild(chip);
    });
  } else {
    detectedSection.hidden = true;
    chipList.innerHTML = "";
  }
}

// Run immediately + on every keystroke (debounced for perf)
inputData.addEventListener("input", debounce(updateStats, 150));
updateStats(); // initial call

// ── 3. Clear button ────────────────────────────────────────────
clearBtn.addEventListener("click", () => {
  inputData.value = "";
  updateStats();
  hideToast();
  inputData.focus();
});

// ── 4. Convert & Download ──────────────────────────────────────
convertBtn.addEventListener("click", async () => {
  const raw = inputData.value.trim();

  // Client-side validation
  if (!raw) {
    showToast("⚠ Please paste your business data into the text area first.", "warning");
    inputData.focus();
    return;
  }

  if (!raw.includes(":")) {
    showToast(
      "⚠ No fields detected. Each line must follow the format  LABEL: VALUE",
      "warning"
    );
    return;
  }

  // Enter loading state
  setLoading(true);
  hideToast();

  try {
    const response = await fetch("/fill", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ raw_text: raw }),
    });

    if (!response.ok) {
      // Parse JSON error message from Flask
      let msg = `Server error (${response.status})`;
      try {
        const err = await response.json();
        msg = err.error || msg;
        if (err.hint)      msg += `\n${err.hint}`;
        if (err.unmatched?.length) {
          msg += `\nUnrecognised labels: ${err.unmatched.join(", ")}`;
        }
      } catch (_) { /* ignore JSON parse errors */ }
      throw new Error(msg);
    }

    // ── The response is a binary PDF blob ─────────────────────
    const blob       = await response.blob();
    const url        = URL.createObjectURL(blob);
    const anchor     = document.createElement("a");
    anchor.href      = url;
    anchor.download  = "completed_form.pdf";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();

    // Release the object URL after a short delay
    setTimeout(() => URL.revokeObjectURL(url), 10_000);

    showToast("✅ PDF generated and downloaded successfully!", "success");

  } catch (err) {
    console.error("[FormFill] Error:", err);
    showToast(`❌ ${err.message}`, "error");

  } finally {
    setLoading(false);
  }
});

// ── Helper: toggle loading state ──────────────────────────────
function setLoading(on) {
  convertBtn.disabled = on;
  btnIcon.hidden      = on;
  btnSpinner.hidden   = !on;
  btnText.textContent = on ? "Generating PDF…" : "Convert & Download";
}

// ── Helper: show toast ─────────────────────────────────────────
function showToast(message, type = "success") {
  toastEl.textContent = message;
  toastEl.className   = `toast ${type}`;

  // Auto-hide after a delay (errors stay longer)
  const delay = type === "error" ? 8000 : 5000;
  clearTimeout(toastEl._timer);
  toastEl._timer = setTimeout(hideToast, delay);
}

function hideToast() {
  toastEl.className = "toast";
  toastEl.textContent = "";
}

// ── Keyboard shortcut: Ctrl+Enter to convert ──────────────────
inputData.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    convertBtn.click();
  }
});
