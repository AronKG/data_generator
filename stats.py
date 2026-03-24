"""
stats.py
--------
Print a full statistical summary of the generated dataset.
Run after generate.py has completed.

Usage:
    python stats.py --gt_dir output/ground_truth
"""

import argparse
import json
import os
import re
from collections import Counter


def run(gt_dir):
    all_data = []
    for idx in range(1, 1001):
        path = os.path.join(gt_dir, f"invoice_{idx:03d}.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                all_data.append(json.load(f))

    if not all_data:
        print("No JSON files found. Run generate.py first.")
        return

    counts = [d["num_line_items"] for d in all_data]

    print("=== BASIC COUNTS ===")
    print(f"  Total documents          : {len(all_data)}")
    print(f"  Total line items         : {sum(counts)}")
    print(f"  Avg line items/document  : {sum(counts)/len(counts):.1f}")
    print(f"  Min line items           : {min(counts)}")
    print(f"  Max line items           : {max(counts)}")

    print("\n=== LAYOUT STYLES ===")
    for k, v in sorted(Counter(d["layout_style"] for d in all_data).items()):
        print(f"  {k:<20} {v}")

    print("\n=== COMPLEXITY TIERS ===")
    for k, v in sorted(Counter(d["complexity_tier"] for d in all_data).items()):
        print(f"  {k:<20} {v}")

    print("\n=== CURRENCIES ===")
    for k, v in Counter(d["currency"] for d in all_data).most_common():
        print(f"  {k:<10} {v}")

    print("\n=== PAGE SIZES ===")
    for k, v in Counter(d["page_size"] for d in all_data).items():
        print(f"  {k:<10} {v}")

    print("\n=== COLOUR PALETTES ===")
    print(f"  Total palettes used: {len(set(d['color_palette_index'] for d in all_data))}")

    print("\n=== UNIQUE ENTITIES ===")
    print(f"  Unique sellers : {len(set(d['seller_name'] for d in all_data))}")
    print(f"  Unique clients : {len(set(d['client_name'] for d in all_data))}")

    print("\n=== OPTIONAL FIELDS ===")
    n = len(all_data)
    print(f"  Has tax            : {sum(d['has_tax'] for d in all_data)} / {n}  ({100*sum(d['has_tax'] for d in all_data)/n:.1f}%)")
    print(f"  Has notes          : {sum(d['has_notes'] for d in all_data)} / {n}  ({100*sum(d['has_notes'] for d in all_data)/n:.1f}%)")
    print(f"  Has bank details   : {sum(d['has_bank_details'] for d in all_data)} / {n}  ({100*sum(d['has_bank_details'] for d in all_data)/n:.1f}%)")
    print(f"  Has discount col   : {sum(d['has_discount_column'] for d in all_data)} / {n}  ({100*sum(d['has_discount_column'] for d in all_data)/n:.1f}%)")
    print(f"  Has PO number      : {sum(d['has_po_number'] for d in all_data)} / {n}  ({100*sum(d['has_po_number'] for d in all_data)/n:.1f}%)")
    print(f"  Has shipping       : {sum(d['has_shipping'] for d in all_data)} / {n}  ({100*sum(d['has_shipping'] for d in all_data)/n:.1f}%)")
    print(f"  Has unit column    : {sum(d['has_unit_column'] for d in all_data)} / {n}  ({100*sum(d['has_unit_column'] for d in all_data)/n:.1f}%)")

    totals = [d["total_due"] for d in all_data]
    print("\n=== FINANCIAL RANGE ===")
    print(f"  Min total due  : {min(totals):>15,.2f}")
    print(f"  Max total due  : {max(totals):>15,.2f}")
    print(f"  Mean total due : {sum(totals)/len(totals):>15,.2f}")

    print("\n=== INVOICE NUMBER FORMATS ===")
    inv_formats = Counter()
    for d in all_data:
        n_str = d["invoice_number"]
        prefix = re.match(r"^[A-Za-z\-/]+", n_str)
        inv_formats[prefix.group() if prefix else "numeric-only"] += 1
    for k, v in inv_formats.most_common():
        print(f"  {k:<20} {v}")

    print(f"\n  Total unique invoice numbers: {len(set(d['invoice_number'] for d in all_data))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gt_dir", default="output/ground_truth",
                        help="Folder containing invoice_NNN.json files")
    args = parser.parse_args()
    run(args.gt_dir)
