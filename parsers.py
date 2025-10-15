import argparse
import re
import pdfplumber

# Optional OCR libraries (used only if pdfplumber text is insufficient)
# To enable OCR fallback, install: pip install pdf2image pytesseract
# and ensure tesseract binary is installed & in PATH.
try:
    from pdf2image import convert_from_path
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False


# ---------- Utility regexes ----------
# number/amount regex: matches 1,234,567.89 or 12345.67 or 12345
AMOUNT_RE = re.compile(r'(?:Rs\.?|INR|₹)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d+)?|\d+(?:\.\d+)?)')

# date regex (common numeric formats): 01/04/2023, 1-4-2023, 12 Feb 2023, Feb 12, 2023
DATE_RE = re.compile(
    r'(\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|'                            # 01/04/2023 or 1-4-23
    r'\b(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*[.,]?\s+\d{2,4})\b|'  # 12 Feb 2023
    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2}[,]?\s+\d{2,4}\b)', re.I)

# helper to find nearest amount after a keyword
def find_amount_near(text, start_idx=0, search_window=200):
    window = text[start_idx:start_idx+search_window]
    m = AMOUNT_RE.search(window)
    if m:
        return m.group(1)
    return None

# ---------- Datapoint extraction logic ----------
def extract_datapoints_from_text(text):
    """
    Returns a dict with keys:
      - cardholder_name (str or None)
      - statement_date (str or None)
      - payment_due_date (str or None)  # might be 'IMMEDIAT' etc.
      - total_amount_due (str or None)  # string representation of amount found
      - card_last4 (str or None)
      - candidates (dict)  # optional extras found: other detected dates/amounts
    """
    out = {
        "cardholder_name": None,
        "statement_date": None,
        "payment_due_date": None,
        "total_amount_due": None,
        "card_last4": None,
        "candidates": {"dates": [], "amounts": []}
    }

    # normalize for matching while preserving original text for capture
    lower = text.lower()

    # 1) CARD LAST 4: prefer a pattern that includes masking characters near digits
    # find tokens that look like masked card numbers and capture trailing 4 digits
    # common forms: "4695 25XX XXXX 3458", "530562******9004", "Card No: 530562******9004"
    masked_patterns = [
        re.compile(r'(?:card(?:\s*no|number)[:\s]*)?([0-9\*xX\-\s]{6,})'),  # loose
    ]
    # We'll instead search for any group where last 4 digits appear after masking symbols nearby
    possible_last4 = None
    # Strategy: find occurrences of patterns containing '*' or 'x' or 'X' or 'XX' or 'XXXX' and a 4-digit tail
    m = re.search(r'([*Xx]{2,}[*Xx0-9\s\-]{0,20}(\d{4}))', text)
    if m:
        possible_last4 = m.group(2)
    else:
        # fallback: look for sequences like 'xxxx xxxx 3458' or any 4-digit sequences that appear with 'card' nearby
        all_four = re.findall(r'(\d{4})', text)
        if all_four:
            # find 'card' occurrences and choose 4-digit closest to them
            card_positions = [m.start() for m in re.finditer(r'card\b|card no|card number|card account', lower)]
            if card_positions:
                best = None
                best_dist = None
                for pos in card_positions:
                    # find nearest 4-digit sequence position
                    for m2 in re.finditer(r'\d{4}', text):
                        dist = abs(m2.start() - pos)
                        if best is None or dist < best_dist:
                            best = m2.group(0)
                            best_dist = dist
                possible_last4 = best
            else:
                # last resort: take the last 4-digit group that occurs in the upper half of the document
                # often card last4 appears near top; choose the last 4-digit that is not a year (>=1900 & <= 2099)
                candidates = []
                for m2 in re.finditer(r'\d{4}', text):
                    d = m2.group(0)
                    if not (1900 <= int(d) <= 2099):
                        candidates.append((m2.start(), d))
                if candidates:
                    # pick the candidate near the top: earliest non-year 4-digit
                    possible_last4 = candidates[0][1]

    if possible_last4:
        out["card_last4"] = possible_last4.strip()

    # 2) TOTAL AMOUNT DUE: lenient search for keywords then amount
    # list of fuzzy keywords to find the "total amount due"
    total_keywords = [
        r'total\s*(?:amount\s*)?due',
        r'total\s*dues',
        r'total\s*payment\s*due',
        r'your\s*total\s*amount\s*due',
        r'total\s*dues\s*[:\-]?',
        r'total\s*amount\s*payable',
        r'total\s*payment',
        r'total\s*d(ue|ues)\b'
    ]
    found_total = None
    for kw in total_keywords:
        for m in re.finditer(kw, lower):
            # try to find an amount near this keyword
            amt = find_amount_near(lower, start_idx=m.end(), search_window=200)
            if amt:
                # clean amount (remove commas)
                out["total_amount_due"] = amt.replace(',', '')
                found_total = True
                break
        if found_total:
            break

    # fallback: if not found, sometimes the amount label is on same line after keyword with parentheses or newlines
    if not out["total_amount_due"]:
        # try to find occurrences of the amount phrase anywhere and then capture next numeric token in original text
        for m in re.finditer(r'(total[\s\w]{0,20}due|total[\s\w]{0,20}dues)', lower):
            # search in original text to preserve formatting
            amt = find_amount_near(text, start_idx=m.start(), search_window=300)
            if amt:
                out["total_amount_due"] = amt.replace(',', '')
                break

    # 3) PAYMENT DUE DATE / DUE DATE:
    # look for explicit labels: 'payment due date', 'due date', 'payment due'
    due_patterns = [r'payment\s*due\s*date', r'due\s*date', r'payment\s*due\b', r'payment\s*due\s*[:\-]?', r'payment\s*due\s*']
    payment_due = None
    for pat in due_patterns:
        for m in re.finditer(pat, lower):
            # search the next 60-120 chars for either a date or a word like IMMEDIAT/IMMEDIATE
            window = text[m.end():m.end()+140]
            # date
            dm = DATE_RE.search(window)
            if dm:
                payment_due = dm.group(0).strip()
                break
            # immediate words
            im = re.search(r'(immediat|immediate|immediately|immediately)', window, re.I)
            if im:
                payment_due = im.group(0).strip()
                break
            # if amount pattern appears (rare), skip
        if payment_due:
            break
    out["payment_due_date"] = payment_due

    # 4) STATEMENT DATE: search for 'statement date' or 'statement generation date' or 'statement period'
    statement_patterns = [r'statement\s*date', r'statement\s*generation\s*date', r'statement\s*period', r'statement\s*for']
    statement_date = None
    for pat in statement_patterns:
        for m in re.finditer(pat, lower):
            window = text[m.end():m.end()+140]
            dm = DATE_RE.search(window)
            if dm:
                statement_date = dm.group(0).strip()
                break
            # for 'statement period' sometimes format is '14/01/2024 - 12/02/2024'
            dm2 = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s*[-–]\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', window)
            if dm2:
                statement_date = dm2.group(0).strip()
                break
        if statement_date:
            break
    out["statement_date"] = statement_date

    # 5) CARDHOLDER NAME: look for 'Name' label or 'Customer Name' or first lines that look like a person
    name = None
    # search for 'Name :' or 'Name :' like patterns
    nm = re.search(r'\bName\s*[:\-]\s*([A-Z][A-Z\s\.\-]{2,100})', text)
    if nm:
        name = nm.group(1).strip()
    else:
        # Customer Name, or 'Customer Name' label
        nm2 = re.search(r'\bCustomer\s+Name\s*[:\-]?\s*([A-Z][A-Z\s\.\-]{2,100})', text)
        if nm2:
            name = nm2.group(1).strip()
    if not name:
        # fallback: take first few lines and pick the first line with 2-4 words starting with capital letter
        for line in text.splitlines()[:12]:
            l = line.strip()
            # skip lines that contain bank terms or are all uppercase bank addresses containing 'bank' etc.
            if not l:
                continue
            # ignore lines with digits (likely addresses or account numbers)
            if re.search(r'\d', l):
                continue
            words = l.split()
            if 1 < len(words) <= 5:
                # heuristic: words start with uppercase letters or are mostly alphabetic
                if sum(1 for w in words if re.match(r'^[A-Z][a-zA-Z\.]{1,}$', w)) >= 1:
                    # ensure it's not generic words like 'Statement', 'Payment', etc.
                    if not re.search(r'(statement|payment|due|account|page|customer|bank|credit|statement date)', l, re.I):
                        name = l
                        break
    out["cardholder_name"] = name

    # EXTRA: collect other dates and amounts as candidates for further logic
    for dm in DATE_RE.finditer(text):
        out["candidates"]["dates"].append(dm.group(0))
    for am in AMOUNT_RE.finditer(text):
        out["candidates"]["amounts"].append(am.group(1).replace(',', ''))

    return out


