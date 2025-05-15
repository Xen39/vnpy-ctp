__all__ = ["input_vt_symbol", "input_symbol_exchange", "input_price_volume", "input_int", "input_interval", "split_win_interval"]

import re
import sys

from vnpy.trader.constant import Interval
from vnpy.trader.object import Exchange


def input_vt_symbol() -> str:
    def is_valid_vt_symbol(vt_symbol: str) -> bool:
        vt_pattern = re.compile(r"^[a-zA-Z0-9-]+\.[A-Z]+$")
        return vt_pattern.match(vt_symbol) is not None

    exchanges = {x.value for x in Exchange}
    vt_symbol = input("请输入 <合约代码>.<交易所代码>:")
    while True:
        if not is_valid_vt_symbol(vt_symbol):
            vt_symbol = input("输入非法！请重新输入 <合约代码>.<交易所代码>:")
        else:
            exchange = vt_symbol.split(".")[1]
            if exchange not in exchanges:
                vt_symbol = input("交易所不存在！请重新输入 <合约代码>.<交易所代码>:")
            else:
                break
    return vt_symbol


def input_symbol_exchange() -> tuple[str, Exchange]:
    symbol, exchange = input_vt_symbol().split(".", 1)
    return symbol, Exchange(exchange)


def input_price_volume() -> tuple[float, float]:
    while True:
        try:
            price = float(input("请输入价格："))
            volume = float(input("请输入数量:"))
            break
        except ValueError:
            continue
    return price, volume


def input_interval() -> str:
    while True:
        s = input("请输入k线间隔(如1m,5m,1h,1d,1w):")
        interval_pattern = re.compile(r"^([1-9][0-9]*)?(m|min|h|hour|d|day|w|week)$")
        match = interval_pattern.match(s)
        if match is None or len(match.groups()) != 2:
            print("非法输入!", file=sys.stderr)
        else:
            break
    return s


def split_win_interval(s: str) -> tuple[int, Interval]:
    interval_pattern = re.compile(r"^([1-9][0-9]*)?(m|h|d|w)$")
    match = interval_pattern.match(s)
    assert match is not None and len(match.groups()) == 2
    window, interval = match.groups()
    window = 1 if window is None else int(window)
    interval = {
        "m": Interval.MINUTE,
        "h": Interval.HOUR,
        "d": Interval.DAILY,
        "w": Interval.WEEKLY,
    }[interval]
    return window, interval


def input_int(min: int, max: int) -> int:
    """input a int in range of [min,max]"""
    while True:
        try:
            ret = int(input("请输入数字:"))
            if min <= ret <= max:
                break
            else:
                print(f"输入超出范围[{min},{max}])", file=sys.stderr)
                continue
        except ValueError:
            continue

    return ret
