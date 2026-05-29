import multiprocessing
import os

# Gunicorn configuration for production deployment
bind = "0.0.0.0:" + os.getenv("APP_PORT", "8000")

# Worker configuration
# Use 1 worker per core, with a minimum of 2
workers = max(2, multiprocessing.cpu_count())
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts
timeout = 120
keepalive = 65

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
