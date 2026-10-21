# Gold Competitor Intelligence Indonesia

**Mode gratis saja:** request berbayar dan harga unknown diblokir permanen. `ALLOW_PAID_PROVIDERS` harus false dan `MAX_COST_PER_RUN` harus 0; nilai lain ditolak saat startup. API X sudah dihapus dari platform, credential, konfigurasi dan CLI. Tidak ada langganan, pembelian kredit, upgrade quota otomatis, atau LLM berbayar.

Pipeline lokal untuk membandingkan **data pemasaran emas yang teramati**, dengan provenance, nilai unavailable, dan gate ranking. Bukan pengukuran market share, penjualan, nasabah, AUM atau conversion kompetitor.

Implementasi berada di `src/mega_crawler/`. Entry point lama `mega-crawler` dipertahankan; berkas contoh buku sebelumnya kosong. `goldintel` adalah entry point intelligence. SQLite dan Parquet dipakai tanpa server database. PostgreSQL belum didukung dan ditolak eksplisit jika dipasang pada `DATABASE_URL`.

## Setup

Windows PowerShell, dari root repo:

```powershell
uv sync --locked
uv run crawl4ai-setup
# Hanya bila belum punya .env; jangan menimpa credential existing:
if (!(Test-Path .env)) { Copy-Item .env.example .env }
uv run goldintel doctor
uv run crawl4ai-doctor
```

Linux:

```bash
uv sync --locked
uv run crawl4ai-setup
test -f .env || cp .env.example .env
uv run goldintel doctor
uv run crawl4ai-doctor
```

Python proyek 3.12; `uv.lock` mempertahankan resolusi yang ada, dengan tambahan httpx/PyYAML sebagai dependensi langsung serta pyarrow/openpyxl untuk ekspor. Chromium diperlukan oleh Crawl4AI. Perkiraan awal: RAM 2–4 GB saat Chromium berjalan, disk environment/browser sekitar 1–3 GB; ini perkiraan operasional, bukan hasil benchmark. Request serial/konkurensi rendah, batas default 100 request/run. Tidak ada paid request atau LLM.

## Command yang tersedia

```powershell
uv run goldintel --help
uv run goldintel check-apis
uv run goldintel check-apis --offline
uv run goldintel doctor
uv run goldintel verify-registry
uv run goldintel discover --segment direct
uv run goldintel collect --platform web --days 90 --dry-run
uv run goldintel collect --platform web --days 90
uv run goldintel collect --platform youtube --days 90
uv run goldintel collect --platform all --days 30
uv run goldintel import --platform instagram --file PATH.json
uv run goldintel normalize --run-id RUN_ID
uv run goldintel analyze --run-id RUN_ID
uv run goldintel report --run-id RUN_ID --format all
uv run goldintel dashboard --run-id RUN_ID
uv run goldintel demo
uv run goldintel --demo-data dashboard
```

Ganti `RUN_ID` dengan ID keluaran collect/import. Collect belum otomatis membuat report; jalankan normalize (idempotent), analyze, lalu report. `--end` menerima timestamp dengan zona, misalnya `2026-10-21T00:00:00+07:00`; interval selalu `[start,end)`. Opsi days: 30/90/180/365. Satu API gagal tidak menghentikan platform lain. Periksa **status manifest**, bukan hanya exit code: collect dapat keluar normal dengan `partial`/`failed` yang menyimpan alasan per sumber.

```powershell
uv run goldintel collect --platform youtube --resume-run-id RUN_ID
uv run goldintel --demo-data report --run-id DEMO_RUN_ID --format all
# Menghapus data dan export lokal satu run untuk kewajiban deletion:
uv run goldintel purge --run-id RUN_ID
```

Resume mempertahankan window/config run asal dan checkpoint halaman YouTube; bukan cara memperluas window. Semua request tetap read-only. Tidak ada scheduler yang dibuat. Jika ingin otomasi, Task Scheduler/cron dapat menjalankan collect, kemudian normalize/analyze/report dengan ID hasilnya; operator tetap harus memastikan izin dan retensi.

## Hasil dan status akses

`data/goldintel.sqlite`, `data/runs/RUN_ID/manifest.json`, metadata/hash di `evidence/`, analisis, dan `processed/` berisi CSV UTF-8-SIG, Parquet, JSON, Excel, HTML, serta brief satu halaman. Report memperlihatkan data mentah, status metrik, sumber, freshness dan limitations. Dashboard memakai HTML lokal yang sama di `http://127.0.0.1:8501/`; tidak ada deployment atau unggah ke layanan lain.

