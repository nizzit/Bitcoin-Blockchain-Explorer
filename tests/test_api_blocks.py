"""
Тесты для API endpoints модуля blocks
"""

import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.block import Block


def get_mock_db():
    """Mock функция для получения БД"""
    return MagicMock()


class TestBlocksAPI(unittest.TestCase):
    """Тесты для API endpoints работы с блоками"""

    def setUp(self):
        """Подготовка к тестам"""
        # Переопределяем зависимость get_db
        app.dependency_overrides[get_db] = get_mock_db
        self.client = TestClient(app)
        self.mock_block = Block(
            id=1,
            hash="00000000000000000001234567890abcdef",
            height=800000,
            version=536870912,
            merkleroot="abc123",
            time=1672574400,  # Unix timestamp вместо datetime
            nonce=12345,
            bits="17034219",
            difficulty=35364065900457.91,
            chainwork="00000000000000000000000000000000000000001234567890abcdef",
            n_tx=2500,
            size=1500000,
            weight=4000000,
            previous_block_hash="00000000000000000000987654321fedcba",
            next_block_hash="00000000000000000002345678901bcdefg",
            created_at=datetime.now(),
        )

    def tearDown(self):
        """Очистка после тестов"""
        # Удаляем переопределение зависимостей
        app.dependency_overrides.clear()

    @patch("app.api.blocks.BlockService")
    def test_get_latest_block_success(self, mock_service_class):
        """Тест успешного получения последнего блока"""
        # Настройка mock
        mock_service = MagicMock()
        mock_service.get_latest_block = AsyncMock(return_value=self.mock_block)
        mock_service_class.return_value = mock_service

        # Выполнение запроса
        response = self.client.get("/api/blocks/latest")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["hash"], self.mock_block.hash)
        self.assertEqual(data["height"], self.mock_block.height)
        mock_service.get_latest_block.assert_called_once()

    @patch("app.api.blocks.BlockService")
    def test_get_latest_block_not_found(self, mock_service_class):
        """Тест получения последнего блока когда блоков нет"""
        # Настройка mock
        mock_service = MagicMock()
        mock_service.get_latest_block = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        # Выполнение запроса
        response = self.client.get("/api/blocks/latest")

        # Проверки
        self.assertEqual(response.status_code, 404)
        self.assertIn("Блок не найден", response.json()["detail"])

    @patch("app.api.blocks.BlockService")
    def test_get_blocks_default_params(self, mock_service_class):
        """Тест получения списка блоков с параметрами по умолчанию"""
        # Настройка mock
        mock_blocks = [self.mock_block]
        mock_service = MagicMock()
        mock_service.get_blocks = AsyncMock(return_value=(mock_blocks, 1))
        mock_service_class.return_value = mock_service

        # Выполнение запроса
        response = self.client.get("/api/blocks")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["blocks"]), 1)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 10)
        self.assertEqual(data["pages"], 1)
        mock_service.get_blocks.assert_called_once_with(page=1, limit=10)

    @patch("app.api.blocks.BlockService")
    def test_get_blocks_custom_params(self, mock_service_class):
        """Тест получения списка блоков с кастомными параметрами"""
        # Настройка mock
        mock_blocks = [self.mock_block] * 5
        mock_service = MagicMock()
        mock_service.get_blocks = AsyncMock(return_value=(mock_blocks, 50))
        mock_service_class.return_value = mock_service

        # Выполнение запроса
        response = self.client.get("/api/blocks?page=2&limit=5")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["blocks"]), 5)
        self.assertEqual(data["total"], 50)
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["limit"], 5)
        self.assertEqual(data["pages"], 10)
        mock_service.get_blocks.assert_called_once_with(page=2, limit=5)

    @patch("app.api.blocks.BlockService")
    def test_get_blocks_invalid_page(self, mock_service_class):
        """Тест с некорректным номером страницы"""
        # Выполнение запроса с некорректным параметром
        response = self.client.get("/api/blocks?page=0")

        # Проверки
        self.assertEqual(response.status_code, 422)

    @patch("app.api.blocks.BlockService")
    def test_get_blocks_invalid_limit(self, mock_service_class):
        """Тест с некорректным лимитом"""
        # Выполнение запроса с некорректным параметром
        response = self.client.get("/api/blocks?limit=101")

        # Проверки
        self.assertEqual(response.status_code, 422)

    @patch("app.api.blocks.BlockService")
    def test_get_block_by_height(self, mock_service_class):
        """Тест получения блока по высоте"""
        # Настройка mock
        mock_service = MagicMock()
        mock_service.get_block_by_height = AsyncMock(return_value=self.mock_block)
        mock_service_class.return_value = mock_service

        # Выполнение запроса
        response = self.client.get("/api/blocks/800000")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["hash"], self.mock_block.hash)
        self.assertEqual(data["height"], 800000)
        mock_service.get_block_by_height.assert_called_once_with(800000)

    @patch("app.api.blocks.BlockService")
    def test_get_block_by_hash(self, mock_service_class):
        """Тест получения блока по хешу"""
        # Настройка mock
        mock_service = MagicMock()
        mock_service.get_block_by_hash = AsyncMock(return_value=self.mock_block)
        mock_service_class.return_value = mock_service

        block_hash = "00000000000000000001234567890abcdef"

        # Выполнение запроса
        response = self.client.get(f"/api/blocks/{block_hash}")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["hash"], block_hash)
        mock_service.get_block_by_hash.assert_called_once_with(block_hash)

    @patch("app.api.blocks.BlockService")
    def test_get_block_not_found_by_height(self, mock_service_class):
        """Тест получения несуществующего блока по высоте"""
        # Настройка mock
        mock_service = MagicMock()
        mock_service.get_block_by_height = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        # Выполнение запроса
        response = self.client.get("/api/blocks/999999")

        # Проверки
        self.assertEqual(response.status_code, 404)
        self.assertIn("Блок 999999 не найден", response.json()["detail"])

    @patch("app.api.blocks.BlockService")
    def test_get_block_not_found_by_hash(self, mock_service_class):
        """Тест получения несуществующего блока по хешу"""
        # Настройка mock
        mock_service = MagicMock()
        mock_service.get_block_by_hash = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        block_hash = "nonexistent_hash"

        # Выполнение запроса
        response = self.client.get(f"/api/blocks/{block_hash}")

        # Проверки
        self.assertEqual(response.status_code, 404)
        self.assertIn(f"Блок {block_hash} не найден", response.json()["detail"])

    @patch("app.api.blocks.BlockService")
    def test_get_block_transactions_success(self, mock_service_class):
        """Тест успешного получения транзакций блока"""
        # Настройка mock
        mock_transactions = [
            MagicMock(txid="tx1", size=250),
            MagicMock(txid="tx2", size=300),
        ]
        mock_service = MagicMock()
        mock_service.get_block_by_hash = AsyncMock(return_value=self.mock_block)
        mock_service.get_block_transactions = AsyncMock(
            return_value=(mock_transactions, 2)
        )
        mock_service_class.return_value = mock_service

        block_hash = "00000000000000000001234567890abcdef"

        # Выполнение запроса
        response = self.client.get(f"/api/blocks/{block_hash}/transactions")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["block_hash"], block_hash)
        self.assertEqual(len(data["transactions"]), 2)
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 25)
        self.assertEqual(data["pages"], 1)
        mock_service.get_block_by_hash.assert_called_once_with(block_hash)
        mock_service.get_block_transactions.assert_called_once_with(
            block_hash=block_hash, page=1, limit=25
        )

    @patch("app.api.blocks.BlockService")
    def test_get_block_transactions_custom_params(self, mock_service_class):
        """Тест получения транзакций блока с кастомными параметрами"""
        # Настройка mock
        mock_transactions = [MagicMock(txid=f"tx{i}") for i in range(10)]
        mock_service = MagicMock()
        mock_service.get_block_by_hash = AsyncMock(return_value=self.mock_block)
        mock_service.get_block_transactions = AsyncMock(
            return_value=(mock_transactions, 100)
        )
        mock_service_class.return_value = mock_service

        block_hash = "00000000000000000001234567890abcdef"

        # Выполнение запроса
        response = self.client.get(
            f"/api/blocks/{block_hash}/transactions?page=2&limit=10"
        )

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["block_hash"], block_hash)
        self.assertEqual(data["total"], 100)
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["limit"], 10)
        self.assertEqual(data["pages"], 10)
        mock_service.get_block_transactions.assert_called_once_with(
            block_hash=block_hash, page=2, limit=10
        )

    @patch("app.api.blocks.BlockService")
    def test_get_block_transactions_block_not_found(self, mock_service_class):
        """Тест получения транзакций несуществующего блока"""
        # Настройка mock
        mock_service = MagicMock()
        mock_service.get_block_by_hash = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        block_hash = "nonexistent_block_hash"

        # Выполнение запроса
        response = self.client.get(f"/api/blocks/{block_hash}/transactions")

        # Проверки
        self.assertEqual(response.status_code, 404)
        self.assertIn(f"Блок {block_hash} не найден", response.json()["detail"])
        mock_service.get_block_by_hash.assert_called_once_with(block_hash)

    @patch("app.api.blocks.BlockService")
    def test_get_block_transactions_invalid_page(self, mock_service_class):
        """Тест с некорректным номером страницы для транзакций"""
        block_hash = "00000000000000000001234567890abcdef"

        # Выполнение запроса с некорректным параметром
        response = self.client.get(f"/api/blocks/{block_hash}/transactions?page=0")

        # Проверки
        self.assertEqual(response.status_code, 422)

    @patch("app.api.blocks.BlockService")
    def test_get_block_transactions_invalid_limit(self, mock_service_class):
        """Тест с некорректным лимитом для транзакций"""
        block_hash = "00000000000000000001234567890abcdef"

        # Выполнение запроса с некорректным параметром
        response = self.client.get(f"/api/blocks/{block_hash}/transactions?limit=101")

        # Проверки
        self.assertEqual(response.status_code, 422)

    @patch("app.api.blocks.BlockService")
    def test_get_blocks_empty_result(self, mock_service_class):
        """Тест получения пустого списка блоков"""
        # Настройка mock
        mock_service = MagicMock()
        mock_service.get_blocks = AsyncMock(return_value=([], 0))
        mock_service_class.return_value = mock_service

        # Выполнение запроса
        response = self.client.get("/api/blocks")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["blocks"]), 0)
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["pages"], 0)


