import logging
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "log"
LOG_DIR.mkdir(exist_ok=True)

_configured = False

def get_logger(name: str = "tuut") -> logging.Logger:
    global _configured
    if not _configured:
        parent = logging.getLogger("tuut")
        parent.setLevel(logging.DEBUG)
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        fh_app = logging.FileHandler(LOG_DIR / "app.log", mode="w", encoding="utf-8")
        fh_app.setLevel(logging.DEBUG)
        fh_app.setFormatter(fmt)
        parent.addHandler(fh_app)
        fh_err = logging.FileHandler(LOG_DIR / "errors.log", mode="w", encoding="utf-8")
        fh_err.setLevel(logging.ERROR)
        fh_err.setFormatter(fmt)
        parent.addHandler(fh_err)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        parent.addHandler(ch)
        _configured = True
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger