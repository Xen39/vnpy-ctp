import sys
import time


from ctp.ctp_session import CtpSession
from ctp.input import *
from ctp.output import *
from vnpy.trader.constant import Direction,Offset
from vnpy.trader.object import  OrderRequest,OrderType,CancelRequest

if __name__ == "__main__":
    session = CtpSession()
    session.read_config()
    session.connect()
    print("请等待信息'结算信息确认成功'后再操作")
    try:
        while True:
            time.sleep(1)
            op = input("1(查询合约列表) 2(查询行情+下单) 3(撤单) 4(查询历史订单) 5(订阅行情) 6(添加策略) 7(查询资金账户) 8(查询所有策略) 9(停止策略) q(退出) 请输入操作: ").strip()
            if op == "1":
                print(session.get_all_contracts_pretty_str())
            elif op == "2":
                contract = session.get_tick(input_vt_symbol())
                if contract is None:
                    print("该行情未订阅，订阅后才能获取最新行情")
                else:
                    print(f"最近一次回调行情:{to_string(contract)}")
                side = input("请输入方向(0买多,1卖多,2买空,3卖空,q退出):")
                if side in ("0", "1", "2", "3"):
                    direction: Direction = Direction.LONG if side in ("0", "1") else Direction.SHORT
                    offset: Offset = Offset.OPEN if side in ("0", "2") else Offset.CLOSE
                    price, volume = input_price_volume()
                    req = OrderRequest(symbol=symbol, exchange=exchange, direction=direction, type=OrderType.LIMIT,
                                       volume=volume, price=price, offset=offset)
                    session.send_order(req)
                elif side == "q":
                    continue
                else:
                    pass
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
            elif op == "8":
                for strategy_name in session.get_all_strategy_names():
                    print(strategy_name)
            elif op == "9":
                strategy_names = input("请输入策略名称(多个策略之间以','间隔):").split(',')
                strategy_names = [x.strip() for x in strategy_names]
                session.stop_strategy(strategy_names)
            elif op == "q":
                print("程序退出！")
                break
            else:
                print("非法输入！", file=sys.stderr)
                continue
    except KeyboardInterrupt:
        print("捕捉到Ctrl+C,程序退出!", file=sys.stderr)
    finally:
        session.close()
