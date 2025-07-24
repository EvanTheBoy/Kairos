# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import logging

def setup_logging():
    """Sets up the basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

def enable_debug_logging():
    """Enables debug level logging for the 'src' logger."""
    logging.getLogger("src").setLevel(logging.DEBUG)
