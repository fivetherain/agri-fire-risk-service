from unittest.mock import MagicMock

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.main import app

def test_fire_create_rolls_back_on_commit_error(
    client,
):
    fake_db = MagicMock(spec=Session)

    fake_db.commit.side_effect = SQLAlchemyError(
        "forced test failure"
    )

    def override_get_db():
        yield fake_db

    app.dependency_ocerrides[get_db] = (
        override_get_db
    )

    try:
         response = client.post(
            "/v1/fire_perimeters",
            json={
                "source": "CNFDB",
                "event_id": "TEST_DAY14_FIRE",
                "name": "Transaction Test Fire",
                "geom_wkt": (
                    "POLYGON(("
                    "-123.10 49.10, "
                    "-123.00 49.10, "
                    "-123.00 49.20, "
                    "-123.10 49.20, "
                    "-123.10 49.10"
                    "))"
                ),
            },
        )
    
    finally:
        app.dependency_ocerrides.pop(
            get_db,
            None,
        )

    assert response.status_code == 500

    assert response.json()["error"]["message"] == (
        "Database operation failed"
    )

    fake_db.rollback.assert_called_once_with()