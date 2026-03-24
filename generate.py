"""
generate.py
-----------
Generates 1,000 synthetic invoice PDFs with paired JSON ground truth files.
PDF and JSON are produced from the SAME data dict in a single pass,
guaranteeing every JSON field is present verbatim in its PDF.

Usage:
    python generate.py
    python generate.py --pdf_dir my_pdfs --gt_dir my_jsons --n 500

Requirements:
    pip install reportlab==4.4.10 pdfplumber==0.10.3

Seeds:
    Global sequence seed  : 42   (controls layout/currency/palette assignment)
    Per-document seed     : index * 9999 + 7  (controls all content per invoice)
"""

import argparse
import json
import os
import random
import re
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

# ── Palettes ──────────────────────────────────────────────────────────────────
PALETTES = [
    {"primary": colors.HexColor("#1a237e"), "accent": colors.HexColor("#3949ab"), "bg": colors.HexColor("#e8eaf6")},
    {"primary": colors.HexColor("#b71c1c"), "accent": colors.HexColor("#e53935"), "bg": colors.HexColor("#ffebee")},
    {"primary": colors.HexColor("#1b5e20"), "accent": colors.HexColor("#43a047"), "bg": colors.HexColor("#e8f5e9")},
    {"primary": colors.HexColor("#e65100"), "accent": colors.HexColor("#fb8c00"), "bg": colors.HexColor("#fff3e0")},
    {"primary": colors.HexColor("#212121"), "accent": colors.HexColor("#616161"), "bg": colors.HexColor("#f5f5f5")},
    {"primary": colors.HexColor("#4a148c"), "accent": colors.HexColor("#8e24aa"), "bg": colors.HexColor("#f3e5f5")},
    {"primary": colors.HexColor("#006064"), "accent": colors.HexColor("#00acc1"), "bg": colors.HexColor("#e0f7fa")},
    {"primary": colors.HexColor("#880e4f"), "accent": colors.HexColor("#d81b60"), "bg": colors.HexColor("#fce4ec")},
    {"primary": colors.HexColor("#33691e"), "accent": colors.HexColor("#7cb342"), "bg": colors.HexColor("#f1f8e9")},
    {"primary": colors.HexColor("#bf360c"), "accent": colors.HexColor("#f4511e"), "bg": colors.white},
    {"primary": colors.HexColor("#37474f"), "accent": colors.HexColor("#78909c"), "bg": colors.HexColor("#eceff1")},
    {"primary": colors.HexColor("#f57f17"), "accent": colors.HexColor("#ffca28"), "bg": colors.white},
    {"primary": colors.black,               "accent": colors.HexColor("#444444"), "bg": colors.white},
    {"primary": colors.HexColor("#1565c0"), "accent": colors.HexColor("#42a5f5"), "bg": colors.white},
    {"primary": colors.HexColor("#00695c"), "accent": colors.HexColor("#26a69a"), "bg": colors.HexColor("#e0f2f1")},
]

COMPANIES = [
    ("Apex Solutions Ltd.",       "14 Baker Street London EC1A 1BB UK",              "info@apexsolutions.co.uk",      "+44 20 7946 0958",   "VAT No: GB123456789"),
    ("NovaBridge Technologies",   "500 Silicon Ave San Jose CA 95110 USA",           "billing@novabridge.io",          "+1 408-555-0172",    "EIN: 12-3456789"),
    ("Crimson and Co.",           "3 Rue de Rivoli 75001 Paris France",              "factures@crimsonco.fr",          "+33 1 40 00 00 00",  "SIRET: 123 456 789 00012"),
    ("Pacific Rim Exports",       "88 Harbour Road Hong Kong",                       "accounts@pacificrimexports.hk",  "+852 2100 0000",     "BR No: 12345678"),
    ("MapleSoft Inc.",            "200 King St W Toronto ON M5H 3T4 Canada",         "ar@maplesoft.ca",                "+1 416-555-0199",    "GST/HST: 123456789 RT0001"),
    ("Desert Bloom LLC",          "9001 E Camelback Rd Scottsdale AZ 85251 USA",     "invoices@desertbloom.com",       "+1 480-555-0144",    "EIN: 98-7654321"),
    ("Nordic Craft AB",           "Kungsgatan 12 111 35 Stockholm Sweden",           "faktura@nordiccraft.se",         "+46 8 555 0100",     "Org.nr: 556123-4567"),
    ("IronCore Manufacturing",    "77 Steel Drive Pittsburgh PA 15201 USA",          "ar@ironcoremfg.com",             "+1 412-555-0177",    "EIN: 45-6789012"),
    ("Sunrise Digital Agency",    "12F 88 Queensway Admiralty Hong Kong",            "hello@sunrisedigital.hk",        "+852 3100 0000",     "BR No: 98765432"),
    ("BlueSky Consulting GmbH",   "Unter den Linden 21 10117 Berlin Germany",        "rechnungen@bluesky.de",          "+49 30 555 0123",    "USt-IdNr: DE123456789"),
    ("Tesseract Labs",            "2001 Infinite Loop Cupertino CA 95014 USA",       "billing@tesseractlabs.com",      "+1 408-555-0201",    "EIN: 77-8901234"),
    ("Oasis Events Co.",          "55 Palm Boulevard Dubai UAE",                     "events@oasisevents.ae",          "+971 4 555 0155",    "TRN: 100234567890003"),
    ("Greenleaf Organics",        "Farm Road 7 Burlington VT 05401 USA",             "orders@greenleaforganics.com",   "+1 802-555-0133",    "EIN: 23-4567890"),
    ("Anchor and Sail Marine",    "Port Lane 3 Auckland 1010 New Zealand",           "billing@anchorsail.nz",          "+64 9 555 0188",     "NZBN: 9429041234567"),
    ("StellarPrint Studios",      "40 Printers Row Chicago IL 60605 USA",            "invoices@stellarprint.com",      "+1 312-555-0140",    "EIN: 34-5678901"),
    ("Meridian Consulting Group", "87 Fleet Street London EC4Y 1HB UK",              "billing@meridiancg.co.uk",       "+44 20 7123 4567",   "VAT No: GB987321654"),
    ("Horizon Tech Ventures",     "3100 Hillview Ave Palo Alto CA 94304 USA",        "ar@horizontech.com",             "+1 650-555-0188",    "EIN: 55-1234567"),
    ("Lumiere Creations SARL",    "18 Bd Haussmann 75009 Paris France",              "comptabilite@lumiere-cr.fr",     "+33 1 44 00 11 22",  "SIRET: 987 654 321 00099"),
    ("Pearl River Trading Co.",   "22 Connaught Rd Central Hong Kong",               "finance@pearlriverco.hk",        "+852 2800 5500",     "BR No: 87654321"),
    ("Boreal Systems Inc.",       "1 Place Ville Marie Montreal QC H3B 4A9 Canada",  "invoices@borealsys.ca",          "+1 514-555-0120",    "GST/HST: 987654321 RT0001"),
    ("Cactus and Clay Designs",   "4501 N Central Ave Phoenix AZ 85012 USA",         "accounts@cactusclay.com",        "+1 602-555-0199",    "EIN: 11-9876543"),
    ("Fjord Analytics AS",        "Drammensveien 60 0271 Oslo Norway",               "faktura@fjordanalytics.no",      "+47 22 00 11 22",    "Org.nr: 999888777"),
    ("Ironwood Precision Mfg.",   "500 Industrial Blvd Cleveland OH 44102 USA",      "ap@ironwoodprecision.com",       "+1 216-555-0166",    "EIN: 66-7890123"),
    ("Cobalt Digital Studio",     "9F Tower 2 Times Square Causeway Bay HK",         "studio@cobaltdigital.hk",        "+852 3900 1111",     "BR No: 11223344"),
    ("Helix Beratung GmbH",       "Leopoldstrasse 82 80802 Munich Germany",          "rechnung@helix-beratung.de",     "+49 89 555 0199",    "USt-IdNr: DE345678901"),
    ("Quantum Leaf Labs",         "500 Terry Francois Blvd San Francisco CA 94158",  "billing@quantumleaf.io",         "+1 415-555-0177",    "EIN: 88-2345678"),
    ("Mirage Productions FZ-LLC", "Dubai Studio City Dubai UAE",                     "accounts@mirageproductions.ae",  "+971 4 444 0199",    "TRN: 100987654321003"),
    ("RedBark Sustainable Co.",   "22 Battery St Burlington VT 05401 USA",           "hello@redbark.com",              "+1 802-555-0177",    "EIN: 44-5678901"),
    ("Southern Cross Marine Ltd.","Princes Wharf Auckland CBD 1010 New Zealand",     "finance@southerncrossmarine.nz", "+64 9 444 0177",     "NZBN: 9429087654321"),
    ("Inkwell Publishing House",  "233 S Wacker Dr Chicago IL 60606 USA",            "billing@inkwellpub.com",         "+1 312-555-0188",    "EIN: 55-6789012"),
]

