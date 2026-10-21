import re

TOPICS = {
    "edukasi": ["tahukah", "edukasi", "tips"],
    "tutorial": ["cara", "langkah"],
    "promo": ["promo", "diskon", "cashback"],
    "product launch": ["hadir", "diluncurkan"],
    "trust/security": ["aman", "keamanan", "palsu"],
    "testimonial": ["pengalaman"],
    "KOL": ["#ad", "#sponsored"],
    "lifestyle": ["gaya hidup"],
    "goal-based saving": ["masa depan", "impian", "nabung"],
    "harga emas": ["harga emas"],
    "cetak fisik": ["cetak", "tarik fisik"],
    "cicilan": ["cicil", "angsuran"],
    "perbandingan harga": ["spread", "selisih harga"],
    "FAQ": ["tanya", "faq"],
    "layanan/keluhan": ["gagal", "error", "keluhan"],
}
ASPECTS = {
    "spread": ["spread", "selisih"],
    "biaya": ["biaya", "admin"],
    "minimum": ["minimum", "minimal"],
    "trust": ["aman", "percaya"],
    "tarik_fisik": ["cetak", "tarik fisik"],
    "buyback": ["buyback", "jual kembali"],
    "aplikasi": ["error", "gangguan", "gagal beli", "gagal jual"],
    "verifikasi": ["verifikasi", "kyc"],
    "pelayanan": ["layanan", "cs", "antrean"],
}


def classify(text):
    text = text.lower()
    gold = bool(re.search(r"\bemas\b|bulion|buyback|brankas", text))
    impersonation = "palsu" in text or "mengatasnamakan" in text
    complaint = any(t in text for t in ("gagal", "error", "mahal", "keluhan", "lambat"))
    positive = any(t in text for t in ("mudah", "terbantu", "bagus"))
    label = "unclear"
    if gold:
        label = (
            "mixed"
            if complaint and positive
            else "negative"
            if complaint
            else "positive"
            if positive
            else "neutral"
        )
        if impersonation or "harga emas turun" in text:
            label = "neutral"
    return {
        "topic_tags": [key for key, terms in TOPICS.items() if any(t in text for t in terms)],
        "aspects": [key for key, terms in ASPECTS.items() if any(t in text for t in terms)],
        "sentiment": label,
        "confidence": 0.3,
        "validation_status": "preliminary_unvalidated",
        "evidence_snippet": text[:160],
        "gold_relevant": gold,
        "speech_type": "impersonation_warning"
        if impersonation
        else "question"
        if "?" in text
        else "complaint"
        if complaint
        else "unclear",
        "severity": "unreviewed",
        "causality": "not_established",
    }
