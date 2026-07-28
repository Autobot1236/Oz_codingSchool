import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core import redis_client


class RedisClientTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        redis_client._redis_client = None

    def test_get_redis_client_reuses_single_instance(self) -> None:
        client = MagicMock()

        with patch(
            "app.core.redis_client.Redis.from_url",
            return_value=client,
        ) as from_url:
            first = redis_client.get_redis_client()
            second = redis_client.get_redis_client()

        self.assertIs(first, client)
        self.assertIs(second, client)
        from_url.assert_called_once_with(
            redis_client.settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

    async def test_close_redis_client_closes_and_resets_instance(self) -> None:
        client = MagicMock()
        client.aclose = AsyncMock()
        redis_client._redis_client = client

        await redis_client.close_redis_client()

        client.aclose.assert_awaited_once_with()
        self.assertIsNone(redis_client._redis_client)


if __name__ == "__main__":
    unittest.main()
