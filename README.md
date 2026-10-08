# NINI Copytrade — nini.web.id

Landing page publik **NINI Copy Trade Follower** (bot auto-trade Binance Futures) — di-host via GitHub Pages dengan domain `nini.web.id`.

## Halaman publik
| URL | Isi |
|---|---|
| `/` | Landing page utama (hero, statistik, download, pricing, panduan, FAQ keamanan) |
| `/security.html` | Keamanan & Arsitektur: pernyataan anti-titip dana, API Read & Trade tanpa penarikan, pembedaan dari skema ponzi |
| `/download/` | Halaman unduh aplikasi v1.0.3 + verifikasi SHA-256 |
| `/portofolio_2nd_account.html` | Audit portofolio live (diregenerasi tiap jam oleh pipeline) |
| `/MC_REPORT_GITHUB.html` | Laporan Monte Carlo publik |
| `/panduan-copy-trading.html` | Panduan/pillar article copy trading Indonesia |
| `/llms.txt` | Ringkasan situs dalam format markdown untuk mesin pencari & asisten AI |

## Rilis aplikasi: NINI Follower v1.0.3
- **Paket**: `download/NINI_Follower_v1.0.3_Package.zip` (64.730.171 byte)
- **SHA-256**: `770047cad300bddff376256e01c5fc70c925c4f0a47e8b7652bb81300103acd6`
- **Isi paket**: folder `NINI Follower v1.0.3/` berisi aplikasi, plus `CHANGELOG.md`, `MULAI_DI_SINI.txt`, `README_INSTALASI.txt`, dan `docs/RISK_ACCEPTANCE.md`
- **Perubahan utama v1.0.3**: tiered limits & single instance lock
- **Instalasi**: unduh paket → cocokkan SHA-256 (PowerShell: `Get-FileHash -Algorithm SHA256 <file>`) → ekstrak → jalankan aplikasi → hubungkan API Key Binance Futures → gunakan mode trial gratis sebelum berlangganan

## Cara kerja (client-side application)
- Aplikasi desktop berjalan di komputer pengguna; tidak ada server pusat yang menerima atau menyimpan dana pengguna.
- Koneksi ke Binance Futures dibuat memakai **API Key milik pengguna sendiri** dengan izin **Read & Trade** — **tanpa izin Withdrawal (penarikan)**.
- Posisi master disalin ke akun pengguna secara **real-time**, lengkap dengan penerapan **Stop Loss & Take Profit**.
- Karena sifatnya non-custodial, modal tidak pernah meninggalkan akun Binance Futures pengguna masing-masing.

## Keamanan API (ringkas)
| Aspek | Ketentuan |
|---|---|
| Izin API | Read & Trade saja |
| Izin penarikan (Withdraw) | Tidak pernah diberikan |
| Penitipan dana | Tidak ada — NINI tidak pernah menampung dana pengguna |
| Bagi hasil piramida | Tidak ada; pendapatan hanya langganan bulanan datar |
| Lock-up period | Tidak ada; pengguna bisa berhenti kapan saja |
| Kendali dana | 100% di tangan pengguna atas akun Binance-nya sendiri |

Pernyataan lengkap (ID/EN): [`/security.html`](https://nini.web.id/security.html) — FAQ: [`/#faq`](https://nini.web.id/#faq).

## Aksesibilitas mesin pencari & AI (GEO)
- `robots.txt` mengizinkan secara eksplisit GPTBot, Google-Extended, ClaudeBot, PerplexityBot, dan bot AI lainnya.
- `sitemap.xml` mencakup seluruh halaman publik termasuk `/security.html` (diregenerasi otomatis oleh `tools/generate_sitemap.py`).
- `llms.txt` di root menyediakan ringkasan situs + tautan ke halaman keamanan dan FAQ.
- Schema markup `FAQPage` (JSON-LD, ID + EN) disematkan di halaman utama.

## Aturan deploy (PENTING)
- **Jangan pernah `git add .`** — deploy hanya file whitelist `GIT_ADD_FILES` di `tradinglab/auto_pipeline.py`.
- **File privat dilarang masuk repo**: `*_audit*.csv`, `REPORT_CONSOLIDATED.html`, `MC_REPORT.html`, `REPORT_NIGHT.html`, `MC_REPORT_NIGHT.html`, dan semua laporan yang memuat jam+harga entry/exit. Aturan ini dijaga oleh `.gitignore`.
- Regenerasi artefak (portofolio, sitemap) dilakukan otomatis oleh `auto_pipeline.py` setiap ±1 jam.

## Local dev
Buka `index.html` langsung di browser, atau jalankan server statis apa pun di root repo ini.
