import os
import logging
from logging.handlers import RotatingFileHandler
# ensure the logs directory exists
os.makedirs("logs", exist_ok=True)

# Create a logger for the whole app
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

# Rotate after 5 MB, keep 3 backups
handler = RotatingFileHandler(
    "logs/wasp-hs-admin.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
)
handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
)
logger.addHandler(handler)
