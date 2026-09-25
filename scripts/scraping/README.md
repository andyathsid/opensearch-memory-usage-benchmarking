# Scraper Metadata BRIN Dataverse

Scraper ini mengambil metadata dataset publik dari BRIN Dataverse.
Progres disimpan di SQLite agar proses yang terhenti dapat dilanjutkan, kemudian
record di-eksport untuk digunakan oleh notebook.

Jalankan semua command ini dari root repository.

## Setup

Siapkan environment uv:

```shell
uv sync
```

Akses internet diperlukan untuk menghubungi API publik BRIN Dataverse.

## Penggunaan

Ambil target default sebanyak 1.000 record dataset:

```shell
uv run python -m scripts.scraping.brin
```

Tentukan target yang berbeda:

```shell
uv run python -m scripts.scraping.brin --target 500
```

Ambil semua record yang tersedia melalui API:

```shell
uv run python -m scripts.scraping.brin --target all
```

Simpan hasil ke direktori lain:

```shell
uv run python -m scripts.scraping.brin --output-dir path/to/output
```

Lihat semua opsi yang tersedia:

```shell
uv run python -m scripts.scraping.brin --help
```

Direktori output default adalah `scripts/scraping/data/brin`. Menjalankan
perintah yang sama akan melanjutkan proses berdasarkan state SQLite di direktori
tersebut. Menekan Ctrl+C akan tetap mengekspor record yang sudah terkumpul.

## File output

- `brin_metadata.sqlite3`: record dan state untuk melanjutkan proses
- `datasets.ndjson`: satu record dataset JSON ringkas per baris
- `coverage.json`: ringkasan cakupan penulis, subjek, dan afiliasi
- `manifest.json`: metadata sumber, permintaan, progres, dan output

Gunakan `--output-dir` yang berbeda jika mengubah `--base-url` atau `--subtree`,
karena database SQLite yang sudah ada terikat dengan sumber awalnya.
