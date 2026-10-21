# Arsip verifikasi awal — 21 Oktober 2026

Hasil ini adalah snapshot awal sebelum credential YouTube dipasang. Status terbaru ada di [free-only-verification.md](free-only-verification.md).

Pemeriksaan dijalankan pada Windows, Python 3.12.11, dari root proyek. Tidak ada token sosial yang tersedia menurut doctor; isinya tidak dicetak. Tidak ada paid request.

| Pemeriksaan | Hasil aktual |
|---|---|
| `uv run crawl4ai-doctor` | Lulus; Chromium dan crawling test halaman Crawl4AI berhasil |
| Inspect signature API terpasang | Crawl4AI 0.9.5, arun/CrawlerRunConfig/BrowserConfig diperiksa |
| `uv run ruff check .` | Lulus |
| `uv run ruff format --check .` | Lulus, 51 berkas formatted pada pemeriksaan terakhir |
| `uv run pytest` | **80 passed**, 7.72s pada pemeriksaan terakhir; tidak memanggil API sosial live |
| `goldintel doctor`, `verify-registry`, `discover`, dry-run | Smoke CLI dijalankan; config/credential status terpisah dari live success |
| `uv run goldintel collect --platform all --days 30` | `partial`; web 1 halaman, 2 request, biaya 0, 9 sumber lain tidak diklaim berhasil |
| `uv run goldintel collect --platform web --days 90` | `success`; satu halaman produk Mandiri, 2 request, tanpa snapshot metrik sosial |
| normalize → analyze → report all | Berhasil untuk run web; 0 ranking, Mandiri belum eligible; CSV/Parquet/JSON/XLSX/HTML/brief dibuat |
| `goldintel demo` | Berhasil, 12 post sintetis, database/output terpisah, 0 ranking riil |
| `uv run python scripts/verify_dashboard.py` | Chromium headless + server dashboard lokal berhasil; 12 post/12 snapshot; filter platform/brand/segment/ownership/format/date/reset; 0 JavaScript errors; `/.env` 404; proses dihentikan setelah smoke |
| Export review | Workbook dibuka dengan openpyxl: sheet wajib/filter/freeze; tidak ada sel formula dari input berbahaya; Parquet mempertahankan unavailable null; HTML payload di-escape; screenshot dashboard diinspeksi |

Run live all: `run-6b096c03379d4829` (30 hari, partial). Run web dengan ekstraksi body produk: `run-33b559e75589491e` (90 hari, success). Hasil lokal: `data/runs/<run-id>/`. Demo hasil terbaru dapat dipilih `goldintel --demo-data dashboard`; ID demo berubah setiap run.

Tes meliputi parsing Indonesia/global/rounded/hidden/zero, timezone/window/umur snapshot, ambiguous relevance dan multibrand 1/k, account/provider identity, dedupe/idempotensi, SCD fakta produk, correction, 401/403/429/5xx/Retry-After/circuit/request budget, pagination YouTube/key missing, unsupported contract semua platform, CSV+sidecar dan JSON semua platform, numerator/zero denominator/pooled vs median, rank gates/tie/missing/cohort intersection/outlier, sensitivity utility, price perspective/time mismatch, preliminary sentiment, PII/token redaction, formula/HTML injection, SSRF/redirect, demo isolation dan retention/purge.

Catatan kegagalan yang diselesaikan: uv awal tidak dapat mengakses cache pengguna di sandbox; pengulangan dengan izin environment berhasil. Acceptance pertama melalui uv menemukan ACL direktori temp pytest Windows dan satu file belum formatted; temp tes kini unik di workspace dan cacheprovider dimatikan, kemudian ketiga pemeriksaan lulus. Kegagalan ini tidak dicatat sebagai tes lulus sebelum perbaikan.

YouTube API hanya diuji fixture; Instagram/TikTok/Threads/Facebook/LinkedIn hanya contract/import, belum endpoint live. RSS/berita hanya impor. Tidak ada kesimpulan peringkat pasar atau rekomendasi campaign riil dari hasil smoke.