CLIENTS = [
    ("Brightside Retailers",           "99 Commerce Blvd Austin TX 78701 USA",           "ap@brightsideretail.com"),
    ("Quantum Dynamics Corp",          "1000 Innovation Pkwy Cambridge MA 02139 USA",    "accounts@quantumdynamics.com"),
    ("The Olive Branch Restaurant",    "25 Gourmet Lane New Orleans LA 70112 USA",       "finance@olivebranch.com"),
    ("Fernwood Property Group",        "300 Collins St Melbourne VIC 3000 Australia",    "ap@fernwoodproperty.com.au"),
    ("Atlas Global Shipping",          "Freihafenstr 10 20457 Hamburg Germany",          "rechnungen@atlasglobal.de"),
    ("Vanguard Healthcare",            "1 Medical Center Dr Boston MA 02115 USA",        "payables@vanguardhealth.com"),
    ("Sunrise Academy",                "10 Scholar Way Singapore 188064",                "finance@sunriseacademy.edu.sg"),
    ("TerraFirm Construction",         "88 Builders Rd Denver CO 80202 USA",             "ap@terrafirm.com"),
    ("Moonbeam Creative Studio",       "33 Artisan Alley Brooklyn NY 11201 USA",         "billing@moonbeamstudio.com"),
    ("GoldenGate Financial",           "101 Market St San Francisco CA 94105 USA",       "invoices@goldengatefin.com"),
    ("Arctic Exploration Ltd.",        "Polar Wharf 1 Tromso 9008 Norway",              "regnskap@arcticexplore.no"),
    ("Vivid Apparel Group",            "7th Ave New York NY 10018 USA",                  "ap@vividapparel.com"),
    ("ClearSky Airlines",              "Terminal 5 Heathrow London TW6 1QG UK",         "procurement@clearskyair.com"),
    ("Royal Palm Hotels",              "Beachfront Drive Miami FL 33139 USA",            "finance@royalpalmhotels.com"),
    ("Iron Horse Brewing Co.",         "2211 Brewery Way Portland OR 97201 USA",         "orders@ironhorsebrewing.com"),
    ("Cornerstone Retail Holdings",    "200 Bay St Toronto ON M5J 2J3 Canada",           "payables@cornerstoneretail.ca"),
    ("Helix Biotech Corp.",            "One Kendall Sq Cambridge MA 02139 USA",          "ap@helixbiotech.com"),
    ("The Grand Brasserie Group",      "15 Rue Montorgueil 75001 Paris France",          "comptabilite@grandbrasserie.fr"),
    ("Summit Real Estate Advisors",    "101 Collins St Melbourne VIC 3000 Australia",    "finance@summitrea.com.au"),
    ("Neptune Logistics GmbH",         "Speicherstadt 5 20457 Hamburg Germany",          "rechnungen@neptunelogistics.de"),
    ("ClearPath Medical Group",        "500 E Pratt St Baltimore MD 21202 USA",          "accounts@clearpathmed.com"),
    ("Evergreen International School", "21 Buona Vista Rd Singapore 275720",             "finance@evergreenintl.edu.sg"),
    ("Rockridge Civil Engineers",      "1600 Wynkoop St Denver CO 80202 USA",            "ap@rockridgecivil.com"),
    ("Prism Animation Works",          "45 Washington St Brooklyn NY 11201 USA",         "billing@prismanimation.com"),
    ("Apex Capital Advisors",          "555 California St San Francisco CA 94104 USA",   "invoices@apexcapital.com"),
    ("Polar Star Expeditions AS",      "Sjogata 4 9008 Tromso Norway",                  "regnskap@polarstarexp.no"),
    ("Luxe Fashion Collective",        "550 Seventh Ave New York NY 10018 USA",          "ap@luxefashion.com"),
    ("SkyBridge Aviation PLC",         "Waterside Harmondsworth UB7 0GB UK",             "procurement@skybridgeav.com"),
    ("Azure Bay Resort Group",         "1 Ocean Dr Miami Beach FL 33139 USA",            "finance@azurebayresorts.com"),
    ("Copper Kettle Brewery",          "3300 Blake St Denver CO 80205 USA",              "purchasing@copperkettlebrew.com"),
]

SERVICES = [
    ("Web Development",      85,   250,   "hrs"), ("Logo Design",           300,  2500,  "ea"),
    ("Cloud Hosting",        49,   999,   "mo"),  ("SEO Optimization",      500,  5000,  "ea"),
    ("Content Writing",      80,   400,   "pg"),  ("Mobile App Dev",        2000, 15000, "ea"),
    ("Data Analysis",        300,  3000,  "ea"),  ("Social Media Mgmt",     400,  2000,  "mo"),
    ("Legal Consultation",   150,  600,   "hr"),  ("Accounting Services",   200,  1500,  "mo"),
    ("IT Support",           75,   200,   "hr"),  ("Print Materials",       150,  800,   "lot"),
    ("Photography Session",  500,  3000,  "ea"),  ("Video Production",      1000, 10000, "ea"),
    ("Freight Forwarding",   50,   2000,  "shpt"),("Raw Materials",         5,    150,   "kg"),
    ("Office Supplies",      100,  1500,  "lot"), ("Training Workshop",     200,  1000,  "person"),
    ("Consulting Day Rate",  800,  4000,  "day"), ("Software License",      500,  10000, "seat"),
    ("Equipment Rental",     100,  1500,  "day"), ("Maintenance Contract",  200,  2000,  "mo"),
    ("Translation Services", 30,   150,   "pg"),  ("Market Research",       2000, 15000, "ea"),
    ("Event Management",     1500, 20000, "ea"),  ("Security Services",     300,  1000,  "day"),
    ("Catering Services",    25,   120,   "head"),("Architecture Fees",     2000, 50000, "ea"),
    ("Manufacturing Parts",  500,  8000,  "lot"), ("Export Documentation",  100,  500,   "ea"),
    ("Software Dev",         95,   280,   "hr"),  ("Brand Identity",        800,  6000,  "ea"),
    ("Managed Cloud",        199,  2499,  "mo"),  ("Digital Marketing",     1200, 8000,  "ea"),
    ("Tech Writing",         60,   300,   "pg"),  ("iOS App Dev",           3000, 20000, "ea"),
    ("BI Reporting",         500,  4000,  "ea"),  ("Community Mgmt",        600,  2500,  "mo"),
    ("Contract Review",      200,  800,   "hr"),  ("Bookkeeping",           300,  2000,  "mo"),
]

CURRENCIES = [
    ("USD","$"), ("EUR","€"), ("GBP","£"), ("CAD","CA$"), ("AUD","A$"),
    ("SGD","S$"), ("HKD","HK$"), ("NOK","kr"), ("SEK","kr"), ("AED","AED"),
]

PAYMENT_TERMS = [
    "Net 30","Net 15","Net 60","Due on Receipt","Net 7","2/10 Net 30",
    "50% upfront balance on delivery","End of Month","Net 45","Cash on Delivery",
    "Net 90","Immediate","Net 21","30 days from delivery","Upon completion",
]

TAXES = [
    ("VAT 20pct",0.20), ("GST 10pct",0.10), ("HST 13pct",0.13),
    ("Sales Tax 8.25pct",0.0825), ("VAT 19pct",0.19), ("Tax 7pct",0.07),
    ("GST-HST 15pct",0.15), ("VAT 21pct",0.21), ("No Tax",0.0),
    ("GST 5pct",0.05), ("VAT 23pct",0.23), ("Service Tax 6pct",0.06),
]

NOTES = [
    "Thank you for your business. We value our long-term partnership.",
    "Payment via bank transfer or credit card. Reference invoice number.",
    "Late payments subject to 1.5 percent monthly finance charge.",
    "All prices exclusive of applicable taxes unless stated otherwise.",
    "Goods remain property of seller until full payment received.",
    "Early payment discount of 2 percent available if paid within 10 days.",
    "Please direct billing queries to our accounts department.",
    "This invoice is computer-generated and is valid without a signature.",
    "Disputes must be raised within 14 days of invoice date.",
    "Our standard warranty terms apply to all goods and services.",
    "This document is strictly private and confidential.",
    "All work performed in accordance with the signed service agreement.",
    "Subject to our standard terms and conditions of service.",
    "Payment accepted via SWIFT SEPA or major credit cards.",
    "Please retain this invoice for your accounting records.",
]

