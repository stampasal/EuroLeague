# ============================================================
# core/config.py
# ------------------------------------------------------------
# Constants + settings του project.
# Κανένα magic number πουθενά αλλού.
# ============================================================

from __future__ import annotations


# ============================================================
# SEASON / LEAGUE
# ============================================================
EUROLEAGUE_SEASON = "2026"
EUROLEAGUE_TEAMS  = 20


# ============================================================
# FANTASY RULES
# ============================================================
BUDGET_START        = 100.0
TOTAL_G             = 3     # Guards
TOTAL_F             = 4     # Forwards
TOTAL_C             = 3     # Centers
TOTAL_PLAYERS       = TOTAL_G + TOTAL_F + TOTAL_C   # 10

DEFAULT_MAX_TRANSFERS = 3
TRANSFER_COST         = 0.0    # κόστος ανά transfer (0 = δωρεάν)


# ============================================================
# OPTIMIZER
# ============================================================
OPTIMIZER_SCENARIOS = ["A", "B"]
OPTIMIZER_TOP_N     = 3
OPTIMIZER_TIME_LIMIT_SEC = 30


# ============================================================
# MODELS
# ============================================================
MODEL_VERSION       = "4.2"
MODEL_FEATURES      = 17
MODEL_ENSEMBLE      = ["ridge", "gb", "ma"]


# ============================================================
# SERVERS
# ============================================================
SERVER_HOST         = "127.0.0.1"
SERVER_PORT_APP     = 5000
SERVER_PORT_CONTROL = 5001
SERVER_DEBUG        = False


# ============================================================
# LOGGING
# ============================================================
LOG_LEVEL           = "INFO"
LOG_FORMAT          = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT     = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES       = 5 * 1024 * 1024   # 5 MB
LOG_BACKUP_COUNT    = 3


# ============================================================
# HTTP (scraping)
# ============================================================
HTTP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)
HTTP_TIMEOUT_SEC = 30
HTTP_RETRIES     = 3
