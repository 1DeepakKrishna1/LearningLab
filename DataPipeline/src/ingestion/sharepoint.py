"""SharePoint ingester using Microsoft Graph API (MSAL client credentials flow)."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from typing import Iterator, Optional

import requests

from src.ingestion.base import BaseIngester
from src.ingestion.deduplicator import Deduplicator
from src.models.schemas import DocumentSource, SourceType
from src.storage.file_store import FileStore
from src.utils.logger import get_logger
from src.utils.metrics import PipelineMetrics
from src.utils.retry import retry_with_backoff
from src.utils.security import SecureConfig

logger = get_logger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class SharePointIngester(BaseIngester):
    """Ingest PDFs from a SharePoint document library via Microsoft Graph API."""

    def __init__(
        self,
        config: SecureConfig,
        file_store: FileStore,
        deduplicator: Deduplicator,
        metrics: PipelineMetrics,
    ) -> None:
        super().__init__(file_store, deduplicator, metrics)
        self.config = config
        self._token: Optional[str] = None
        self._tmp_dir = tempfile.mkdtemp(prefix="sharepoint_")

    def _get_token(self) -> str:
        """Acquire an access token using client credentials (app-only)."""
        try:
            import msal
        except ImportError as e:
            raise ImportError("msal not installed. Run: pip install msal") from e

        if self._token:
            return self._token

        s = self.config.settings
        app = msal.ConfidentialClientApplication(
            s.sharepoint_client_id,
            authority=f"https://login.microsoftonline.com/{s.sharepoint_tenant_id}",
            client_credential=self.config.get_sharepoint_secret(),
        )
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in result:
            raise RuntimeError(f"Failed to acquire SharePoint token: {result.get('error_description')}")

        self._token = result["access_token"]
        return self._token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_token()}", "Accept": "application/json"}

    def discover(self, drive_id: Optional[str] = None, folder_path: str = "/", **kwargs) -> Iterator[DocumentSource]:
        """Enumerate all PDFs in a SharePoint drive folder."""
        drive_id = drive_id or self.config.settings.sharepoint_drive_id
        if not drive_id:
            logger.error("sharepoint_drive_id_not_configured")
            return

        url = f"{GRAPH_BASE}/drives/{drive_id}/root:{folder_path}:/children"
        while url:
            resp = requests.get(url, headers=self._headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("value", []):
                if not item.get("file") or not item["name"].lower().endswith(".pdf"):
                    continue
                modified = None
                if item.get("lastModifiedDateTime"):
                    modified = datetime.fromisoformat(
                        item["lastModifiedDateTime"].replace("Z", "+00:00")
                    )
                yield DocumentSource(
                    source_type=SourceType.SHAREPOINT,
                    source_path=item.get("webUrl", ""),
                    file_name=item["name"],
                    file_size_bytes=item.get("size", 0),
                    last_modified=modified,
                    remote_id=item["id"],
                    metadata={"drive_id": drive_id},
                )

            url = data.get("@odata.nextLink")

    @retry_with_backoff(max_attempts=3)
    def _fetch_local(self, source: DocumentSource) -> str:
        """Download a SharePoint file via its download URL."""
        drive_id = source.metadata.get("drive_id", self.config.settings.sharepoint_drive_id)
        url = f"{GRAPH_BASE}/drives/{drive_id}/items/{source.remote_id}/content"

        resp = requests.get(url, headers=self._headers(), stream=True, timeout=120)
        resp.raise_for_status()

        dest = os.path.join(self._tmp_dir, source.file_name)
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)

        logger.info("sharepoint_file_downloaded", file=source.file_name, dest=dest)
        return dest
