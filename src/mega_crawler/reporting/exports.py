import json
from pathlib import Path

import pandas as pd
from openpyxl.styles import Font, PatternFill

from mega_crawler.collection.pipeline import export_review_sample
from mega_crawler.utils.safety import atomic_json, safe_cell

EXPORTS = {
    "master_accounts": ("Akun", ["platform", "platform_id", "url", "brand_id", "reviewer_status"]),
    "master_posts": (
        "Post",
        ["platform", "post_id", "canonical_url", "published_at_utc", "text", "relevance_score"],
    ),
    "metric_snapshots": (
        "Snapshot Metrik",
        ["platform", "post_id", "observed_at_utc", "values", "metric_status"],
    ),
    "product_comparison": (
        "Produk & Biaya",
        ["product_id", "fact_name", "value", "unit", "official_source_url", "verification_status"],
    ),
    "issue_summary": (
        "Isu",
        [
            "platform",
            "aspect",
            "n_observed",
            "n_complaints",
            "observed_complaint_rate",
            "validation_status",
        ],
    ),
    "platform_rankings": (
        "Ranking per Platform",
        [
            "platform",
            "brand_id",
            "format",
            "n_posts",
            "efficiency_rank",
            "median_er_pct",
            "pooled_er_pct",
        ],
    ),
    "source_coverage": ("Coverage", ["platform", "status", "access_status", "coverage"]),
    "collection_errors": ("Error Pengumpulan", ["platform", "access_status", "error_type"]),
    "recommendations": (
        "Rekomendasi",
        [
            "finding",
            "supporting_records",
            "observed_association",
            "business_implication",
            "proposed_action",
            "effort",
            "KPI",
            "validation_experiment",
            "confidence",
            "limitations",
        ],
    ),
}


def flat_row(row):
    output = {}
    for key, value in row.items():
        if isinstance(value, dict):
            for subkey, item in value.items():
                output[f"{key}.{subkey}"] = (
                    json.dumps(item, ensure_ascii=False) if isinstance(item, (list, dict)) else item
                )
        else:
            output[key] = (
                json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value
            )
    return output


def frame(rows, columns, label):
    df = pd.DataFrame([flat_row(r) for r in rows]) if rows else pd.DataFrame(columns=columns)
    df = df.drop(columns=["dataset_label"], errors="ignore")
    df.insert(0, "dataset_label", label)
    return df


