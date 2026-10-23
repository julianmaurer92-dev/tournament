"""Regressionstest fuer die Datenbank-URL.

Hintergrund: SQLAlchemy 2.1 waehlt fuer "postgresql://" den Treiber psycopg
(v3). Im Image steckt aber psycopg2-binary – die App startete nach einem
Image-Neubau nicht mehr. Der Treiber muss deshalb explizit in der URL stehen.
"""
import pytest

from app import _normalize_db_uri


@pytest.mark.parametrize("eingabe,erwartet", [
    ("postgresql://u:p@db:5432/x", "postgresql+psycopg2://u:p@db:5432/x"),
    ("postgres://u:p@db:5432/x", "postgresql+psycopg2://u:p@db:5432/x"),
    # Schon explizit: unveraendert lassen
    ("postgresql+psycopg2://u:p@db:5432/x", "postgresql+psycopg2://u:p@db:5432/x"),
    # Anderer Treiber bewusst gewaehlt: nicht ueberschreiben
    ("postgresql+psycopg://u:p@db:5432/x", "postgresql+psycopg://u:p@db:5432/x"),
    ("sqlite:////tmp/x.sqlite", "sqlite:////tmp/x.sqlite"),
    ("", ""),
    (None, None),
])
def test_treiber_wird_festgenagelt(eingabe, erwartet):
    assert _normalize_db_uri(eingabe) == erwartet


def test_app_nutzt_explizite_sqlite_url(app):
    assert app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///")
