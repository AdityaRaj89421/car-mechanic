"""
gunicorn.conf.py — Production Gunicorn configuration.

Tune workers based on available CPUs:
  workers = (2 × CPU_cores) + 1
  For EC2 t2.micro (1 vCPU): 3 workers is ideal.
"""

import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 120          # Extended for Gemini API calls (can take 20-30s)
keepalive = 5
accesslog = "-"        # stdout
errorlog = "-"         # stderr
loglevel = "info"
