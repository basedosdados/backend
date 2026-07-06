# -*- coding: utf-8 -*-
import json
import os
import urllib.error
import urllib.request
from typing import Iterator


class Prefect3Client:
    """Thin HTTP client for the Prefect 3 REST API.

    Reads PREFECT3_API_URL and PREFECT3_API_KEY from environment variables.
    """

    def __init__(self) -> None:
        self.api = os.getenv("PREFECT3_API_URL", "https://prefect3.basedosdados.org/api")
        self._headers = {
            "Authorization": f"Bearer {os.getenv('PREFECT3_API_KEY', '')}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, body: dict | None = None) -> dict | list:
        """Send an authenticated HTTP request to the Prefect 3 API.

        Args:
            method: HTTP method (GET, POST, PATCH, etc.).
            path: API path, e.g. ``/deployments/filter``.
            body: Optional request body serialized as JSON.

        Returns:
            Parsed JSON response as a dict or list.
        """
        payload = json.dumps(body or {}).encode()
        req = urllib.request.Request(
            f"{self.api}{path}",
            data=payload,
            headers=self._headers,
            method=method,
        )
        with urllib.request.urlopen(req) as r:
            return json.load(r)

    def iter_deployments(self, page_size: int = 200) -> Iterator[dict]:
        """Yield every deployment registered in Prefect 3, paginated.

        Args:
            page_size: Number of deployments to fetch per page. Defaults to 200.

        Yields:
            Deployment dicts containing at least ``id`` and ``name`` keys.
        """
        for offset in range(0, 10_000, page_size):
            page = self._request(
                "POST",
                "/deployments/filter",
                {"limit": page_size, "offset": offset},
            )
            yield from page
            if len(page) < page_size:
                break

    def get_recent_completed_runs(self, deployment_id: str, limit: int = 2) -> list[dict]:
        """Fetch the most recent completed runs for a deployment.

        Only terminal states are returned (Failed, Crashed, Completed, Cancelled)
        so pending or running flow runs are excluded from the consecutive-failure check.

        Args:
            deployment_id: Prefect 3 deployment UUID.
            limit: Maximum number of runs to return. Defaults to 2.

        Returns:
            List of flow run dicts ordered by start time descending, each
            containing at least ``state_name`` and ``start_time`` keys.
        """
        return self._request(
            "POST",
            "/flow_runs/filter",
            {
                "flow_runs": {
                    "deployment_id": {"any_": [deployment_id]},
                    "state": {"name": {"any_": ["Failed", "Crashed", "Completed", "Cancelled"]}},
                },
                "sort": "START_TIME_DESC",
                "limit": limit,
            },
        )

    def get_failed_task_runs(self, flow_run_id: str) -> list[dict]:
        """Fetch failed task runs for a specific flow run.

        Args:
            flow_run_id: Prefect 3 flow run UUID.

        Returns:
            List of failed task run dicts containing at least ``name``
            and ``state_message`` keys.
        """
        return self._request(
            "POST",
            "/task_runs/filter",
            {
                "task_runs": {
                    "flow_run_id": {"any_": [flow_run_id]},
                    "state": {"name": {"any_": ["Failed", "Crashed"]}},
                }
            },
        )

    def set_paused(self, deployment_id: str, *, paused: bool) -> None:
        """Pause or unpause a deployment.

        Args:
            deployment_id: Prefect 3 deployment UUID.
            paused: ``True`` to pause the deployment, ``False`` to activate it.
        """
        self._request("PATCH", f"/deployments/{deployment_id}", {"paused": paused})
