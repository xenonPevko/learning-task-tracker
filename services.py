from datetime import date

from models import Task, TaskStatus
from repositories import TaskRepository, SubjectRepository, UserRepository


class ValidationError(Exception):
    """Ошибка валидации данных задачи."""


class TaskService:
    """Бизнес-логика задач. Никакого SQL и никакого aiogram."""

    def __init__(self,
                 tasks: TaskRepository,
                 subjects: SubjectRepository,
                 users: UserRepository):
        self.tasks = tasks
        self.subjects = subjects
        self.users = users

    async def add_task(self, telegram_id: int, username: str | None, *,
                       title: str, subject_id: int | None,
                       deadline: str | None, effort_hours: float | None,
                       description: str | None = None) -> int:
        title = (title or "").strip()
        if not title:
            raise ValidationError("Название задачи не может быть пустым.")
        if len(title) > 200:
            raise ValidationError("Название слишком длинное (макс. 200 символов).")

        if deadline:
            try:
                d = date.fromisoformat(deadline)
            except ValueError:
                raise ValidationError("Некорректный формат даты.")
            if d < date.today():
                raise ValidationError("Дедлайн не может быть в прошлом.")

        if effort_hours is not None and effort_hours <= 0:
            raise ValidationError("Трудоёмкость должна быть положительной.")

        user = await self.users.get_or_create(telegram_id, username)
        return await self.tasks.create(
            user_id=user.id,
            subject_id=subject_id,
            title=title,
            description=description,
            deadline=deadline,
            effort_hours=effort_hours,
        )

    async def list_active(self, telegram_id: int,
                          subject_id: int | None = None,
                          deadline: str | None = None) -> list[Task]:
        user = await self.users.get_by_telegram_id(telegram_id)
        if not user:
            return []
        return await self.tasks.list_active(user.id, subject_id, deadline)

    async def list_completed(self, telegram_id: int) -> list[Task]:
        user = await self.users.get_by_telegram_id(telegram_id)
        if not user:
            return []
        return await self.tasks.list_completed(user.id)

    async def get_task(self, task_id: int) -> Task | None:
        return await self.tasks.get(task_id)

    async def complete_task(self, task_id: int):
        await self.tasks.complete(task_id)

    async def delete_task(self, task_id: int):
        task = await self.tasks.get(task_id)
        if task and task.status == TaskStatus.COMPLETED.value:
            raise ValidationError("Выполненную задачу удалить нельзя — она в истории.")
        await self.tasks.delete(task_id)

    async def edit_task(self, task_id: int, **fields):
        if "deadline" in fields and fields["deadline"]:
            try:
                d = date.fromisoformat(fields["deadline"])
            except ValueError:
                raise ValidationError("Некорректный формат даты.")
            if d < date.today():
                raise ValidationError("Дедлайн не может быть в прошлом.")
        await self.tasks.update(task_id, **fields)

    async def list_subjects(self, telegram_id: int):
        user = await self.users.get_by_telegram_id(telegram_id)
        if not user:
            return []
        return await self.subjects.list_by_user(user.id)

    async def add_subject(self, telegram_id: int, username: str | None, name: str):
        name = (name or "").strip()
        if not name:
            raise ValidationError("Название предмета не может быть пустым.")
        user = await self.users.get_or_create(telegram_id, username)
        return await self.subjects.create(user.id, name)