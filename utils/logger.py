import logging

def setup_logger(name: str = "supportai", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s in %(module)s: %(message)s')
    handler.setFormatter(formatter)
    # Avoid duplicate handlers in environments that reload modules
    if not logger.handlers:
        logger.addHandler(handler)
    return logger

logger = setup_logger()
