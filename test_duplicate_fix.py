"""
Тест для проверки исправления ошибки дубликатов транзакций
"""

import sys

from app.database import SessionLocal
from app.services.transaction_service import TransactionService


def test_duplicate_transaction():
    """Тест сохранения дубликата транзакции"""

    db = SessionLocal()
    try:
        service = TransactionService(db)

        # Создаем тестовую транзакцию
        test_tx_data = {
            "txid": "test_duplicate_tx_12345",
            "version": 2,
            "locktime": 0,
            "size": 250,
            "vsize": 150,
            "weight": 600,
            "vin": [],
            "vout": [
                {
                    "n": 0,
                    "value": 0.5,
                    "scriptPubKey": {"hex": "76a914...", "address": "test_address"},
                }
            ],
        }

        print("Тест 1: Сохранение новой транзакции...")
        tx1 = service.save_transaction_to_db(test_tx_data)
        print(f"✓ Транзакция создана: {tx1.txid}")

        print("\nТест 2: Попытка сохранить ту же транзакцию снова...")
        tx2 = service.save_transaction_to_db(test_tx_data)
        print(f"✓ Возвращена существующая транзакция: {tx2.txid}")

        print("\nТест 3: Проверка, что это тот же объект...")
        assert tx1.id == tx2.id, "ID транзакций должны совпадать"
        print(f"✓ ID совпадают: {tx1.id} == {tx2.id}")

        print("\n✅ Все тесты пройдены успешно!")
        print("Исправление работает корректно - дубликаты обрабатываются без ошибок.")

        # Очищаем тестовые данные
        db.delete(tx1)
        db.commit()
        print("\n🧹 Тестовые данные удалены")

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Тестирование исправления дубликатов транзакций")
    print("=" * 60)
    print()
    test_duplicate_transaction()
