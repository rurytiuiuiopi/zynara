"""
AI Moderation Engine for SHATTA TUESDAY MARKET
Rule-based analysis with risk scoring 0-100.
"""
import json
import hashlib
import re
from datetime import datetime

SCAM_KEYWORDS = [
    "double your money", "100% profit", "guaranteed returns", "miracle cure",
    "get rich quick", "investment scheme", "pyramid", "ponzi", "forex signals",
    "bitcoin doubler", "crypto pump", "send money first", "advance fee",
    "western union", "gift card payment", "win prize", "lottery winner",
    "congratulations you won", "unclaimed funds", "inheritance money",
    "emergency cash", "urgent transfer", "419", "click here to claim",
    "limited time only act now", "no risk guaranteed profit",
    "make money from home doing nothing", "secret method", "hidden trick",
    "exclusive offer for you only", "your account has been selected",
    "loan sharks", "quick money", "easy money", "passive income scheme",
]

SUSPICIOUS_PRICE_PATTERNS = [
    r"\b100%\s*(profit|return|gain)\b",
    r"\bdouble\b.{0,20}\b(money|investment|cash)\b",
    r"\bguaranteed\b.{0,20}\b(profit|return|income)\b",
    r"\b(zero|no)\s*risk\b",
    r"\btriple\b.{0,20}\b(money|investment)\b",
]

PROHIBITED_CATEGORIES = [
    "weapons", "drugs", "illegal", "counterfeit", "fake currency",
    "human trafficking", "adult content", "gambling site", "hacking",
    "piracy", "stolen goods",
]

BUSINESS_CATEGORIES = [
    "Food & Beverages", "Fashion & Clothing", "Beauty & Cosmetics",
    "Electronics & Tech", "Agriculture & Farming", "Health & Wellness",
    "Education & Training", "Services & Consulting", "Real Estate",
    "Transport & Logistics", "Entertainment & Events", "Crafts & Artwork",
    "Supermarket & Retail", "Construction & Hardware", "Financial Services",
    "Tourism & Hospitality", "Sports & Fitness", "Auto & Mechanics",
    "Media & Advertising", "Other",
]

GHANA_HASHTAGS_BY_CATEGORY = {
    "Food & Beverages": ["#GhanaianFood", "#MadeInGhana", "#GhanaFood", "#Ghanaian", "#AccraFood"],
    "Fashion & Clothing": ["#GhanaFashion", "#AfricanFashion", "#MadeInGhana", "#KenteStyle", "#GhanaStyle"],
    "Beauty & Cosmetics": ["#GhanaBeauty", "#NaturalGlow", "#AfricanBeauty", "#GhanaCosmetics"],
    "Electronics & Tech": ["#GhanaTech", "#TechGhana", "#AfricaTech", "#GhanaStartup"],
    "Agriculture & Farming": ["#GhanaAgric", "#GhanaFarms", "#AgricGhana", "#GhanaFarming"],
    "default": ["#ShattaTuesdayMarket", "#GhanaBusiness", "#SupportGhana", "#BuyGhanaian",
                 "#GhanaEntrepreneur", "#ShattaWale", "#PromotingGhana", "#GhanaVendor"],
}


def analyze_text(text: str) -> dict:
    """Check text for scam/suspicious content. Returns list of issues found."""
    if not text:
        return {"issues": [], "score": 0}

    text_lower = text.lower()
    issues = []
    score = 0

    for kw in SCAM_KEYWORDS:
        if kw in text_lower:
            issues.append(f"Scam keyword detected: '{kw}'")
            score += 20

    for pattern in SUSPICIOUS_PRICE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            issues.append(f"Suspicious offer pattern detected")
            score += 15
            break

    for cat in PROHIBITED_CATEGORIES:
        if cat in text_lower:
            issues.append(f"Prohibited content keyword: '{cat}'")
            score += 30

    return {"issues": issues, "score": min(score, 60)}


def check_contact_info(contact_details: str) -> dict:
    """Validate contact info completeness."""
    issues = []
    score = 0

    if not contact_details or len(contact_details.strip()) < 10:
        issues.append("Missing or incomplete contact information")
        score += 20

    # Check for at least a phone number pattern
    phone_pattern = r"(\+?233|0)\d{9}"
    if not re.search(phone_pattern, contact_details):
        issues.append("No valid Ghana phone number found in contact details")
        score += 10

    return {"issues": issues, "score": score}


def check_file_quality(file_path: str, file_size: int) -> dict:
    """Basic quality check for uploaded files."""
    issues = []
    score = 0

    if file_size < 5000:  # Less than 5KB suggests very low quality
        issues.append("Image appears to be very low quality (small file size)")
        score += 15

    return {"issues": issues, "score": score}


