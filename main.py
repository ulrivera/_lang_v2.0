# main.py
import logging
import sys
from config.settings import LOG_LEVEL, LOGS_DIR
from data.db import Database
from interface.cli import CLI

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "lang2.log"),
        logging.StreamHandler(sys.stdout)
    ]
)


def main():
    db = Database()
    db.connect()
    try:
        CLI(db=db).run()
    except KeyboardInterrupt:
        print("\nInterrumpido.")
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()