BANK_DETAILS = [
    {"Bank": "Chase Bank",      "Account": "1234567890", "Routing": "021000021",       "SWIFT": "CHASUS33"},
    {"Bank": "Barclays Bank",   "Sort Code": "20-00-01", "Account": "87654321",         "IBAN": "GB12BARC20000187654321"},
    {"Bank": "Deutsche Bank",   "IBAN": "DE89370400440532013000",                       "BIC": "DEUTDEDB370"},
    {"Bank": "HSBC Hong Kong",  "Account": "400-123456-001",                            "SWIFT": "HSBCHKHHHKH"},
    {"Bank": "TD Bank Canada",  "Transit": "00000",      "Institution": "004",          "Account": "1234567"},
    {"Bank": "Westpac",         "BSB": "032-000",        "Account": "123456",           "SWIFT": "WPACAU2S"},
    {"Bank": "DBS Bank",        "Account": "012-345678-9",                              "SWIFT": "DBSSSGSG"},
    {"Bank": "DNB Bank ASA",    "Account": "1503.12.34567",                             "BIC": "DNBANOKK"},
    {"Bank": "Handelsbanken",   "Account": "123 456 789", "Clearing": "6000",          "IBAN": "SE4560000000012345678901"},
    {"Bank": "Emirates NBD",    "IBAN": "AE070331234567890123456",                      "SWIFT": "EBILAEAD"},
]

LAYOUT_STYLES    = ["classic","modern","minimal","ledger","bold_header",
                    "sidebar","two_tone","formal","creative","compact"]
COMPLEXITY_TIERS = ["simple","medium","complex","very_complex"]
COMPLEXITY_RANGE = {"simple":(1,3),"medium":(3,7),"complex":(7,14),"very_complex":(14,25)}
DATE_FORMATS     = ["%d %B %Y","%B %d %Y","%d/%m/%Y","%m/%d/%Y","%Y-%m-%d","%d-%b-%Y"]
PAGE_SIZES       = {"A4": A4, "letter": letter}
INV_PREFIXES     = ["INV","INVOICE","SI","TAX-INV","BILL","REF","PROFORMA","RCPT"]

# ── CRITICAL FIX 1: fmt_money always symbol-first, no trailing variant ────────
def fmt_money(amount, sym):
    return f"{sym}{amount:,.2f}"

def fmt_date(d, rng):
    fmt = rng.choice(DATE_FORMATS)
    try:    return d.strftime(fmt)
    except: return d.strftime("%Y-%m-%d")


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


def pick_text_color(bg, preferred=colors.white):
    choices = []
    if preferred is not None:
        choices.append(preferred)
    choices.extend([colors.black, colors.white])

    best = max(choices, key=lambda c: contrast_ratio(bg, c))
    if preferred is not None and contrast_ratio(bg, preferred) >= 4.5:
        return preferred
    return best

# ── Balanced sequence builder ─────────────────────────────────────────────────
def balanced_seq(pool, n, weights=None):
    if weights:
        seq = []
        for item, w in zip(pool, weights):
            seq += [item] * round(w * n)
        while len(seq) < n: seq.append(random.choice(pool))
        seq = seq[:n]
    else:
        base = n // len(pool)
        seq  = pool * base
        seq += random.choices(pool, k=n - len(seq))
    random.shuffle(seq)
    return seq

# ── Data builder ──────────────────────────────────────────────────────────────
def build(idx, layout, complexity, cur_idx, ps_name, pal_idx):
    rng = random.Random(idx * 9999 + 7)

    seller   = rng.choice(COMPANIES)
    client   = rng.choice(CLIENTS)
    cur, sym = CURRENCIES[cur_idx]
    pal      = PALETTES[pal_idx]

    issue  = datetime(2022,1,1) + timedelta(days=rng.randint(0, 3*365))
    due    = issue + timedelta(days=rng.choice([7,14,15,21,30,45,60,90]))

    lo, hi  = COMPLEXITY_RANGE[complexity]
    n_items = rng.randint(lo, hi)
    svc_pool = rng.sample(SERVICES, min(n_items, len(SERVICES)))

    items = []
    for name, low, high, unit in svc_pool:
        qty   = rng.choice([1,1,1,2,3,5,10,25,50])
        price = round(rng.uniform(low, high), 2)
        disc  = rng.choice([0,0,0,5,10,15,20]) if n_items > 3 else 0
        total = round(qty * price * (1 - disc/100), 2)
        items.append({"description": name, "unit": unit, "quantity": qty,
                      "unit_price": price, "discount_pct": disc, "line_total": total})

    subtotal  = round(sum(i["line_total"] for i in items), 2)
    tax_lbl, tax_rate = rng.choice(TAXES)
    tax_amt   = round(subtotal * tax_rate, 2)
    has_ship  = complexity in ("complex","very_complex") and rng.random() < 0.4
    shipping  = round(rng.uniform(15, 300), 2) if has_ship else 0.0
    total_due = round(subtotal + tax_amt + shipping, 2)

    notes    = rng.choice(NOTES)        if rng.random() < 0.70 else None
    bank     = rng.choice(BANK_DETAILS) if rng.random() < 0.60 else None
    po_num   = f"PO-{rng.randint(10000,99999)}" if rng.random() < 0.40 else None
    show_unit = rng.random() < 0.60
    show_disc = any(i["discount_pct"] for i in items) and rng.random() < 0.60

    # invoice number — deterministic per invoice
    rng2 = random.Random(idx * 3571)
    p = rng2.choice(INV_PREFIXES); y = rng2.randint(2022,2025); n = rng2.randint(1000,99999)
    inv_no = rng2.choice([f"{p}-{n}", f"{p}/{y}/{n:05d}", f"{y}-{n}", f"{p}-{y}-{n}", f"{n:06d}", f"{p}{n}"])

    issue_str = fmt_date(issue, rng)
    due_str   = fmt_date(due, rng)
    terms     = rng.choice(PAYMENT_TERMS)

    return {
        # ground-truth fields — written to JSON AND rendered to PDF
        "id":                  idx,
        "filename":            f"invoice_{idx:03d}.pdf",
        "layout_style":        layout,
        "page_size":           ps_name,
        "complexity_tier":     complexity,
        "color_palette_index": pal_idx,
        "invoice_number":      inv_no,
        "issue_date":          issue_str,
        "due_date":            due_str,
        "payment_terms":       terms,
        "currency":            cur,
        "currency_symbol":     sym,
        "po_number":           po_num,
        "seller_name":         seller[0],
        "seller_address":      seller[1],
        "seller_email":        seller[2],
        "seller_phone":        seller[3],
        "seller_tax_id":       seller[4],
        "client_name":         client[0],
        "client_address":      client[1],
        "client_email":        client[2],
        "num_line_items":      len(items),
        "line_items":          items,
        "subtotal":            subtotal,
        "tax_label":           tax_lbl,
        "tax_rate_pct":        round(tax_rate * 100, 4),
        "tax_amount":          tax_amt,
        "shipping_amount":     shipping,
        "total_due":           total_due,
        "notes":               notes,
        "bank_details":        bank,
        "has_logo":            True,
        "has_discount_column": show_disc,
        "has_unit_column":     show_unit,
        "has_notes":           notes is not None,
        "has_bank_details":    bank is not None,
        "has_shipping":        shipping > 0,
        "has_po_number":       po_num is not None,
        "has_tax":             tax_rate > 0,
        # render-only (not in JSON)
        "_pal": pal, "_sym": sym, "_ps": PAGE_SIZES[ps_name],
    }

