# Konfigurasi credential dan langkah OAuth berikutnya

Pembaruan 21 Oktober 2026: `.env` lokal dipetakan dari credential operator tanpa mencetak nilainya. `.env.example` hanya berisi placeholder dan default biaya aman. App ID/Client ID adalah identitas aplikasi, bukan ID akun media sosial. App/Client Secret bukan access token.

| Platform | Konfigurasi aplikasi | Token / identitas akun setelah otorisasi |
|---|---|---|
| YouTube | YOUTUBE_API_KEY | API publik tidak memerlukan user access token; channel ID resmi tetap harus diverifikasi pada registry |
| Instagram | INSTAGRAM_APP_ID, INSTAGRAM_APP_SECRET | INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_ACCOUNT_ID |
| Facebook | META_APP_ID, META_APP_SECRET | META_ACCESS_TOKEN, FACEBOOK_PAGE_ID |
| Threads | THREADS_APP_ID, THREADS_APP_SECRET | THREADS_ACCESS_TOKEN; identitas profil tidak ditebak dari App ID |
| TikTok | TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET | TIKTOK_ACCESS_TOKEN dari persetujuan pengguna |
| LinkedIn | LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET | LINKEDIN_ACCESS_TOKEN, LINKEDIN_ORGANIZATION_ID yang hak aksesnya telah dibuktikan |

`goldintel doctor` memisahkan application_credentials, access credential, dan account_ids; configured tidak berarti token valid atau permission disetujui. Credential opsional kosong memakai default kosong dan tidak menggagalkan startup. Instagram tidak lagi memakai META_ACCESS_TOKEN milik Facebook secara otomatis. Semua secret baru bertipe SecretStr dan masuk daftar redaction logger.

YouTube: probe live terbatas `i18nRegions.list` berhasil pada 21 Oktober 2026: satu request, reserved monetary cost 0. Probe ini memvalidasi akses key ke Data API, bukan membuktikan seluruh channel/video/komentar dapat diambil. Endpoint tersebut memakai satu quota unit menurut [dokumentasi primer](https://developers.google.com/youtube/data/reference/rest/v3/i18nRegions/list). Tidak ada post kompetitor yang diambil dalam probe. Collector masih memerlukan verified_social_accounts berstatus approved pada registry; analitik turunan tetap diblokir sesuai kebijakan/izin sebelumnya.

Untuk OAuth, pilih produk API dan permission read-only yang disetujui di developer console masing-masing, daftarkan redirect URI yang benar-benar ditangani backend, lakukan login/consent melalui halaman resmi provider dengan state acak, lalu tukarkan authorization code di server. Simpan access token secara lokal pada variabel yang sesuai; periksa scope, expiry dan refresh/revocation sesuai provider. Secret tidak dimasukkan ke URL, log atau dashboard. Dashboard saat ini tidak menyediakan callback OAuth, dan tidak ada flow OAuth yang dijalankan otomatis.

Instagram/Facebook/Threads: periksa API login path, jenis akun, scope dan proses app review pada developer console sebelum memulai. Dokumen primer Meta yang dicoba kembali pada 21 Oktober membalas 429; endpoint dan scope tidak ditebak. Sesudah otorisasi sah, ambil Instagram Account ID/Facebook Page ID dari hasil API yang diizinkan, bukan dari App ID. Akun/Page yang dapat dikelola tidak otomatis memberi akses competitor discovery/insights. App credential tersimpan belum mengaktifkan adapter API ketiga platform ini. Referensi: [Instagram](https://developers.facebook.com/docs/instagram-platform/), [Facebook Pages](https://developers.facebook.com/docs/pages-api/getting-started/), [Threads](https://developers.facebook.com/docs/threads/get-started/).

TikTok: aktifkan produk Login Kit yang sesuai dan scope yang disetujui, daftarkan HTTPS redirect URI, gunakan state dan consent pengguna, lalu tukarkan code di backend. Isi TIKTOK_ACCESS_TOKEN hanya dengan token hasil flow resmi. [Login Kit Web](https://developers.tiktok.com/docs/en/login-kit-web) menjelaskan client key/secret, redirect URI dan state. Ini tidak memberikan Research API atau akses semua konten kompetitor; adapter pengumpulan masih import-only.

LinkedIn: pastikan produk API dan scope telah disetujui, daftarkan redirect URL HTTPS, lakukan authorization-code flow dengan consent anggota, lalu simpan LINKEDIN_ACCESS_TOKEN. Organization ID harus berasal dari organisasi yang diizinkan oleh produk/role pengguna. Client ID tidak dapat dipakai sebagai Organization ID, dan token sign-in tidak otomatis memberikan Community Management. [Authorization Code Flow](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow) mendokumentasikan proses tersebut. Adapter pengumpulan organisasi belum diimplementasikan.

Konfigurasi operasional lokal: SQLite `data/goldintel.sqlite`, Asia/Jakarta, mode gratis terkunci. Flag paid true atau budget positif ditolak saat startup, dan guard runtime tetap menolak biaya positif meskipun konfigurasi dibypass. Harga unknown diblokir. API X sudah dihapus, bukan sekadar belum mempunyai token. `uv run goldintel check-apis` menguji jalur gratis yang siap; `--offline` hanya memeriksa readiness. [Hasil pengujian terbaru](free-only-verification.md).
