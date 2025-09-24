from typing import Dict, List, Optional
import logging
from services.api_clients.base.news_api_client import BaseNewsApiClient
from services.api_clients.safety_checker import ApiSafetyChecker
from services.api_clients.usage_tracking import ApiUsageTracker
from config.api_configs import ApiClientConfig

class ApiClientRegistry:
    """
    Registry that manages API clients with safety checking and auto-deregistration.

    Features:
    - Automatic safety checking before requests
    - Deregistration of unsafe APIs
    - Warning system for approaching limits
    - Usage statistics and monitoring
    """

    def __init__(self):
        self._clients: Dict[str, BaseNewsApiClient] = {}
        self._safety_checkers: Dict[str, ApiSafetyChecker] = {}
        self._deregistered_clients: Dict[str, str] = {}  # provider_id -> reason
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_client(self, client: BaseNewsApiClient, config: ApiClientConfig, usage_tracker: ApiUsageTracker):
        """Register a client with safety checking."""
        provider_id = client.provider_id

        # Create safety checker
        safety_checker = ApiSafetyChecker(usage_tracker, config)

        # Check if client is safe to register
        is_safe, reason = safety_checker.is_api_safe_to_use()
        if not is_safe:
            self.logger.warning(f"Not registering {provider_id}: {reason}")
            self._deregistered_clients[provider_id] = reason
            return False

        # Register client and safety checker
        self._clients[provider_id] = client
        self._safety_checkers[provider_id] = safety_checker

        self.logger.info(f"Registered API client: {provider_id}")

        # Log any warnings
        warnings = safety_checker.get_warnings()
        for warning in warnings:
            self.logger.warning(f"{provider_id}: {warning}")

        return True

    def get_active_clients(self) -> List[BaseNewsApiClient]:
        """Get all currently active (safe) clients."""
        # Check safety before returning
        self._check_all_clients_safety()
        return list(self._clients.values())

    def get_client(self, provider_id: str) -> Optional[BaseNewsApiClient]:
        """Get a specific client if it's active and safe."""
        if provider_id not in self._clients:
            return None

        # Check safety first
        is_safe = self._check_client_safety(provider_id)
        if not is_safe:
            return None

        return self._clients[provider_id]

    def _check_all_clients_safety(self):
        """Check safety of all registered clients and deregister unsafe ones."""
        clients_to_remove = []

        for provider_id in list(self._clients.keys()):
            if not self._check_client_safety(provider_id):
                clients_to_remove.append(provider_id)

        # Log summary if any clients were removed
        if clients_to_remove:
            self.logger.info(f"Deregistered {len(clients_to_remove)} unsafe clients: {clients_to_remove}")

    def _check_client_safety(self, provider_id: str) -> bool:
        """Check safety of a specific client."""
        if provider_id not in self._safety_checkers:
            return False

        safety_checker = self._safety_checkers[provider_id]
        is_safe, reason = safety_checker.is_api_safe_to_use()

        if not is_safe:
            # Deregister the client
            self._deregister_client(provider_id, reason)
            return False

        return True

    def _deregister_client(self, provider_id: str, reason: str):
        """Remove a client from active registry."""
        if provider_id in self._clients:
            del self._clients[provider_id]
            self.logger.warning(f"Deregistered client {provider_id}: {reason}")

        if provider_id in self._safety_checkers:
            del self._safety_checkers[provider_id]

        self._deregistered_clients[provider_id] = reason

    def get_registry_status(self) -> Dict[str, Any]:
        """Get complete status of the registry."""
        active_clients = []
        for provider_id, checker in self._safety_checkers.items():
            if provider_id in self._clients:
                status = checker.get_safety_status()
                active_clients.append(status)

        return {
            "active_clients": active_clients,
            "deregistered_clients": dict(self._deregistered_clients),
            "total_active": len(self._clients),
            "total_deregistered": len(self._deregistered_clients)
        }

    def get_all_warnings(self) -> Dict[str, List[str]]:
        """Get warnings for all active clients."""
        warnings = {}

        for provider_id, checker in self._safety_checkers.items():
            if provider_id in self._clients:
                client_warnings = checker.get_warnings()
                if client_warnings:
                    warnings[provider_id] = client_warnings

        return warnings

    def force_check_all_clients(self) -> Dict[str, Any]:
        """Manually trigger safety check on all clients and return results."""
        self._check_all_clients_safety()
        return self.get_registry_status()