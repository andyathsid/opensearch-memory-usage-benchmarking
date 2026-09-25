def estimate_raw_embedding_bytes(
    num_vectors: int,
    dimensions: int,
    bytes_per_dimension: int = 4,
) -> int:
    """Estimate raw embedding storage, assuming float32 by default."""
    return num_vectors * dimensions * bytes_per_dimension


def estimate_hnsw_bytes(
    num_vectors: int,
    dimensions: int,
    m: int = 16,
) -> float:
    """Estimate the OpenSearch HNSW memory footprint for float32 vectors."""
    bytes_per_vector = 1.1 * (4 * dimensions + 8 * m)
    return num_vectors * bytes_per_vector


def estimate_hnsw_sq16_bytes(
    num_vectors: int,
    dimensions: int,
    m: int = 16,
) -> float:
    """Estimate the OpenSearch HNSW footprint with 16-bit scalar quantization."""
    bytes_per_vector = 1.1 * (2 * dimensions + 8 * m)
    return num_vectors * bytes_per_vector


def bytes_to_gib(size_bytes: float) -> float:
    """Convert bytes to gibibytes."""
    return size_bytes / (1024**3)
