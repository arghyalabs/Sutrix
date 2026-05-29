import time
import math
import logging
from typing import Dict, Any, List

logger = logging.getLogger("sdo.backend.workers.tracker")

class ProgressTracker:
    """
    Computes real-time execution telemetry during descriptor enrichment pipelines.
    Enforces calculation throttles (max 5 frames/sec) to avoid React rendering storms.
    """
    def __init__(self, job_id: str, total_compounds: int, throttle_seconds: float = 0.2):
        self.job_id = job_id
        self.total = total_compounds
        self.start_time = time.time()
        self.last_update_time = 0.0
        self.throttle_seconds = throttle_seconds
        
        # Trailing averages for smooth ETA estimations
        self.history_limit = 10
        self.speed_history: List[float] = []
        self.current_phase = "🔍 Phase 1: Identity Resolution"
        self.log_buffer: List[str] = []

    def log(self, message: str):
        """Adds a log statement formatted for high-performance WebSocket terminal feeds."""
        elapsed = time.time() - self.start_time
        timestamp = f"[{int(elapsed // 60):02d}:{int(elapsed % 60):02d}]"
        self.log_buffer.append(f"{timestamp} {message}")
        if len(self.log_buffer) > 200:
            self.log_buffer.pop(0) # Keep buffer tight

    def calculate_telemetry(self, current: int) -> Dict[str, Any]:
        """
        Calculates compounds/sec velocity, average smooth speed, and precise ETA.
        """
        now = time.time()
        elapsed = now - self.start_time
        remaining = self.total - current
        
        if current <= 0 or elapsed <= 0.01:
            return {
                "progress_pct": 0, "eta_seconds": 0.0,
                "compounds_per_sec": 0.0, "elapsed_seconds": round(elapsed, 1),
                "phase": self.current_phase, "logs": self.log_buffer[-8:]
            }

        # Raw velocity
        raw_speed = current / elapsed
        
        # Smooth trailing velocity average
        self.speed_history.append(raw_speed)
        if len(self.speed_history) > self.history_limit:
            self.speed_history.pop(0)
        avg_speed = sum(self.speed_history) / len(self.speed_history)

        # ETA based on smooth trailing speed
        eta = remaining / avg_speed if avg_speed > 0 else 0.0
        progress_pct = int((current / self.total) * 100)

        # Deduce phase dynamically based on percentage
        if progress_pct < 10:
            self.current_phase = "🔍 Phase 1: Identity Resolution"
        elif progress_pct < 85:
            self.current_phase = "⚗️ Phase 2: Descriptor Computation"
        else:
            self.current_phase = "📦 Phase 3: Columnar Compression"

        return {
            "progress_pct": min(100, progress_pct),
            "eta_seconds": round(eta, 1),
            "compounds_per_sec": round(avg_speed, 1),
            "elapsed_seconds": round(elapsed, 1),
            "phase": self.current_phase,
            "logs": self.log_buffer[-8:] # Send only the latest 8 logs to shrink payload weights
        }

    def should_broadcast(self, force: bool = False) -> bool:
        """Throttling mechanism to restrict update streams to a max of 5Hz (0.2s interval)."""
        now = time.time()
        if force or (now - self.last_update_time) >= self.throttle_seconds:
            self.last_update_time = now
            return True
        return False
