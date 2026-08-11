import time
import threading
import os
import asyncio

CACHE_TTL_SECONDS = int(os.getenv("RUN_STATUS_CACHE_TTL", "3600"))

class RunStatusCacheManager:
    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS):
        self._cache = {}
        self._lock = threading.Lock()
        self.ttl_seconds = ttl_seconds
        self._logger = None

    def _get_logger(self):
        if self._logger is None:
            try:
                from src.utils.logger import get_agent_logger
                self._logger = get_agent_logger("API")
            except Exception:
                import logging
                self._logger = logging.getLogger("API")
        return self._logger

    def create_run(self, run_id: str, company: str, domain: str):
        with self._lock:
            self._cache[run_id] = {
                "run_id": run_id,
                "company": company,
                "domain": domain,
                "status": "running",
                "step": 1,
                "node": "initial",
                "error": None,
                "result": None,
                "created_at": time.time(),
                "updated_at": time.time()
            }
        self._get_logger().info(f"[RunStatusCache] Run created: run_id={run_id}, company={company}, domain={domain}")

    def update_run(self, run_id: str, **kwargs):
        with self._lock:
            if run_id in self._cache:
                if self._cache[run_id].get("status") in ("completed", "failed"):
                    return
                self._cache[run_id].update(kwargs)
                self._cache[run_id]["updated_at"] = time.time()
                step = kwargs.get("step", self._cache[run_id].get("step"))
                node = kwargs.get("node", self._cache[run_id].get("node"))
        self._get_logger().info(f"[RunStatusCache] Run updated: step={step} node={node}")

    def complete_run(self, run_id: str, step: int, result: dict):
        with self._lock:
            if run_id in self._cache:
                if self._cache[run_id].get("status") == "completed":
                    return
                self._cache[run_id].update({
                    "status": "completed",
                    "step": step,
                    "result": result,
                    "updated_at": time.time()
                })
        self._get_logger().info(f"[RunStatusCache] Run completed: step={step}")

    def fail_run(self, run_id: str, error_msg: str):
        with self._lock:
            if run_id in self._cache:
                self._cache[run_id].update({
                    "status": "failed",
                    "error": error_msg,
                    "updated_at": time.time()
                })
        self._get_logger().warning(f"[RunStatusCache] Run failed: run_id={run_id}, error={error_msg}")

    def get_run(self, run_id: str):
        with self._lock:
            return self._cache.get(run_id)

    def cleanup_expired(self):
        now = time.time()
        expired_ids = []
        with self._lock:
            for rid, data in list(self._cache.items()):
                status = data.get("status")
                if status in ("completed", "failed") and (now - data.get("updated_at", now) > self.ttl_seconds):
                    expired_ids.append((rid, status))
                elif status == "running" and (now - data.get("updated_at", now) > (self.ttl_seconds * 2)):
                    expired_ids.append((rid, status))
            for rid, _ in expired_ids:
                del self._cache[rid]

        for rid, status in expired_ids:
            self._get_logger().info(f"[RunStatusCache] Run expired/removed: run_id={rid}, previous_status={status}")
        return len(expired_ids)

run_status_cache = RunStatusCacheManager()
