"""Generate pixel-accurate UI previews of SHATTA TUESDAY MARKET."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = "/home/user/zynara/static/shatta/"
W, H = 1440, 900

# ── Colours (matching main.css) ────────────────────────────
BG      = (8,   8,   8)
BG2     = (17,  17,  17)
BG3     = (26,  26,  26)
BG4     = (34,  34,  34)
GOLD    = (212, 175,  55)
GOLD_L  = (245, 208,  96)
GOLD_D  = (154, 125,  26)
TEXT    = (240, 240, 240)
TEXT2   = (170, 170, 170)
TEXT3   = (102, 102, 102)
BORDER  = (42,  42,  42)
BORDER2 = (58,  58,  58)
GREEN   = (34,  197,  94)
RED     = (239,  68,  68)
AMBER   = (245, 158,  11)
BLUE    = (59,  130, 246)
PINK    = (233,  30, 140)

# ── Fonts ──────────────────────────────────────────────────
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
SANS_R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
MONO   = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

def font(path, size):
    try:   return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

def fB(s): return font(SANS_B, s)
def fR(s): return font(SANS_R, s)

# ── Drawing helpers ────────────────────────────────────────
def grad_rect(img, x1, y1, x2, y2, c1, c2, vertical=True):
    """Draw a vertical or horizontal gradient rectangle."""
    d = ImageDraw.Draw(img)
    steps = (y2 - y1) if vertical else (x2 - x1)
    for i in range(steps):
        t = i / max(steps - 1, 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        if vertical:
            d.line([(x1, y1 + i), (x2, y1 + i)], fill=(r, g, b))
        else:
            d.line([(x1 + i, y1), (x1 + i, y2)], fill=(r, g, b))

def rounded_rect(d, x1, y1, x2, y2, r, fill=None, outline=None, width=1):
    d.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill, outline=outline, width=width)

def text_c(d, text, cx, y, fnt, fill):
    """Draw text centred at cx."""
    bb = d.textbbox((0, 0), text, font=fnt)
    tw = bb[2] - bb[0]
    d.text((cx - tw // 2, y), text, font=fnt, fill=fill)

def navbar(img, active=""):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 64], fill=(10, 10, 10))
    d.line([(0, 64), (W, 64)], fill=BORDER, width=1)
    # Brand
    d.text((40, 18), "SHATTA ", font=fB(18), fill=GOLD)
    bw = d.textbbox((0,0),"SHATTA ", font=fB(18))[2]
    d.text((40 + bw, 18), "TUESDAY ", font=fB(18), fill=TEXT)
    bw2 = d.textbbox((0,0),"SHATTA TUESDAY ", font=fB(18))[2]
    d.text((40 + bw2, 18), "MARKET", font=fB(18), fill=GOLD_L)
    # Nav links
    links = [("Home", 900), ("Login", 1000), ("Register Vendor", 1100)]
    for lbl, x in links:
        if lbl == active:
            rounded_rect(d, x-10, 20, x + d.textbbox((0,0),lbl,font=fR(14))[2]+10, 44, 6, fill=GOLD)
            d.text((x, 22), lbl, font=fB(14), fill=(0, 0, 0))
        else:
            d.text((x, 22), lbl, font=fR(14), fill=TEXT2)

def footer(img):
    d = ImageDraw.Draw(img)
    fy = H - 120
    d.rectangle([0, fy, W, H], fill=BG2)
    d.line([(0, fy), (W, fy)], fill=BORDER, width=1)
    d.text((60, fy + 22), "SHATTA TUESDAY MARKET", font=fB(14), fill=GOLD)
    d.text((60, fy + 46), "Promoting Ghanaian Businesses. Supporting The People.", font=fR(12), fill=TEXT3)
    d.text((60, fy + 66), "Founded by Shatta Wale", font=fR(11), fill=TEXT3)
    text_c(d, "© 2024 SHATTA TUESDAY MARKET. All rights reserved.", W//2, fy + 95, fR(11), TEXT3)


# ══════════════════════════════════════════════════════════════
# PAGE 1 — HOME / LANDING
# ══════════════════════════════════════════════════════════════
def make_home():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Hero gradient
    grad_rect(img, 0, 64, W, 580, (10, 8, 0), (8, 8, 8))

    # Gold radial glow (faked with ellipse)
    glow = Image.new("RGB", (W, 516), BG)
    gd = ImageDraw.Draw(glow)
    for r2 in range(180, 0, -1):
        alpha = int(18 * (1 - r2 / 180))
        gd.ellipse([W//2-r2*3, 50-r2, W//2+r2*3, 50+r2], fill=(min(BG[0]+alpha,255), min(BG[1]+alpha//2,255), BG[2]))
    img.paste(glow, (0, 64))
    d = ImageDraw.Draw(img)

    # Hero badge
    badge_txt = "🇬🇭  Official Business Promotion Platform"
    rounded_rect(d, W//2-200, 90, W//2+200, 118, 999,
                 fill=(30, 25, 0), outline=(80, 60, 10), width=1)
    text_c(d, badge_txt, W//2, 96, fR(13), GOLD)

    # Hero title
    text_c(d, "SHATTA", W//2, 130, fB(80), TEXT)
    text_c(d, "TUESDAY", W//2, 210, fB(80), GOLD)
    text_c(d, "MARKET", W//2, 290, fB(80), TEXT)

    # Slogan
    text_c(d, "Promoting Ghanaian Businesses. Supporting The People.", W//2, 385, fB(18), GOLD)
    text_c(d, "Founded by  Shatta Wale  — empowering entrepreneurs across Ghana.", W//2, 415, fR(15), TEXT2)

    # CTA buttons
    rounded_rect(d, W//2-230, 450, W//2-20, 490, 10, fill=GOLD)
    text_c(d, "Register Your Business", W//2-125, 461, fB(15), (0,0,0))
    rounded_rect(d, W//2+20, 450, W//2+230, 490, 10, fill=None, outline=BORDER2, width=1)
    text_c(d, "Browse Promotions", W//2+125, 461, fB(15), TEXT)

    # Stats bar
    d.rectangle([0, 510, W, 570], fill=BG2)
    d.line([(0, 570), (W, 570)], fill=BORDER, width=1)
    stats = [("0", "Registered Vendors"), ("0", "Live Promotions"), ("GHS", "Payments via MoMo"), ("3", "Subscription Plans")]
    sx = 200
    for val, lbl in stats:
        d.text((sx, 518), val, font=fB(22), fill=GOLD)
        d.text((sx, 546), lbl, font=fR(11), fill=TEXT3)
        sx += 280
        if sx < W - 200:
            d.line([(sx - 140, 525), (sx - 140, 560)], fill=BORDER, width=1)

    # Section: Live Promotions
    d.text((60, 590), "Live ", font=fB(26), fill=TEXT)
    lw = d.textbbox((0,0),"Live ", font=fB(26))[2]
    d.text((60 + lw, 590), "Promotions", font=fB(26), fill=GOLD)
    d.text((60, 622), "Verified businesses approved by Shatta Wale's team", font=fR(14), fill=TEXT2)

    # Promo cards (3 placeholder cards)
    card_y, card_h = 655, 200
    for i, (cat, biz) in enumerate([("Fashion & Clothing", "Kofi's Fashion Store"),
                                     ("Food & Beverages",  "Mama Akosua Kitchen"),
                                     ("Beauty & Cosmetics","Abena Glow Beauty")]):
        cx = 60 + i * 440
        rounded_rect(d, cx, card_y, cx+400, card_y+card_h, 12, fill=BG2, outline=BORDER, width=1)
        # image placeholder
        rounded_rect(d, cx+8, card_y+8, cx+392, card_y+120, 8, fill=BG3)
        text_c(d, "🏪", cx+200, card_y+48, fR(28), TEXT3)
        # category tag
        rounded_rect(d, cx+16, card_y+16, cx+16+len(cat)*7+10, card_y+34, 999, fill=(20,16,0), outline=(60,45,8), width=1)
        d.text((cx+22, card_y+18), cat, font=fR(10), fill=GOLD)
        # body
        d.text((cx+12, card_y+128), biz, font=fB(13), fill=TEXT)
        d.text((cx+12, card_y+148), "by Vendor Name", font=fR(11), fill=TEXT3)
        d.text((cx+12, card_y+168), "Quality products at great prices...", font=fR(11), fill=TEXT2)

    navbar(img, "Home")
    footer(img)
    img.save(OUT + "preview_home.png")
    print("✓ Home page")


# ══════════════════════════════════════════════════════════════
# PAGE 2 — LOGIN
# ══════════════════════════════════════════════════════════════
def make_login():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    navbar(img, "Login")

    # Card left (form)
    cx = W//2 - 360
    rounded_rect(d, cx, 80, cx+720, H-90, 16, fill=BG2, outline=BORDER, width=1)

    # Gold circle logo
    d.ellipse([cx+300, 110, cx+420, 230], fill=GOLD)
    text_c(d, "STM", cx+360, 148, fB(30), (0,0,0))

    d.text((cx+260, 248), "Welcome Back", font=fB(26), fill=TEXT)
    text_c(d, "Login to your SHATTA TUESDAY MARKET account", cx+360, 285, fR(13), TEXT2)

    # Email field
    d.text((cx+40, 320), "Email Address", font=fB(12), fill=TEXT2)
    rounded_rect(d, cx+40, 340, cx+680, 376, 10, fill=BG3, outline=BORDER, width=1)
    d.text((cx+56, 351), "your@email.com", font=fR(14), fill=TEXT3)

    # Password field
    d.text((cx+40, 396), "Password", font=fB(12), fill=TEXT2)
    rounded_rect(d, cx+40, 416, cx+680, 452, 10, fill=BG3, outline=BORDER, width=1)
    d.text((cx+56, 427), "••••••••••••", font=fR(14), fill=TEXT3)
    d.text((cx+648, 430), "👁", font=fR(14), fill=TEXT3)

    # Login button
    rounded_rect(d, cx+40, 474, cx+680, 514, 10, fill=GOLD)
    text_c(d, "Login", cx+360, 485, fB(16), (0,0,0))

    d.text((cx+210, 530), "Don't have an account?  ", font=fR(13), fill=TEXT3)
    d.text((cx+390, 530), "Register as a Vendor", font=fB(13), fill=GOLD)

    # Divider
    d.line([(cx+40, 560), (cx+680, 560)], fill=BORDER, width=1)
    text_c(d, "OR", cx+360, 551, fR(12), TEXT3)

    # Admin badge
    rounded_rect(d, cx+40, 576, cx+100, 596, 999, fill=(20,40,80), outline=(40,80,160), width=1)
    d.text((cx+48, 579), "ADMIN", font=fB(10), fill=(96,165,250))
    d.text((cx+108, 579), "Admin and Super Admin can log in with their credentials above.", font=fR(11), fill=TEXT3)

    # Right panel
    grad_rect(img, cx+720, 80, cx+1440, H-90, (17, 14, 0), (10, 8, 0))
    d.line([(cx+720, 80), (cx+720, H-90)], fill=BORDER, width=1)
    text_c(d, "SHATTA TUESDAY MARKET", cx+1080, 230, fB(20), GOLD)
    text_c(d, "Promoting Ghanaian Businesses. Supporting The People.", cx+1080, 268, fR(13), GOLD_L)
    features = ["🇬🇭  Ghana's #1 Business Promotion Platform",
                "✅  AI-Powered Trust Verification",
                "📱  Reach Millions via Social Media",
                "💛  Founded by Shatta Wale"]
    for i, f in enumerate(features):
        d.text((cx+760, 320 + i*44), f, font=fR(14), fill=TEXT2)

    navbar(img, "Login")
    footer(img)
    img.save(OUT + "preview_login.png")
    print("✓ Login page")


# ══════════════════════════════════════════════════════════════
# PAGE 3 — VENDOR DASHBOARD
# ══════════════════════════════════════════════════════════════
def make_vendor_dashboard():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    navbar(img)

    pad = 60

    # Welcome header
    d.text((pad, 84), "Welcome, ", font=fB(30), fill=TEXT)
    ww = d.textbbox((0,0),"Welcome, ", font=fB(30))[2]
    d.text((pad + ww, 84), "Kofi", font=fB(30), fill=GOLD)
    d.text((pad, 122), "Kofi's Fashion Store", font=fR(14), fill=TEXT3)
    # Badges
    rounded_rect(d, W-320, 88, W-180, 112, 999, fill=(10,30,10), outline=(30,100,30), width=1)
    d.text((W-312, 92), "✓ Verified Business", font=fB(11), fill=(74,222,128))

    # Stats row
    sy = 155
    stat_data = [("📊", "4", "Total Promotions"), ("✅", "2", "Approved"),
                 ("⏳", "1", "Pending Review"), ("⭐", "4.8", "Avg Rating")]
    sw = (W - pad*2 - 48) // 4
    for i, (icon, val, lbl) in enumerate(stat_data):
        sx2 = pad + i*(sw+16)
        rounded_rect(d, sx2, sy, sx2+sw, sy+90, 10, fill=BG2, outline=BORDER, width=1)
        d.text((sx2+20, sy+10), icon, font=fR(22), fill=GOLD)
        d.text((sx2+20, sy+38), val, font=fB(28), fill=GOLD)
        d.text((sx2+20, sy+72), lbl, font=fR(11), fill=TEXT3)

    # Two column cards
    col1_w = int((W - pad*2 - 20) * 0.48)
    col2_w = W - pad*2 - 20 - col1_w
    cy = 265

    # Subscription card
    rounded_rect(d, pad, cy, pad+col1_w, cy+170, 12, fill=BG2, outline=BORDER, width=1)
    d.text((pad+20, cy+16), "💳  Subscription Status", font=fB(14), fill=TEXT)
    d.line([(pad+20, cy+40), (pad+col1_w-20, cy+40)], fill=BORDER, width=1)
    d.text((pad+20, cy+52), "✅ Active — Standard Plan", font=fB(14), fill=GREEN)
    d.text((pad+20, cy+80), "Expires:  2027-05-18", font=fR(13), fill=TEXT2)
    d.text((pad+20, cy+102),"This month:  1 promotion(s) uploaded", font=fR(13), fill=TEXT2)
    rounded_rect(d, pad+20, cy+126, pad+180, cy+154, 8, fill=GOLD)
    d.text((pad+38, cy+133), "📤  Upload Promotion", font=fB(12), fill=(0,0,0))

    # Profile card
    px = pad + col1_w + 20
    rounded_rect(d, px, cy, px+col2_w, cy+170, 12, fill=BG2, outline=BORDER, width=1)
    d.text((px+20, cy+16), "👤  Your Profile", font=fB(14), fill=TEXT)
    d.line([(px+20, cy+40), (px+col2_w-20, cy+40)], fill=BORDER, width=1)
    profile = [("Business:", "Kofi's Fashion Store"), ("Category:", "Fashion & Clothing"),
               ("Location:", "Accra, Ghana"), ("Phone:", "0244 123 456"), ("MoMo:", "0244 123 456")]
    for i, (lbl, val) in enumerate(profile):
        d.text((px+20, cy+52+i*22), lbl, font=fB(11), fill=TEXT3)
        d.text((px+110, cy+52+i*22), val, font=fR(11), fill=TEXT)

    # Promotions table
    ty = 455
    rounded_rect(d, pad, ty, W-pad, ty+300, 12, fill=BG2, outline=BORDER, width=1)
    d.text((pad+20, ty+16), "📢  My Promotions", font=fB(14), fill=TEXT)
    rounded_rect(d, W-200, ty+12, W-pad-10, ty+40, 8, fill=GOLD)
    d.text((W-192, ty+18), "+ New Promotion", font=fB(11), fill=(0,0,0))
    d.line([(pad+20, ty+46), (W-pad-20, ty+46)], fill=BORDER, width=1)

    # Table header
    cols = [(pad+20,"Description"), (pad+680,"Status"), (pad+820,"AI Score"), (pad+960,"Date"), (pad+1100,"Media")]
    for cx2, lbl in cols:
        d.text((cx2, ty+54), lbl, font=fB(10), fill=TEXT3)
    d.line([(pad+20, ty+72), (W-pad-20, ty+72)], fill=BORDER, width=1)

    rows = [
        ("Quality fashion items at affordable prices...", "approved", 10, "2026-05-10", "🖼"),
        ("Beautiful traditional attire for all occasions...", "pending", 22, "2026-05-16", "🖼 🎬"),
        ("Exclusive Kente collection now available...", "approved", 8, "2026-04-28", "🖼"),
        ("Premium quality shirts — great for all...", "rejected", 65, "2026-04-15", ""),
    ]
    status_colors = {"approved": GREEN, "pending": AMBER, "rejected": RED, "held": BLUE}
    for i, (desc, status, score, date, media) in enumerate(rows):
        ry = ty + 80 + i*44
        d.text((pad+20, ry), desc[:55]+"…", font=fR(11), fill=TEXT2)
        sc = status_colors.get(status, TEXT3)
        rounded_rect(d, pad+674, ry-2, pad+760, ry+18, 999,
                     fill=(sc[0]//8, sc[1]//8, sc[2]//8))
        d.text((pad+680, ry), f"{'✅' if status=='approved' else '⏳' if status=='pending' else '❌'} {status.title()}", font=fR(10), fill=sc)
        risk_c = GREEN if score<30 else AMBER if score<60 else RED
        rounded_rect(d, pad+814, ry-2, pad+870, ry+18, 999,
                     fill=(risk_c[0]//8, risk_c[1]//8, risk_c[2]//8))
        d.text((pad+820, ry), f"{score}%", font=fB(11), fill=risk_c)
        d.text((pad+960, ry), date, font=fR(11), fill=TEXT3)
        d.text((pad+1100, ry), media, font=fR(12), fill=GOLD)
        if i < len(rows)-1:
            d.line([(pad+20, ry+26), (W-pad-20, ry+26)], fill=BORDER, width=1)

    navbar(img)
    footer(img)
    img.save(OUT + "preview_vendor_dashboard.png")
    print("✓ Vendor dashboard")


# ══════════════════════════════════════════════════════════════
# PAGE 4 — ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════════
def make_admin_dashboard():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    navbar(img)
    pad = 60

    # Header + nav pills
    d.text((pad, 84), "Admin ", font=fB(28), fill=TEXT)
    aw = d.textbbox((0,0),"Admin ", font=fB(28))[2]
    d.text((pad+aw, 84), "Dashboard", font=fB(28), fill=GOLD)
    d.text((pad, 118), "SHATTA TUESDAY MARKET — Control Centre", font=fR(13), fill=TEXT3)

    pills = ["Overview", "Submissions", "Subscriptions", "Vendors", "Blacklist", "Reports"]
    px2 = pad
    for p in pills:
        pw = d.textbbox((0,0),p,font=fB(12))[2] + 28
        active = p == "Overview"
        rounded_rect(d, px2, 144, px2+pw, 168, 999,
                     fill=GOLD if active else None,
                     outline=BORDER2 if not active else GOLD, width=1)
        d.text((px2+14, 149), p, font=fB(12), fill=(0,0,0) if active else TEXT2)
        px2 += pw + 10

    # 6 stat cards
    card_w = (W - pad*2 - 50) // 6
    for i, (icon, val, lbl, alert) in enumerate([
        ("👥", "12", "Total Vendors", False),
        ("⏳", "3",  "Pending Subs", True),
        ("📋", "5",  "Pending Promos", True),
        ("✅", "28", "Approved Promos", False),
        ("🚨", "2",  "Open Reports", True),
        ("🚫", "1",  "Blacklisted", False),
    ]):
        sx2 = pad + i*(card_w+10)
        bc = (80,50,0) if alert else BORDER
        rounded_rect(d, sx2, 186, sx2+card_w, 276, 10, fill=BG2, outline=bc, width=1 if not alert else 1)
        text_c(d, icon, sx2+card_w//2, 196, fR(20), GOLD)
        text_c(d, val,  sx2+card_w//2, 222, fB(28), GOLD)
        text_c(d, lbl,  sx2+card_w//2, 256, fR(10), TEXT3)
        if alert and val != "0":
            text_c(d, "Review →", sx2+card_w//2, 272, fR(9), GOLD)

    # Two column section
    col_w = (W - pad*2 - 20) // 2
    cy2 = 296

    # Pending submissions
    rounded_rect(d, pad, cy2, pad+col_w, H-130, 12, fill=BG2, outline=BORDER, width=1)
    d.text((pad+20, cy2+16), "📋  Pending Submissions", font=fB(14), fill=TEXT)
    rounded_rect(d, pad+col_w-130, cy2+12, pad+col_w-10, cy2+40, 8,
                 fill=None, outline=GOLD, width=1)
    d.text((pad+col_w-122, cy2+18), "View All", font=fB(11), fill=GOLD)
    d.line([(pad+20, cy2+46), (pad+col_w-20, cy2+46)], fill=BORDER, width=1)

    subs = [
        ("Kofi's Fashion Store", "Kofi Mensah", 8,  "verified"),
        ("Mama Akosua Kitchen",  "Akosua Asante", 45, "unverified"),
        ("GoldTech Solutions",   "Kwame Boateng", 72, "verified"),
        ("Beauty by Abena",      "Abena Darko", 15,  "verified"),
        ("Quick Cash Services",  "John Doe", 91,      "unverified"),
    ]
    for i, (biz, name, risk, ver) in enumerate(subs):
        ry2 = cy2 + 56 + i*86
        rounded_rect(d, pad+16, ry2, pad+col_w-16, ry2+78, 8, fill=BG3, outline=BORDER, width=1)
        d.text((pad+28, ry2+10), biz, font=fB(13), fill=TEXT)
        d.text((pad+28, ry2+28), f"by {name}", font=fR(11), fill=TEXT3)
        rc = GREEN if risk<30 else AMBER if risk<60 else RED
        rounded_rect(d, pad+col_w-130, ry2+8, pad+col_w-26, ry2+28, 999,
                     fill=(rc[0]//6,rc[1]//6,rc[2]//6))
        d.text((pad+col_w-122, ry2+11), f"{risk}% Risk", font=fB(10), fill=rc)
        vc = (10,30,10) if ver=="verified" else (30,10,10)
        vo = (30,100,30) if ver=="verified" else (100,30,30)
        rounded_rect(d, pad+28, ry2+42, pad+28+80, ry2+60, 999, fill=vc, outline=vo, width=1)
        vt = "✓ Verified" if ver=="verified" else "⚠ Unverified"
        vf = (74,222,128) if ver=="verified" else (248,113,113)
        d.text((pad+36, ry2+45), vt, font=fR(10), fill=vf)
        # Action buttons
        rounded_rect(d, pad+28,  ry2+54, pad+100, ry2+72, 6, fill=GREEN)
        d.text((pad+36, ry2+57), "✅ Approve", font=fB(9), fill=(0,0,0))
        rounded_rect(d, pad+108, ry2+54, pad+160, ry2+72, 6, fill=AMBER)
        d.text((pad+116, ry2+57), "⏸ Hold", font=fB(9), fill=(0,0,0))

    # Pending subscriptions
    px3 = pad + col_w + 20
    rounded_rect(d, px3, cy2, px3+col_w, H-130, 12, fill=BG2, outline=BORDER, width=1)
    d.text((px3+20, cy2+16), "💳  Pending Subscriptions", font=fB(14), fill=TEXT)
    rounded_rect(d, px3+col_w-130, cy2+12, px3+col_w-10, cy2+40, 8,
                 fill=None, outline=GOLD, width=1)
    d.text((px3+col_w-122, cy2+18), "View All", font=fB(11), fill=GOLD)
    d.line([(px3+20, cy2+46), (px3+col_w-20, cy2+46)], fill=BORDER, width=1)

    plan_subs = [
        ("Mama Akosua Kitchen", "Akosua Asante", "standard", 600),
        ("Beauty by Abena",     "Abena Darko",   "basic",    300),
        ("Quick Cash Ser...",   "John Doe",      "premium",  1200),
    ]
    plan_colors = {"basic":(100,100,100), "standard":GOLD, "premium":GOLD_L}
    for i, (biz, name, plan, amt) in enumerate(plan_subs):
        ry2 = cy2 + 56 + i*116
        rounded_rect(d, px3+16, ry2, px3+col_w-16, ry2+108, 8, fill=BG3, outline=BORDER, width=1)
        pc = plan_colors.get(plan, TEXT2)
        rounded_rect(d, px3+28, ry2+10, px3+28+60, ry2+28, 6,
                     fill=(pc[0]//8,pc[1]//8,pc[2]//8))
        d.text((px3+36, ry2+13), plan.title(), font=fB(10), fill=pc)
        d.text((px3+28, ry2+36), biz, font=fB(13), fill=TEXT)
        d.text((px3+28, ry2+54), name, font=fR(11), fill=TEXT3)
        d.text((px3+28, ry2+72), f"GHS {amt}  •  MoMo  •  2026-05-15", font=fR(11), fill=TEXT2)
        rounded_rect(d, px3+28, ry2+80, px3+28+90, ry2+100, 6, fill=GREEN)
        d.text((px3+36, ry2+83), "✅ Approve", font=fB(10), fill=(0,0,0))
        rounded_rect(d, px3+130, ry2+80, px3+196, ry2+100, 6, fill=RED)
        d.text((px3+138, ry2+83), "❌ Reject", font=fB(10), fill=TEXT)

    navbar(img)
    footer(img)
    img.save(OUT + "preview_admin_dashboard.png")
    print("✓ Admin dashboard")


# ══════════════════════════════════════════════════════════════
# PAGE 5 — ADMIN SUBMISSIONS (review card)
# ══════════════════════════════════════════════════════════════
def make_admin_submissions():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    navbar(img)
    pad = 60

    d.text((pad, 84), "Promotion ", font=fB(28), fill=TEXT)
    pw = d.textbbox((0,0),"Promotion ", font=fB(28))[2]
    d.text((pad+pw, 84), "Submissions", font=fB(28), fill=GOLD)
    d.text((pad, 118), "Review, approve, reject or hold vendor promotions", font=fR(13), fill=TEXT3)

    # Filter bar
    filters = ["⏳ Pending", "✅ Approved", "⏸ Held", "❌ Rejected", "All"]
    fx = pad
    for fi, ft in enumerate(filters):
        fw = d.textbbox((0,0),ft,font=fB(12))[2] + 24
        active = fi == 0
        rounded_rect(d, fx, 144, fx+fw, 168, 999,
                     fill=GOLD if active else None, outline=GOLD if active else BORDER2, width=1)
        d.text((fx+12, 149), ft, font=fB(12), fill=(0,0,0) if active else TEXT2)
        fx += fw + 10

    # Full submission card
    card_y = 182
    risk = 8
    rc = GREEN
    # Left border colour by risk
    d.rectangle([pad, card_y, pad+4, H-130], fill=rc)
    rounded_rect(d, pad+4, card_y, W-pad, H-130, 12, fill=BG2, outline=BORDER, width=1)

    # Card header
    d.rectangle([pad+4, card_y, W-pad, card_y+70], fill=BG3)
    d.text((pad+24, card_y+12), "Kofi's Fashion Store", font=fB(18), fill=TEXT)
    d.text((pad+24, card_y+38), "👤 Kofi Mensah  📧 kofi@example.com  📞 0244 123 456  💰 MoMo: 0244 123 456", font=fR(12), fill=TEXT3)
    # Risk gauge
    d.rectangle([W-400, card_y+18, W-280, card_y+26], fill=BG4)
    d.rectangle([W-400, card_y+18, W-400+int(120*risk/100), card_y+26], fill=rc)
    d.text((W-270, card_y+14), f"AI Risk: {risk}%", font=fB(12), fill=rc)
    rounded_rect(d, W-200, card_y+10, W-70, card_y+34, 999,
                 fill=(10,30,10), outline=(30,100,30), width=1)
    d.text((W-194, card_y+14), "✓ ID Verified", font=fB(10), fill=(74,222,128))
    rounded_rect(d, W-120, card_y+10, W-pad-4, card_y+34, 8,
                 fill=(50,40,0), outline=GOLD, width=1)
    d.text((W-112, card_y+14), "Pending", font=fB(10), fill=GOLD)

    # Body: left panel
    left_x = pad + 24
    body_y = card_y + 80
    # Flyer placeholder
    rounded_rect(d, left_x, body_y, left_x+380, body_y+200, 8, fill=BG3)
    text_c(d, "🖼  Flyer Preview", left_x+190, body_y+88, fR(16), TEXT3)

    # Description
    d.text((left_x, body_y+214), "📝  Description", font=fB(11), fill=TEXT3)
    d.text((left_x, body_y+234), "We sell quality fashion items including T-shirts, trousers,", font=fR(12), fill=TEXT2)
    d.text((left_x, body_y+252), "dresses and traditional attire at affordable prices.", font=fR(12), fill=TEXT2)
    d.text((left_x, body_y+280), "📞  Contact Details", font=fB(11), fill=TEXT3)
    d.text((left_x, body_y+300), "Phone: 0244 123 456  |  WhatsApp: 0244 123 456  |  Location: Accra, Osu", font=fR(12), fill=TEXT2)

    # Right panel
    right_x = left_x + 420
    right_w = W - pad - right_x - 20

    # AI clean box
    rounded_rect(d, right_x, body_y, right_x+right_w, body_y+80, 8,
                 fill=(5,20,5), outline=(20,80,20), width=1)
    d.text((right_x+14, body_y+12), "🤖  AI Analysis", font=fB(12), fill=(74,222,128))
    d.text((right_x+14, body_y+36), "✅ No issues detected — content appears clean.", font=fR(12), fill=(134,239,172))
    d.text((right_x+14, body_y+56), "Risk Level: LOW  (8%)", font=fR(11), fill=(74,222,128))

    # AI Caption
    rounded_rect(d, right_x, body_y+92, right_x+right_w, body_y+250, 8, fill=BG3, outline=BORDER, width=1)
    d.text((right_x+14, body_y+104), "✍  AI-Generated Caption", font=fB(11), fill=TEXT3)
    rounded_rect(d, right_x+right_w-80, body_y+100, right_x+right_w-10, body_y+122, 6,
                 fill=None, outline=GOLD, width=1)
    d.text((right_x+right_w-72, body_y+104), "📋 Copy", font=fR(10), fill=GOLD)
    caption_lines = [
        "🇬🇭✨ SHATTA TUESDAY MARKET | SUNDAY, MAY 18 ✨🇬🇭",
        "",
        "👤 Vendor: Kofi's Fashion Store",
        "📍 Location: Accra, Ghana",
        "🏪 Category: Fashion & Clothing",
        "",
        "We sell quality fashion items...",
        "",
        "💛 Promoting Ghanaian Businesses. Supporting The People.",
        "— Shatta Wale",
    ]
    for i, line in enumerate(caption_lines):
        d.text((right_x+14, body_y+128+i*12), line, font=fR(10), fill=TEXT2)

    # Hashtags
    tags = ["#ShattaTuesdayMarket", "#GhanaFashion", "#MadeInGhana", "#GhanaVendor"]
    tx = right_x + 14
    for tag in tags:
        tw2 = d.textbbox((0,0),tag,font=fR(10))[2] + 14
        rounded_rect(d, tx, body_y+256, tx+tw2, body_y+272, 999, fill=(10,20,50))
        d.text((tx+7, body_y+258), tag, font=fR(9), fill=BLUE)
        tx += tw2 + 6

    # Action buttons
    rounded_rect(d, right_x, body_y+284, right_x+right_w, body_y+310, 8, fill=GREEN)
    text_c(d, "✅  APPROVE", right_x+right_w//2, body_y+289, fB(13), (0,0,0))
    mid = right_x + right_w//2 - 5
    rounded_rect(d, right_x, body_y+316, mid, body_y+342, 8, fill=AMBER)
    text_c(d, "⏸ HOLD", right_x+(mid-right_x)//2, body_y+321, fB(12), (0,0,0))
    rounded_rect(d, mid+10, body_y+316, right_x+right_w, body_y+342, 8, fill=RED)
    text_c(d, "❌ REJECT", right_x+right_w-(right_x+right_w-mid-10)//2, body_y+321, fB(12), TEXT)

    navbar(img)
    footer(img)
    img.save(OUT + "preview_admin_submissions.png")
    print("✓ Admin submissions")


if __name__ == "__main__":
    make_home()
    make_login()
    make_vendor_dashboard()
    make_admin_dashboard()
    make_admin_submissions()
    print("\nAll previews saved to", OUT)