# ── PDF helpers ───────────────────────────────────────────────────────────────
def draw_logo(c, x, y, size, pal, name):
    initials = "".join(w[0] for w in name.split()[:2]).upper()
    style = hash(name) % 6
    p, a  = pal["primary"], pal["accent"]
    logo_txt = pick_text_color(p)
    if style == 0:
        c.setFillColor(p); c.circle(x+size/2,y+size/2,size/2,fill=1,stroke=0)
        c.setFillColor(logo_txt); c.setFont("Helvetica-Bold",size*0.4)
        c.drawCentredString(x+size/2,y+size/2-size*0.15,initials)
    elif style == 1:
        c.setFillColor(p); c.rect(x,y,size,size,fill=1,stroke=0)
        c.setFillColor(logo_txt); c.setFont("Helvetica-Bold",size*0.38)
        c.drawCentredString(x+size/2,y+size/2-size*0.15,initials)
    elif style == 2:
        path=c.beginPath(); path.moveTo(x+size/2,y+size); path.lineTo(x+size,y+size/2)
        path.lineTo(x+size/2,y); path.lineTo(x,y+size/2); path.close()
        c.setFillColor(p); c.drawPath(path,fill=1,stroke=0)
        c.setFillColor(logo_txt); c.setFont("Helvetica-Bold",size*0.3)
        c.drawCentredString(x+size/2,y+size/2-size*0.12,initials)
    elif style == 3:
        c.setFillColor(p); c.circle(x+size*0.35,y+size/2,size*0.38,fill=1,stroke=0)
        c.setFillColor(a); c.circle(x+size*0.65,y+size/2,size*0.38,fill=1,stroke=0)
    elif style == 4:
        c.setFillColor(p); c.roundRect(x,y,size,size,size*0.2,fill=1,stroke=0)
        c.setFillColor(logo_txt); c.setFont("Helvetica-Bold",size*0.38)
        c.drawCentredString(x+size/2,y+size/2-size*0.15,initials)
    else:
        bh=size*0.22
        for i2,col in enumerate([p,a,p]):
            c.setFillColor(col); c.rect(x,y+i2*(bh+size*0.07),size,bh,fill=1,stroke=0)

