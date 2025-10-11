#!/usr/bin/env python3
import logging
import logging.config

from src.config import LOGGING_CONFIG
from src.cli.app import main as cli_main


def main():
    logging.config.dictConfig(LOGGING_CONFIG)
    cli_main()


if __name__ == "__main__":
    main()
