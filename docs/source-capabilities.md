# Capability dan status adapter

Mode gratis terkunci; X telah dihapus. Hasil terbaru: [free-only verification](free-only-verification.md).

Tanggal pemeriksaan dokumentasi: **21 Oktober 2026**. Mesin membaca `configs/source_capabilities.yaml`; status akses aktual per run berada di manifest dan export Coverage. “Contract tested” berarti pengujian fixture lokal, bukan bukti akses API. Semua adapter menyediakan capabilities/discover_accounts/fetch_posts/fetch_metrics/fetch_comments/healthcheck; yang tidak tersedia mengembalikan model `UnsupportedCapability`, bukan list kosong.

| Sumber | Implementasi dan test | Akses live | Keterbatasan |
|---|---|---|---|
| Web resmi | HTTP + robots + Crawl4AI raw extraction, fixture dan live | 1 halaman Mandiri berhasil, 2 request | Allowlist satu URL, publication unknown; tidak diikutkan ranking periode sosial. Penilaian halaman/privacy bukan izin seluruh situs. |
| YouTube | Public Data API v3 channels → uploads playlist → videos; pagination/checkpoint, stats dan komentar top-level time order; fixture tested | Probe i18nRegions.list LIVE_OK; belum ada channel approved | API key dan ID akun approved diperlukan; format `video_unknown` kecuali live, tidak menebak Shorts dari durasi. Analitik turunan diblokir karena izin belum ada. |
| Instagram | Contract + CSV/JSON import tested | NOT_CONFIGURED; docs_unverified | Dokumentasi 429; versi, jenis akun, Business Discovery scopes/path belum diverifikasi. Tidak ada endpoint tebakan. |
| TikTok | Contract + import tested | NOT_CONFIGURED / permission required | FAQ Research Tools menyatakan pengguna komersial tidak eligible. Display API creator authorization belum diimplementasikan. |
| Threads | Contract + import tested | NOT_CONFIGURED; docs_unverified | Dokumentasi 429; profile/keyword discovery, token/scopes belum diverifikasi. |
| Facebook | Contract + import tested | NOT_CONFIGURED; docs_unverified | Dokumentasi 429; Page publik/own Page/other Page tidak disamakan. Personal profile/group tidak didukung. |
| LinkedIn | Contract + import tested | NOT_CONFIGURED / vetted permission | Dokumentasi Community Management terbaca; token admin bukan akses insight kompetitor. Belum ada adapter endpoint organisasi. |
| RSS/berita | Contract + JSON/CSV post import tested | docs_unverified / import only | Tidak ada feed network aktif, XML ingestion/search discovery/story clustering otomatis belum diimplementasikan. |

Dokumentasi primer: [Crawl4AI 0.9](https://docs.crawl4ai.com/core/simple-crawling/), [channels](https://developers.google.com/youtube/data/reference/rest/v3/channels/list), [playlistItems](https://developers.google.com/youtube/data/reference/rest/v3/playlistItems/list), [videos](https://developers.google.com/youtube/data/reference/rest/v3/videos/list), [commentThreads](https://developers.google.com/youtube/data/reference/rest/v3/commentThreads/list). Uploads dipakai untuk enumerasi owned; earned `search.list` belum diimplementasikan dan tidak ada janji 90 hari search.

YouTube public key tidak memberi reach, impressions, shares, saves, dislike, watch time atau insight privat. Setiap field yang tidak ada tetap null/status. Views bukan unique viewer; definisi Shorts berubah sejak 31 Maret 2025, ditandai pada definition version dan format tidak diinferensikan. [Kebijakan data/derived metrics](https://developers.google.com/youtube/terms/developer-policies) mengharuskan izin analitik tertentu; implementasi default raw-only. Penghapusan/refresh non-authorized data paling lambat 30 hari harus dipatuhi.

Dokumen tambahan: [TikTok Research FAQ](https://developers.tiktok.com/docs/en/research-api-faq), [LinkedIn](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/community-management-overview), [Instagram](https://developers.facebook.com/docs/instagram-platform/), [Facebook](https://developers.facebook.com/docs/pages-api/), [Threads](https://developers.facebook.com/docs/threads/). Meta ditandai docs_unverified, bukan berhasil diinspeksi.

Adapter sosial yang belum live menggunakan base contract bersama; credential configured tidak berarti endpoint implemented/permission approved. Raw response tidak dipersistenkan; metadata/hash dan extract minimal tersimpan. Impor membutuhkan hak penggunaan/retensi yang sah; provider berlisensi belum dikonfigurasi. Region dan window aktual provider tidak diisi dengan angka rekaan.
