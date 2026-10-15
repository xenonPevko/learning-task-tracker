from database import Database
from models import User, Subject, Task


class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_or_create(self, telegram_id: int, username: str | None) -> User:
        row = await self.db.fetchone(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        if row:
            return User(row["id"], row["telegram_id"], row["username"])
        cur = await self.db.execute(
            "INSERT INTO users (telegram_id, username) VALUES (?, ?)",
            (telegram_id, username),
        )
        return User(cur.lastrowid, telegram_id, username)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        row = await self.db.fetchone(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        return User(row["id"], row["telegram_id"], row["username"]) if row else None


class SubjectRepository:
    def __init__(self, db: Database):
        self.db = db

    async def list_by_user(self, user_id: int) -> list[Subject]:
        rows = await self.db.fetchall(
            "SELECT * FROM subjects WHERE user_id = ? ORDER BY name", (user_id,)
        )
        return [Subject(r["id"], r["user_id"], r["name"]) for r in rows]

    async def create(self, user_id: int, name: str) -> Subject:
        cur = await self.db.execute(
            "INSERT OR IGNORE INTO subjects (user_id, name) VALUES (?, ?)",
            (user_id, name),
        )
        if cur.lastrowid:
            return Subject(cur.lastrowid, user_id, name)
        row = await self.db.fetchone(
            "SELECT * FROM subjects WHERE user_id = ? AND name = ?", (user_id, name)
        )
        return Subject(row["id"], row["user_id"], row["name"])

    async def get(self, subject_id: int) -> Subject | None:
        row = await self.db.fetchone("SELECT * FROM subjects WHERE id = ?", (subject_id,))
        return Subject(row["id"], row["user_id"], row["name"]) if row else None


class TaskRepository:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def _to_task(row) -> Task:
        return Task(
            id=row["id"],
            user_id=row["user_id"],
            subject_id=row["subject_id"],
            title=row["title"],
            description=row["description"],
            deadline=row["deadline"],
            effort_hours=row["effort_hours"],
            status=row["status"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )

    async def create(self, user_id, subject_id, title, description,
                     deadline, effort_hours) -> int:
        cur = await self.db.execute(
            """INSERT INTO tasks
               (user_id, subject_id, title, description, deadline, effort_hours)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, subject_id, title, description, deadline, effort_hours),
        )
        return cur.lastrowid

    async def get(self, task_id: int) -> Task | None:
        row = await self.db.fetchone("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return self._to_task(row) if row else None

    async def list_active(self, user_id: int, subject_id: int | None = None,
                          deadline: str | None = None) -> list[Task]:
        q = "SELECT * FROM tasks WHERE user_id = ? AND status = 'ACTIVE'"
        params: list = [user_id]
        if subject_id is not None:
            q += " AND subject_id = ?"
            params.append(subject_id)
        if deadline is not None:
            q += " AND deadline = ?"
            params.append(deadline)
        q += " ORDER BY (deadline IS NULL), deadline"
        rows = await self.db.fetchall(q, tuple(params))
        return [self._to_task(r) for r in rows]

    async def list_completed(self, user_id: int) -> list[Task]:
        rows = await self.db.fetchall(
            """SELECT * FROM tasks
               WHERE user_id = ? AND status = 'COMPLETED'
               ORDER BY completed_at DESC""",
            (user_id,),
        )
        return [self._to_task(r) for r in rows]

    async def update(self, task_id: int, **fields):
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        await self.db.execute(
            f"UPDATE tasks SET {cols} WHERE id = ?",
            (*fields.values(), task_id),
        )

    async def complete(self, task_id: int):
        await self.db.execute(
            """UPDATE tasks
               SET status = 'COMPLETED', completed_at = datetime('now')
               WHERE id = ?""",
            (task_id,),
        )

    async def delete(self, task_id: int):
        await self.db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))