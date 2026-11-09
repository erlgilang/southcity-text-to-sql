from datetime import date, datetime
from decimal import Decimal
from typing import Any

# Built with chr() because ruff format rewrites a unicode escape into the literal character
EM_DASH = chr(0x2014)


def strip_em_dash(text: str) -> str:
    """Safety net for model output: the style rule bans the em dash everywhere."""
    return text.replace(f" {EM_DASH} ", ", ").replace(EM_DASH, "-")


def format_rupiah(amount: Decimal | int | float) -> str:
    """Format as Rp 1.554.000.000. Cents appear only when they are not zero."""
    value = Decimal(str(amount)).quantize(Decimal("0.01"))
    whole = int(abs(value))
    cents = int(abs(value) % 1 * 100)
    text = "Rp " + f"{whole:,}".replace(",", ".")
    if cents:
        text += f",{cents:02d}"
    return f"-{text}" if value < 0 else text


def format_table(
    columns: list[str], rows: list[tuple[Any, ...]], money_columns: list[str]
) -> list[list[str]]:
    money = {name.lower() for name in money_columns}
    is_money = [column.lower() in money for column in columns]
    return [
        [_format_cell(value, flag) for value, flag in zip(row, is_money, strict=True)]
        for row in rows
    ]


def _format_cell(value: Any, is_money: bool) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Ya" if value else "Tidak"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, int | float | Decimal):
        if is_money:
            return format_rupiah(value)
        if isinstance(value, int):
            return str(value)
        number = Decimal(str(value))
        # Indonesian decimal comma, and no ".00" on whole numbers
        return (
            str(int(number))
            if number == number.to_integral()
            else format(number.normalize(), "f").replace(".", ",")
        )
    return str(value)
