# Kamus data dan provenance

Model validasi: `schemas/intelligence.py`. SQLite menyimpan tabel bernama domain dengan kolom `id`, `run_id`, JSON `data`, dan `created_at`; indeks run tersedia. Ini document store ringan dalam SQLite, bukan skema kolom SQL analitik penuh. Migrasi v1 dicatat; `run_record_data` membekukan representasi per run agar laporan lama tidak berubah saat post global di-upsert. Gunakan export Parquet untuk analisis kolom.

| Tabel | Isi / aturan |
|---|---|
| entities, brands, products | ID entitas/brand/produk terpisah; ANTAM produk digital dan fisik tetap entitas sama; DANA/GoPay kanal bukan pedagang tambahan |
| relationships | Many-to-many dengan sumber, checked_at, valid_from/to nullable; tanggal berlaku belum diketahui tidak diisi tanggal rilis |
| accounts | Tautan domain primer, platform ID, tanggal, alasan, confidence, reviewer status; registry awal belum mempunyai akun approved |
| posts | Platform+post_id sebagai identity, canonical_url tracking-free; text/title disaring PII; published nullable aware UTC, collected UTC; format/ownership/disclosure/provenance/hash |
| post_versions | Versi sebelum upsert post; tidak menggabungkan caption identik atau cross-post beda platform |
| post_brand_mentions | Satu row per post+brand, matched alias, alasan dan fractional allocation 1/k; full allocation juga tersimpan |
| metric_observations | Append-only observation_id; nilai raw+parsed+precision+status per field; versi definisi, source_url/hash, correction; analytics_permission |
| account_observations | Dicadangkan untuk snapshot akun; collector follower belum diimplementasikan, tidak diisi followers kini sebagai followers historis |
| comments_or_mentions | ID internal hash; tidak menyimpan profil/handle personal; teks gold-relevant disaring, selection_method dan sumber |
| product_facts | Fakta tervalidasi dari impor, unit/kanal/sumber/effective/checked, live/planned/unknown, SCD valid_from/to; halaman crawl tidak otomatis menjadi fakta biaya |
| price_quotes | Model harga tersedia; importer terintegrasi harga/ranking harga belum tersedia; sisi customer_buy/customer_sell harus diverifikasi |
| news_items | Dicadangkan; berita dapat diimpor sebagai posts, story clustering belum tersedia |
| issue_clusters | Ringkasan aspek preliminary, denominator komentar relevan teramati, bukti, tanpa incidence nasabah |
| source_capabilities | Dokumentasi/versi/scopes/status/retensi dari config; live result ada di collection_runs/events |
| collection_runs, collection_events, extraction_errors | Manifest, config hash, window, request/cost, bukti pengumpulan, status error aman |
| ranking_runs, ranking_components | Analisis/gate/dimensi dan daftar bukti; konfigurasi dibekukan per run |
| analyst_reviews | Tabel tersedia; workflow review manusia melalui berkas review dan utility agreement, tidak ada label gold otomatis |
| checkpoints | Token halaman YouTube yang disimpan setelah data page durable; resume window sama |

Nilai metrik `null` berarti unavailable. Status: observed, not_exposed, hidden, requires_permission, unsupported, request_failed, not_collected. Nol hanya jika sumber mengobservasi nol. `count_precision`: exact/rounded/estimated/unknown. Model snapshot menolak status observed tanpa angka, angka negatif/nonfinite, serta angka untuk field request_failed. Koma/titik/rb/jt/K/M diparse; format ambigu perlu locale dan review.

Metric hanya level post; denominator follower belum diintegrasikan. likes dan reactions tidak dijumlahkan bersama. Penyimpanan UTC; window half-open. Dashboard filter tanggal mengubah WIB ke UTC. Observasi pertama umur 90 hari tidak menjadi statistik 24h/7d. Penurunan count diberi correction, bukan velocity negatif.

JSON mempertahankan tipe/null/nested status. Parquet/CSV/Excel flatten field, misalnya `values.likes`, `metric_status.likes`. CSV UTF-8-SIG dan Excel menetralkan awalan formula; HTML meng-escape teks/JSON dan membatasi protokol tautan. Setiap artefak demo mempunyai prefix dan label. Data evidence berupa hash/locator bukan bukti raw yang selalu dapat direkonstruksi; simpan sumber asli sesuai izin operator dan kebutuhan audit.
