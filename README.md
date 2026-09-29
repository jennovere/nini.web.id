# NINI Copytrade — nini.web.id

Landing page publik **NINI Copy Trade Follower** (bot auto-trade Binance Futures) — di-host via GitHub Pages dengan domain `nini.web.id`.

## Halaman publik
| URL | Isi |
|---|---|
| `/` | Landing page utama (hero, statistik, download, pricing, panduan) |
| `/download/` | Halaman unduh aplikasi v1.0.2 + verifikasi SHA-256 |
| `/portofolio_2nd_account.html` | Audit portofolio live (diregenerasi tiap jam oleh pipeline) |
| `/MC_REPORT_GITHUB.html` | Laporan Monte Carlo publik |
| `/panduan-copy-trading.html` | Panduan/pillar article copy trading Indonesia |

## Aturan deploy (PENTING)
- **Jangan pernah `git add .`** — deploy hanya file whitelist `GIT_ADD_FILES` di `tradinglab/auto_pipeline.py`.
- **File privat dilarang masuk repo**: `*_audit*.csv`, `REPORT_CONSOLIDATED.html`, `MC_REPORT.html`, `REPORT_NIGHT.html`, `MC_REPORT_NIGHT.html`, dan semua laporan yang memuat jam+harga entry/exit. Aturan ini dijaga oleh `.gitignore`.
- Regenerasi artefak (portofolio, sitemap) dilakukan otomatis oleh `auto_pipeline.py` setiap ±1 jam.

## Local dev
Buka `index.html` langsung di browser, atau jalankan server statis apa pun di root repo ini.
