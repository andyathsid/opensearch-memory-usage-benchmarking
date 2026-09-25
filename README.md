# Benchmark Penggunaan Memori OpenSearch

WIP benchmarking project buat membandingkan ukuran mentah dokumen metadata
[BRIN Dataverse](https://data.brin.go.id/), estimasi embedding, dan ukuran
penyimpanan aktual dilaporkan oleh OpenSearch.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Docker with Docker Compose

## Setup

Siapkan environment Python berdasarkan lockfile:

```shell
uv sync
```

Jalankan OpenSearch dan OpenSearch Dashboards:

```shell
docker compose up -d
```

OpenSearch tersedia di <http://localhost:9200> dan OpenSearch Dashboards di
<http://localhost:5601>. Tunggu beberapa saat sampai OpenSearch selesai dimulai
sebelum menjalankan notebook.

Buka `notebooks/index-usage-calculation-experiment.ipynb`, lalu jalankan semua
cell secara berurutan.

Notebook akan membuat ulang index khusus `brin-datasets-size-demo` setiap kali
dijalankan. Dataset sampel yang diperlukan sudah tersedia di repository.

Setelah selesai, hentikan service lokal:

```shell
docker compose down
```

## Dataset

Project ini menggunakan 1.000 sampel metadata dataset yang diperoleh
melalui scraping dari BRIN Dataverse di [data.brin.go.id](https://data.brin.go.id/).

- [Scraping metadata BRIN Dataverse](scripts/scraping/README.md)
