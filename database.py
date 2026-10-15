import aiosqlite
from config import DB_PATH


class Database:
    """Единственный класс, который знает про подключение к SQLite."""

    def __init__(self, path: str = DB_PATH):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self._create_tables()

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def _create_tables(self):
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username    TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name    TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE (user_id, name)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                subject_id   INTEGER,
                title        TEXT NOT NULL,
                description  TEXT,
                deadline     TEXT,              -- YYYY-MM-DD
                effort_hours REAL,              -- трудоёмкость (хранится, но нагрузка не считается)
                status       TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at   TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT,
                FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
            );
            """
        )
        await self.conn.commit()

    async def execute(self, query: str, params: tuple = ()):
        cur = await self.conn.execute(query, params)
        await self.conn.commit()
        return cur

    async def fetchone(self, query: str, params: tuple = ()):
        cur = await self.conn.execute(query, params)
        return await cur.fetchone()

    async def fetchall(self, query: str, params: tuple = ()):
        cur = await self.conn.execute(query, params)
        return await cur.fetchall()