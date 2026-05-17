import pytest

from day01.src.tools import describe_table, list_tables, run_readonly_query


def test_list_tables():
    assert list_tables() == ["orders", "regions"]


def test_describe_orders():
    text = describe_table("orders")
    assert "order_id" in text


def test_reject_write():
    with pytest.raises(ValueError, match="read-only"):
        run_readonly_query("DELETE FROM orders")


def test_select_orders():
    result = run_readonly_query("SELECT COUNT(*) AS n FROM orders")
    assert result.row_count == 1
    assert result.rows[0][0] == 7
