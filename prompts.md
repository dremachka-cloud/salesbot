# Промпты для поэтапной разработки Salesbot

Каждый промпт — самостоятельный шаг. Выполнять последовательно. Перед каждым шагом читать CLAUDE.md.

---

## Промпт 1 — Структура проекта и конфигурация

```
Прочитай CLAUDE.md. Создай структуру каталогов и файлов проекта salesbot согласно разделу
"Структура файлов проекта". Заполни файлы-заглушки:

- config/token.txt — строка-заглушка "YOUR_BOT_TOKEN"
- config/admins.txt — один тестовый ID: 000000000
- config/group.txt — строка-заглушка "-100000000000"
- data/bread.csv — 5 видов хлеба с ценами (придумай реалистичные)
- data/calendar.json — пустой массив []
- data/orders.json — пустой массив []

Не пиши никакого Python-кода на этом шаге.
```

---

## Промпт 2 — Сервис ассортимента (bread_service.py)

```
Прочитай CLAUDE.md (раздел "Внешние файлы конфигурации" и команды администраторов
/breadadd, /breadremove, /breadlist).

Реализуй services/bread_service.py со следующими функциями:
- load_bread() -> list[dict]          # читает data/bread.csv, возвращает [{name, price}, ...]
- save_bread(items: list[dict])       # перезаписывает data/bread.csv
- add_bread(name: str, price: int)    # добавляет, если не существует; ошибка если уже есть
- remove_bread(name: str)             # удаляет по имени; ошибка если нет
- list_bread() -> str                 # форматированная строка для вывода в Telegram

Покрой каждую функцию юнит-тестами в tests/test_bread_service.py.
```

---

## Промпт 3 — Сервис календаря (calendar_service.py)

```
Прочитай CLAUDE.md (раздел "Логика календаря").

Реализуй services/calendar_service.py:
- generate_dates(weeks_ahead: int = 4) -> list[str]
    Генерирует даты сред и суббот на weeks_ahead недель вперёд, формат YYYYMMDD.
- load_calendar() -> list[str]        # читает data/calendar.json
- save_calendar(dates: list[str])     # записывает data/calendar.json
- refresh_calendar()                  # дополняет файл сгенерированными датами, не дублируя
- add_date(date_str: str)             # добавляет дату вручную
- remove_date(date_str: str)          # удаляет дату
- get_available_dates(n: int = 3) -> list[str]
    Возвращает n ближайших дат, дедлайн которых (дата - 2 дня, 20:00) ещё не прошёл.
- format_date(date_str: str) -> str   # "20260318" → "18 марта (среда)"

Покрой тестами в tests/test_calendar_service.py, особенно граничные случаи дедлайна.
```

---

## Промпт 4 — Сервис заказов (order_service.py)

```
Прочитай CLAUDE.md (раздел "Хранение заказа" и "Уведомления в группу").

Реализуй services/order_service.py:
- load_orders() -> list[dict]
- save_orders(orders: list[dict])
- create_order(user_id, username, date, items) -> dict
    Создаёт заказ, присваивает uuid, сохраняет в orders.json. Возвращает объект заказа.
- get_orders_for_date(date_str: str) -> list[dict]
- get_orders_for_today() -> list[dict]
- format_order_notification(order: dict) -> str
    Форматирует сообщение для группы при новом заказе (см. пример в CLAUDE.md).
- format_daily_summary(orders: list[dict]) -> str
    Форматирует суточный итог: сводка по датам и позициям.

Покрой тестами в tests/test_order_service.py.
```

---

## Промпт 5 — Точка входа и конфигурация бота (bot.py, config loader)

```
Прочитай CLAUDE.md.

Реализуй:
1. config/loader.py — функции:
   - get_token() -> str           # читает config/token.txt
   - get_admins() -> set[int]     # читает config/admins.txt, возвращает множество int
   - get_group_id() -> int        # читает config/group.txt

2. bot.py — точка входа:
   - Инициализирует aiogram Bot и Dispatcher
   - Подключает роутеры handlers/user.py и handlers/admin.py
   - Запускает polling
   - При старте вызывает calendar_service.refresh_calendar()

Не реализуй хендлеры на этом шаге — только регистрацию роутеров-заглушек.
```

---

## Промпт 6 — FSM пользователя: шаг 1, выбор даты (handlers/user.py)

```
Прочитай CLAUDE.md (раздел "Пользовательский сценарий", Шаг 1).

Реализуй в handlers/user.py:
- FSM-состояния: OrderState (choosing_date, choosing_bread, reviewing_cart)
- Хендлер /start и /order:
  Получает список из 3 доступных дат через calendar_service.get_available_dates(3).
  Если дат нет — сообщение "Заказы временно не принимаются".
  Если есть — сообщение "На какую дату хотите заказать хлеб?" с inline-кнопками дат.
- Хендлер callback_query для выбора даты:
  Сохраняет выбранную дату в FSMContext, переводит в состояние choosing_bread,
  вызывает отображение шага 2 (заглушка — просто сообщение "Дата выбрана: ...").
```

