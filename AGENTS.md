# Kebijakan proyek

- Pengguna menghendaki **gratis saja** (21 Oktober 2026). Pertahankan mode free-only: jangan menambahkan pembelian, langganan, paid provider, paid LLM, atau upgrade quota otomatis.
- `ALLOW_PAID_PROVIDERS=false` dan `MAX_COST_PER_RUN=0` dikunci. Harga unknown/positif dan provider berbayar harus ditolak sebelum request, termasuk retry. Jangan menyediakan jalan pintas yang melewati guard biaya.
- API X sudah dihapus atas permintaan pengguna. Jangan mengembalikannya ke CLI, credential, sumber aktif atau jalur network.
- App/Client Secret berbeda dari access token; ID aplikasi berbeda dari ID akun/Page/organisasi. Jangan mengarang token, permission atau akun.
- Jangan mencetak `.env`, credential, auth headers, payload privat atau secret dalam error/test/report. `.env.example` hanya placeholder dan default aman.
- Uji sumber gratis yang memang tersedia; laporkan missing OAuth/permission/adapter sebagai keterbatasan, bukan live success. Quota habis berarti berhenti; tidak ada fallback berbayar atau evasion.
- Pertahankan `src/mega_crawler`, SQLite lokal, timestamp UTC/presentasi Asia/Jakarta, nilai unavailable null, provenance, dan demo yang terpisah.
- Pemeriksaan: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`. `uv run goldintel check-apis` hanya probe gratis terbatas; `--offline` tidak memakai network.
