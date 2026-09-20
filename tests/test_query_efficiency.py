from contextlib import contextmanager

from sqlalchemy import event

from app.db.session import engine

@contextmanager
def capture_sql():
    statements = []

    def record_statement(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        statements.append(statement)

    event.listen(
        engine,
        "before_cursor_execute",
        record_statement,
    )

    try:
        yield statements

    finally:
        event.remove(
            engine,
            "before_cursor_execute",
            record_statement,
        )

def count_selects(statements: list[str]) -> int:
    return sum(
        statement.lstrip()
        .upper()
        .startswith("SELECT")
        for statement in statements
    )

def test_fire_list_uses_one_select(
    client,
    exposure_seed,
):
    with capture_sql() as statements:
        response = client.get(
            "/v1/fire_perimeters"
        )

    assert response.status_code == 200
    assert count_selects(statements) == 1

def test_exposure_query_count_is_constant(
    client,
    exposure_seed,
):
    plot, _ = exposure_seed

    with capture_sql() as statements:
        response = client.get(
            f"/v1/exposure/plots/{plot.plot_id}"
        )

    assert response.status_code == 200
    assert count_selects(statements) == 3
