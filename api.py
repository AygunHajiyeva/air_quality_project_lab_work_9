import sqlite3
from contextlib import closing

from fastapi import FastAPI, HTTPException

from config import DB_PATH, PAGE_SIZE
from models import DeviceCreate

app = FastAPI(title="Air Quality Monitor API")


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create the rooms and devices tables if they do not exist yet."""
    with closing(get_connection()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                room_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS devices (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL UNIQUE,
                model     TEXT NOT NULL,
                status    TEXT NOT NULL,
                room_id   INTEGER NOT NULL,
                FOREIGN KEY (room_id) REFERENCES rooms (room_id)
            );
            """
        )
        conn.commit()


# Make sure the schema exists as soon as the API module is imported.
init_db()


@app.get("/devices")
def list_devices(limit: int = PAGE_SIZE, offset: int = 0):
    """Return devices joined with their room name."""
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT d.id, d.device_id, d.model, d.status, d.room_id,
                   r.name AS room_name
            FROM devices d
            LEFT JOIN rooms r ON d.room_id = r.room_id
            ORDER BY d.id
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]


@app.post("/devices", status_code=201)
def create_device(device: DeviceCreate):
    """Insert a new device after validating the referenced room."""
    with closing(get_connection()) as conn:
        room = conn.execute(
            "SELECT room_id FROM rooms WHERE room_id = ?", (device.room_id,)
        ).fetchone()
        if room is None:
            raise HTTPException(
                status_code=400, detail=f"Room {device.room_id} does not exist"
            )

        try:
            cur = conn.execute(
                """
                INSERT INTO devices (device_id, model, status, room_id)
                VALUES (?, ?, ?, ?)
                """,
                (device.device_id, device.model, device.status, device.room_id),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=400,
                detail=f"Device '{device.device_id}' already exists",
            )

        return {"id": cur.lastrowid, **device.model_dump()}
