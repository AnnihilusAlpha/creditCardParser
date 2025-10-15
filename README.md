# PDF Credit Card Statement Data Extractor

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/) 

Note: All the PDFs are publicly available, except SBI.pdf.

**Extract key information from real-world bank and credit card PDF statements using Python.**

This project provides a robust pipeline to extract structured data from PDFs, supporting both **digital text PDFs** and **scanned PDFs using OCR**, handling the variability commonly found in real-world financial documents.

---

## Features

* **First-Page PDF Extraction**
  Extracts key data from the **first page** of any PDF statement for faster processing.

* **Supports Digital & Scanned PDFs (OCR)**

  * Direct text extraction via **pdfplumber**
  * **OCR fallback** using **pdf2image + pytesseract** for scanned or image-only PDFs.

* **Key Financial Data Detection**
  Extracts structured information:

  * Cardholder / Account Holder Name
  * Statement Date
  * Payment Due Date (including “IMMEDIATE” warnings)
  * Total Amount Due
  * Last 4 Digits of Card (from masked numbers)

* **Robust Regex Patterns**
  Handles multiple formats:

  * Dates (`01/08/2025`, `12 Feb 2025`, `Feb 12, 2025`)
  * Amounts (`₹12,345.67`, `Rs. 12345.67`, `INR 12,345`)
  * Masked card numbers (`XXXX-1234`, `25XX XXXX 3458`)

* **Candidate Collection for Extra Context**
  Collects all dates and amounts in the text for further validation or processing.

* **Heuristic Fallbacks for Real-World PDFs**

  * Infers cardholder names from labels or top lines
  * Determines card last 4 digits even if masking varies
  * Searches amounts and dates near relevant keywords

* **Flexible & Extensible**

  * Works with **varied bank/credit card statement layouts**
  * Easy to add **custom keywords or regex patterns**

* **Command-Line & Python Module Usage**

  * Run via CLI: `python parsers.py --file path/to/file.pdf`
  * Optional flag: `--no-ocr` to disable OCR
  * Importable as a module for integration into larger workflows

* **Diagnostic Output**
  Prints extracted fields and sample candidate dates/amounts for verification.

* **Cross-Platform Compatible**
  Works on **Windows, macOS, and Linux** (OCR requires Tesseract + Poppler installed).

---

## Installation

```bash
git clone https://github.com/your-username/pdf-statement-extractor.git
cd pdf-statement-extractor
pip install -r requirements.txt
````

**Additional Setup for OCR:**

* **Poppler** (required by `pdf2image`):

  * Windows: Download [Poppler for Windows](http://blog.alivate.com.au/poppler-windows/) and add `bin/` to PATH
  * macOS: `brew install poppler`
  * Linux: `sudo apt install poppler-utils`

* **Tesseract OCR**:

  * Windows: [Tesseract installer](https://github.com/tesseract-ocr/tesseract)
  * macOS: `brew install tesseract`
  * Linux: `sudo apt install tesseract-ocr`

---

## Usage

### Command-line

```bash
python parsers.py --file path/to/statement.pdf
```

* Optional flag to **disable OCR**:

```bash
python parsers.py --file path/to/statement.pdf --no-ocr
```

### Example Output

```bash
Processing 'SBI.pdf'...

=== Extracted datapoints ===
cardholder_name: SOMNATH SAWANT
statement_date: 09 Oct 2025
payment_due_date: 29 Oct 2025
total_amount_due: 35018.00
card_last4: 5981

Candidates (sample):
Dates found: ['09 Oct 2025', '29 Oct 2025', '10 Sep 25', '09 Oct 25', '22 Sep 25']
Amounts found: ['06', '598', '1', '1', '61', '35018.00', '27', '251']
```

---

## How It Works

### 1. PDF Text Extraction

* Attempts to extract text using `pdfplumber`.
* If extraction fails or text is insufficient, performs OCR on the first page using `pytesseract`.

### 2. Regex-based Identification

* Detects amounts, dates, masked card numbers, and names.
* Supports multiple formats (e.g., `01/08/2025`, `Aug 1, 2025`, `₹12,345.67`, `XXXX-1234`).

### 3. Candidate Collection

* For extra context.

### 4. Fallbacks

* Heuristics to handle missing or ambiguous data.
* Works on noisy or non-standard PDF layouts.

---

## Workflow Diagram

```text
          +-----------------------+
          | PDF Statement (input) |
          +----------+------------+
                     |
           +---------v---------+
           | Text Extraction   |--(if fails)--> OCR Extraction
           +---------+---------+
                     |
           +---------v---------+
           | Regex Detection   |
           | (dates, amounts,  |
           |  card number, name)|
           +---------+---------+
                     |
           +---------v---------+
           |Candidate Collection|
           | for Extra Context  |
           +---------+---------+
                     |
           +---------v---------+
           | Structured Output |
           +------------------+
```
---

```bash
## Project Structure


PDF Parser/
├── Input - Real World PDFs/  # Contains Credit Card Statements
│   └── AXIS.pdf
│   └── BOB.pdf
│   └── HDFC.pdf
│   └── ICICI.pdf
│   └── SBI.pdf
├── Output/                   # Contains output screenshot
│   └── output.png
├── README.md                 # This file
├── parsers.py                # Core parsing logic
└── requirements.txt          # Python dependencies

```
---

## Supported PDF Formats

* Real-world Bank statements
* Credit card statements
* Digital PDFs and scanned documents
* Multi-column tables, varying labels, and layouts

---

## Example PDFs Output Screenshot

<img width="797" height="931" alt="image" src="https://github.com/user-attachments/assets/e0388d33-d072-428e-8859-e86cc5e62627" />

---

## Acknowledgements

* [pdfplumber](https://github.com/jsvine/pdfplumber)
* [pdf2image](https://github.com/Belval/pdf2image)
* [pytesseract](https://github.com/madmaze/pytesseract)

---
