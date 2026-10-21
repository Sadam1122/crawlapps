# Verifikasi akun dan ekosistem

`verify-registry` memvalidasi struktur dan menampilkan gap, **tidak mengklaim verifikasi live**. `discover` membaca seed per segmen; tidak melakukan pencarian akun dengan nama serupa. Gunakan sumber domain resmi atau bukti primer lain. Centang biru saja tidak cukup.

Tambahkan pada produk yang relevan di `competitors.yaml`:

```yaml
verified_social_accounts:
  - platform: youtube
    platform_id: CHANNEL_ID_DARI_BUKTI_PRIMER
    url: https://www.youtube.com/channel/CHANNEL_ID_DARI_BUKTI_PRIMER
    evidence_url: https://DOMAIN_RESMI/HALAMAN_YANG_MENAUTKAN_CHANNEL
    verification_reason: Tautan channel dari halaman domain resmi, diperiksa reviewer
    checked_at: 'TIMESTAMP_DENGAN_ZONA'
    confidence: 0.95
    reviewer_status: approved
```

Jangan isi placeholder sebagai akun sungguhan. Registrasi awal sengaja tidak menebak channel ID atau memasukkan akun dari search/centang biru. Tautan layanan MandiriCare terlihat pada halaman Mandiri, tetapi bukan otomatis akun marketing produk dan numeric platform ID-nya belum diverifikasi. Collector YouTube hanya memilih `approved`.

Setiap relationship mempunyai from/to entity, jenis relasi, sumber, checked_at, valid_from/to nullable, status verifikasi. ANTAM/Hartadinata dapat sekaligus kompetitor/pemasok; sumber rilis Mandiri adalah self_reported untuk hubungan tersebut. GoPay → Treasury adalah kanal/provider berdasarkan terms primer. Galeri24 → Pegadaian masih candidate yang memerlukan bukti badan hukum/ownership. DANA eMAS harus ditelusuri per varian Treasury/Pluang; provider tidak ditebak. Tokopedia/BukaEmas/marketplace fisik dipisah dan status pending, bukan otomatis aktif.

Quantum Metal tetap pending operation/license dan tidak eligible ranking. BSI legal name diperiksa pada laporan primer; jangan menyamakan nama brand dengan badan hukum lama. Galeri24/Lotus/King Halim masih memiliki gap legal-name; daftar ini bukan daftar izin lengkap regulator. Verifikasi operasi dan izin harus diperbarui terpisah dari keberhasilan membuka halaman pemasaran.
