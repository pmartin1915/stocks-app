"""
Network utilities for Asymmetric application.

Provides port availability checking and automatic port selection
for the MCP HTTP server.
"""

import socket
import logging

logger = logging.getLogger(__name__)


def is_port_available(host: str, port: int) -> bool:
    """
    Check if a port is available for binding.

    Args:
        host: Host address to check (e.g., "0.0.0.0", "127.0.0.1")
        port: Port number to check

    Returns:
        True if port is available, False if in use
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Don't use SO_REUSEADDR for availability check - we want to know
            # if something else is actively using the port
            sock.settimeout(1)
            # Try to connect to the port - if connection succeeds, port is in use
            result = sock.connect_ex((host if host != "0.0.0.0" else "127.0.0.1", port))
            if result == 0:
                # Connection succeeded, port is in use
                return False
            # Connection failed, try to bind
            sock.close()

        # Now try to bind
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(
    host: str,
    start_port: int,
    max_attempts: int = 10,
) -> int | None:
    """
    Find an available port starting from start_port.

    Searches sequentially from start_port up to start_port + max_attempts.

    Args:
        host: Host address to check
        start_port: Port number to start searching from
        max_attempts: Maximum number of ports to try (default: 10)

    Returns:
        Available port number, or None if no port found in range
    """
    for offset in range(max_attempts):
        port = start_port + offset
        if is_port_available(host, port):
            logger.debug(f"Found available port: {port}")
            return port
        logger.debug(f"Port {port} is in use, trying next...")

    logger.warning(
        f"No available port found in range {start_port}-{start_port + max_attempts - 1}"
    )
    return None
