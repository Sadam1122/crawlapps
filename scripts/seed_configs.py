"""Maintainer script: evidence checked 2026-10-21; does not imply crawl permission."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CHECKED = "2026-10-21"
SEEDS = [
    (
        "mandiri",
        "PT Bank Mandiri (Persero) Tbk",
        "Mandiri",
        "tabungan-emas",
        "Tabungan Emas / Livin' Emas",
        "direct",
        "https://www.bankmandiri.co.id/livin/emas",
        "verified_active",
        ["mandiri", "livin", "livin' emas"],
        "page_checked_legal_name_pending",
    ),
    (
        "pegadaian",
        "PT Pegadaian",
        "Pegadaian",
        "tabungan-emas",
        "Tabungan Emas / Tring!",
        "direct",
        "https://pegadaian.co.id/emas/tabungan-emas",
        "verified_active",
        ["pegadaian", "tring"],
        "page_checked_legal_name_pending",
    ),
    (
        "bsi",
        "PT Bank Syariah Indonesia Tbk",
        "BSI",
        "emas",
        "BSI Emas / BYOND",
        "direct",
        "https://www.bankbsi.co.id/produk%26layanan/produk/layanan-bank-emas",
        "verified_active",
        ["bsi", "byond"],
        "legal_name_latest_pending_verification",
    ),
    (
        "antam",
        "PT Aneka Tambang Tbk",
        "ANTAM Logam Mulia",
        "brankas",
        "BRANKAS",
        "direct",
        "https://logammulia.com/id/brankas",
        "pending_verification",
        ["antam", "brankas", "logam mulia"],
        "permission_blocked_403",
    ),
    (
        "treasury",
        "PT Indonesia Logam Pratama",
        "Treasury",
        "emas",
        "Treasury Emas",
        "direct",
        "https://www.treasury.id/",
        "verified_active",
        ["treasury"],
        "page_checked_legal_name_pending",
    ),
    (
        "pluang",
        "PT Pluang Emas Sejahtera",
        "Pluang",
        "emas",
        "Emas Pluang",
        "direct",
        "https://pluang.com/faq/gold/gold-product/apa-itu-emas-pluang",
        "verified_active",
        ["pluang"],
        "self_reported",
    ),
    (
        "indogold",
        "PT Indogold Makmur Sejahtera",
        "IndoGold",
        "emas",
        "IndoGold Emas",
        "direct",
        "https://www.indogold.id/member/registration",
        "pending_verification",
        ["indogold"],
        "registration_page_insufficient_for_activity",
    ),
    (
        "lakuemas",
        "PT Laku Emas Indonesia",
        "Lakuemas",
        "emas",
        "Lakuemas",
        "direct",
        "https://lakuemas.com/",
        "verified_active",
        ["lakuemas", "laku emas"],
        "page_checked_legal_name_pending",
    ),
    (
        "shariacoin",
        "PT Syariah Koin Indonesia",
        "ShariaCoin",
        "emas",
        "Tabungan Emas ShariaCoin",
        "direct",
        "https://www.shariacoin.co.id/",
        "verified_active",
        ["shariacoin"],
        "self_reported",
    ),
    (
        "quantum",
        "PT Quantum Metal Indonesia",
        "Quantum Metal Indonesia",
        "emas",
        "Quantum Metal Emas",
        "direct",
        "https://quantummetal.id/tentang-kami/",
        "pending_verification",
        ["quantum metal", "quantummetal"],
        "current_operation_and_license_pending",
    ),
    (
        "ubs",
        "PT Untung Bersama Sejahtera",
        "UBS Gold",
        "fisik",
        "UBS Gold",
        "physical",
        "https://ubsgold.com/",
        "verified_active",
        ["ubs gold"],
        "page_checked_legal_name_pending",
    ),
    (
        "galeri24",
        None,
        "Galeri 24",
        "fisik",
        "Galeri 24 Emas",
        "physical",
        "https://galeri24.co.id/",
        "verified_active",
        ["galeri 24", "galeri24"],
        "legal_name_pending_verification",
    ),
    (
        "hartadinata",
        "PT Hartadinata Abadi Tbk",
        "HRTA Gold / EMASKU",
        "emasku",
        "EMASKU",
        "physical",
        "https://hartadinataabadi.co.id/",
        "verified_active",
        ["hartadinata", "hrta gold", "emasku"],
        "self_reported",
    ),
    (
        "lotus",
        None,
        "Lotus Archi",
        "fisik",
        "Lotus Archi Emas",
        "physical",
        "https://lotusarchi.com/",
        "verified_active",
        ["lotus archi"],
        "legal_name_pending_verification",
    ),
    (
        "kinghalim",
        None,
        "King Halim",
        "fisik",
        "King Halim Emas",
        "physical",
        "https://kinghalim.com/",
        "pending_verification",
        ["king halim"],
        "discovery_only_requires_origin_review",
    ),
    (
        "dana",
        None,
        "DANA",
        "emas",
        "DANA eMAS",
        "distribution",
        "https://www.dana.id/help-center/keuangan-DANA/apa-saja-kelebihan-fitur-e-mas?lng=id",
        "pending_verification",
        ["dana emas", "dana emas digital"],
        "provider_per_variant_pending",
    ),
    (
        "gopay",
        None,
        "GoPay",
        "emas",
        "GoPay Emas Digital",
        "distribution",
        "https://www.treasury.id/syarat-dan-ketentuan-treasury-x-gopay",
        "verified_active",
        ["gopay emas"],
        "provider_terms_checked",
    ),
    (
        "bcasyariah",
        "PT Bank BCA Syariah",
        "BCA Syariah",
        "emas-ib",
        "Emas iB",
        "financing",
        "https://www.bcasyariah.co.id/emas-ib",
        "verified_active",
        ["bca syariah", "emas ib"],
        "page_checked_legal_name_pending",
    ),
    (
        "muamalat",
        "PT Bank Muamalat Indonesia Tbk",
        "Bank Muamalat",
        "emas-hijrah",
        "Solusi Emas Hijrah",
        "financing",
        "https://www.bankmuamalat.co.id/index.php/pembiayaan-consumer/solusi-emas-hijrah",
        "verified_active",
        ["muamalat", "solusi emas hijrah"],
        "page_checked_legal_name_pending",
    ),
]


def main():
    from urllib.parse import urlsplit

    competitors = []
    for entity, legal, brand, product, name, segment, url, active, aliases, verification in SEEDS:
        competitors.append(
            {
                "entity_id": entity,
                "legal_name": legal,
                "brand_id": entity,
                "brand_name": brand,
                "product_id": f"{entity}-{product}",
                "product_name": name,
                "segment": segment,
                "priority": 1 if segment == "direct" else 2,
                "active_status": active,
                "activity_checked_at": CHECKED,
                "relationship_to_mandiri": [
                    "benchmark"
                    if entity == "mandiri"
                    else "competitor"
                    if segment == "direct"
                    else segment
                ],
                "parent_group_id": None,
                "provider_entity_id": "treasury" if entity == "gopay" else None,
                "official_domains": [urlsplit(url).hostname],
                "verified_social_accounts": [],
                "aliases": aliases,
                "gold_product_keywords": ["emas", "gold", "bulion", "brankas", "buyback"],
                "exclusion_keywords": [
                    "ubs bank",
                    "swiss bank",
                    "antam pertanian",
                    "treasury banking",
                    "mandiri tunas finance",
                    "mtr tujuan emas",
                ],
                "verification_sources": [
                    {
                        "url": url,
                        "checked_at": CHECKED,
                        "status": verification,
                        "claim_scope": "product page activity only; not independent regulatory verification",
                    }
                ],
                "regulatory_status": "self_reported"
                if entity in {"pluang", "shariacoin", "treasury", "mandiri"}
                else "pending_verification",
                "regulatory_checked_at": None,
                "verification_status": verification,
            }
        )
    for entity, product, name, segment in [
        ("mandiri", "ksm-emas", "KSM Emas", "financing"),
        ("mandiri", "titip-emas", "Titip Emas", "custody"),
        ("mandiri", "ambil-emas", "Ambil Emas", "physical_withdrawal"),
        ("pegadaian", "cicil-emas", "Cicil Emas Pegadaian", "financing"),
        ("bsi", "cicil-emas", "BSI Cicil Emas", "financing"),
        ("antam", "fisik", "ANTAM Emas Fisik", "physical"),
    ]:
        template = next(r for r in competitors if r["entity_id"] == entity)
        competitors.append(
            {
                **template,
                "product_id": f"{entity}-{product}",
                "product_name": name,
                "segment": segment,
                "active_status": "pending_verification",
            }
        )
    for entity, brand, product in [
        ("shopee", "Shopee", "toko-fisik"),
        ("tokopedia", "Tokopedia", "toko-fisik"),
        ("blibli", "Blibli", "toko-fisik"),
        ("tokopedia", "Tokopedia", "emas-digital"),
        ("bukalapak", "Bukalapak", "bukaemas"),
    ]:
        competitors.append(
            {
                **competitors[0],
                "entity_id": entity,
                "legal_name": None,
                "brand_id": entity,
                "brand_name": brand,
                "product_id": f"{entity}-{product}",
                "product_name": product,
                "segment": "distribution",
                "priority": 3,
                "active_status": "pending_verification",
                "activity_checked_at": None,
                "relationship_to_mandiri": ["distribution_candidate"],
                "official_domains": [],
                "aliases": [brand.lower()],
                "verification_sources": [],
                "regulatory_status": "pending_verification",
                "verification_status": "unverified_seed",
            }
        )
    relationships = [
        {
            "from_entity_id": "antam",
            "to_entity_id": "mandiri",
            "relationship": "supplier_partner",
            "source_url": "https://www.bankmandiri.co.id/en/web/guest/news-detail?backUrl=/en/news&primaryKey=615042480",
            "valid_from": None,
            "valid_to": None,
            "checked_at": CHECKED,
            "verification_status": "self_reported",
            "note": "Release date is not effective/launch date",
        },
        {
            "from_entity_id": "hartadinata",
            "to_entity_id": "mandiri",
            "relationship": "supplier_partner",
            "source_url": "https://www.bankmandiri.co.id/en/web/guest/news-detail?backUrl=/en/news&primaryKey=615042480",
            "valid_from": None,
            "valid_to": None,
            "checked_at": CHECKED,
            "verification_status": "self_reported",
            "note": "Effective date unverified",
        },
        {
            "from_entity_id": "gopay",
            "to_entity_id": "treasury",
            "relationship": "distribution_provider",
            "source_url": "https://www.treasury.id/syarat-dan-ketentuan-treasury-x-gopay",
            "valid_from": None,
            "valid_to": None,
            "checked_at": CHECKED,
            "verification_status": "self_reported",
            "note": "No independent trader count for channel",
        },
        {
            "from_entity_id": "galeri24",
            "to_entity_id": "pegadaian",
            "relationship": "group_candidate",
            "source_url": "https://galeri24.co.id/",
            "valid_from": None,
            "valid_to": None,
            "checked_at": CHECKED,
            "verification_status": "pending_verification",
            "note": "Confirm legal name and ownership",
        },
    ]
    # Follow-up checks against primary pages, not search snippets.
    for record in competitors:
        if record["entity_id"] == "bsi":
            record["legal_name"] = "PT Bank Syariah Indonesia (Persero) Tbk"
            record["verification_status"] = "primary_report_name_checked"
            record["verification_sources"].append(
                {
                    "url": "https://ir.bankbsi.co.id/misc/AR/AR2025-ID/72/",
                    "checked_at": CHECKED,
                    "status": "primary_report_name_checked",
                    "claim_scope": "Current report masthead only; legal effective date not inferred",
                }
            )
        if record["entity_id"] in {
            "antam",
            "indogold",
            "treasury",
            "lakuemas",
            "shariacoin",
            "pluang",
        }:
            record["verification_sources"].append(
                {
                    "url": "https://www.icdx.co.id/membership/members-of-icdx?category=digital-gold-trader",
                    "checked_at": CHECKED,
                    "status": "exchange_membership_verified",
                    "claim_scope": "Listed member of exchange; not a fresh Bappebti operating-license determination",
                }
            )
            if record["entity_id"] in {"indogold", "treasury", "lakuemas"}:
                record["verification_status"] = (
                    "legal_name_exchange_directory_checked_activity_separate"
                )
        if record["entity_id"] == "kinghalim":
            record["verification_status"] = "physical_jewellery_page_checked_legal_name_pending"
    config = ROOT / "configs"
    config.mkdir(exist_ok=True)

    def save(name, value):
        (config / name).write_text(
            yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )

    save(
        "competitors.yaml",
        {
            "seed_universe_not_exhaustive": True,
            "checked_at": CHECKED,
            "mandiri_active_since_utc": None,
            "competitors": competitors,
            "relationships": relationships,
        },
    )
    docs = {
        "web": (
            "https://docs.crawl4ai.com/core/simple-crawling/",
            "checked",
            "HTTP + Crawl4AI 0.9.5 offline extraction",
            "No social metrics; product page publication may be unknown",
        ),
        "youtube": (
            "https://developers.google.com/youtube/data/reference/rest/v3/videos",
            "checked",
            "Data API v3",
            "Uploads pagination; no public reach/shares/watch time/dislikes; video format unknown unless verified",
        ),
        "instagram": (
            "https://developers.facebook.com/docs/instagram-platform/",
            "docs_unverified",
            "unknown",
            "429 reading docs; Business Discovery path/version/scopes not verified",
        ),
        "tiktok": (
            "https://developers.tiktok.com/docs/en/research-api-faq",
            "checked",
            "Research API ineligible for commercial use",
            "Display API creator authorization unverified; import only",
        ),
        "threads": (
            "https://developers.facebook.com/docs/threads/",
            "docs_unverified",
            "unknown",
            "429 reading docs; discovery scopes and fields unverified",
        ),
        "facebook": (
            "https://developers.facebook.com/docs/pages-api/",
            "docs_unverified",
            "unknown",
            "429 reading docs; Page access eligibility unverified",
        ),
        "linkedin": (
            "https://learn.microsoft.com/en-us/linkedin/marketing/community-management/community-management-overview",
            "checked",
            "2026-10 documentation; API endpoint not implemented",
            "Vetted access; organization permission does not imply competitor insights",
        ),
        "rss": (
            "https://www.rssboard.org/rss-specification",
            "docs_unverified",
            "RSS 2.0 / Atom import",
            "Feed network requires explicit terms assessment; no feed allowlisted initially",
        ),
        "news": (
            "https://www.rssboard.org/rss-specification",
            "docs_unverified",
            "licensed import",
            "Observed articles only; no search snippet facts",
        ),
    }
    sources = []
    for platform, (url, status, version, limits) in docs.items():
        sources.append(
            {
                "platform": platform,
                "docs_url": url,
                "docs_checked_at": CHECKED,
                "docs_status": status,
                "api_version": version,
                "scopes": "API key, public data only"
                if platform == "youtube"
                else "unverified / import provenance required",
                "metrics": ["likes", "comments", "video_views"] if platform == "youtube" else [],
                "quota": "project quota; bounded local request budget"
                if platform == "youtube"
                else "unknown",
                "historical_window": "uploads available from API; no historical snapshots reconstructed"
                if platform == "youtube"
                else "unknown",
                "region": "public source availability; Indonesia contextual relevance",
                "limitations": limits,
                "implementation": "api_implemented_credential_required"
                if platform == "youtube"
                else "web_implemented"
                if platform == "web"
                else "import_only",
                "live_verification": "not_run",
                "import_fallback": True,
                "retention_days": 30,
                "raw_evidence_policy": "metadata_hash_only",
                "cost": "no_paid_requests; API quota tracked",
            }
        )
    sources[1]["derived_metrics_status"] = (
        "permission_required; API metrics raw display only by default"
    )
    sources[1]["terms_url"] = "https://developers.google.com/youtube/terms/developer-policies"
    sources[1]["terms_checked_at"] = CHECKED
    sources[1]["retention_policy"] = (
        "Non-authorized API statistics <=30 days; delete expired data/exports. No retention extension inferred."
    )
    sources[1]["endpoint_docs"] = [
        "https://developers.google.com/youtube/data/reference/rest/v3/" + p + "/list"
        for p in ("channels", "playlistItems", "videos", "commentThreads")
    ]
    save("source_capabilities.yaml", {"sources": sources})
    save(
        "analysis.yaml",
        {
            "min_posts": 10,
            "min_availability": 0.8,
            "min_brands": 3,
            "relevance_threshold": 0.8,
            "composite_enabled": False,
            "weights": {
                "efficiency": 0.35,
                "exposure": 0.25,
                "conversation": 0.25,
                "consistency": 0.15,
            },
            "age_tolerance_hours": 12,
            "allocation": "fractional",
            "exploratory_gates": True,
        },
    )
    save(
        "web_sources.yaml",
        {
            "sources": [
                {
                    "url": "https://www.bankmandiri.co.id/livin/emas",
                    "product_id": "mandiri-tabungan-emas",
                    "terms_status": "permitted",
                    "terms_url": "https://www.bankmandiri.co.id/web/guest/kebijakan-privasi",
                    "assessment": "2026-10-21: public product HTML and linked privacy policy inspected; no automated-access restriction found for this URL. robots 200 allows non-PDF. Limited collection of this URL with metadata/hash, no media, no login; not blanket site authorization. Reassess on policy change.",
                    "raw_retention_allowed": False,
                }
            ]
        },
    )


if __name__ == "__main__":
    main()