class TestBlocksAPIPagination(unittest.TestCase):
    """Тесты для проверки пагинации"""

    def setUp(self):
        """Подготовка к тестам"""
        # Переопределяем зависимость get_db
        app.dependency_overrides[get_db] = get_mock_db
        self.client = TestClient(app)

    def tearDown(self):
        """Очистка после тестов"""
        # Удаляем переопределение зависимостей
        app.dependency_overrides.clear()

    @patch("app.api.blocks.BlockService")
    def test_pagination_calculation(self, mock_service_class):
        """Тест правильности расчета пагинации"""
        # Настройка mock
        mock_blocks = []
        mock_service = MagicMock()
        mock_service.get_blocks = AsyncMock(return_value=(mock_blocks, 45))
        mock_service_class.return_value = mock_service

        # Выполнение запроса
        response = self.client.get("/api/blocks?page=1&limit=10")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pages"], 5)  # 45 элементов / 10 на странице = 5 страниц

    @patch("app.api.blocks.BlockService")
    def test_pagination_last_page_partial(self, mock_service_class):
        """Тест расчета пагинации для неполной последней страницы"""
        # Настройка mock
        mock_blocks = []
        mock_service = MagicMock()
        mock_service.get_blocks = AsyncMock(return_value=(mock_blocks, 43))
        mock_service_class.return_value = mock_service

        # Выполнение запроса
        response = self.client.get("/api/blocks?page=1&limit=10")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data["pages"], 5
        )  # 43 элемента / 10 на странице = 4.3 -> 5 страниц


if __name__ == "__main__":
    unittest.main()
