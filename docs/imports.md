# Impor berizin

`goldintel import --platform instagram --file hasil.json` membaca envelope berikut. Ganti timestamp/source/bukti izin dengan ekspor yang sebenarnya. Contoh ini spesifikasi, bukan data kompetitor nyata; jangan mengimpor contoh sebagai observasi riil.

```json
{
  "source": {
    "provider": "nama_export_berizin",
    "permission_basis": "scope ekspor dan hak penggunaan yang telah diperiksa",
    "source_url": "https://www.instagram.com/AKUN/",
    "observed_at_utc": "2026-10-21T03:00:00Z",
    "metric_definition_version": "provider-definition-version",
    "locale": "id",
    "enumeration_status": "partial",
    "comment_selection_method": "jelaskan urutan, limit, window dan query"
  },
  "posts": [
    {
      "post_id": "ID_ASLI_PLATFORM",
      "canonical_url": "https://www.instagram.com/p/ID_ASLI_PLATFORM/",
      "published_at_utc": "2026-10-20T09:00:00+07:00",
      "account_id": "ID_AKUN_PLATFORM",
      "text": "teks sumber relevan yang diizinkan",
      "format": "reels",
      "content_type": "video",
      "ownership_type": "owned",
      "product_id": "mandiri-tabungan-emas",
      "commercial_disclosure": "unknown",
      "metrics": {"likes": "1,2 rb", "comments": 0, "video_views": null},
      "metric_status": {"video_views": "not_exposed"}
    }
  ],
  "comments": [],
  "product_facts": []
}
```

CSV kolom: `post_id,canonical_url,published_at_utc,text,title,account_id,format,content_type,ownership_type,product_id,likes,comments,video_views,...`. Field metrics di tingkat row diperbolehkan; CSV kosong = null, nol string = observed 0. Sidecar `hasil.meta.json` berisi objek `source` saja. Setiap platform memakai kontrak yang sama; provider tidak otomatis resmi karena nama yang diketik. Import provenance adalah pernyataan operator yang harus dapat diaudit.

JSON dapat memuat `product_facts`: product_id, fact_name, value (string), unit, channel, official_source_url, evidence_locator, evidence_hash, checked_at, valid_from; availability_status live/planned/unknown, verification_status, published_at/effective_at/valid_to opsional. Tidak menganggap roadmap live; waktu unknown tetap null. Perubahan value/status membentuk versi baru, cek ulang fakta sama memperbarui checked_at. PriceQuote memakai perspektif nasabah dan belum masuk importer terpadu.

Komentar memerlukan comment_id/post_id/text/source_url. Penulis tidak disimpan, comment_id di-hash; teks PII disaring. Tidak ada klaim seluruh komentar tercakup. Payload salah ditolak sebelum menulis baris. Snapshot ID deterministik pada platform/post/observed_at/provider; rerun file sama tidak menggandakan observasi. Snapshot timestamp baru menambah baris. Caption identik tidak menggabungkan post berbeda.

YouTube impor tetap raw-only/analytics blocked; jangan menggunakan impor untuk menghindari ketentuan sumber. `.json` dengan `source.demo=true` ditolak command production; gunakan `goldintel demo` untuk contoh sintetis yang terisolasi. Berkas asli impor tidak disalin ke data/raw; pipeline menyimpan metadata/hash/locator dan extract minimum, bukan token atau raw pribadi.
