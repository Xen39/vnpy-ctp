import re
from vnpy.trader.object import Exchange


def input_symbol_exchange() -> tuple[str, Exchange]:
    def is_valid_vt_symbol(vt_symbol: str) -> bool:
        vt_pattern = re.compile(r"[a-zA-Z0-9]+\.[A-Z]+")
        return vt_pattern.match(vt_symbol) is not None
    vt_symbol = input("请输入 <合约代码>.<交易所代码>:")
    while not is_valid_vt_symbol(vt_symbol):
        vt_symbol = input("输入非法！请重新输入 <合约代码>.<交易所代码>:")
    symbol, exchange = vt_symbol.split(".", 1)
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
