import logging
import os
import pprint

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

logger = logging.getLogger('PR-Reminder')

# pretty printer
pp = pprint.PrettyPrinter(indent=2)
