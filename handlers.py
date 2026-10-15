import logging
from datetime import date

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from keyboards import (
    main_menu, cancel_kb, subjects_kb, effort_kb, calendar_kb,
    confirm_kb, task_actions_kb, filter_kb,
)
from services import TaskService, ValidationError
from states import AddTaskForm, AddSubjectForm, EditTaskForm

router = Router()
log = logging.getLogger(__name__)

svc: TaskService  # проставим в main.py


def set_service(service: TaskService):
    global svc
    svc = service


# ---------- /start и меню ----------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Я трекер учебных задач студента.\n"
        "Помогу фиксировать дела на ходу и не пропускать дедлайны.\n\n"
        "Выбери действие:",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "menu:main")
async def back_to_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Главное меню:", reply_markup=main_menu())
    await cb.answer()


@router.callback_query(F.data == "flow:cancel")
async def cancel_flow(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Действие отменено.", reply_markup=main_menu())
    await cb.answer("Отменено")


# ---------- Добавление задачи (FSM) ----------

@router.callback_query(F.data == "task:add")
async def add_task_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddTaskForm.title)
    await state.update_data(title=None, subject_id=None, deadline=None, effort=None)
    await cb.message.edit_text(
        "📝 Шаг 1/5. Введите название задачи:", reply_markup=cancel_kb()
    )
    await cb.answer()


@router.message(AddTaskForm.title, F.text)
async def add_task_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title:
        await message.answer("Название не может быть пустым. Введите ещё раз:")
        return
    await state.update_data(title=title)

    subjects = await svc.list_subjects(message.from_user.id)
    await state.set_state(AddTaskForm.subject)
    await message.answer(
        "📚 Шаг 2/5. Выберите предмет:",
        reply_markup=subjects_kb(subjects),
    )


@router.callback_query(AddTaskForm.subject, F.data.startswith("pick:subject:"))
async def add_task_subject(cb: CallbackQuery, state: FSMContext):
    sid = int(cb.data.split(":")[-1])
    await state.update_data(subject_id=sid if sid else None)
    await state.set_state(AddTaskForm.deadline)
    today = date.today()
    await cb.message.edit_text(
        "📅 Шаг 3/5. Выберите дедлайн:",
        reply_markup=calendar_kb(today.year, today.month),
    )
    await cb.answer()


@router.callback_query(AddTaskForm.subject, F.data == "subject:add")
async def add_subject_from_flow(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddSubjectForm.name)
    await cb.message.edit_text(
        "Введите название нового предмета:", reply_markup=cancel_kb()
    )
    await cb.answer()


@router.message(AddSubjectForm.name, F.text)
async def subject_created(message: Message, state: FSMContext):
    try:
        await svc.add_subject(message.from_user.id, message.from_user.username,
                              message.text)
    except ValidationError as e:
        await message.answer(f"⚠️ {e}")
        return
    subjects = await svc.list_subjects(message.from_user.id)
    await state.set_state(AddTaskForm.subject)
    await message.answer(
        "Предмет добавлен. Выберите предмет:",
        reply_markup=subjects_kb(subjects),
    )


@router.callback_query(AddTaskForm.deadline, F.data.startswith("pick:date:"))
async def add_task_deadline(cb: CallbackQuery, state: FSMContext):
    value = cb.data.split(":")[-1]
    await state.update_data(deadline=None if value == "skip" else value)
    await state.set_state(AddTaskForm.effort)
    await cb.message.edit_text(
        "⏱ Шаг 4/5. Оцените трудоёмкость (часы):",
        reply_markup=effort_kb(),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("cal:nav:"))
async def calendar_nav(cb: CallbackQuery):
    _, _, ym = cb.data.split(":")
    y, m = map(int, ym.split("-"))
    await cb.message.edit_reply_markup(reply_markup=calendar_kb(y, m))
    await cb.answer()


@router.callback_query(F.data == "cal:ignore")
async def cal_ignore(cb: CallbackQuery):
    await cb.answer()


