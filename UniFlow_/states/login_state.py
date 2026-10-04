import reflex as rx

import asyncio
import logging
import os
from typing import Any

import bcrypt
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


class LoginState(rx.State):
    email: str = ""
    full_name: str = ""
    role: str = ""
    signed_in: bool = False
    loading: bool = False
    message: str = ""
    password_revision: int = 0

    @rx.event
    def clear_feedback(self):
        if not self.loading:
            self.message = ""

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            encoded = password.encode("utf-8")
            if not encoded or len(encoded) > 72:
                return False
            return bcrypt.checkpw(encoded, stored_hash.encode("ascii"))
        except (ValueError, TypeError, UnicodeError):
            logging.exception("Unexpected error")
            return False

    @rx.event
    async def sign_in(self, form_data: dict[str, Any]):
        password = form_data.pop("password", "")
        if self.loading or self.signed_in:
            return
        self.email = str(form_data.get("email", "")).strip().lower()
        self.message = ""
        self.full_name = ""
        self.role = ""
        self.loading = True
        self.password_revision += 1
        yield

        engine = None
        try:
            if not self.email or not isinstance(password, str) or not password:
                self.message = "Invalid email or password"
                return
            database_url = os.environ.get("REFLEX_DB_URL", "")
            if not database_url:
                self.message = "Sign-in is temporarily unavailable. Please try again later."
                return
            engine = create_async_engine(
                make_url(database_url).set(drivername="postgresql+psycopg"),
                poolclass=NullPool,
                hide_parameters=True,
                echo=False,
                connect_args={"connect_timeout": 10},
            )
            async with engine.connect() as connection:
                result = await connection.execute(
                    text(
                        "SELECT email, password_hash, status, full_name, role "
                        "FROM public.users "
                        "WHERE lower(trim(email)) = :email LIMIT 2"
                    ),
                    {"email": self.email},
                )
                accounts = result.mappings().all()
            if len(accounts) != 1:
                self.message = "Invalid email or password"
                return
            account = accounts[0]
            verified = await asyncio.to_thread(
                self._verify_password, password, account["password_hash"]
            )
            if not verified:
                self.message = "Invalid email or password"
                return
            match account["status"]:
                case "pending":
                    self.message = "Your account is awaiting approval"
                case "rejected":
                    self.message = "Your request was not approved"
                case "active":
                    self.full_name = str(account["full_name"]).strip()
                    self.role = str(account["role"])
                    self.email = str(account["email"])
                    self.signed_in = True
                case _:
                    self.message = "Invalid email or password"
        except Exception:
            # Suppress exception details that could contain connection or account data.
            e = RuntimeError("Sign-in could not be completed")
            logging.exception(f"Error: {e}", exc_info=(RuntimeError, e, None))
            self.signed_in = False
            self.full_name = ""
            self.role = ""
            self.message = (
                "Sign-in is temporarily unavailable. Please try again later."
            )
        finally:
            password = ""
            form_data.clear()
            self.loading = False
            self.password_revision += 1
            if engine is not None:
                try:
                    await engine.dispose()
                except Exception:
                    e = RuntimeError("Sign-in connection cleanup failed")
                    logging.exception(
                        f"Error: {e}", exc_info=(RuntimeError, e, None)
                    )

    @rx.event
    def sign_out(self):
        if self.loading:
            return
        self.signed_in = False
        self.full_name = ""
        self.role = ""
        self.email = ""
        self.message = ""
        self.password_revision += 1
