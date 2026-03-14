import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from services.bread_service import load_bread, list_bread
from services.calendar_service import get_available_dates, format_date, format_deadline
from services.order_service import create_order, format_order_notification
from config.loader import get_notify_group_id

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")
logger = logging.getLogger(__name__)

INACTIVITY_TIMEOUT = timedelta(minutes=10)

# Хранилище времени последней активности: {user_id: datetime}
_last_activity: dict = {}

NEW_ORDER_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Ассортимент и цены")],
        [KeyboardButton(text="🛒 Новый заказ")],
    ],
    resize_keyboard=True,
)


class OrderState(StatesGroup):
    choosing_date = State()
    choosing_bread = State()
    reviewing_cart = State()


def _touch(user_id: int):
    _last_activity[user_id] = datetime.now()


def _is_inactive(user_id: int) -> bool:
    last = _last_activity.get(user_id)
    if last is None:
        return True
    return datetime.now() - last > INACTIVITY_TIMEOUT


async def _show_new_order_prompt(target: Message, text: str = "Нажмите кнопку чтобы сделать заказ 👇"):
    await target.answer(text, reply_markup=NEW_ORDER_KB)


# ---------------------------------------------------------------------------
# /start и кнопка «Новый заказ»
# ---------------------------------------------------------------------------

