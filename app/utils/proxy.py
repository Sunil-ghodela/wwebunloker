import logging
import random

from app.config import get_settings


logger = logging.getLogger(__name__)


class ProxyRotator:
    """Randomized proxy picker for simple free-proxy rotation.

    Free proxies are unreliable by nature, so callers should treat a proxy as an
    optional best-effort hint and retry with a different one (or no proxy at all)
    when a request fails.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._proxies: list[str] = settings.proxies
        self._max_attempts: int = settings.max_proxy_attempts

    def selection(self) -> list[str | None]:
        """Return an ordered list of proxies to try for a single request.

        The list starts with up to ``max_proxy_attempts`` randomly chosen proxies
        and always ends with ``None`` so the caller can fall back to a direct
        connection if every proxy fails. When no proxies are configured the
        result is simply ``[None]`` (direct connection only).
        """

        if not self._proxies:
            return [None]
        pool = self._proxies[:]
        random.shuffle(pool)
        chosen: list[str | None] = pool[: self._max_attempts]
        chosen.append(None)
        return chosen


proxy_rotator = ProxyRotator()
