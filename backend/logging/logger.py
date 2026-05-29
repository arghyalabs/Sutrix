import os
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Any

# Optional Sentry SDK integration for enterprise crash tracking
try:
    import sentry_sdk
    HAS_SENTRY = True
except ImportError:
    HAS_SENTRY = False

def initialize_sentry(dsn: str = None, environment: str = "production"):
    """Initializes Sentry for global exception capture in production."""
    if not HAS_SENTRY:
        return
        
    dsn = dsn or os.getenv("SENTRY_DSN")
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
        print(f"Observability Alert: Sentry initialized successfully under environment '{environment}'.")

def setup_production_logging(name: str = "sdo", log_dir: str = "outputs/logs") -> logging.Logger:
    """
    Sets up enterprise-grade production logger with:
    - Size-based rotation (max 10MB per file, keeping 5 backups)
    - Consolidated console standard output stream
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Console stream handler (INFO and above)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 2. Size-based rotating file handler (DEBUG and above)
    file_path = log_path / "sdo_production.log"
    # Keep up to 5 rotation files, max 10MB each
    rotating_file = RotatingFileHandler(
        file_path, 
        maxBytes=10 * 1024 * 1024, 
        backupCount=5, 
        encoding="utf-8"
    )
    rotating_file.setLevel(logging.DEBUG)
    rotating_file.setFormatter(formatter)
    logger.addHandler(rotating_file)

    logger.info("SDO Production Logging successfully initialized with size-based RotatingFileHandler.")
    return logger

# Global default production logger
logger = setup_production_logging()

def profile_scientific_stage(stage_name: str):
    """
    Decorator to calculate and log timings for complex scientific calculations.
    Outputs telemetry timings to rotating log files for performance auditing.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            logger.info(f"PERFORMANCE: Starting scientific calculation stage '{stage_name}'...")
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                logger.info(f"PERFORMANCE: Stage '{stage_name}' completed successfully in {elapsed:.4f} seconds.")
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                logger.error(f"PERFORMANCE: Stage '{stage_name}' failed after {elapsed:.4f} seconds. Error: {e}")
                raise e
        return wrapper
    return decorator