@router.message(CommandStart())
@router.message(Command("order"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    _touch(message.from_user.id)
    await _show_new_order_prompt(message, "Добро пожаловать! Нажмите кнопку чтобы сделать заказ 👇")


@router.message(F.text == "🛒 Новый заказ")
async def on_new_order_button(message: Message, state: FSMContext):
    await state.clear()
    _touch(message.from_user.id)
    await _start_order_flow(message, state)


async def _start_order_flow(message: Message, state: FSMContext):
    dates = get_available_dates(3)
    if not dates:
        await message.answer(
            "На данный момент заказы не принимаются. Попробуйте позже.",
            reply_markup=NEW_ORDER_KB,
        )
        return
    await state.set_state(OrderState.choosing_date)
    await message.answer("На какую дату хотите заказать хлеб?", reply_markup=_dates_keyboard(dates))


# ---------------------------------------------------------------------------
# Ассортимент и цены
# ---------------------------------------------------------------------------

@router.message(F.text == "📋 Ассортимент и цены")
async def on_assortment(message: Message, state: FSMContext):
    _touch(message.from_user.id)
    text = list_bread() + "\n\nНажмите «🛒 Новый заказ» чтобы сделать заказ."
    await message.answer(text, parse_mode="HTML", reply_markup=NEW_ORDER_KB)


# ---------------------------------------------------------------------------
# Шаг 1 — Выбор даты
# ---------------------------------------------------------------------------

def _dates_keyboard(dates: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"{format_date(d)}  ·  заказ {format_deadline(d)}",
            callback_data=f"date:{d}",
        )]
        for d in dates
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(OrderState.choosing_date, F.data.startswith("date:"))
async def on_date_chosen(callback: CallbackQuery, state: FSMContext):
    _touch(callback.from_user.id)
    date_str = callback.data.split(":", 1)[1]
    await state.update_data(date=date_str, cart={})
    await state.set_state(OrderState.choosing_bread)
    await callback.answer()
    await show_bread_menu(callback.message, state, edit=True)


# ---------------------------------------------------------------------------
# Шаг 2 — Выбор хлеба
# ---------------------------------------------------------------------------

def _bread_keyboard(cart: dict) -> InlineKeyboardMarkup:
    items = load_bread()
    rows = []
    row = []
    for item in items:
        qty = cart.get(item["name"], 0)
        label = item["name"]
        if qty:
            label += f" ×{qty}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"bread:{item['name']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🛒 ЗАКАЗАТЬ", callback_data="go_cart")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _cart_summary(cart: dict) -> str:
    if not cart:
        return ""
    items = load_bread()
    price_map = {b["name"]: b["price"] for b in items}
    lines = ["<b>Корзина:</b>"]
    total = 0
    for name, qty in cart.items():
        price = price_map.get(name, 0)
        subtotal = price * qty
        total += subtotal
        lines.append(f"  {name} ×{qty} — {subtotal} ₽")
    lines.append(f"Итого: <b>{total} ₽</b>")
    return "\n".join(lines)


async def show_bread_menu(message: Message, state: FSMContext, edit: bool = False):
    data = await state.get_data()
    cart = data.get("cart", {})
    date_str = data.get("date", "")
    summary = _cart_summary(cart)
    text = f"Дата выдачи: <b>{format_date(date_str)}</b>\n\nВыберите хлеб:"
    if summary:
        text += f"\n\n{summary}"
    keyboard = _bread_keyboard(cart)
    if edit:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(OrderState.choosing_bread, F.data.startswith("bread:"))
async def on_bread_chosen(callback: CallbackQuery, state: FSMContext):
    _touch(callback.from_user.id)
    name = callback.data.split(":", 1)[1]
    data = await state.get_data()
    cart = data.get("cart", {})
    cart[name] = cart.get(name, 0) + 1
    await state.update_data(cart=cart)
    await callback.answer(f"+1 {name}")
    await show_bread_menu(callback.message, state, edit=True)


@router.callback_query(OrderState.choosing_bread, F.data == "go_cart")
async def on_go_cart(callback: CallbackQuery, state: FSMContext):
    _touch(callback.from_user.id)
    data = await state.get_data()
    cart = data.get("cart", {})
    if not cart:
        await callback.answer("Корзина пуста — выберите хлеб", show_alert=True)
        return
    await state.set_state(OrderState.reviewing_cart)
    await callback.answer()
    await show_cart(callback.message, state, edit=True)


# ---------------------------------------------------------------------------
# Шаг 3 — Корзина и оформление
# ---------------------------------------------------------------------------

def _cart_keyboard(cart: dict) -> InlineKeyboardMarkup:
    items = load_bread()
    price_map = {b["name"]: b["price"] for b in items}
    rows = []
    for name, qty in cart.items():
        price = price_map.get(name, 0)
        rows.append([
            InlineKeyboardButton(
                text=f"❌ {name} ×{qty} — {price * qty} ₽",
                callback_data=f"remove_item:{name}",
            )
        ])
    rows.append([
        InlineKeyboardButton(text="✅ РАЗМЕСТИТЬ ЗАКАЗ", callback_data="place_order"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_bread"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_cart(message: Message, state: FSMContext, edit: bool = False):
    data = await state.get_data()
    cart = data.get("cart", {})
    date_str = data.get("date", "")
    items = load_bread()
    price_map = {b["name"]: b["price"] for b in items}

    lines = [f"🧺 <b>Ваш заказ на {format_date(date_str)}</b>", ""]
    total = 0
    for name, qty in cart.items():
        price = price_map.get(name, 0)
        subtotal = price * qty
        total += subtotal
        lines.append(f"{name} × {qty} — {subtotal} ₽")
    lines.append("──────────────")
    lines.append(f"Итого: <b>{total} ₽</b>")
    lines.append("")
    lines.append("Нажмите ❌ на позицию чтобы убрать её из заказа.")

    text = "\n".join(lines)
    keyboard = _cart_keyboard(cart)
    if edit:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(OrderState.reviewing_cart, F.data.startswith("remove_item:"))
async def on_remove_item(callback: CallbackQuery, state: FSMContext):
    _touch(callback.from_user.id)
    name = callback.data.split(":", 1)[1]
    data = await state.get_data()
    cart = data.get("cart", {})
    cart.pop(name, None)
    await state.update_data(cart=cart)
    await callback.answer(f"Удалено: {name}")
    if not cart:
        await state.set_state(OrderState.choosing_bread)
        await show_bread_menu(callback.message, state, edit=True)
    else:
        await show_cart(callback.message, state, edit=True)


@router.callback_query(OrderState.reviewing_cart, F.data == "back_to_bread")
async def on_back_to_bread(callback: CallbackQuery, state: FSMContext):
    _touch(callback.from_user.id)
    await state.set_state(OrderState.choosing_bread)
    await callback.answer()
    await show_bread_menu(callback.message, state, edit=True)


@router.callback_query(OrderState.reviewing_cart, F.data == "place_order")
async def on_place_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", {})
    date_str = data.get("date", "")
    user = callback.from_user

    order = create_order(
        user_id=user.id,
        username=user.username,
        delivery_date=date_str,
        items=cart,
    )

    await callback.answer()
    await callback.message.edit_text(
        "✅ Заказ принят!\n\nС вами свяжутся для уточнения деталей.",
    )

    # Уведомление в группу
    from aiogram.exceptions import TelegramAPIError
    try:
        group_id = get_notify_group_id()
        notification = format_order_notification(order)
        from aiogram.types import ReplyKeyboardRemove as RKR
        await callback.bot.send_message(group_id, notification, parse_mode="HTML", reply_markup=RKR())
    except TelegramAPIError as e:
        logger.error("Не удалось отправить в группу: %s", e)

    await state.clear()
    _last_activity.pop(user.id, None)  # сбрасываем — следующее сообщение покажет кнопку

    await _show_new_order_prompt(callback.message)


# ---------------------------------------------------------------------------
# Catch-all: любое сообщение вне активного сценария или после таймаута
# ---------------------------------------------------------------------------

@router.message()
async def catch_all(message: Message, state: FSMContext):
    user_id = message.from_user.id
    current_state = await state.get_state()

    if current_state is None:
        # Нет активного сценария — сразу показываем кнопку
        _touch(user_id)
        await _show_new_order_prompt(message)
        return

    if _is_inactive(user_id):
        # Пользователь был неактивен 10+ минут во время сценария — сбрасываем
        await state.clear()
        _touch(user_id)
        await _show_new_order_prompt(message, "Сессия истекла. Нажмите кнопку чтобы начать новый заказ 👇")
        return

    # Пользователь в активном сценарии — напоминаем про кнопки
    _touch(user_id)
    await message.answer("Пожалуйста, используйте кнопки выше для навигации.")