def draw_table(c, d, x, y, width, row_h=0.65*cm, fs=8.5):
    pal=d["_pal"]; sym=d["_sym"]; items=d["line_items"]
    sd=d["has_discount_column"]; su=d["has_unit_column"]
    if sd and su:
        cols=[width*0.35,width*0.07,width*0.08,width*0.14,width*0.08,width*0.16,width*0.12]; hdrs=["Description","Unit","Qty","Unit Price","Disc%","Amount",""]
    elif sd:
        cols=[width*0.42,width*0.08,width*0.14,width*0.10,width*0.16,width*0.10]; hdrs=["Description","Qty","Unit Price","Disc%","Amount",""]
    elif su:
        cols=[width*0.42,width*0.08,width*0.10,width*0.16,width*0.14,width*0.10]; hdrs=["Description","Unit","Qty","Unit Price","Amount",""]
    else:
        cols=[width*0.50,width*0.10,width*0.17,width*0.14,width*0.09]; hdrs=["Description","Qty","Unit Price","Amount",""]
    cols=cols[:-1]; hdrs=hdrs[:-1]
    hh=row_h*1.1
    c.setFillColor(pal["primary"]); c.rect(x,y-hh,width,hh,fill=1,stroke=0)
    c.setFillColor(pick_text_color(pal["primary"])); c.setFont("Helvetica-Bold",fs-0.5)
    cx=x
    for i,(hdr,cw) in enumerate(zip(hdrs,cols)):
        if i==0: c.drawString(cx+0.15*cm,y-hh+0.2*cm,hdr)
        else:    c.drawRightString(cx+cw-0.1*cm,y-hh+0.2*cm,hdr)
        cx+=cw
    y-=hh
    for ri,item in enumerate(items):
        c.setFillColor(pal["bg"] if ri%2==0 else colors.white)
        c.rect(x,y-row_h,width,row_h,fill=1,stroke=0)
        c.setFillColor(colors.black); c.setFont("Helvetica",fs)
        vals=[item["description"][:40]]
        if su: vals.append(item["unit"])
        vals.append(str(item["quantity"]))
        vals.append(fmt_money(item["unit_price"],sym))
        if sd: vals.append(f"{item['discount_pct']}%" if item["discount_pct"] else "0%")
        vals.append(fmt_money(item["line_total"],sym))
        cx=x
        for i,(val,cw) in enumerate(zip(vals,cols)):
            if i==0: c.drawString(cx+0.15*cm,y-row_h+0.18*cm,val)
            else:    c.drawRightString(cx+cw-0.1*cm,y-row_h+0.18*cm,val)
            cx+=cw
        y-=row_h
    y-=0.2*cm
    c.setStrokeColor(pal["primary"]); c.setLineWidth(0.5); c.line(x,y,x+width,y)
    tx=x+width*0.58; tw=width*0.42
    def trow(lbl,amt,bold=False,bg=None):
        nonlocal y; y-=row_h
        if bg: c.setFillColor(bg); c.rect(tx,y,tw,row_h,fill=1,stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold" if bold else "Helvetica",fs)
        c.drawString(tx+0.2*cm,y+0.18*cm,lbl)
        c.drawRightString(tx+tw-0.15*cm,y+0.18*cm,amt)
    trow("Subtotal:",fmt_money(d["subtotal"],sym))
    if d["has_tax"]:    trow(f"{d['tax_label']}:",fmt_money(d["tax_amount"],sym))
    if d["has_shipping"]:trow("Shipping:",fmt_money(d["shipping_amount"],sym))
    trow("TOTAL DUE:",fmt_money(d["total_due"],sym),bold=True,bg=pal["bg"])
    y-=0.4*cm
    if d["notes"]:
        c.setFont("Helvetica-Oblique",fs-1); c.setFillColor(colors.HexColor("#555"))
        c.drawString(x,y,f"Note: {d['notes'][:100]}"); y-=0.4*cm
    if d["bank_details"]:
        c.setFont("Helvetica-Bold",fs-1); c.setFillColor(pick_text_color(colors.white, preferred=pal["primary"]))
        c.drawString(x,y,"BANK DETAILS"); y-=0.35*cm
        c.setFont("Helvetica",fs-1); c.setFillColor(colors.black)
        parts=[f"{k}: {v}" for k,v in d["bank_details"].items()]
        line="  |  ".join(parts)
        if len(line)>90:
            mid=len(parts)//2
            c.drawString(x,y,"  |  ".join(parts[:mid])); y-=0.3*cm
            c.drawString(x,y,"  |  ".join(parts[mid:]))
        else:
            c.drawString(x,y,line)
    return y

# ── Meta info block (currency + PO always shown) ──────────────────────────────
def draw_meta(c, d, x, y, fs=9):
    """Draw invoice number, dates, terms, currency code, PO — ALL guaranteed visible."""
    c.setFillColor(colors.black); c.setFont("Helvetica",fs)
    lines = [
        f"Invoice No:  {d['invoice_number']}",
        f"Date:        {d['issue_date']}",
        f"Due Date:    {d['due_date']}",
        f"Terms:       {d['payment_terms']}",
        f"Currency:    {d['currency']}",
    ]
    if d["po_number"]:
        lines.append(f"PO Number:   {d['po_number']}")
    for i,l in enumerate(lines):
        c.drawString(x, y-i*0.5*cm, l)


def wrap_text_to_width(c, text, max_width, font_name="Helvetica", font_size=8.5):
    text = str(text)
    if not text:
        return [""]
    words = text.split()
    if not words:
        return [text]

    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if c.stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_wrapped_center(c, text, center_x, y_top, max_width,
                        font_name="Helvetica", font_size=8, line_h=0.38*cm, max_lines=None):
    lines = wrap_text_to_width(c, text, max_width, font_name, font_size)
    if max_lines is not None:
        lines = lines[:max_lines]
    c.setFont(font_name, font_size)
    y = y_top
    for line in lines:
        c.drawCentredString(center_x, y, line)
        y -= line_h
    return y


def draw_fit_text(c, text, x, y, max_width,
                  font_name="Helvetica", font_size=10, min_size=6):
    txt = str(text)
    size = float(font_size)
    while size > min_size and c.stringWidth(txt, font_name, size) > max_width:
        size -= 0.25
    if size < min_size:
        size = min_size
    c.setFont(font_name, size)
    c.drawString(x, y, txt)
    return size

# ── Layout renderers ──────────────────────────────────────────────────────────
def r_classic(c,d,W,H):
    pal=d["_pal"]; sym=d["_sym"]; m=2*cm
    header_txt = pick_text_color(pal["primary"])
    ink_on_white = pick_text_color(colors.white, preferred=pal["primary"])
    left_x = m + 2.2*cm
    right_col_start = W - 8.0*cm
    left_max_w = max(4.0*cm, right_col_start - left_x - 0.2*cm)
    c.setFillColor(pal["primary"]); c.rect(0,H-3.2*cm,W,3.2*cm,fill=1,stroke=0)
    draw_logo(c,m,H-2.8*cm,1.8*cm,pal,d["seller_name"])
    c.setFillColor(header_txt)
    draw_fit_text(c, d["seller_name"], left_x, H-1.5*cm, left_max_w,
                  font_name="Helvetica-Bold", font_size=14, min_size=8)
    draw_fit_text(c, d["seller_address"], left_x, H-2.1*cm, left_max_w,
                  font_name="Helvetica", font_size=8, min_size=6)
    draw_fit_text(c, d["seller_email"], left_x, H-2.6*cm, left_max_w,
                  font_name="Helvetica", font_size=8, min_size=6)
    c.setFont("Helvetica-Bold",22); c.drawRightString(W-m,H-1.5*cm,"INVOICE")
    c.setFont("Helvetica",9); c.setFillColor(header_txt)
    c.drawRightString(W-m,H-2.2*cm,f"No: {d['invoice_number']}")
    y=H-4*cm
    c.setFillColor(pal["bg"]); c.rect(W-7.5*cm,y-3.2*cm,5.5*cm,3.2*cm,fill=1,stroke=0)
    c.setFillColor(colors.black); c.setFont("Helvetica",8.5)
    c.drawString(W-7.2*cm,y-0.45*cm,f"Date:     {d['issue_date']}")
    c.drawString(W-7.2*cm,y-0.95*cm,f"Due:      {d['due_date']}")
    c.drawString(W-7.2*cm,y-1.45*cm,f"Terms:    {d['payment_terms']}")
    c.drawString(W-7.2*cm,y-1.95*cm,f"Currency: {d['currency']}")
    if d["po_number"]: c.drawString(W-7.2*cm,y-2.45*cm,f"PO:       {d['po_number']}")
    c.setFont("Helvetica-Bold",9); c.setFillColor(ink_on_white); c.drawString(m,y-0.4*cm,"BILL TO")
    c.setFont("Helvetica",9); c.setFillColor(colors.black)
    c.drawString(m,y-0.9*cm,d["client_name"]); c.drawString(m,y-1.4*cm,d["client_address"])
    c.drawString(m,y-1.9*cm,d["client_email"])
    draw_table(c,d,m,y-3.2*cm,W-2*m)
    c.setFillColor(pal["primary"]); c.rect(0,0,W,1.2*cm,fill=1,stroke=0)
    c.setFillColor(pick_text_color(pal["primary"])); c.setFont("Helvetica",7)
    c.drawCentredString(W/2,0.45*cm,f"{d['seller_name']}  |  {d['seller_tax_id']}  |  {d['seller_email']}")

def r_modern(c,d,W,H):
    pal=d["_pal"]; m=2*cm
    ink_on_white = pick_text_color(colors.white, preferred=pal["primary"])
    ink_on_bg = pick_text_color(pal["bg"], preferred=pal["primary"])
    c.setFillColor(pal["primary"]); c.rect(0,0,0.8*cm,H,fill=1,stroke=0)
    c.setFillColor(pal["accent"]);  c.rect(0,H-0.5*cm,W,0.5*cm,fill=1,stroke=0)
    y=H-1.5*cm
    c.setFillColor(ink_on_white); c.setFont("Helvetica-Bold",18); c.drawString(m,y,d["seller_name"])
    c.setFont("Helvetica",8); c.setFillColor(colors.HexColor("#555"))
    c.drawString(m,y-0.55*cm,d["seller_address"]); c.drawString(m,y-1.0*cm,d["seller_email"])
    draw_logo(c,W-m-2*cm,H-2.6*cm,2*cm,pal,d["seller_name"])
    y-=2*cm; c.setStrokeColor(pal["accent"]); c.setLineWidth(2); c.line(m,y,W-m,y); y-=0.8*cm
    c.setFillColor(pal["primary"]); c.roundRect(m,y-0.7*cm,3*cm,0.9*cm,0.2*cm,fill=1,stroke=0)
    c.setFillColor(pick_text_color(pal["primary"])); c.setFont("Helvetica-Bold",11); c.drawCentredString(m+1.5*cm,y-0.2*cm,"INVOICE")
    c.setFillColor(colors.black); c.setFont("Helvetica",9)
    c.drawString(m+3.4*cm,y-0.15*cm,f"No: {d['invoice_number']}")
    c.drawString(m+3.4*cm,y-0.55*cm,f"Date: {d['issue_date']}  Due: {d['due_date']}")
    y-=1.8*cm; half=(W-2*m)/2
    c.setFillColor(pal["bg"]); c.rect(m,y-2.6*cm,half-0.3*cm,2.6*cm,fill=1,stroke=0)
    c.setFillColor(ink_on_bg); c.setFont("Helvetica-Bold",8); c.drawString(m+0.3*cm,y-0.4*cm,"BILL TO")
    c.setFont("Helvetica",8.5); c.setFillColor(colors.black)
    c.drawString(m+0.3*cm,y-0.8*cm,d["client_name"]); c.drawString(m+0.3*cm,y-1.2*cm,d["client_address"])
    c.drawString(m+0.3*cm,y-1.6*cm,d["client_email"])
    c.setFillColor(pal["bg"]); c.rect(m+half+0.3*cm,y-2.6*cm,half-0.3*cm,2.6*cm,fill=1,stroke=0)
    c.setFillColor(ink_on_bg); c.setFont("Helvetica-Bold",8); c.drawString(m+half+0.6*cm,y-0.4*cm,"PAYMENT INFO")
    c.setFont("Helvetica",8.5); c.setFillColor(colors.black)
    c.drawString(m+half+0.6*cm,y-0.8*cm,f"Terms:    {d['payment_terms']}")
    c.drawString(m+half+0.6*cm,y-1.2*cm,f"Currency: {d['currency']}")
    c.drawString(m+half+0.6*cm,y-1.6*cm,f"Due:      {d['due_date']}")
    if d["po_number"]: c.drawString(m+half+0.6*cm,y-2.0*cm,f"PO:       {d['po_number']}")
    draw_table(c,d,m,y-3.2*cm,W-2*m)
    c.setFillColor(colors.HexColor("#888")); c.setFont("Helvetica",7)
    c.drawCentredString(W/2,0.7*cm,f"{d['seller_name']}  |  {d['seller_tax_id']}  |  {d['seller_email']}")

def r_minimal(c,d,W,H):
    pal=d["_pal"]; m=2.5*cm
    ink_on_white = pick_text_color(colors.white, preferred=pal["primary"])
    c.setStrokeColor(pal["primary"]); c.setLineWidth(3); c.line(m,H-1.5*cm,W-m,H-1.5*cm)
    c.setFillColor(ink_on_white); c.setFont("Helvetica-Bold",24); c.drawString(m,H-2.4*cm,"INVOICE")
    c.setFont("Helvetica",9); c.setFillColor(colors.HexColor("#333"))
    c.drawString(m,H-3.0*cm,d["seller_name"]); c.drawString(m,H-3.5*cm,d["seller_address"])
    c.drawString(m,H-4.0*cm,d["seller_email"])
    c.setFont("Helvetica-Bold",9); c.drawRightString(W-m,H-2.4*cm,f"No. {d['invoice_number']}")
    c.setFont("Helvetica",9)
    c.drawRightString(W-m,H-3.0*cm,d["issue_date"])
    c.drawRightString(W-m,H-3.5*cm,f"Due: {d['due_date']}")
    c.drawRightString(W-m,H-4.0*cm,f"Terms: {d['payment_terms']}")
    c.drawRightString(W-m,H-4.5*cm,f"Currency: {d['currency']}")
    if d["po_number"]: c.drawRightString(W-m,H-5.0*cm,f"PO: {d['po_number']}")
    c.setLineWidth(0.5); c.line(m,H-5.5*cm,W-m,H-5.5*cm)
    c.setFont("Helvetica-Bold",9); c.setFillColor(colors.black); c.drawString(m,H-6.1*cm,"TO:")
    c.setFont("Helvetica",9)
    c.drawString(m+0.8*cm,H-6.1*cm,d["client_name"]); c.drawString(m+0.8*cm,H-6.6*cm,d["client_address"])
    c.drawString(m+0.8*cm,H-7.1*cm,d["client_email"])
    draw_table(c,d,m,H-7.8*cm,W-2*m)
    c.setStrokeColor(pal["primary"]); c.setLineWidth(1); c.line(m,1.5*cm,W-m,1.5*cm)
    c.setFont("Helvetica",7); c.setFillColor(colors.HexColor("#666"))
    c.drawString(m,1.0*cm,f"{d['seller_name']}  |  {d['seller_tax_id']}")

def r_ledger(c,d,W,H):
    pal=d["_pal"]; sym=d["_sym"]; m=1.5*cm
    ledger_bg = colors.HexColor("#2d4a1e")
    ledger_txt = pick_text_color(ledger_bg)
    c.setFillColor(ledger_bg); c.rect(0,H-2.5*cm,W,2.5*cm,fill=1,stroke=0)
    c.setFillColor(ledger_txt); c.setFont("Helvetica-Bold",16); c.drawString(m,H-1.2*cm,"SALES LEDGER INVOICE")
    c.setFont("Helvetica",8); c.drawString(m,H-1.8*cm,d["seller_name"])
    c.drawString(m,H-2.2*cm,d["seller_address"])
    c.drawRightString(W-m,H-1.2*cm,f"No: {d['invoice_number']}"); c.drawRightString(W-m,H-1.8*cm,d["issue_date"])
    c.setFillColor(colors.black); c.setFont("Helvetica",8.5); y=H-3.2*cm
    c.drawString(m,y,f"Account: {d['client_name']}"); c.drawString(m,y-0.5*cm,d["client_address"])
    c.drawString(m,y-1.0*cm,d["client_email"])
    c.drawRightString(W-m,y,f"Due: {d['due_date']}"); c.drawRightString(W-m,y-0.5*cm,f"Terms: {d['payment_terms']}")
    c.drawRightString(W-m,y-1.0*cm,f"Currency: {d['currency']}")
    if d["po_number"]: c.drawRightString(W-m,y-1.5*cm,f"PO: {d['po_number']}")
    y-=2.2*cm; tw=W-2*m; cw=[1.5*cm,tw*0.42,3*cm,3*cm,3*cm]; rh=0.6*cm
    c.setFillColor(ledger_bg); c.rect(m,y-rh,tw,rh,fill=1,stroke=0)
    c.setFillColor(ledger_txt); c.setFont("Helvetica-Bold",8)
    offs=[m,m+cw[0],m+cw[0]+cw[1],m+sum(cw[:3]),m+sum(cw[:4])]
    for hdr,ox in zip(["Ref","Particulars","Debit","Credit","Balance"],offs): c.drawString(ox+0.1*cm,y-rh+0.2*cm,hdr)
    y-=rh; running=0.0
    for i,item in enumerate(d["line_items"]):
        running+=item["line_total"]
        c.setFillColor(colors.HexColor("#f0fff0") if i%2==0 else colors.white)
        c.rect(m,y-rh,tw,rh,fill=1,stroke=0); c.setFillColor(colors.black); c.setFont("Helvetica",8)
        for val,ox in zip([f"L{i+1:03d}",item["description"][:36],fmt_money(item["line_total"],sym),"",fmt_money(running,sym)],offs):
            c.drawString(ox+0.1*cm,y-rh+0.18*cm,val)
        y-=rh
    if d["has_tax"]:
        running+=d["tax_amount"]
        c.setFillColor(colors.HexColor("#e8f5e9")); c.rect(m,y-rh,tw,rh,fill=1,stroke=0)
        c.setFillColor(colors.black); c.setFont("Helvetica",8)
        for val,ox in zip(["TAX",d["tax_label"],fmt_money(d["tax_amount"],sym),"",fmt_money(running,sym)],offs):
            c.drawString(ox+0.1*cm,y-rh+0.18*cm,val)
        y-=rh
    if d["has_shipping"]:
        running+=d["shipping_amount"]
        c.setFillColor(colors.HexColor("#e8f5e9")); c.rect(m,y-rh,tw,rh,fill=1,stroke=0)
        c.setFillColor(colors.black); c.setFont("Helvetica",8)
        for val,ox in zip(["SHIP","Shipping",fmt_money(d["shipping_amount"],sym),"",fmt_money(running,sym)],offs):
            c.drawString(ox+0.1*cm,y-rh+0.18*cm,val)
        y-=rh
    c.setFillColor(ledger_bg); c.rect(m,y-rh,tw,rh,fill=1,stroke=0)
    c.setFillColor(ledger_txt); c.setFont("Helvetica-Bold",8)
    for val,ox in zip(["TOTAL","AMOUNT DUE",fmt_money(d["total_due"],sym)],[m,m+cw[0],m+cw[0]+cw[1]]):
        c.drawString(ox+0.1*cm,y-rh+0.2*cm,val)
    y-=rh+0.3*cm
    if d["notes"]: c.setFont("Helvetica-Oblique",7.5); c.setFillColor(colors.black); c.drawString(m,y,f"Note: {d['notes'][:90]}"); y-=0.4*cm
    if d["bank_details"]:
        c.setFont("Helvetica-Bold",7.5); c.drawString(m,y,f"Bank: {d['bank_details'].get('Bank','')}"); y-=0.35*cm
        c.setFont("Helvetica",7.5)
        parts=[f"{k}: {v}" for k,v in d["bank_details"].items()]
        c.drawString(m,y,"  |  ".join(parts)[:110])
    c.setFillColor(ledger_bg); c.rect(0,0,W,0.8*cm,fill=1,stroke=0)
    c.setFillColor(ledger_txt); c.setFont("Helvetica",6.5)
    c.drawCentredString(W/2,0.25*cm,f"{d['seller_name']}  |  {d['seller_tax_id']}  |  {d['seller_email']}")

def r_bold_header(c,d,W,H):
    pal=d["_pal"]; m=1.8*cm; hh=4.5*cm
    header_txt = pick_text_color(pal["primary"])
    ink_on_bg = pick_text_color(pal["bg"], preferred=pal["primary"])
    c.setFillColor(pal["primary"]); c.rect(0,H-hh,W,hh,fill=1,stroke=0)
    c.setFillColor(pal["accent"])
    path=c.beginPath(); path.moveTo(W*0.55,H-hh); path.lineTo(W,H-hh); path.lineTo(W,H); path.lineTo(W*0.75,H); path.close()
    c.drawPath(path,fill=1,stroke=0)
    draw_logo(c,W-m-2.5*cm,H-hh+0.5*cm,2.2*cm,pal,d["seller_name"])
    c.setFillColor(header_txt); c.setFont("Helvetica-Bold",20); c.drawString(m,H-1.6*cm,d["seller_name"])
    c.setFont("Helvetica",8); c.drawString(m,H-2.2*cm,d["seller_address"]); c.drawString(m,H-2.7*cm,d["seller_email"])
    c.setFont("Helvetica-Bold",28); c.drawRightString(W-m-3*cm,H-2.2*cm,"INVOICE")
    c.setFont("Helvetica",9); c.drawRightString(W-m-3*cm,H-2.8*cm,f"No: {d['invoice_number']}")
    y=H-hh-0.8*cm; bw=(W-2*m-0.5*cm)/2
    c.setFillColor(pal["bg"]); c.rect(m,y-2.5*cm,bw,2.5*cm,fill=1,stroke=0)
    c.setFont("Helvetica-Bold",8); c.setFillColor(ink_on_bg); c.drawString(m+0.3*cm,y-0.4*cm,"BILLED TO")
    c.setFont("Helvetica",8.5); c.setFillColor(colors.black)
    c.drawString(m+0.3*cm,y-0.8*cm,d["client_name"]); c.drawString(m+0.3*cm,y-1.2*cm,d["client_address"]); c.drawString(m+0.3*cm,y-1.6*cm,d["client_email"])
    c.setFillColor(pal["bg"]); c.rect(m+bw+0.5*cm,y-2.5*cm,bw,2.5*cm,fill=1,stroke=0)
    c.setFont("Helvetica-Bold",8); c.setFillColor(ink_on_bg); c.drawString(m+bw+0.8*cm,y-0.4*cm,"INVOICE DETAILS")
    c.setFont("Helvetica",8.5); c.setFillColor(colors.black)
    c.drawString(m+bw+0.8*cm,y-0.8*cm,f"Date:     {d['issue_date']}")
    c.drawString(m+bw+0.8*cm,y-1.2*cm,f"Due:      {d['due_date']}")
    c.drawString(m+bw+0.8*cm,y-1.6*cm,f"Currency: {d['currency']}")
    c.drawString(m+bw+0.8*cm,y-2.0*cm,f"Terms:    {d['payment_terms']}")
    if d["po_number"]: c.drawString(m+bw+0.8*cm,y-2.4*cm,f"PO:       {d['po_number']}")
    draw_table(c,d,m,y-3.2*cm,W-2*m)
    c.setFillColor(pal["primary"]); c.rect(0,0,W,1*cm,fill=1,stroke=0)
    c.setFillColor(pick_text_color(pal["primary"])); c.setFont("Helvetica",7)
    c.drawCentredString(W/2,0.35*cm,f"{d['seller_name']}  |  {d['seller_email']}  |  {d['seller_tax_id']}")

def r_sidebar(c,d,W,H):
    pal=d["_pal"]; sbw=5.5*cm
    sidebar_txt = pick_text_color(pal["primary"])
    c.setFillColor(pal["primary"]); c.rect(0,0,sbw,H,fill=1,stroke=0)
    draw_logo(c,sbw*0.2,H-2.5*cm,1.8*cm,pal,d["seller_name"])
    c.setFillColor(sidebar_txt)
    y_name_end = draw_wrapped_center(c, d["seller_name"], sbw/2, H-3.2*cm, sbw-0.6*cm,
                                     font_name="Helvetica-Bold", font_size=8.5, line_h=0.35*cm, max_lines=2)
    y_addr_end = draw_wrapped_center(c, d["seller_address"], sbw/2, y_name_end-0.05*cm, sbw-0.6*cm,
                                     font_name="Helvetica", font_size=7, line_h=0.32*cm, max_lines=3)
    draw_wrapped_center(c, d["seller_email"], sbw/2, y_addr_end-0.05*cm, sbw-0.6*cm,
                        font_name="Helvetica", font_size=7, line_h=0.32*cm, max_lines=2)
    c.drawCentredString(sbw/2,H-5.15*cm,d["seller_phone"])
    labels=[("INVOICE NO",d["invoice_number"]),("DATE",d["issue_date"]),
            ("DUE DATE",d["due_date"]),("TERMS",d["payment_terms"]),
            ("CURRENCY",d["currency"])]
    if d["po_number"]: labels.append(("PO NUMBER",d["po_number"]))
    yl=H-6.3*cm
    for lbl,val in labels:
        c.setFillColor(pick_text_color(pal["primary"], preferred=pal["accent"])); c.setFont("Helvetica-Bold",6.5); c.drawCentredString(sbw/2,yl,lbl)
        c.setFillColor(sidebar_txt)
        y_end = draw_wrapped_center(c, str(val), sbw/2, yl-0.35*cm, sbw-0.5*cm,
                                    font_name="Helvetica", font_size=7.2, line_h=0.30*cm, max_lines=2)
        yl = y_end - 0.25*cm
    mx=sbw+1*cm; cw2=W-mx-1*cm
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold",18); c.drawString(mx,H-1.5*cm,"INVOICE")
    c.setFont("Helvetica-Bold",9); c.drawString(mx,H-2.5*cm,"BILLED TO:")
    c.setFont("Helvetica",9)
    c.drawString(mx,H-3.0*cm,d["client_name"]); c.drawString(mx,H-3.5*cm,d["client_address"]); c.drawString(mx,H-4.0*cm,d["client_email"])
    draw_table(c,d,mx,H-5.5*cm,cw2)

def r_two_tone(c,d,W,H):
    pal=d["_pal"]; m=2*cm; split=H*0.42
    top_txt = pick_text_color(pal["primary"])
    ink_on_white = pick_text_color(colors.white, preferred=pal["primary"])
    ink_on_bg = pick_text_color(pal["bg"], preferred=pal["primary"])
    left_x = m + 2.8*cm
    right_col_start = W - m - 6.8*cm
    left_max_w = max(3.8*cm, right_col_start - left_x - 0.2*cm)
    c.setFillColor(pal["primary"]); c.rect(0,split,W,H-split,fill=1,stroke=0)
    draw_logo(c,m,H-3*cm,2.2*cm,pal,d["seller_name"])
    c.setFillColor(top_txt)
    draw_fit_text(c, d["seller_name"], left_x, H-1.8*cm, left_max_w,
                  font_name="Helvetica-Bold", font_size=16, min_size=9)
    draw_fit_text(c, d["seller_address"], left_x, H-2.4*cm, left_max_w,
                  font_name="Helvetica", font_size=8, min_size=6)
    draw_fit_text(c, d["seller_email"], left_x, H-3.0*cm, left_max_w,
                  font_name="Helvetica", font_size=8, min_size=6)
    c.setFont("Helvetica-Bold",26); c.drawRightString(W-m,H-1.8*cm,"INVOICE")
    c.setFont("Helvetica",9)
    c.drawRightString(W-m,H-2.5*cm,f"No: {d['invoice_number']}"); c.drawRightString(W-m,H-3.0*cm,d["issue_date"])
    cy=split-1.5*cm
    c.setFillColor(colors.white); c.roundRect(m,cy,W/2-2.5*cm,3.2*cm,0.3*cm,fill=1,stroke=0)
    c.setFillColor(ink_on_white); c.setFont("Helvetica-Bold",8); c.drawString(m+0.4*cm,cy+2.7*cm,"BILL TO")
    c.setFont("Helvetica",8.5); c.setFillColor(colors.black)
    c.drawString(m+0.4*cm,cy+2.2*cm,d["client_name"]); c.drawString(m+0.4*cm,cy+1.7*cm,d["client_address"]); c.drawString(m+0.4*cm,cy+1.2*cm,d["client_email"])
    c.setFillColor(pal["bg"]); c.roundRect(W/2,cy,W/2-m,3.2*cm,0.3*cm,fill=1,stroke=0)
    c.setFillColor(ink_on_bg); c.setFont("Helvetica-Bold",8); c.drawString(W/2+0.4*cm,cy+2.7*cm,"PAYMENT INFO")
    c.setFont("Helvetica",8.5); c.setFillColor(colors.black)
    c.drawString(W/2+0.4*cm,cy+2.2*cm,f"Terms:    {d['payment_terms']}")
    c.drawString(W/2+0.4*cm,cy+1.7*cm,f"Due:      {d['due_date']}")
    c.drawString(W/2+0.4*cm,cy+1.2*cm,f"Currency: {d['currency']}")
    if d["po_number"]: c.drawString(W/2+0.4*cm,cy+0.7*cm,f"PO:       {d['po_number']}")
    draw_table(c,d,m,cy-1.5*cm,W-2*m)

def r_formal(c,d,W,H):
    pal=d["_pal"]; m=2*cm
    ink_on_white = pick_text_color(colors.white, preferred=pal["primary"])
    c.setStrokeColor(pal["primary"]); c.setLineWidth(2); c.rect(m*0.5,m*0.5,W-m,H-m,stroke=1,fill=0)
    c.setLineWidth(0.5); c.rect(m*0.7,m*0.7,W-m*1.4,H-m*1.4,stroke=1,fill=0)
    c.setFillColor(ink_on_white); c.setFont("Helvetica-Bold",20); c.drawCentredString(W/2,H-2.2*cm,"OFFICIAL INVOICE")
    c.setLineWidth(1); c.line(m*1.5,H-2.6*cm,W-m*1.5,H-2.6*cm)
    c.setFont("Helvetica-Bold",10); c.setFillColor(colors.black); c.drawString(m*1.5,H-3.3*cm,d["seller_name"])
    c.setFont("Helvetica",8.5)
    for j,f in enumerate(["seller_address","seller_email","seller_phone","seller_tax_id"]):
        c.drawString(m*1.5,H-(3.8+j*0.5)*cm,d[f])
    draw_logo(c,W/2-1*cm,H-5.2*cm,2*cm,pal,d["seller_name"])
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold",9); c.drawRightString(W-m*1.5,H-3.3*cm,f"Invoice No: {d['invoice_number']}")
    c.setFont("Helvetica",9)
    c.drawRightString(W-m*1.5,H-3.8*cm,f"Issue Date:  {d['issue_date']}")
    c.drawRightString(W-m*1.5,H-4.3*cm,f"Due Date:    {d['due_date']}")
    c.drawRightString(W-m*1.5,H-4.8*cm,f"Currency:    {d['currency']}")
    c.drawRightString(W-m*1.5,H-5.3*cm,f"Terms:       {d['payment_terms']}")
    if d["po_number"]: c.drawRightString(W-m*1.5,H-5.8*cm,f"PO Number:   {d['po_number']}")
    c.line(m*1.5,H-6.2*cm,W-m*1.5,H-6.2*cm)
    c.setFont("Helvetica-Bold",9); c.drawString(m*1.5,H-6.8*cm,"BILL TO:")
    c.setFont("Helvetica",9)
    c.drawString(m*1.5,H-7.3*cm,d["client_name"]); c.drawString(m*1.5,H-7.8*cm,d["client_address"]); c.drawString(m*1.5,H-8.3*cm,d["client_email"])
    draw_table(c,d,m*1.5,H-9.5*cm,W-3*m)
    c.setFont("Helvetica",8); c.setFillColor(colors.HexColor("#666"))
    sy=m*1.2; c.line(m*1.5,sy,m*1.5+5*cm,sy); c.drawString(m*1.5,sy-0.4*cm,"Authorised Signature")
    c.line(W-m*1.5-5*cm,sy,W-m*1.5,sy); c.drawRightString(W-m*1.5,sy-0.4*cm,"Date")

def r_creative(c,d,W,H):
    pal=d["_pal"]; m=2*cm
    ink_on_white = pick_text_color(colors.white, preferred=pal["primary"])
    left_x = m
    right_col_start = W - m - 6.8*cm
    left_max_w = max(4.0*cm, right_col_start - left_x - 0.2*cm)
    c.setFillColor(pal["bg"]); c.circle(W+1*cm,H+1*cm,8*cm,fill=1,stroke=0)
    c.setFillColor(ink_on_white)
    draw_fit_text(c, d["seller_name"], left_x, H-1.8*cm, left_max_w,
                  font_name="Helvetica-Bold", font_size=22, min_size=11)
    draw_logo(c,W-m-2.5*cm,H-3.0*cm,2.2*cm,pal,d["seller_name"])
    c.setFillColor(colors.HexColor("#555"))
    draw_fit_text(c, d["seller_address"], left_x, H-2.4*cm, left_max_w,
                  font_name="Helvetica", font_size=8, min_size=6)
    draw_fit_text(c, d["seller_email"], left_x, H-2.9*cm, left_max_w,
                  font_name="Helvetica", font_size=8, min_size=6)
    c.setFillColor(ink_on_white); c.setFont("Helvetica-Bold",13); c.drawRightString(W-m,H-1.8*cm,"INVOICE")
    c.setFont("Helvetica",9); c.setFillColor(colors.black)
    c.drawRightString(W-m,H-2.15*cm,f"No: {d['invoice_number']}")
    c.drawRightString(W-m,H-2.60*cm,f"Date: {d['issue_date']}")
    c.drawRightString(W-m,H-3.05*cm,f"Due: {d['due_date']}")
    c.drawRightString(W-m,H-3.50*cm,f"Currency: {d['currency']}")
    c.drawRightString(W-m,H-3.95*cm,f"Terms: {d['payment_terms']}")
    if d["po_number"]: c.drawRightString(W-m,H-4.40*cm,f"PO: {d['po_number']}")
    c.setFillColor(pal["primary"]); c.setFont("Helvetica-Bold",9); c.drawString(m,H-4.8*cm,"BILLED TO")
    c.setFont("Helvetica",9); c.setFillColor(colors.black)
    c.drawString(m,H-5.3*cm,d["client_name"]); c.drawString(m,H-5.8*cm,d["client_address"])
    c.drawString(m,H-6.3*cm,d["client_email"])
    c.setFillColor(pal["accent"]); c.rect(m,H-6.7*cm,4*cm,0.15*cm,fill=1,stroke=0)
    draw_table(c,d,m,H-7.5*cm,W-2*m)

def r_compact(c,d,W,H):
    pal=d["_pal"]; m=1.5*cm
    header_txt = pick_text_color(pal["primary"])
    c.setFillColor(pal["primary"]); c.rect(0,H-1.2*cm,W,1.2*cm,fill=1,stroke=0)
    c.setFillColor(header_txt); c.setFont("Helvetica-Bold",10)
    c.drawString(m,H-0.8*cm,d["seller_name"]); c.drawRightString(W-m,H-0.8*cm,f"INVOICE  {d['invoice_number']}")
    c.setFillColor(colors.HexColor("#333")); c.setFont("Helvetica",7.5)
    c.drawString(m,H-1.7*cm,d["seller_address"])
    c.drawString(m,H-2.2*cm,d["seller_email"])
    c.drawRightString(W-m,H-2.2*cm,d["client_email"])
    c.setFont("Helvetica-Bold",7.5); c.drawString(m,H-2.7*cm,"TO:")
    c.setFont("Helvetica",7.5); c.drawString(m+0.8*cm,H-2.7*cm,d["client_name"])
    c.drawString(m+0.8*cm,H-3.2*cm,d["client_address"])
    line1=f"Date: {d['issue_date']}  Due: {d['due_date']}  Terms: {d['payment_terms']}  Currency: {d['currency']}"
    c.drawString(m,H-3.7*cm,line1)
    if d["po_number"]: c.drawString(m,H-4.2*cm,f"PO: {d['po_number']}")
    draw_table(c,d,m,H-4.8*cm,W-2*m,row_h=0.55*cm,fs=7.5)
    c.setFillColor(pal["primary"]); c.rect(0,0,W,0.7*cm,fill=1,stroke=0)
    c.setFillColor(header_txt); c.setFont("Helvetica",6.5)
    c.drawCentredString(W/2,0.22*cm,f"{d['seller_tax_id']}  |  {d['seller_email']}")

RENDERERS = {
    "classic":r_classic,"modern":r_modern,"minimal":r_minimal,"ledger":r_ledger,
    "bold_header":r_bold_header,"sidebar":r_sidebar,"two_tone":r_two_tone,
    "formal":r_formal,"creative":r_creative,"compact":r_compact,
}

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate synthetic invoice dataset")
    parser.add_argument("--pdf_dir", default="output/pdfs",
                        help="Output folder for PDF files (default: output/pdfs)")
    parser.add_argument("--gt_dir",  default="output/ground_truth",
                        help="Output folder for JSON ground truth files (default: output/ground_truth)")
    parser.add_argument("--n",       type=int, default=1000,
                        help="Number of invoices to generate (default: 1000)")
    parser.add_argument("--zip",     action="store_true",
                        help="Also produce output/pdfs.zip and output/ground_truth.zip")
    args = parser.parse_args()

    N = args.n

    # ── Balanced sequences ────────────────────────────────────────────────────
    random.seed(42)
    LAYOUTS      = balanced_seq(LAYOUT_STYLES, N)
    COMPLEXITIES = balanced_seq(COMPLEXITY_TIERS, N,
                                weights=[45/200, 60/200, 57/200, 38/200])
    CUR_IDXS     = balanced_seq(list(range(len(CURRENCIES))), N,
                                weights=[17/200,13/200,20/200,21/200,25/200,
                                         26/200,22/200,20/200,13/200,23/200])
    PS_NAMES     = balanced_seq(["A4","letter"], N,
                                weights=[115/200, 85/200])
    PAL_IDXS     = balanced_seq(list(range(len(PALETTES))), N)

    os.makedirs(args.pdf_dir, exist_ok=True)
    os.makedirs(args.gt_dir,  exist_ok=True)

    print(f"Generating {N} invoices → PDFs: {args.pdf_dir}  JSONs: {args.gt_dir}")

    for si in range(N):
        idx = si + 1
        d   = build(idx, LAYOUTS[si], COMPLEXITIES[si],
                    CUR_IDXS[si], PS_NAMES[si], PAL_IDXS[si])

        # ── Write PDF ─────────────────────────────────────────────────────────
        W, H = d["_ps"]
        pdf_path = os.path.join(args.pdf_dir, f"invoice_{idx:03d}.pdf")
        canv = canvas.Canvas(pdf_path, pagesize=d["_ps"])
        canv.setTitle(f"Invoice {d['invoice_number']}")
        canv.setAuthor(d["seller_name"])
        try:
            RENDERERS[d["layout_style"]](canv, d, W, H)
        except Exception as e:
            print(f"  Render fallback #{idx}: {e}")
            r_minimal(canv, d, W, H)
        canv.save()

        # ── Write JSON (same dict, strip render-only keys starting with _) ────
        gt = {k: v for k, v in d.items() if not k.startswith("_")}
        gt_path = os.path.join(args.gt_dir, f"invoice_{idx:03d}.json")
        with open(gt_path, "w", encoding="utf-8") as f:
            json.dump(gt, f, indent=2, ensure_ascii=False)

        if (si + 1) % 100 == 0:
            print(f"  ...{si+1}/{N} done")

    print(f"\nGeneration complete: {N} PDFs and {N} JSONs written.")

    # ── Optional ZIP ──────────────────────────────────────────────────────────
    if args.zip:
        import zipfile
        os.makedirs("output", exist_ok=True)

        zip_pdf = "output/pdfs.zip"
        with zipfile.ZipFile(zip_pdf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fn in sorted(os.listdir(args.pdf_dir)):
                zf.write(os.path.join(args.pdf_dir, fn), fn)
        print(f"  Zipped PDFs → {zip_pdf}  ({os.path.getsize(zip_pdf)/1024/1024:.1f} MB)")

        zip_gt = "output/ground_truth.zip"
        with zipfile.ZipFile(zip_gt, "w", zipfile.ZIP_DEFLATED) as zf:
            for fn in sorted(os.listdir(args.gt_dir)):
                zf.write(os.path.join(args.gt_dir, fn), fn)
        print(f"  Zipped JSONs → {zip_gt}  ({os.path.getsize(zip_gt)/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()
