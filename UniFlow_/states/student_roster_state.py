import logging
import os
from typing import TypedDict

import reflex as rx
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine


class StudentRow(TypedDict):
    id: int
    name: str


class StudentRosterState(rx.State):
    students: list[StudentRow] = []
    loading: bool = True
    error: str = ""

    @rx.event(background=True)
    async def load_students(self):
        async with self:
            self.loading = True
            self.error = ""

        engine = None
        try:
            database_url = os.getenv("REFLEX_DB_URL")
            if not database_url:
                raise RuntimeError("Database connection is unavailable")
            url = make_url(database_url).set(drivername="postgresql+psycopg")
            engine = create_async_engine(url)
            async with engine.connect() as connection:
                result = await connection.execute(
                    text("SELECT id, name FROM public.students ORDER BY id")
                )
                students: list[StudentRow] = [
                    {"id": int(row["id"]), "name": str(row["name"])}
                    for row in result.mappings().all()
                ]
            async with self:
                self.students = students
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.students = []
                self.error = "The student roster could not be loaded. Please try refreshing."
        finally:
            if engine is not None:
                try:
                    await engine.dispose()
                except Exception as e:
                    logging.exception(f"Error: {e}")
            async with self:
                self.loading = False