def check_blacklist(phone: str, momo: str, email: str, business_name: str) -> dict:
    """Check against blacklist database."""
    from shatta_db import get_db
    conn = get_db()
    issues = []
    score = 0

    clauses = []
    params = []
    if phone:
        clauses.append("phone = ?")
        params.append(phone)
    if momo:
        clauses.append("momo_number = ?")
        params.append(momo)
    if email:
        clauses.append("email = ?")
        params.append(email)
    if business_name:
        clauses.append("business_name = ?")
        params.append(business_name)

    if clauses:
        query = f"SELECT reason FROM blacklist WHERE {' OR '.join(clauses)} LIMIT 1"
        hit = conn.execute(query, params).fetchone()
        if hit:
            issues.append(f"Vendor is on the fraud blacklist: {hit['reason']}")
            score += 50

    conn.close()
    return {"issues": issues, "score": score}


def check_duplicate(description: str, vendor_id: int) -> dict:
    """Check for duplicate submission content."""
    from shatta_db import get_db
    conn = get_db()
    issues = []
    score = 0

    content_hash = hashlib.md5(description.strip().lower().encode()).hexdigest()
    existing = conn.execute(
        "SELECT id FROM promotions WHERE vendor_id = ? AND business_description = ? AND status != 'rejected'",
        (vendor_id, description.strip())
    ).fetchone()

    if existing:
        issues.append("Duplicate submission detected — identical content already submitted")
        score += 25

    conn.close()
    return {"issues": issues, "score": score}


def generate_caption(vendor_name: str, business_name: str, category: str,
                     description: str, location: str) -> str:
    """Generate a social media caption for the promotion."""
    today = datetime.now().strftime("%A, %B %d")
    short_desc = description[:200].strip()
    if len(description) > 200:
        short_desc += "..."

    caption = (
        f"🇬🇭✨ SHATTA TUESDAY MARKET | {today.upper()} ✨🇬🇭\n\n"
        f"👤 Vendor: {business_name}\n"
        f"📍 Location: {location}\n"
        f"🏪 Category: {category}\n\n"
        f"{short_desc}\n\n"
        f"💛 Promoting Ghanaian Businesses. Supporting The People.\n"
        f"— Shatta Wale"
    )
    return caption


def generate_hashtags(category: str) -> list:
    base = GHANA_HASHTAGS_BY_CATEGORY.get("default", [])
    category_tags = GHANA_HASHTAGS_BY_CATEGORY.get(category, [])
    combined = list(dict.fromkeys(category_tags + base))
    return combined[:12]


def run_full_analysis(
    vendor_id: int,
    description: str,
    contact_details: str,
    prices_text: str,
    flyer_size: int = 0,
    vendor_phone: str = "",
    vendor_momo: str = "",
    vendor_email: str = "",
    business_name: str = "",
    vendor_name: str = "",
    category: str = "",
    location: str = "",
    id_verified: bool = False,
) -> dict:
    all_issues = []
    total_score = 0

    # Text analysis on description + prices
    combined_text = f"{description} {prices_text}"
    text_result = analyze_text(combined_text)
    all_issues.extend(text_result["issues"])
    total_score += text_result["score"]

    # Contact info check
    contact_result = check_contact_info(contact_details)
    all_issues.extend(contact_result["issues"])
    total_score += contact_result["score"]

    # File quality check
    if flyer_size > 0:
        file_result = check_file_quality("", flyer_size)
        all_issues.extend(file_result["issues"])
        total_score += file_result["score"]

    # Blacklist check
    bl_result = check_blacklist(vendor_phone, vendor_momo, vendor_email, business_name)
    all_issues.extend(bl_result["issues"])
    total_score += bl_result["score"]

    # Duplicate check
    dup_result = check_duplicate(description, vendor_id)
    all_issues.extend(dup_result["issues"])
    total_score += dup_result["score"]

    # Unverified ID penalty
    if not id_verified:
        all_issues.append("Vendor ID not yet verified by admin")
        total_score += 10

    risk_score = min(total_score, 100)

    caption = generate_caption(vendor_name, business_name, category, description, location)
    hashtags = generate_hashtags(category)

    return {
        "risk_score": risk_score,
        "warnings": all_issues,
        "caption": caption,
        "hashtags": hashtags,
        "risk_level": (
            "LOW" if risk_score < 30
            else "MEDIUM" if risk_score < 60
            else "HIGH"
        ),
    }
