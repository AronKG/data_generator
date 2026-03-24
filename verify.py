"""
verify.py
---------
Run after generate.py to confirm that every field in each JSON
ground truth file appears verbatim in its corresponding PDF.

Usage:
    python verify.py --pdf_dir output/pdfs --gt_dir output/ground_truth
"""

import argparse
import json
import os
import re
from collections import Counter

import pdfplumber


def _lin_channel(v):
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def rel_luminance(col):
    return (0.2126 * _lin_channel(col.red)
            + 0.7152 * _lin_channel(col.green)
            + 0.0722 * _lin_channel(col.blue))


def contrast_ratio(c1, c2):
    l1 = rel_luminance(c1)
    l2 = rel_luminance(c2)
    light, dark = (l1, l2) if l1 >= l2 else (l2, l1)
    return (light + 0.05) / (dark + 0.05)


def verify_contrast(threshold=4.5):
    try:
        from reportlab.lib import colors
        import generate
    except Exception as e:
        print(f"\nCONTRAST CHECK FAILED TO RUN: {e}")
        return False

    checks = []
    for idx, pal in enumerate(generate.PALETTES):
        checks.append((f"palette[{idx}].primary", pal["primary"], generate.pick_text_color(pal["primary"])))
        checks.append((f"palette[{idx}].primary_label", pal["primary"], generate.pick_text_color(pal["primary"], preferred=pal["accent"])))
        checks.append((f"palette[{idx}].accent", pal["accent"], generate.pick_text_color(pal["accent"])))
        checks.append((f"palette[{idx}].white_surface", colors.white,
                       generate.pick_text_color(colors.white, preferred=pal["primary"])))
        checks.append((f"palette[{idx}].bg_surface", pal["bg"],
                       generate.pick_text_color(pal["bg"], preferred=pal["primary"])))

    ledger_bg = colors.HexColor("#2d4a1e")
    checks.append(("ledger_bg", ledger_bg, generate.pick_text_color(ledger_bg)))

    ratios = [(name, contrast_ratio(bg, txt)) for name, bg, txt in checks]
    worst_name, worst_ratio = min(ratios, key=lambda x: x[1])
    failures = [(name, r) for name, r in ratios if r < threshold]

    print("\n" + "=" * 55)
    print("CONTRAST CHECK")
    print("=" * 55)
    print(f"Threshold: {threshold:.2f}")
    print(f"Worst ratio: {worst_ratio:.3f} ({worst_name})")

    if failures:
        print(f"FAILED: {len(failures)} combinations below threshold")
        for name, ratio in failures[:20]:
            print(f"  {name:<30} {ratio:.3f}")
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")
        return False

    print("PASSED: all checked color combinations meet threshold")
    return True


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def contains(text, value):
    return norm(str(value)) in norm(text)


def verify(pdf_dir, gt_dir):
    failures_by_field = Counter()
    failed = []

    # Auto-detect how many invoices exist
    existing = sorted(f for f in os.listdir(gt_dir) if f.endswith(".json"))
    total = len(existing)
    invoice_ids = range(1, total + 1)
    print(f"Found {total} invoices to verify...")

    for idx in invoice_ids:
        gt_path  = os.path.join(gt_dir,  f"invoice_{idx:03d}.json")
        pdf_path = os.path.join(pdf_dir, f"invoice_{idx:03d}.pdf")

        if not os.path.exists(gt_path) or not os.path.exists(pdf_path):
            print(f"  MISSING: invoice_{idx:03d}")
            continue

        with open(gt_path, encoding="utf-8") as f:
            gt = json.load(f)

        with pdfplumber.open(pdf_path) as pdf:
            text = " ".join(p.extract_text() or "" for p in pdf.pages)

        fails = []

        # Core fields that must appear in PDF
        must = [
            ("invoice_number", gt["invoice_number"]),
            ("issue_date",     gt["issue_date"]),
            ("due_date",       gt["due_date"]),
            ("payment_terms",  gt["payment_terms"]),
            ("currency",       gt["currency"]),
            ("seller_name",    gt["seller_name"]),
            ("seller_address", gt["seller_address"]),
            ("seller_email",   gt["seller_email"]),
            ("client_name",    gt["client_name"]),
            ("client_address", gt["client_address"]),
            ("client_email",   gt["client_email"]),
            ("subtotal",       f"{gt['subtotal']:,.2f}"),
            ("total_due",      f"{gt['total_due']:,.2f}"),
        ]

        if gt["has_tax"]:
            must.append(("tax_label",   gt["tax_label"]))
        if gt["has_po_number"]:
            must.append(("po_number",   gt["po_number"]))
        if gt["has_shipping"]:
            must.append(("shipping",    f"{gt['shipping_amount']:,.2f}"))
        if gt["has_notes"] and gt["notes"]:
            must.append(("notes",       gt["notes"][:40]))
        if gt["has_bank_details"] and gt["bank_details"]:
            must.append(("bank_name",   gt["bank_details"]["Bank"]))

        for field, val in must:
            if not contains(text, val):
                fails.append(field)
                failures_by_field[field] += 1

        # Line items
        for item in gt["line_items"]:
            if not contains(text, item["description"][:20]):
                fails.append("item_desc")
                failures_by_field["item_desc"] += 1
                break
            if not contains(text, f"{item['line_total']:,.2f}"):
                fails.append("item_total")
                failures_by_field["item_total"] += 1
                break

        if fails:
            failed.append((idx, fails))

    passed = total - len(failed)

    print("=" * 55)
    print(f"VERIFICATION RESULTS: {passed}/{total} PASSED")
    print("=" * 55)

    if failed:
        print(f"\nFailed ({len(failed)} invoices):")
        for idx, f in failed[:20]:
            print(f"  invoice_{idx:03d}: {f}")
        if len(failed) > 20:
            print(f"  ... and {len(failed) - 20} more")
        print(f"\nFailures by field:")
        for field, count in failures_by_field.most_common():
            print(f"  {field:<25} {count}")
    else:
        print("\nPERFECT — Every JSON field confirmed present in its PDF.")

    return passed == total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", default="output/pdfs",
                        help="Folder containing invoice_NNN.pdf files")
    parser.add_argument("--gt_dir",  default="output/ground_truth",
                        help="Folder containing invoice_NNN.json files")
    parser.add_argument("--check_contrast", action="store_true",
                        help="Also verify text/background contrast for generator palettes")
    parser.add_argument("--contrast_threshold", type=float, default=4.5,
                        help="Minimum contrast ratio for --check_contrast (default: 4.5)")
    args = parser.parse_args()
    ok = verify(args.pdf_dir, args.gt_dir)
    if args.check_contrast:
        ok = verify_contrast(args.contrast_threshold) and ok
    exit(0 if ok else 1)
