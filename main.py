import asyncio
import os
import logging
from typing import Optional, Dict
from services.article_service import ArticleService
from repository.article_repository import ArticleRepository
from services.base.time_service import get_time_service, close_time_service
from dotenv import load_dotenv

load_dotenv()
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


def load_config() -> Dict[str, str]:
    """Load configuration from environment variables"""
    config = {
        'db_host': os.environ.get('DB_HOST', 'localhost'),
        'db_port': os.environ.get('DB_PORT', '5432'),
        'db_name': os.environ.get('DB_NAME', 'api_sorcerer'),
        'db_user': os.environ.get('DB_USER', 'user'),
        'db_password': os.environ.get('DB_PASSWORD', 'password'),
        'config_path': os.environ.get('CONFIG_PATH', 'configs/config.yaml')
    }

    logger.info("Configuration loaded:")
    logger.info(f"  Database: {config['db_user']}@{config['db_host']}:{config['db_port']}/{config['db_name']}")
    logger.info(f"  Config path: {config['config_path']}")

    return config


def build_connection_string(config: Dict[str, str]) -> str:
    """Build PostgreSQL connection string from config"""
    return (f"postgresql://{config['db_user']}:{config['db_password']}"
            f"@{config['db_host']}:{config['db_port']}/{config['db_name']}")


async def initialize_repository(connection_string: str) -> Optional[ArticleRepository]:
    """Initialize and return repository, or None on failure"""
    repo = ArticleRepository(connection_string)

    try:
        await repo.initialize()
        logger.info("Repository initialized successfully")
        return repo
    except Exception as e:
        logger.error(f"Failed to initialize repository: {e}", exc_info=True)
        return None


async def initialize_time_service() -> bool:
    """Initialize time service and return success status"""
    try:
        time_service = await get_time_service()
        sync_status = time_service.get_sync_status()
        logger.info(f"Time service initialized: synced={sync_status['is_synced']}, "
                   f"offset={sync_status.get('offset_seconds', 0):.2f}s")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize time service: {e}", exc_info=True)
        return False


async def initialize_article_service(config_path: str, repo: ArticleRepository) -> Optional[ArticleService]:
    """Initialize and return article service, or None on failure"""
    try:
        service = ArticleService(config_path, repo)
        logger.info("Article service initialized successfully")
        return service
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize article service: {e}", exc_info=True)
        return None


async def fetch_and_store_articles(service: ArticleService, query: str) -> int:
    """Fetch articles and return count of new articles stored"""
    logger.info(f"Starting article fetch for query: '{query}'")

    try:
        new_count = await service.fetch_articles(query)
        logger.info(f"Successfully stored {new_count} new articles")
        return new_count
    except Exception as e:
        logger.error(f"Error fetching articles: {e}", exc_info=True)
        return 0


async def log_repository_stats(repo: ArticleRepository) -> None:
    """Retrieve and log repository statistics"""
    try:
        stats = await repo.get_stats()
        logger.info("Repository Statistics:")
        logger.info(f"  Total articles: {stats['total_articles']}")
        logger.info(f"  Unique URLs: {stats['unique_urls']}")
        logger.info(f"  Number of providers: {stats['providers']}")

        if stats.get('earliest_article'):
            logger.info(f"  Earliest article: {stats['earliest_article']}")
        if stats.get('latest_article'):
            logger.info(f"  Latest article: {stats['latest_article']}")

        logger.info("  Articles by provider:")
        for provider, count in stats['articles_by_provider'].items():
            logger.info(f"    {provider}: {count}")
    except Exception as e:
        logger.error(f"Error retrieving repository stats: {e}")


async def log_usage_stats(service: ArticleService) -> None:
    """Retrieve and log API usage statistics"""
    try:
        usage_stats = await service.get_usage_stats()
        logger.info("API Usage Statistics:")

        for provider, usage in usage_stats.items():
            daily_used = usage.get('daily_count', 0)
            daily_remaining = usage.get('daily_remaining', 'unlimited')
            monthly_used = usage.get('monthly_count', 0)
            monthly_remaining = usage.get('monthly_remaining', 'unlimited')
            total_used = usage.get('total_count', 0)

            logger.info(f"  {provider}:")
            logger.info(f"    Daily: {daily_used} used / {daily_remaining} remaining")
            logger.info(f"    Monthly: {monthly_used} used / {monthly_remaining} remaining")
            logger.info(f"    Total: {total_used}")
    except Exception as e:
        logger.error(f"Error retrieving usage stats: {e}")


async def cleanup_resources(service: Optional[ArticleService],
                           repo: Optional[ArticleRepository]) -> None:
    """Clean up all resources"""
    logger.info("Starting cleanup")

    if service:
        try:
            await service.cleanup()
            logger.info("Service cleanup completed")
        except Exception as e:
            logger.error(f"Error during service cleanup: {e}")

    if repo:
        try:
            await repo.close()
            logger.info("Repository closed")
        except Exception as e:
            logger.error(f"Error closing repository: {e}")

    try:
        await close_time_service()
        logger.info("Time service closed")
    except Exception as e:
        logger.error(f"Error closing time service: {e}")


async def main():
    """Main entry point for news article fetching"""
    logger.info("Starting news aggregator")

    # Load configuration
    config = load_config()
    connection_string = build_connection_string(config)

    # Initialize repository
    repo = await initialize_repository(connection_string)
    if not repo:
        logger.error("Cannot proceed without repository")
        return

    # Initialize time service
    if not await initialize_time_service():
        logger.error("Cannot proceed without time service")
        await repo.close()
        return

    service = None

    try:
        # Initialize article service
        service = await initialize_article_service(config['config_path'], repo)
        if not service:
            logger.error("Cannot proceed without article service")
            return

        # Fetch articles
        new_count = await fetch_and_store_articles(service, "technology")

        # Log statistics
        await log_repository_stats(repo)
        await log_usage_stats(service)

    except Exception as e:
        logger.error(f"Unexpected error in main: {e}", exc_info=True)
    finally:
        # Always cleanup resources
        await cleanup_resources(service, repo)

    logger.info("News aggregator finished")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        exit(1)