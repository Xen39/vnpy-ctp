import sys
import time
import re

from vnpy.trader.setting import SETTINGS
from vnpy.trader.object import *
from logging import INFO
from ctp.ctp_session import CtpSession

SETTINGS["log.active"] = True
SETTINGS["log.level"] = INFO
SETTINGS["log.console"] = True


def is_valid_vt_symbol(vt_symbol: str) -> bool:
    vt_pattern = re.compile(r"[a-zA-Z]+[0-9]+\.[A-Z]+")
    return vt_pattern.match(vt_symbol) is not None


if __name__ == "__main__":
    session = CtpSession()
    session.read_config()
    session.connect()
    time.sleep(8)
    print("等待连接结束")
    print("交易所列表: ", [xch.value for xch in session.get_all_exchanges()])
    print("合约列表：")
    while True:
        op = input("请输入操作: 1(查询行情/下单) q(退出程序)").strip()
        if op == "1":
            vt_symbol = input("请输入 合约代码.交易所代码:")
            while not is_valid_vt_symbol(vt_symbol):
                vt_symbol = input("输入非法！请重新输入 <合约代码>.<交易所代码>:")
            symbol, exchange = vt_symbol.split(".", 1)
            exchange = Exchange(exchange)
            print(session.query_contract(vt_symbol))
            try:
                price = float(input("请输入价格:"))
                volume = float(input("请输入数量:"))
                side = int(input("请输入方向(0买多,1卖多,2买空,3卖空)"))
            except ValueError:
                print("退出下单！")
                continue
            direction: Direction = Direction.LONG if side in (0, 1) else Direction.SHORT
            offset: Offset = Offset.OPEN if side in (0, 2) else Offset.CLOSE
            req = OrderRequest(symbol=symbol, exchange=exchange, direction=direction, type=OrderType.LIMIT,
                               volume=volume, price=price, offset=offset)
            print("下单:", req)
            session.send_order(req)
        elif op == "q":
            print("程序退出！")
            break
        else:
            print("非法输入！", file=sys.stderr)
            continue
