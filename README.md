# Synthetic Invoice Dataset Generator

Generates synthetic invoice PDFs with paired JSON ground-truth files.
The PDF and JSON are generated from the same in-memory record, which keeps values aligned across both outputs.

## Project Structure

```text
invoice_dataset_generator/
├── generate.py
├── verify.py
├── stats.py
├── requirements.txt
└── README.md

output/
├── pdfs/
├── ground_truth/
├── pdfs.zip                # only when --zip is used
└── ground_truth.zip        # only when --zip is used
```

## Requirements

- Python 3.9+
- Dependencies in requirements.txt:
  - reportlab==4.4.10
  - pdfplumber==0.10.3
  - pillow==10.2.0

Install:

```bash
pip install -r requirements.txt
```

## Quick Start

Run all commands from the repository root.

Generate default dataset (1000 invoices):

```bash
python generate.py
```

Generate a custom size/location:

```bash
python generate.py --n 100 --pdf_dir output_test/pdfs --gt_dir output_test/ground_truth
```

Generate and zip outputs:

```bash
python generate.py --zip
```

## Validation

Verify JSON-to-PDF field presence:

```bash
python verify.py
```

Verify field presence + color contrast:

```bash
python verify.py --check_contrast
```

Notes on verification behavior:

- PDF text is extracted with pdfplumber.
- Matching is normalization-based (case-insensitive, whitespace-collapsed substring check).
- Required core fields are always checked.
- Conditional fields are checked only when enabled in JSON (tax, PO, shipping, notes, bank details).
- Contrast check uses WCAG-style relative luminance and contrast ratio with default threshold 4.5.

## Dataset Statistics

Print summary statistics from generated JSON files:

```bash
python stats.py
```

Current values for the latest generated set (n=1000 in output/):

- Total documents: 1000
- Total line items: 8642
- Average line items/document: 8.6
- Line-item range: 1 to 25
- Unique sellers: 30
- Unique clients: 30
- Page sizes: A4=575, Letter=425
- Currency count: 10

## Generation Logic

- The generator supports 10 layout styles.
- Company-to-template mapping is deterministic and realistic:
  - each seller is assigned 1 primary template,
  - some sellers get 1 additional template,
  - so each seller uses at most 2 templates.
- Complexity tiers are balanced with fixed weights.
- Optional fields (notes, bank details, PO, shipping, discount/unit columns) are conditionally included.

## Reproducibility

Generation is deterministic with fixed seeds:

- global sequence seed: 42
- per-document content seed: index * 9999 + 7
- invoice number seed: index * 3571
- seller-template mapping seed: 2026

Given the same code, dependencies, and seeds, regenerated datasets are reproducible.

## Ground Truth Schema (Summary)

Each invoice JSON has 39 top-level keys:

- 38 scalar/object keys
- 1 array key: line_items

Important key groups:

- metadata: id, filename, layout_style, page_size, complexity_tier
- document header: invoice_number, issue_date, due_date, payment_terms, currency
- parties: seller_* and client_*
- amounts: subtotal, tax_*, shipping_amount, total_due
- options/flags: has_tax, has_notes, has_bank_details, has_shipping, has_po_number, etc.

## Troubleshooting

- If verify reports missing fields:
  - regenerate with python generate.py,
  - rerun python verify.py,
  - inspect the reported invoice IDs for layout overflow or text collisions.
- If contrast check fails to import generate:
  - ensure you run from repository root,
  - ensure dependencies are installed in the active environment.

