# Synthetic Invoice Dataset Generator

Generates 1,000 synthetic invoice PDFs with paired JSON ground truth files.
Designed for training and evaluating document understanding models such as
LayoutLMv3, Donut, and similar architectures.

---

## File Structure

```
invoice_dataset_generator/
│
├── generate.py          # Main script — generates all PDFs and JSONs
├── verify.py            # Checks every JSON field appears in its PDF
├── stats.py             # Prints full dataset statistics
├── requirements.txt     # Python dependencies
└── README.md            # This file

output/                  # Created automatically when you run generate.py
├── pdfs/
│   ├── invoice_001.pdf
│   ├── invoice_002.pdf
│   └── ... (1000 files)
├── ground_truth/
│   ├── invoice_001.json
│   ├── invoice_002.json
│   └── ... (1000 files)
├── pdfs.zip             # Only if --zip flag used
└── ground_truth.zip     # Only if --zip flag used
```

---

## Installation

```bash
pip install -r requirements.txt
```

Tested with Python 3.9, 3.10, 3.11.

---

## Usage

### Generate 1,000 invoices (default)
```bash
python generate.py
```

### Generate with ZIP archives
```bash
python generate.py --zip
```

### Generate a smaller set (e.g. 100 for testing)
```bash
python generate.py --n 100 --pdf_dir test_pdfs --gt_dir test_jsons
```

### Verify PDF/JSON alignment
```bash
python verify.py
```
Expected output: `VERIFICATION RESULTS: 1000/1000 PASSED`

### Verify alignment + contrast safety
```bash
python verify.py --check_contrast
```
Also prints a contrast audit summary (default threshold: `4.5`).

### Print dataset statistics
```bash
python stats.py
```

---

## Reproducibility

The dataset is fully deterministic given the same random seeds:

| Seed | Controls |
|---|---|
| `random.seed(42)` | Which layout, currency, palette, page size each invoice gets |
| `random.Random(idx * 9999 + 7)` | All content inside each individual invoice |

Running `generate.py` twice on the same machine with the same library
versions produces bit-identical output files.

---

## Dataset Properties

| Property | Value |
|---|---|
| Total documents | 1,000 |
| Layout styles | 10 (100 each) |
| Colour palettes | 15 |
| Currencies | 10 |
| Page sizes | A4 (575), Letter (425) |
| Unique sellers | 30 |
| Unique clients | 30 |
| Complexity tiers | 4 (simple / medium / complex / very_complex) |
| Line items range | 1 – 25 per invoice |
| Total line items | 8,698 |
| Invoice number formats | 17+ variants |
| Date formats | 6 variants |
| Tax regimes | 12 variants |
| Payment terms | 15 variants |
| JSON fields per document | 38 + line_items array |

---

## JSON Ground Truth Schema

Each `invoice_NNN.json` contains:

```json
{
  "id": 1,
  "filename": "invoice_001.pdf",
  "layout_style": "two_tone",
  "page_size": "letter",
  "complexity_tier": "complex",
  "color_palette_index": 1,
  "invoice_number": "2025-25526",
  "issue_date": "December 17 2022",
  "due_date": "January 01 2023",
  "payment_terms": "Cash on Delivery",
  "currency": "AUD",
  "currency_symbol": "A$",
  "po_number": "PO-74733",
  "seller_name": "IronCore Manufacturing",
  "seller_address": "77 Steel Drive Pittsburgh PA 15201 USA",
  "seller_email": "ar@ironcoremfg.com",
  "seller_phone": "+1 412-555-0177",
  "seller_tax_id": "EIN: 45-6789012",
  "client_name": "Quantum Dynamics Corp",
  "client_address": "1000 Innovation Pkwy Cambridge MA 02139 USA",
  "client_email": "accounts@quantumdynamics.com",
  "num_line_items": 9,
  "line_items": [
    {
      "description": "Data Analysis",
      "unit": "ea",
      "quantity": 1,
      "unit_price": 1160.95,
      "discount_pct": 0,
      "line_total": 1160.95
    }
  ],
  "subtotal": 213367.41,
  "tax_label": "Sales Tax 8.25pct",
  "tax_rate_pct": 8.25,
  "tax_amount": 17602.81,
  "shipping_amount": 0.0,
  "total_due": 230970.22,
  "notes": null,
  "bank_details": null,
  "has_logo": true,
  "has_discount_column": false,
  "has_unit_column": true,
  "has_notes": false,
  "has_bank_details": false,
  "has_shipping": false,
  "has_po_number": true,
  "has_tax": true
}
```

---

## Known Limitations

| Issue | Count | Description |
|---|---|---|
| Low contrast header text | 66 | White text on light primary colour, contrast < 4.5:1 |
| Sidebar name truncation | 33 | Seller names > 22 chars may be clipped in sidebar layout |
| Page overflow risk | 16 | Very complex invoices in compact layout may exceed page height |
| Payment terms overflow | 7 | Long terms string may overflow single line in compact layout |

These are intentional — real invoice datasets contain the same imperfections.

---

## Citation

If you use this dataset in your research, please cite as:

```
Synthetic Invoice Dataset, generated using Python 3 and ReportLab 4.4.10.
Random seeds: global=42, per-document=index*9999+7.
1,000 documents across 10 layout styles, 10 currencies, 15 colour palettes.
```
