"""Register and deploy the multilingual MiniLM model in OpenSearch ML Commons."""

from __future__ import annotations

import time
from typing import Any

from opensearchpy import OpenSearch


OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200

# OpenSearch prefixes registry models with their provider. This is the same
# sentence-transformers model used by FastEmbed in the notebook.
MODEL_NAME = (
    "huggingface/sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)
MODEL_VERSION = "1.0.2"
MODEL_FORMAT = "TORCH_SCRIPT"

TASK_TIMEOUT_SECONDS = 30 * 60
TASK_POLL_INTERVAL_SECONDS = 5


def create_client() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        use_ssl=False,
        verify_certs=False,
    )


def configure_local_ml_commons(client: OpenSearch) -> None:
    """Allow ML Commons inference on this single non-ML development node."""
    client.transport.perform_request(
        "PUT",
        "/_cluster/settings",
        body={
            "persistent": {
                "plugins.ml_commons.only_run_on_ml_node": "false",
                "plugins.ml_commons.native_memory_threshold": "99",
            }
        },
    )


def wait_for_task(
    client: OpenSearch,
    task_id: str,
    *,
    timeout_seconds: int = TASK_TIMEOUT_SECONDS,
    poll_interval_seconds: int = TASK_POLL_INTERVAL_SECONDS,
) -> dict[str, Any]:
    started_at = time.monotonic()
    deadline = started_at + timeout_seconds
    previous_state: str | None = None

    while time.monotonic() < deadline:
        task = client.transport.perform_request(
            "GET",
            f"/_plugins/_ml/tasks/{task_id}",
        )
        state = task.get("state", "UNKNOWN")

        if state != previous_state:
            print(f"Task {task_id}: {state}", flush=True)
            previous_state = state
        else:
            elapsed_seconds = int(time.monotonic() - started_at)
            print(
                f"Task {task_id}: still {state}, waiting... "
                f"({elapsed_seconds}s elapsed)",
                flush=True,
            )

        if state == "COMPLETED":
            return task
        if state in {"FAILED", "CANCELLED"}:
            error = task.get("error", "No error details returned")
            raise RuntimeError(f"ML Commons task {task_id} {state}: {error}")

        time.sleep(poll_interval_seconds)

    raise TimeoutError(
        f"ML Commons task {task_id} did not finish within "
        f"{timeout_seconds} seconds"
    )


def register_and_deploy_model(client: OpenSearch) -> str:
    response = client.transport.perform_request(
        "POST",
        "/_plugins/_ml/models/_register",
        params={"deploy": "true"},
        body={
            "name": MODEL_NAME,
            "version": MODEL_VERSION,
            "model_format": MODEL_FORMAT,
        },
    )

    task_id = response.get("task_id")
    if not task_id:
        raise RuntimeError(f"Model registration returned no task_id: {response}")

    task = wait_for_task(client, task_id)
    model_id = task.get("model_id")
    if not model_id:
        raise RuntimeError(f"Completed registration returned no model_id: {task}")
    return model_id


def main() -> None:
    client = create_client()
    cluster_info = client.info()
    print(f"Connected to OpenSearch {cluster_info['version']['number']}.")

    configure_local_ml_commons(client)
    print(f"Registering and deploying {MODEL_NAME!r} ...")
    model_id = register_and_deploy_model(client)
    print(f"Model ID: {model_id}")
    print("Copy this value into notebooks/vector-calculation.py:")
    print(f'OPENSEARCH_MODEL_ID = "{model_id}"')


if __name__ == "__main__":
    main()