# ---------- PDF text extraction with optional OCR fallback ----------
def extract_first_page_text(file_path, ocr_fallback=True):
    """
    Try direct extraction (pdfplumber). If result is too short and OCR is available
    and ocr_fallback==True, attempt OCR via pdf2image + pytesseract.
    Returns extracted text (string).
    """
    print(f"Processing '{file_path}'...")
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                raise ValueError("PDF has no pages.")
            page = pdf.pages[0]
            # try direct text extraction
            text = page.extract_text(x_tolerance=2) or ""
            if text and len(text.strip()) > 40:
                return text
            else:
                print("Direct extraction returned little/no text.")
    except Exception as e:
        print(f"Direct extraction error: {e}")
        text = ""

    # OCR fallback (optional)
    if ocr_fallback and OCR_AVAILABLE:
        try:
            print("Attempting OCR fallback (pdf2image + pytesseract)...")
            images = convert_from_path(file_path, first_page=1, last_page=1)
            if images:
                ocr_text = pytesseract.image_to_string(images[0])
                if ocr_text and len(ocr_text.strip()) > 20:
                    return ocr_text
        except Exception as e:
            print(f"OCR fallback failed: {e}")
    elif ocr_fallback:
        print("OCR fallback requested but pdf2image/pytesseract not available. Install them to enable OCR.")

    return text or ""


# ---------- Main integration ----------
def parse_pdf_page_one_and_extract(file_path, ocr_fallback=True):
    text = extract_first_page_text(file_path, ocr_fallback=ocr_fallback)
    if not text:
        print("❌ No text could be extracted from the PDF (even after OCR fallback).")
        return None

    datapoints = extract_datapoints_from_text(text)

    # Print nicely
    print("\n=== Extracted datapoints ===")
    for k, v in datapoints.items():
        if k == "candidates":
            continue
        print(f"{k}: {v}")
    # Optionally show candidate extras (first few)
    print("\nCandidates (sample):")
    print("Dates found:", datapoints["candidates"]["dates"][:5])
    print("Amounts found:", datapoints["candidates"]["amounts"][:8])
    return datapoints


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse first page of PDF and extract key datapoints (cardholder, statement date, due date, total due, last4)."
    )
    parser.add_argument("--file", required=True, help="Path to PDF file")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR fallback even if available")
    args = parser.parse_args()

    result = parse_pdf_page_one_and_extract(args.file, ocr_fallback=(not args.no_ocr))