# PDF Statement Data Extractor

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/) 
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Extract key information from real-world bank and credit card PDF statements using Python.**

This project provides a robust pipeline to extract structured data from PDFs, supporting **digital text PDFs** and **scanned PDFs using OCR**, handling the variability commonly found in real-world financial documents.

---

## Features

- **OCR Fallback:** Automatically uses `pytesseract` + `pdf2image` for scanned statements.
- **Key Data Extraction:** Detects and extracts:
  - Cardholder / account holder name
  - Statement date
  - Payment due date
  - Total amount due
  - Last 4 digits of the card
- **Flexible Regex Matching:** Handles multiple formats for dates, currency, and masked card numbers.
- **Candidate Scoring:** Ranks matches based on proximity to keywords and context.
- **Resilient to Real-World Variability:** Works on PDFs with:
  - Different layouts and column alignments
  - Labels like "Amount Payable", "Outstanding Balance", or "Total Due"
  - Noise, headers, footers, and disclaimers
- **Easy Integration:** Can be used as a standalone script or as a Python module.

---

## Installation

```bash
git clone https://github.com/your-username/pdf-statement-extractor.git
cd pdf-statement-extractor
pip install -r requirements.txt
