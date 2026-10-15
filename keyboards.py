from datetime import date, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить задачу", callback_data="task:add")
    kb.button(text="📋 Текущие задачи", callback_data="task:list")
    kb.button(text="✅ История", callback_data="task:history")
    kb.button(text="📚 Предметы", callback_data="subject:list")
    kb.adjust(1, 2, 1)
    return kb.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data="flow:cancel")
    return kb.as_markup()


def subjects_kb(subjects, prefix: str = "pick:subject") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in subjects:
        kb.button(text=s.name, callback_data=f"{prefix}:{s.id}")
    kb.button(text="➕ Новый предмет", callback_data="subject:add")
    kb.button(text="⏭ Без предмета", callback_data=f"{prefix}:0")
    kb.button(text="❌ Отмена", callback_data="flow:cancel")
    kb.adjust(1)
    return kb.as_markup()


def effort_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for h in (0.5, 1, 2, 3, 5, 8):
        kb.button(text=f"{h:g} ч", callback_data=f"pick:effort:{h}")
    kb.button(text="⏭ Пропустить", callback_data="pick:effort:skip")
    kb.button(text="❌ Отмена", callback_data="flow:cancel")
    kb.adjust(3, 3, 1, 1)
    return kb.as_markup()


def calendar_kb(year: int, month: int, prefix: str = "pick:date") -> InlineKeyboardMarkup:
    """Простой Inline-календарь: без ручного ввода дат."""
    kb = InlineKeyboardBuilder()
    kb.button(text=f"📅 {month:02d}.{year}", callback_data="cal:ignore")
    kb.button(text="Пн", callback_data="cal:ignore")
    kb.button(text="Вт", callback_data="cal:ignore")
    kb.button(text="Ср", callback_data="cal:ignore")
    kb.button(text="Чт", callback_data="cal:ignore")
    kb.button(text="Пт", callback_data="cal:ignore")
    kb.button(text="Сб", callback_data="cal:ignore")
    kb.button(text="Вс", callback_data="cal:ignore")

    first = date(year, month, 1)
    start_weekday = first.weekday()  # 0 = Пн
    days_in_month = (date(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1)).day

    for _ in range(start_weekday):
        kb.button(text=" ", callback_data="cal:ignore")

    today = date.today()
    for d in range(1, days_in_month + 1):
        cur = date(year, month, d)
        label = f"·{d}·" if cur == today else str(d)
        kb.button(text=label, callback_data=f"{prefix}:{cur.isoformat()}")

    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)
    kb.button(text="◀", callback_data=f"cal:nav:{prev_y}-{prev_m:02d}")
    kb.button(text="⏭ Без дедлайна", callback_data=f"{prefix}:skip")
    kb.button(text="▶", callback_data=f"cal:nav:{next_y}-{next_m:02d}")

    kb.adjust(1, 7, 7, 7, 7, 7, 7)
    return kb.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="flow:confirm")
    kb.button(text="❌ Отмена", callback_data="flow:cancel")
    kb.adjust(2)
    return kb.as_markup()


def task_actions_kb(task_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Выполнено", callback_data=f"task:done:{task_id}")
    kb.button(text="✏️ Редактировать", callback_data=f"task:edit:{task_id}")
    kb.button(text="🗑 Удалить", callback_data=f"task:del:{task_id}")
    kb.button(text="⬅️ К списку", callback_data="task:list")
    kb.adjust(1)
    return kb.as_markup()


def filter_kb(subjects) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Все предметы", callback_data="filter:subject:0")
    for s in subjects:
        kb.button(text=s.name, callback_data=f"filter:subject:{s.id}")
    kb.button(text="⬅️ Назад", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()