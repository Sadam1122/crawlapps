# Hasil pemeriksaan mode gratis — 21 Oktober 2026

Preferensi pengguna disimpan pada AGENTS.md dan dikunci dalam Settings + RunBudget. API X dihapus dari credential, daftar platform, CLI, konfigurasi sumber, seed generator dan metadata capability aktif. Host x.com/twitter.com juga ditolak sebelum network. Artefak run lama dipertahankan sebagai arsip audit; tidak menjadi sumber aktif.

`ALLOW_PAID_PROVIDERS=true` dan budget positif ditolak saat startup. Guard runtime tetap melarang provider berbayar/biaya positif walau validasi Settings dibypass. Harga unknown, nonfinite dan negatif ditolak. Tidak ada pembelian, langganan atau upgrade quota otomatis. Web/YouTube hanya memakai rute yang dinilai tidak mempunyai biaya moneter; quota API tetap dibatasi dan berbeda dari uang.

Hasil `uv run goldintel check-apis` pada 14:17 WIB:

| Sumber | Hasil aktual | Request jaringan |
|---|---|---:|
| Web Mandiri | LIVE_OK: robots + satu halaman produk publik | 2 |
| YouTube | LIVE_OK: i18nRegions.list, key dapat mengakses API; bukan bukti seluruh metode/akun | 1 |
| Instagram | App credential ada; access token belum ada; adapter API/docs belum siap, tidak diklaim live | 0 |
| Facebook | App credential ada; access token/Page ID belum ada; adapter API/docs belum siap | 0 |
| Threads | App credential ada; access token belum ada; adapter API/docs belum siap | 0 |
| TikTok | Client credential ada; access token OAuth belum ada; adapter import-only | 0 |
| LinkedIn | Client credential ada; access token/organization permission belum ada; adapter import-only | 0 |
| RSS/berita | Import-only; belum ada feed jaringan yang disetujui | 0 |

Total pemeriksaan: **3 request, biaya moneter 0**, tanpa retry. Sumber/hasil JSON: `data/health/api-check.json`. Endpoint YouTube ini menggunakan satu quota unit menurut [dokumentasi primer](https://developers.google.com/youtube/data/reference/rest/v3/i18nRegions/list). Web diperiksa sesuai penilaian terms dan robots, tidak mengikuti seluruh tautan. Credential/response pribadi tidak disimpan pada laporan.

Smoke `uv run goldintel collect --platform all --days 30`: run `run-06c0bc0303d84340`, status partial, 9 sumber aktif tanpa X. Web berhasil dengan 2 request dan biaya 0. YouTube belum mempunyai channel approved (NO_VERIFIED_ACCOUNTS), sehingga tidak mengambil post kompetitor. Lima API sosial lain NOT_CONFIGURED; RSS/berita docs_unverified/import-only. Kegagalan sumber ini tidak menghentikan web.

`uv run pytest -q`: **95 passed**. Tes meliputi mapping credential, kosongnya token opsional, startup bebas credential, guard mode gratis, bypass konfigurasi tetap diblokir, harga unknown/positif, larangan API X sebelum dispatch, penolakan opsi CLI/import X, check-apis offline tanpa network, contract/import platform tersisa, HTTP/quota error, serta pipeline/export/analytics dan keamanan yang sudah ada. Test fixture bukan bukti live API sosial.

Gunakan:

```powershell
uv run goldintel doctor
uv run goldintel check-apis
uv run goldintel check-apis --offline
uv run goldintel collect --platform all --days 30 --dry-run
```

Offline akan menulis hasil readiness terbaru ke file health yang sama; perhatikan live_requested/live_verified, bukan hanya keberadaan file. Tidak ada kesimpulan ranking kompetitor dari probe ini.
