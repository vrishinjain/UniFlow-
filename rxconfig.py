import os

import reflex as rx
from sqlalchemy.engine import make_url


def _normalized_db_url() -> str | None:
    raw_url = os.environ.get("REFLEX_DB_URL")
    if not raw_url:
        return None
    url = make_url(raw_url)
    if url.drivername in ("postgresql", "postgres"):
        url = url.set(drivername="postgresql+psycopg")
    if url.drivername.startswith("postgresql"):
        url = url.set(query={**dict(url.query), "sslmode": "require"})
    return url.render_as_string(hide_password=False)


_DB_URL = _normalized_db_url()

config = rx.Config(
    app_name="UniFlow_",
    db_url=_DB_URL,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(),
    ],
)