Demo berada di **`data/demo/` dengan database terpisah**, setiap export diberi nama `DEMO_*` dan label dataset. Fixture tidak memuat peringkat kompetitor riil. Tidak ada demo yang diimpor melalui command production. Unit test memakai direktori sementara.

Pemeriksaan terbaru 21 Oktober 2026: `goldintel check-apis` berhasil menguji halaman publik Mandiri (2 request) dan `i18nRegions.list` YouTube (1 request), biaya moneter 0. Lima platform sosial lain baru mempunyai App/Client credential, belum access token OAuth dan belum integrasi API live. RSS/berita melalui impor. Detail setiap sumber disimpan di `data/health/api-check.json`; `--offline` memeriksa readiness tanpa network. Pemeriksaan live dibatasi maksimal 3 request dan tanpa retry, tidak mengambil post kompetitor. Lihat [hasil terbaru](docs/free-only-verification.md) dan [matriks adapter](docs/source-capabilities.md).

## Credential dan izin

Pembaruan credential lokal 21 Oktober 2026: YouTube API key sudah dikonfigurasi dan probe satu request API publik berhasil. Credential aplikasi Instagram/Facebook/Threads/TikTok/LinkedIn tersimpan terpisah dari access token; token dan ID akun belum tersedia. Ini pembaruan setelah smoke awal yang tercatat di atas. Pemetaan variabel dan langkah OAuth: [docs/credential-setup.md](docs/credential-setup.md).

Edit `.env` **secara lokal**, jangan kirim secret ke chat. Minimum untuk web dan impor: tidak ada token. Untuk YouTube: isi `YOUTUBE_API_KEY` dari project yang mengaktifkan YouTube Data API, lalu tambahkan channel ID yang telah dibuktikan dari domain resmi ke `verified_social_accounts` pada registry. Tanpa akun berstatus `approved`, hasilnya `NO_VERIFIED_ACCOUNTS`. Tidak ada tebakan ID/akun. [Contoh verifikasi akun](docs/account-verification.md).

Kebijakan YouTube yang diperiksa membatasi metrik turunan dan retensi API data. Implementasi menampilkan data mentah dan **memblokir analitik turunan YouTube secara default**, termasuk hasil impor YouTube. Key saja tidak memberikan izin derived metrics. Tidak ada jalur OAuth/refresh token yang belum diverifikasi. Token Instagram/Meta/Threads/TikTok/LinkedIn dapat dideteksi oleh doctor tetapi **tidak mengaktifkan endpoint yang belum diimplementasikan**. Jangan mengisi credential yang tidak diperlukan.

`.env`, sesi, data dan log diabaikan Git; log menyaring token dan pola PII. Saat browser/API meminta login, CAPTCHA atau 403, adapter berhenti; jangan memakai proxy/akun untuk menghindari pembatasan. Redirect perlu review dan tidak diikuti otomatis. [Biaya dan retensi](docs/costing.md).

## Impor manual

Format utama JSON adalah envelope `source`, `posts`, opsional `comments` dan `product_facts`. [Spesifikasi dan template](docs/imports.md). CSV membutuhkan sidecar `.meta.json` dengan nama dasar sama. Bukti izin, provider, source URL, timestamp snapshot dan versi definisi metrik wajib; angka kosong berbeda dari nol.

Registry menyediakan 30 produk/seed awal dalam beberapa segmen, **bukan daftar seluruh Indonesia**. Status legal, izin, operasi dan akun memiliki tingkat verifikasi tersendiri. Tanggal rilis Mandiri tidak dijadikan tanggal aktif. Facts produk masih memerlukan impor/review, bukan diisi dengan tebakan dari teks marketing. Tidak ada asumsi saldo emas dijamin LPS.

## Pemeriksaan

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run goldintel demo
```

Jika `uv` gagal mengakses cache, perbaiki izin cache pengguna atau gunakan `UV_CACHE_DIR` pada direktori milik pengguna; kegagalan environment bukan hasil pengujian. Jika Chromium belum tersedia, jalankan setup dan doctor; web mencatat error extraction, impor tetap berfungsi. Bila report sedang dibuka Excel, tutup workbook sebelum menulis ulang. Hasil pengujian yang benar-benar dijalankan dicatat di [docs/verification.md](docs/verification.md).

Detail: [metodologi](docs/methodology.md), [kamus data](docs/data-dictionary.md), [batas implementasi](docs/limitations.md), [review manual](docs/manual-review.md), [audit awal](docs/audit.md).
