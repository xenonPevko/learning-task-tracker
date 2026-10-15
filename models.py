from dataclasses import dataclass
from datetime import date
from enum import Enum


class TaskStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


@dataclass
class User:
    id: int
    telegram_id: int
    username: str | None


@dataclass
class Subject:
    id: int
    user_id: int
    name: str


@dataclass
class Task:
    id: int
    user_id: int
    subject_id: int | None
    title: str
    description: str | None
    deadline: str | None
    effort_hours: float | None
    status: str
    created_at: str
    completed_at: str | None

    def is_overdue(self) -> bool:
        """Просрочена = дедлайн в прошлом И статус ACTIVE."""
        if self.status != TaskStatus.ACTIVE.value or not self.deadline:
            return False
        try:
            return date.fromisoformat(self.deadline) < date.today()
        except ValueError:
            return False