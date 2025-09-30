#!/bin/bash

echo "Используется конфигурационный файл: /home/bitcoin/.bitcoin/bitcoin.conf"

# Ожидание готовности Bitcoin Core
echo "Ожидание готовности Bitcoin Core..."
while ! bitcoin-cli -conf=/home/bitcoin/.bitcoin/bitcoin.conf -rpcconnect=bitcoin-regtest getblockchaininfo >/dev/null 2>&1; do
    echo "Bitcoin Core еще не готов, ожидание 5 секунд..."
    sleep 5
done

echo "Bitcoin Core готов! Начинаем майнинг..."

bitcoin-cli -conf=/home/bitcoin/.bitcoin/bitcoin.conf -rpcconnect=bitcoin-regtest createwallet "miner"

# Проверка и создание кошелька
echo "Проверка существования кошелька 'miner'..."
WALLET_EXISTS=$(bitcoin-cli -conf=/home/bitcoin/.bitcoin/bitcoin.conf -rpcconnect=bitcoin-regtest listwallets | grep -c "miner" || echo "0")

if [ "$WALLET_EXISTS" -eq 0 ]; then
    echo "Создание нового кошелька 'miner'..."
    bitcoin-cli -conf=/home/bitcoin/.bitcoin/bitcoin.conf -rpcconnect=bitcoin-regtest createwallet "miner"
    if [ $? -eq 0 ]; then
        echo "Кошелек 'miner' успешно создан!"
    else
        echo "Ошибка при создании кошелька 'miner'"
        exit 1
    fi
else
    echo "Кошелек 'miner' уже существует"
fi

# Загрузка кошелька если он не загружен
echo "Загрузка кошелька 'miner'..."
bitcoin-cli -conf=/home/bitcoin/.bitcoin/bitcoin.conf -rpcconnect=bitcoin-regtest loadwallet "miner" >/dev/null 2>&1 || echo "Кошелек уже загружен"

# Получение адреса для майнинга
echo "Получение адреса для майнинга..."
MINING_ADDRESS=$(bitcoin-cli -conf=/home/bitcoin/.bitcoin/bitcoin.conf -rpcconnect=bitcoin-regtest -rpcwallet=miner getnewaddress)
echo "Адрес для майнинга: $MINING_ADDRESS"

# Начальная генерация 101 блока для активации сети
echo "Генерация начальных 101 блоков..."
bitcoin-cli -conf=/home/bitcoin/.bitcoin/bitcoin.conf -rpcconnect=bitcoin-regtest generatetoaddress 101 $MINING_ADDRESS

# Непрерывный майнинг по 1 блоку каждые 10 секунд
echo "Начинаем непрерывный майнинг..."
while true; do
    bitcoin-cli -conf=/home/bitcoin/.bitcoin/bitcoin.conf -rpcconnect=bitcoin-regtest generatetoaddress 1 $MINING_ADDRESS
    bitcoin-cli -conf=/home/bitcoin/.bitcoin/bitcoin.conf -rpcconnect=bitcoin-regtest sendtoaddress $MINING_ADDRESS 1
    sleep 10
done
