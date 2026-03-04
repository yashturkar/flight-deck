import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    fmt = "%(asctime)s %(levelname)-8s %(name)s  %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        stream=sys.stderr,
    )
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
