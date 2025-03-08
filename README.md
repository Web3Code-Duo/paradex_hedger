# Paradex Hedger

## Описание
Paradex Hedger - это автоматизированный инструмент для хеджирования позиций между биржами Paradex и Bitget. Скрипт позволяет создавать противоположные позиции на двух биржах для спокойного набития объемов.

## Требования
- Python 3.10+
- Аккаунты на биржах, заргайтесь тут [Paradex](https://app.paradex.trade/r/boldwhale88) и тут [Bitget](https://www.bitget.com/ru/referral/register?clacCode=W1ELKUN)
- API ключ для доступа к Bitget
- EVM кошелек для доступа к Paradex

## Дисклеймер
⚠️ ВАЖНОЕ ЗАМЕЧАНИЕ: В настоящее время скрипт не работает на Windows из-за проблем совместимости библиотеки starknet-py. Если вам удастся успешно запустить скрипт на Windows, будем рады, если вы сообщите нам об этом. Несмотря на данное ограничение, в инструкции по установке мы все равно оставляем команды для Windows для полноты документации.


## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/Web3Code-Duo/paradex_hedger.git
cd paradex_hedger
```

2. Создайте и активируйте виртуальное окружение:
```bash
python -m venv .venv
source .venv/bin/activate  # Для Linux/Mac
# или
.venv\Scripts\activate     # Для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Переименуйте файл `.env-example` в `.env` и измените необходимые переменные окружения:
```
PRIVATE_KEY=ваш_приватный_ключ_ethereum
BITGET_API_KEY=ваш_api_ключ_bitget
BITGET_API_SECRET=ваш_api_секрет_bitget
BITGET_API_PASSPHRASE=ваш_пароль_bitget
```

## Использование

Запустите основной скрипт:
```bash
python main.py
```

Скрипт автоматически определит рандомную сумму ордера из заданного диапазона в настройках
и выполнит хэджирование на Paradex и Bitget

## Конфигурация

Настройки проекта находятся в файле `config.py`. 
Вы можете изменить минимальный и максимальный размер позиции в долларах, отредактировав список `POSITION_USD_LIMITS`.

## Лицензия
MIT
