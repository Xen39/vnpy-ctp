import sys
import time

from logging import INFO
from vnpy.trader.setting import SETTINGS
from vnpy.trader.object import *

from ctp.ctp_session import CtpSession
from ctp.input import *

SETTINGS["log.active"] = True
SETTINGS["log.level"] = INFO
SETTINGS["log.console"] = True

if __name__ == "__main__":
    session = CtpSession()
    session.read_config()
    session.connect()
    time.sleep(5)
    print("合约列表:")
    print(session.get_all_contracts_pretty_str())
    while True:
        time.sleep(1)
        op = input("1(查询合约列表) 2(查询行情+下单) 3(撤单) 4(查询历史订单) 5(订阅行情) 6(添加策略) 7(查询资金账户) q(退出) 请输入操作: ").strip()
        if op == "1":
            print(session.get_all_contracts_pretty_str())
        elif op == "2":
            symbol, exchange = input_symbol_exchange()
            contract = session.query_contract(symbol, exchange)
            if contract is None:
                print("该行情未订阅，订阅后才能获取最新行情")
            else:
                print(f"最近一次回调行情:{contract}")
            while True:
                side = input("请输入方向(0买多,1卖多,2买空,3卖空,q退出):")
                if side in ("0", "1", "2", "3"):
                    direction: Direction = Direction.LONG if side in ("0", "1") else Direction.SHORT
                    offset: Offset = Offset.OPEN if side in ("0", "2") else Offset.CLOSE
                    price, volume = input_price_volume()
                    req = OrderRequest(symbol=symbol, exchange=exchange, direction=direction, type=OrderType.LIMIT,
                                       volume=volume, price=price, offset=offset)
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
            session.cancel_order(req)
        elif op == "4":
            session.get_history_orders()
        elif op == "5":
            session.subscribe(*input_symbol_exchange())
        elif op == "6":
            session.add_strategy(session.input_strategy_class_name(), input_vt_symbol())
        elif op == "7":
            session.get_all_accounts()
        elif op == "q":
            session.close()
            print("程序退出！")
            break
        else:
            print("非法输入！", file=sys.stderr)
            continue
