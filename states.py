from aiogram.fsm.state import State, StatesGroup


class AddTaskForm(StatesGroup):
    """FSM диалога добавления задачи (5 шагов + подтверждение)."""
    title = State()
    subject = State()
    deadline = State()
    effort = State()
    confirm = State()


class AddSubjectForm(StatesGroup):
    name = State()


class EditTaskForm(StatesGroup):
    choosing = State()
    title = State()
    deadline = State()
    effort = State()