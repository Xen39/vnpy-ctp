__all__ = ["input_vt_symbol", "input_symbol_exchange", "input_price_volume", "input_int", "input_strategy"]

import re
import sys

from vnpy.trader.object import Exchange

from strategy.MACD import MACDStrategy


def input_vt_symbol() -> str:
    def is_valid_vt_symbol(vt_symbol: str) -> bool:
        vt_pattern = re.compile(r"[a-zA-Z0-9]+\.[A-Z]+")
        return vt_pattern.match(vt_symbol) is not None
    vt_symbol = input("请输入 <合约代码>.<交易所代码>:")
    while not is_valid_vt_symbol(vt_symbol):
        vt_symbol = input("输入非法！请重新输入 <合约代码>.<交易所代码>:")
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

def input_int(min:int, max:int) -> int:
    """input a int in range of [min,max]"""
    while True:
        try:
            ret = int(input("请输入数字:"))
            if ret < min or ret > max:
                print(f"输入超出范围[{min},{max}])", file=sys.stderr)
                continue
        except ValueError:
            continue

    return ret

def input_strategy():
    strategy_dict = {
        1 : MACDStrategy,
    }
    for k,v in sorted(list(strategy_dict.items())):
        print(f"{k}: {v.__name__}")
    return strategy_dict[input_int(1,1)]
