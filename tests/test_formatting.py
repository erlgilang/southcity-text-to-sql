from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.formatting import format_rupiah, format_table, strip_em_dash


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("1554000000.00"), "Rp 1.554.000.000"),
        (1554000000, "Rp 1.554.000.000"),
        (Decimal("750000"), "Rp 750.000"),
        (Decimal("999"), "Rp 999"),
        (Decimal("0"), "Rp 0"),
        (Decimal("1234.50"), "Rp 1.234,50"),
        (Decimal("0.05"), "Rp 0,05"),
        (Decimal("-600000.00"), "-Rp 600.000"),
        (Decimal("-0.001"), "Rp 0"),
        (1234.5, "Rp 1.234,50"),
    ],
)
def test_format_rupiah(amount, expected):
    assert format_rupiah(amount) == expected


def test_table_formats_money_dates_and_plain_numbers():
    rows = [("Budi", Decimal("65000000.00"), date(2026, 3, 10), 101, Decimal("24.50"))]
    table = format_table(
        ["name", "outstanding", "duedate", "contractid", "area"], rows, ["outstanding"]
    )
    assert table == [["Budi", "Rp 65.000.000", "2026-03-10", "101", "24,5"]]


def test_ids_and_counts_never_get_thousand_separators():
    assert format_table(["penaltyid"], [(9001,)], []) == [["9001"]]


def test_money_columns_match_ignores_case():
    assert format_table(["Total"], [(Decimal("1000"),)], ["total"]) == [["Rp 1.000"]]


def test_null_boolean_and_timestamp_cells():
    rows = [(None, True, False, datetime(2026, 1, 2, 3, 4, 5))]
    assert format_table(["a", "b", "c", "d"], rows, []) == [
        ["-", "Ya", "Tidak", "2026-01-02 03:04"]
    ]


def test_null_in_money_column_stays_a_dash():
    assert format_table(["total"], [(None,)], ["total"]) == [["-"]]


def test_strip_em_dash_replaces_spaced_and_bare_dashes():
    dash = chr(0x2014)
    assert strip_em_dash(f"satu {dash} dua") == "satu, dua"
    assert strip_em_dash(f"A{dash}B") == "A-B"


def test_whole_decimal_outside_money_drops_zero_fraction():
    assert format_table(["n"], [(Decimal("12.00"),)], []) == [["12"]]
