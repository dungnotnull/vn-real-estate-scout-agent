"""Main entry point for vn-real-estate-scout."""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def setup_logging():
    """Configure application logging."""
    from src.config import app, LOGS_DIR

    log_level = getattr(logging, app.log_level.upper(), logging.INFO)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # File handler
    log_file = LOGS_DIR / app.log_file_path
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting vn-real-estate-scout")

    try:
        from src.cli.main import main as cli_main
        cli_main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
