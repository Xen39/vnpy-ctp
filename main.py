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




def input_symbol_exchange() -> tuple[str, Exchange]:
    def is_valid_vt_symbol(vt_symbol: str) -> bool:
        vt_pattern = re.compile(r"[a-zA-Z]+[0-9]+\.[A-Z]+")
        return vt_pattern.match(vt_symbol) is not None
    vt_symbol = input("请输入 <合约代码>.<交易所代码>:")
    while not is_valid_vt_symbol(vt_symbol):
        vt_symbol = input("输入非法！请重新输入 <合约代码>.<交易所代码>:")
    symbol, exchange = vt_symbol.split(".", 1)
    return symbol, Exchange(exchange)

if __name__ == "__main__":
    session = CtpSession()
    session.read_config()
    session.connect()
    time.sleep(8)
    print("等待连接结束")
    print("合约列表：")
    print(session.get_all_contracts_pretty_str())
    while True:
        op = input("请输入操作: 1(查询合约列表) 2(查询行情+下单) 3(撤单) 4(查询历史订单) q(退出程序)").strip()
        if op == "1":
            print(session.get_all_contracts_pretty_str())
        elif op == "2":
            symbol, exchange = input_symbol_exchange()
            print(session.query_contract(symbol, exchange))
            while True:
                side = input("请输入方向(0买多,1卖多,2买空,3卖空,q退出):")
                if side in ("0", "1", "2", "3"):
                    price, volume = [float(x) for x in input("请输入价格@数量:").split('@', 1)]
                    direction: Direction = Direction.LONG if side in (0, 1) else Direction.SHORT
                    offset: Offset = Offset.OPEN if side in (0, 2) else Offset.CLOSE
                    req = OrderRequest(symbol=symbol, exchange=exchange, direction=direction, type=OrderType.LIMIT,
                                       volume=volume, price=price, offset=offset)
                    print("下单:", req)
                    session.send_order(req)
                elif side == "q":
                    break
                else:
                    print("非法输入！", file=sys.stderr)
                    continue
        elif op == "3":
            order_id = input("请输入订单号：")
            symbol, exchange = input_symbol_exchange()
            req = CancelRequest(orderid=order_id, symbol=symbol, exchange=exchange)
        elif op == "4":
            print("\n".join(session.get_history_orders()))
        elif op == "q":
            session.close()
            print("程序退出！")
            break
        else:
            print("非法输入！", file=sys.stderr)
            continue