def export_bundle(pipeline, manifest, analysis, format="all"):
    run_id = manifest["run_id"]
    root = pipeline.directory(run_id) / "processed"
    root.mkdir(parents=True, exist_ok=True)
    store = pipeline.store
    records = {
        "master_accounts": store.rows("accounts"),
        "master_posts": store.rows("posts", run_id),
        "metric_snapshots": store.rows("metric_observations", run_id),
        "product_comparison": store.rows("product_facts", run_id),
        "issue_summary": analysis["issues"],
        "platform_rankings": analysis["rankings"],
        "source_coverage": manifest["sources"],
        "collection_errors": store.rows("extraction_errors", run_id),
        "recommendations": analysis["recommendations"],
    }
    frames = {}
    prefix = "DEMO_" if manifest["demo"] else ""
    for name, rows in records.items():
        df = frame(rows, EXPORTS[name][1], manifest["label"])
        frames[name] = df
        if format in {"all", "data"}:
            atomic_json(
                root / f"{prefix}{name}.json",
                {"dataset_label": manifest["label"], "run_id": run_id, "records": rows},
            )
            # Flatten nested values to avoid object schema ambiguity in empty/nullable Parquet.
            temporary = root / f"{prefix}{name}.parquet.tmp"
            df.to_parquet(temporary, index=False)
            temporary.replace(root / f"{prefix}{name}.parquet")
            temporary = root / f"{prefix}{name}.csv.tmp"
            df.map(safe_cell).to_csv(temporary, index=False, encoding="utf-8-sig")
            temporary.replace(root / f"{prefix}{name}.csv")
    atomic_json(root / f"{prefix}analysis.json", analysis)
    atomic_json(
        root / f"{prefix}review_sample.json",
        {"dataset_label": manifest["label"], "rows": export_review_sample(store, run_id)},
    )
    if format in {"all", "xlsx"}:
        path = root / f"{prefix}goldintel.xlsx"
        temporary = path.with_suffix(".tmp.xlsx")
        with pd.ExcelWriter(temporary, engine="openpyxl") as writer:
            summary = [
                {
                    "dataset_label": manifest["label"],
                    "run_id": run_id,
                    "status": manifest["status"],
                    "Mandiri": analysis["mandiri_status"],
                    "periode_mulai": manifest["window_start"],
                    "periode_akhir_eksklusif": manifest["window_end"],
                    "jumlah_post": manifest["counts"].get("posts"),
                    "keterbatasan": " | ".join(analysis["limitations"]),
                }
            ]
            frame(summary, [], manifest["label"]).drop(
                columns=["dataset_label"], errors="ignore"
            ).assign(dataset_label=manifest["label"]).map(safe_cell).to_excel(
                writer, sheet_name="Ringkasan", index=False
            )
            frame(pipeline.registry, [], manifest["label"]).map(safe_cell).to_excel(
                writer, sheet_name="Kompetitor", index=False
            )
            for name, df in frames.items():
                exported = df.copy()
                for col in exported.columns:
                    if col.endswith("_pct"):
                        exported[col] = pd.to_numeric(exported[col], errors="coerce") / 100
                exported.map(safe_cell).to_excel(writer, sheet_name=EXPORTS[name][0], index=False)
            definitions = [
                {
                    "field": "core_interactions",
                    "definition": "likes OR total equivalent reactions + comments; common cohort numerator",
                },
                {
                    "field": "ER_views",
                    "definition": "common_interactions / video_views * 100; views>0",
                },
                {
                    "field": "pooled_er_pct",
                    "definition": "sum interactions / sum denominator *100; not mean ER",
                },
                {
                    "field": "null",
                    "definition": "unavailable; status gives reason; never zero imputed",
                },
                {
                    "field": "coverage",
                    "definition": "earned population denominator unknown; official enumeration partial unless proven",
                },
                {
                    "field": "percentile",
                    "definition": "100*(average ascending tied rank-1)/(n-1); exploratory n small",
                },
            ]
            frame(definitions, [], manifest["label"]).map(safe_cell).to_excel(
                writer, sheet_name="Definisi", index=False
            )
            frame(store.rows("source_capabilities"), [], manifest["label"]).map(safe_cell).to_excel(
                writer, sheet_name="Sumber", index=False
            )
            for sheet in writer.book:
                sheet.freeze_panes = "B2"
                sheet.auto_filter.ref = sheet.dimensions
                sheet.row_dimensions[1].height = 28
                for cell in sheet[1]:
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill("solid", fgColor="163A4A")
                    sheet.column_dimensions[cell.column_letter].width = min(
                        45, max(16, len(str(cell.value)) + 2)
                    )
                    for value in list(sheet.columns)[cell.column - 1][1:]:
                        if (
                            str(cell.value).endswith("_pct")
                            or str(cell.value).endswith("_rate")
                            or str(cell.value) == "availability"
                        ):
                            value.number_format = "0.00%"
                        elif isinstance(value.value, (int, float)):
                            value.number_format = "#,##0.00"
        temporary.replace(path)
    if format in {"all", "html"}:
        from mega_crawler.reporting.html import render

        render(root / f"{prefix}report.html", manifest, analysis, records, pipeline.registry)
    write_brief(root / f"{prefix}brief.md", manifest, analysis)
    return root


def write_brief(path: Path, manifest, analysis):
    text = f"{manifest['label']} — Brief manajemen\n\nRun: {manifest['run_id']}\n\n{analysis['mandiri_status']}\n\n"
    text += "Belum tersedia bukti memadai untuk menyatakan tiga peluang campaign Mandiri atau prioritas 30/60/90 hari.\n\n"
    text += "Tiga pemeriksaan berikutnya:\n1. Verifikasi tanggal aktif Tabungan Emas dan pisahkan KSM/Titip/Ambil Emas.\n2. Setujui akun resmi melalui tautan domain primer dan periksa scope/izin ekspor.\n3. Kumpulkan cohort format/periode/umur sama, audit availability dan review komentar terstratifikasi.\n\n"
    text += "Tindakan pengumpulan: impor berizin; YouTube public API setelah key dan akun approved tersedia; ulang snapshot untuk velocity.\n\n"
    text += "Keterbatasan: " + " ".join(analysis["limitations"])
    path.write_text(text, encoding="utf-8")
