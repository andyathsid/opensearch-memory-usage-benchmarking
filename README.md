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

## Mengukur Ukuran Index

Ada dua cara untuk mengetahui ukuran index, tergantung apakah dokumen sudah
di-index ke OpenSearch atau belum.

### Sebelum Dokumen Di-index

Sebelum dokumen di-index, estimasi ukuran data index dilakukan dalam dua langkah.
Pertama, hitung ukuran data vektor mentah atau embedding:

```text
embedding_size = total_vectors × dimensions × bytes_per_dimension
```

- `total_vectors`: jumlah dokumen, chunk, atau point yang berisi embedding.
- `dimensions`: jumlah dimensi dari model embedding.
- `bytes_per_dimension`: ukuran tipe data yang digunakan oleh OpenSearch atau
  Qdrant. Contohnya, `float32` menggunakan 4 byte per dimensi.

Kedua, tambahkan ukuran embedding tersebut dengan total ukuran metadata dokumen
dan data lain yang akan di-index ke OpenSearch:

```text
estimated_index_data_size = embedding_size + total_document_data_size
```

Hasil ini merupakan estimasi ukuran data sebelum proses indexing. Penggunaan RAM
dan disk yang sebenarnya juga mencakup struktur index dan overhead lainnya,
seperti HNSW index. Lihat
[panduan capacity planning Qdrant](https://qdrant.tech/documentation/capacity-planning/#calculating-ram-and-disk-size)
untuk perhitungan lebih lanjut.

### Setelah Dokumen Di-index

Ukuran aktual index dapat diperoleh dari OpenSearch Index Stats API:

```shell
curl http://localhost:9200/NAMA_INDEX/_stats/store
```

Nilai `indices.NAMA_INDEX.primaries.store.size_in_bytes` menunjukkan ukuran
primary shard. Gunakan `indices.NAMA_INDEX.total.store.size_in_bytes` jika ingin
menghitung seluruh shard, termasuk replica. Detail respons tersedia di
[dokumentasi OpenSearch Index Stats API](https://docs.opensearch.org/latest/api-reference/index-apis/stats/).

## Dataset

Project ini menggunakan 1.000 sampel metadata dataset yang diperoleh
melalui scraping dari BRIN Dataverse di [data.brin.go.id](https://data.brin.go.id/).

- [Scraping metadata BRIN Dataverse](scripts/scraping/README.md)
