import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from config.loader import get_admins, get_admin_group_id
from services.calendar_service import add_date, remove_date, load_calendar, format_date, get_available_dates, get_upcoming_dates
from services.bread_service import add_bread, remove_bread, list_bread, load_bread
from services.order_service import get_orders_for_date

router = Router()
router.message.filter(
    F.chat.type.in_({"group", "supergroup"}),
    F.func(lambda m: m.chat.id == get_admin_group_id()),
)
logger = logging.getLogger(__name__)

HELP_TEXT = """<b>Команды администратора:</b>

/dateadd YYYYMMDD — добавить дату в календарь
/dateremove YYYYMMDD — удалить дату из календаря
/datedisplay — показать 6 ближайших дат
/breadadd Название, цена — добавить хлеб
/breadremove Название — удалить хлеб
/breadlist — показать ассортимент
/orders — заказы на 3 ближайшие даты
/bake — сколько какого хлеба печь на каждую дату
/help — эта справка"""


def _is_admin(message: Message) -> bool:
    admins = get_admins()
    user = message.from_user
    return (
        user.id in admins
        or (user.username and user.username.lower() in admins)
    )


@router.message(Command("dateadd"))
async def cmd_dateadd(message: Message):
    if not _is_admin(message):
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("Использование: /dateadd YYYYMMDD", reply_markup=ReplyKeyboardRemove())
        return
    try:
        add_date(parts[1])
        await message.reply(f"✅ Дата {format_date(parts[1])} добавлена в календарь", reply_markup=ReplyKeyboardRemove())
    except ValueError as e:
        await message.reply(f"❌ {e}")


@router.message(Command("dateremove"))
async def cmd_dateremove(message: Message):
    if not _is_admin(message):
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("Использование: /dateremove YYYYMMDD", reply_markup=ReplyKeyboardRemove())
        return
    try:
        remove_date(parts[1])
        await message.reply(f"✅ Дата {parts[1]} удалена из календаря", reply_markup=ReplyKeyboardRemove())
    except ValueError as e:
        await message.reply(f"❌ {e}", reply_markup=ReplyKeyboardRemove())


@router.message(Command("datedisplay"))
async def cmd_datedisplay(message: Message):
    if not _is_admin(message):
        return
    dates = load_calendar()[:6]
    if not dates:
        await message.reply("Календарь пуст", reply_markup=ReplyKeyboardRemove())
        return
    lines = ["<b>Ближайшие 6 дат:</b>"]
    for d in dates:
        lines.append(f"• {format_date(d)} ({d})")
    await message.reply("\n".join(lines), parse_mode="HTML", reply_markup=ReplyKeyboardRemove())


@router.message(Command("breadadd"))
async def cmd_breadadd(message: Message):
    if not _is_admin(message):
        return
    # Формат: /breadadd Название, цена
    raw = message.text.split(maxsplit=1)
    if len(raw) < 2 or "," not in raw[1]:
        await message.reply("Использование: /breadadd Название, цена", reply_markup=ReplyKeyboardRemove())
        return
    name_part, price_part = raw[1].rsplit(",", 1)
    name = name_part.strip()
    try:
        price = int(price_part.strip())
    except ValueError:
        await message.reply("❌ Цена должна быть целым числом", reply_markup=ReplyKeyboardRemove())
        return
    try:
        add_bread(name, price)
        await message.reply(f"✅ Добавлен: {name} — {price} ₽", reply_markup=ReplyKeyboardRemove())
    except ValueError as e:
        await message.reply(f"❌ {e}", reply_markup=ReplyKeyboardRemove())


@router.message(Command("breadremove"))
async def cmd_breadremove(message: Message):
    if not _is_admin(message):
        return
    raw = message.text.split(maxsplit=1)
    if len(raw) < 2:
        await message.reply("Использование: /breadremove Название", reply_markup=ReplyKeyboardRemove())
        return
    name = raw[1].strip()
    try:
        remove_bread(name)
        await message.reply(f"✅ Удалён из ассортимента: {name}", reply_markup=ReplyKeyboardRemove())
    except ValueError as e:
        await message.reply(f"❌ {e}", reply_markup=ReplyKeyboardRemove())


@router.message(Command("breadlist"))
async def cmd_breadlist(message: Message):
    if not _is_admin(message):
        return
    await message.reply(list_bread(), parse_mode="HTML", reply_markup=ReplyKeyboardRemove())


@router.message(Command("orders"))
async def cmd_orders(message: Message):
    if not _is_admin(message):
        return
    dates = get_upcoming_dates(3)
    if not dates:
        await message.reply("Нет ближайших доступных дат", reply_markup=ReplyKeyboardRemove())
        return

    lines = []
    for date_str in dates:
        orders = get_orders_for_date(date_str)
        if not orders:
            continue
        lines.append(f"📋 <b>{format_date(date_str)}</b> — {len(orders)} заказ(ов)")
        for i, o in enumerate(orders, 1):
            user_info = f"@{o['username']}" if o.get("username") else f"ID {o['user_id']}"
            positions = ", ".join(f"{it['name']} ×{it['qty']}" for it in o["items"])
            lines.append(f"  {i}. {user_info} — {positions} — <b>{o['total']} ₽</b>")
        lines.append("")

    if not lines:
        await message.reply("На ближайшие 3 даты заказов нет", reply_markup=ReplyKeyboardRemove())
        return

    await message.reply("\n".join(lines).rstrip(), parse_mode="HTML", reply_markup=ReplyKeyboardRemove())


@router.message(Command("bake"))
async def cmd_bake(message: Message):
    if not _is_admin(message):
        return
    from datetime import date as _date
    today = _date.today().strftime("%Y%m%d")
    all_dates = get_upcoming_dates(4)  # берём с запасом чтобы исключить сегодня и взять 3
    dates = [d for d in all_dates if d > today][:3]

    if not dates:
        await message.reply("Нет предстоящих дат", reply_markup=ReplyKeyboardRemove())
        return

    current_breads = {b["name"] for b in load_bread()}
    lines = []

    for date_str in dates:
        orders = get_orders_for_date(date_str)
        lines.append(f"🍞 <b>{format_date(date_str)}</b>")

        if not orders:
            lines.append("  нет заказов")
            lines.append("")
            continue

        totals = {}
        date_extra = []
        for o in orders:
            unknown = [it for it in o["items"] if it["name"] not in current_breads]
            if unknown:
                user_info = f"@{o['username']}" if o.get("username") else f"ID {o['user_id']}"
                created = o.get("created_at", "")[:16].replace("T", " ")
                pos = ", ".join(f"{it['name']} ×{it['qty']}" for it in unknown)
                date_extra.append(f"  ⚠️ {user_info} ({created}): {pos}")
            for item in o["items"]:
                if item["name"] in current_breads:
                    totals[item["name"]] = totals.get(item["name"], 0) + item["qty"]

        for name, qty in sorted(totals.items()):
            lines.append(f"  {name} — {qty} шт.")
        if date_extra:
            lines.extend(date_extra)
        lines.append("")

    await message.reply("\n".join(lines).rstrip(), parse_mode="HTML", reply_markup=ReplyKeyboardRemove())


@router.message(Command("help"))
async def cmd_help(message: Message):
    if not _is_admin(message):
        return
    await message.reply(HELP_TEXT, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