---

## Промпт 7 — FSM пользователя: шаг 2, выбор хлеба (handlers/user.py)

```
Прочитай CLAUDE.md (Шаг 2 пользовательского сценария).

Дополни handlers/user.py:
- Функция show_bread_menu(message_or_query, state):
  Загружает ассортимент, строит inline keyboard в 3 колонки.
  Внизу — кнопка "🛒 Заказать" на всю ширину.
  В тексте сообщения отображает текущую корзину (если не пуста).

- Хендлер callback_query для нажатия на хлеб:
  Добавляет +1 к qty выбранного хлеба в FSMContext (ключ "cart": {name: qty}).
  Обновляет сообщение (edit_message) с новым счётчиком корзины.

- Хендлер callback_query "🛒 Заказать":
  Переводит в состояние reviewing_cart, вызывает отображение шага 3 (заглушка).

Корзина хранится в FSMContext как dict {название: количество}.
```

---

## Промпт 8 — FSM пользователя: шаг 3, корзина и оформление (handlers/user.py)

```
Прочитай CLAUDE.md (Шаг 3 пользовательского сценария и "Уведомления в группу").

Дополни handlers/user.py:
- Функция show_cart(message_or_query, state):
  Форматирует корзину: каждая позиция — строка "Название × qty — сумма ₽".
  Итого в конце.
  Для каждой позиции — кнопка "❌ Название" (callback: remove_item:Название).
  Внизу кнопки: "✅ Разместить заказ" и "◀️ Вернуться к выбору".

- Хендлер callback_query "remove_item:*":
  Удаляет позицию из корзины, обновляет сообщение.
  Если корзина стала пустой — возвращает на шаг 2.

- Хендлер callback_query "◀️ Вернуться к выбору":
  Переводит в состояние choosing_bread, показывает шаг 2 (корзина сохранена).

- Хендлер callback_query "✅ Разместить заказ":
  Вызывает order_service.create_order(...).
  Отправляет пользователю: "С вами свяжется пекарь для уточнения деталей".
  Отправляет в группу сообщение через order_service.format_order_notification().
  Сбрасывает FSM-состояние.
```

---

## Промпт 9 — Хендлеры администраторов (handlers/admin.py)

```
Прочитай CLAUDE.md (раздел "Команды администраторов").

Реализуй handlers/admin.py:
- Middleware или декоратор is_admin(func): проверяет, что user_id в get_admins()
  и что сообщение пришло из get_group_id(). Иначе — игнорировать (не отвечать).

- Хендлеры команд:
  /dateadd YYYYMMDD     → calendar_service.add_date()
  /dateremove YYYYMMDD  → calendar_service.remove_date()
  /datedisplay          → calendar_service.load_calendar()[:6], форматировать и вывести
  /breadadd Название, цена → bread_service.add_bread()
  /breadremove Название → bread_service.remove_bread()
  /breadlist            → bread_service.list_bread()
  /help                 → вывести таблицу всех доступных команд

Каждый хендлер отвечает в группу подтверждением или текстом ошибки.
```

---

## Промпт 10 — Планировщик (scheduler.py)

```
Прочитай CLAUDE.md (раздел "Планировщик").

Реализуй scheduler.py с использованием APScheduler (AsyncIOScheduler):
- Задача 1: каждый день в 00:01 — вызвать calendar_service.refresh_calendar()
- Задача 2: каждый день в 21:00 —
  Получить order_service.get_orders_for_today().
  Если список не пуст — отправить order_service.format_daily_summary() в группу.

Интегрируй scheduler в bot.py: запускать при старте бота, останавливать при завершении.
```

---

## Промпт 11 — Финальная интеграция и проверка

```
Прочитай CLAUDE.md целиком.

Выполни финальную интеграцию:
1. Убедись, что все роутеры зарегистрированы в bot.py.
2. Проверь, что refresh_calendar() вызывается при старте.
3. Запусти все тесты (pytest), исправь упавшие.
4. Проверь граничный случай: если пользователь пишет боту когда доступных дат нет.
5. Проверь граничный случай: пустой ассортимент.
6. Проверь: команда от не-администратора в группе игнорируется без ответа.
7. Создай requirements.txt со всеми зависимостями.
8. Создай README.md с инструкцией по запуску (заполнить конфиг-файлы, python bot.py).
```

---

## Порядок выполнения промптов

```
1 → 2 → 3 → 4   (независимые сервисы, можно параллельно 2-4)
         ↓
         5       (конфигурация и точка входа)
         ↓
    6 → 7 → 8   (FSM пользователя, строго последовательно)
         ↓
         9       (хендлеры администраторов)
         ↓
        10       (планировщик)
         ↓
        11       (финальная интеграция)
```
