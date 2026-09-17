"""Background download-and-import job for JMdict."""

from __future__ import annotations

import threading
from collections.abc import Callable

from sqlalchemy.orm import Session

from kotoba.core.config import Paths
from kotoba.services.capture.gate import gate
from kotoba.services.dictionary.jmdict.download import download, latest_asset
from kotoba.services.dictionary.jmdict.importer import import_json


class InstallJob:
    """Background JMdict install with observable state."""

    def __init__(self) -> None:
        self.state = "idle"
        self.message = ""
        self.done = 0
        self.total = 0
        self._thread: threading.Thread | None = None

    def snapshot(self) -> dict:
        return {
            "state": self.state,
            "message": self.message,
            "done": self.done,
            "total": self.total,
        }

    def start(
        self, session_factory: Callable[[], Session], paths: Paths, url: str | None = None
    ) -> bool:
        if self._thread and self._thread.is_alive():
            return False
        gate.begin_long_write("jmdict-install")

        def run() -> None:
            db = session_factory()
            try:
                self.state, self.message = "downloading", "正在下载 JMdict…"
                asset_url = url or latest_asset()[0]
                json_path = download(asset_url, paths.dicts_dir)

                def prog(done: int, total: int) -> None:
                    self.done, self.total = done, total

                self.state, self.message = "importing", "正在导入词典…"
                import_json(db, json_path, progress=prog)
                self.state, self.message = "done", "词典已安装"
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                self.state, self.message = "error", str(exc)
            finally:
                db.close()
                gate.end_long_write("jmdict-install")

        # If the thread never starts, the claim must not outlive this call: a leaked
        # claim blocks every future restore until the application is restarted.
        try:
            self._thread = threading.Thread(target=run, name="jmdict-install", daemon=True)
            self._thread.start()
        except BaseException:
            gate.end_long_write("jmdict-install")
            raise
        return True


install_job = InstallJob()
