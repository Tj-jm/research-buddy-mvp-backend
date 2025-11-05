import logging
from collections import deque

log_buffer = deque(maxlen=200)  # store last 200 lines

class FrontendLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        log_buffer.append(msg)

logger = logging.getLogger("scraper")
logger.setLevel(logging.INFO)
handler = FrontendLogHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