@router.callback_query(AddTaskForm.effort, F.data.startswith("pick:effort:"))
async def add_task_effort(cb: CallbackQuery, state: FSMContext):
    value = cb.data.split(":")[-1]
    effort = None if value == "skip" else float(value)
    await state.update_data(effort=effort)

    data = await state.get_data()
    subject_name = "—"
    if data.get("subject_id"):
        for s in await svc.list_subjects(cb.from_user.id):
            if s.id == data["subject_id"]:
                subject_name = s.name
                break

    await state.set_state(AddTaskForm.confirm)
    text = (
        "🧾 Шаг 5/5. Проверьте данные:\n\n"
        f"📌 <b>{data['title']}</b>\n"
        f"📚 Предмет: {subject_name}\n"
        f"📅 Дедлайн: {data.get('deadline') or '—'}\n"
        f"⏱ Трудоёмкость: {data.get('effort') or '—'} ч"
    )
    await cb.message.edit_text(text, reply_markup=confirm_kb(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(AddTaskForm.confirm, F.data == "flow:confirm")
async def add_task_confirm(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        await svc.add_task(
            telegram_id=cb.from_user.id,
            username=cb.from_user.username,
            title=data["title"],
            subject_id=data.get("subject_id"),
            deadline=data.get("deadline"),
            effort_hours=data.get("effort"),
        )
    except ValidationError as e:
        await cb.message.edit_text(f"⚠️ {e}", reply_markup=main_menu())
        await state.clear()
        await cb.answer()
        return

    await state.clear()
    await cb.message.edit_text("✅ Задача добавлена!", reply_markup=main_menu())
    await cb.answer("Готово")


# ---------- Список текущих задач ----------

def _format_task(t) -> str:
    deadline = t.deadline or "—"
    overdue = " ⚠️ просрочена" if t.is_overdue() else ""
    effort = f"{t.effort_hours:g} ч" if t.effort_hours else "—"
    return (
        f"📌 <b>{t.title}</b>\n"
        f"📅 Дедлайн: {deadline}{overdue}\n"
        f"⏱ Трудоёмкость: {effort}"
    )


@router.callback_query(F.data == "task:list")
async def list_tasks(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    tasks = await svc.list_active(cb.from_user.id)
    if not tasks:
        await cb.message.edit_text(
            "📭 Текущих задач нет. Добавим?", reply_markup=main_menu()
        )
        await cb.answer()
        return

    subjects = await svc.list_subjects(cb.from_user.id)
    await cb.message.edit_text(
        f"📋 Текущих задач: {len(tasks)}",
        reply_markup=filter_kb(subjects),
    )
    for t in tasks[:20]:
        await cb.message.answer(_format_task(t), parse_mode="HTML",
                                reply_markup=task_actions_kb(t.id))
    await cb.answer()


@router.callback_query(F.data.startswith("filter:subject:"))
async def filter_by_subject(cb: CallbackQuery):
    sid = int(cb.data.split(":")[-1]) or None
    tasks = await svc.list_active(cb.from_user.id, subject_id=sid)
    if not tasks:
        await cb.answer("Нет задач по этому предмету", show_alert=True)
        return
    for t in tasks[:20]:
        await cb.message.answer(_format_task(t), parse_mode="HTML",
                                reply_markup=task_actions_kb(t.id))
    await cb.answer()


# ---------- Действия над задачей ----------

@router.callback_query(F.data.startswith("task:done:"))
async def task_done(cb: CallbackQuery):
    task_id = int(cb.data.split(":")[-1])
    await svc.complete_task(task_id)
    await cb.message.edit_text("✅ Задача выполнена и перемещена в историю.")
    await cb.answer("Выполнено")


@router.callback_query(F.data.startswith("task:del:"))
async def task_delete(cb: CallbackQuery):
    task_id = int(cb.data.split(":")[-1])
    try:
        await svc.delete_task(task_id)
        await cb.message.edit_text("🗑 Задача удалена.")
        await cb.answer("Удалено")
    except ValidationError as e:
        await cb.answer(str(e), show_alert=True)


@router.callback_query(F.data.startswith("task:edit:"))
async def task_edit_start(cb: CallbackQuery, state: FSMContext):
    task_id = int(cb.data.split(":")[-1])
    await state.set_state(EditTaskForm.choosing)
    await state.update_data(task_id=task_id)
    await cb.message.edit_text(
        "Что изменить?",
        reply_markup=_edit_choice_kb(task_id),
    )
    await cb.answer()


def _edit_choice_kb(task_id: int):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="Название", callback_data=f"edit:title:{task_id}")
    kb.button(text="Дедлайн", callback_data=f"edit:deadline:{task_id}")
    kb.button(text="Трудоёмкость", callback_data=f"edit:effort:{task_id}")
    kb.button(text="⬅️ Назад", callback_data="task:list")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data.startswith("edit:title:"))
async def edit_title_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(EditTaskForm.title)
    await cb.message.edit_text("Введите новое название:", reply_markup=cancel_kb())
    await cb.answer()


@router.message(EditTaskForm.title, F.text)
async def edit_title_save(message: Message, state: FSMContext):
    data = await state.get_data()
    await svc.edit_task(data["task_id"], title=message.text.strip())
    await state.clear()
    await message.answer("✏️ Название обновлено.", reply_markup=main_menu())


@router.callback_query(F.data.startswith("edit:deadline:"))
async def edit_deadline_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(EditTaskForm.deadline)
    today = date.today()
    await cb.message.edit_text(
        "Выберите новый дедлайн:",
        reply_markup=calendar_kb(today.year, today.month, prefix="edit:date"),
    )
    await cb.answer()


@router.callback_query(EditTaskForm.deadline, F.data.startswith("edit:date:"))
async def edit_deadline_save(cb: CallbackQuery, state: FSMContext):
    value = cb.data.split(":")[-1]
    data = await state.get_data()
    if value == "skip":
        await svc.edit_task(data["task_id"], deadline=None)
    else:
        try:
            await svc.edit_task(data["task_id"], deadline=value)
        except ValidationError as e:
            await cb.answer(str(e), show_alert=True)
            return
    await state.clear()
    await cb.message.edit_text("✏️ Дедлайн обновлён.", reply_markup=main_menu())
    await cb.answer()


@router.callback_query(F.data.startswith("edit:effort:"))
async def edit_effort_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(EditTaskForm.effort)
    await cb.message.edit_text(
        "Выберите трудоёмкость:", reply_markup=effort_kb()
    )
    await cb.answer()


@router.callback_query(EditTaskForm.effort, F.data.startswith("pick:effort:"))
async def edit_effort_save(cb: CallbackQuery, state: FSMContext):
    value = cb.data.split(":")[-1]
    effort = None if value == "skip" else float(value)
    data = await state.get_data()
    await svc.edit_task(data["task_id"], effort_hours=effort)
    await state.clear()
    await cb.message.edit_text("✏️ Трудоёмкость обновлена.", reply_markup=main_menu())
    await cb.answer()


# ---------- История ----------

@router.callback_query(F.data == "task:history")
async def task_history(cb: CallbackQuery):
    tasks = await svc.list_completed(cb.from_user.id)
    if not tasks:
        await cb.message.edit_text(
            "📭 История пуста.", reply_markup=main_menu()
        )
        await cb.answer()
        return
    lines = ["✅ <b>Выполненные задачи:</b>\n"]
    for t in tasks[:30]:
        lines.append(f"• {t.title} — {t.completed_at[:10] if t.completed_at else '—'}")
    await cb.message.edit_text("\n".join(lines), parse_mode="HTML",
                               reply_markup=main_menu())
    await cb.answer()


# ---------- Предметы ----------

@router.callback_query(F.data == "subject:list")
async def subject_list(cb: CallbackQuery):
    subjects = await svc.list_subjects(cb.from_user.id)
    if not subjects:
        text = "📚 Предметов пока нет."
    else:
        text = "📚 <b>Ваши предметы:</b>\n" + "\n".join(f"• {s.name}" for s in subjects)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    await cb.answer()