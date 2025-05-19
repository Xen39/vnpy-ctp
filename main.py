import sys
import os
import time
import traceback

from vnpy.trader.constant import Direction, Offset
from vnpy.trader.object import OrderRequest, OrderType, CancelRequest

from ctp.ctp_session import CtpSession
from ctp.input import *
from ctp.output import *
from ctp.time_manager import sleep_till

help_list = {
    "q": "quit 退出程序",
    "h": "help 查看帮助",
    # query
    "qa": "query account 查询资金账户",
    "qc": "query contracts 查询合约列表",
    "qm": "query market data 查询指定合约行情",
    "qp": "query position 查询持仓",
    # order
    "so": "send order 下单",
    "co": "cancel order 撤单",
    "lo": "list order 列出历史订单",
    # strategy
    "as": "add strategy 添加策略",
    "ls": "list strategy 列出所有策略",
    "ss": "stop strategy 停止策略",
    # subscribe
    "sub": "subscribe 订阅行情",
    "unsub": "unsubscribe 取消订阅行情"
}

if __name__ == "__main__":
    session = CtpSession()
    session.read_config()
    session.connect()
    if sleep_till(session.inited):
        session.logger().info("CTP连接成功!")
    else:
        session.logger().error("连接CTP超时")
    strategy_record_filepath = os.path.join(os.path.dirname(__file__), "config/strategies.json")
    if os.path.isfile(strategy_record_filepath):
        session.load_strategy(strategy_record_filepath)
    try:
        while True:
            time.sleep(0.5)  # to print input tip after last operation's output
            op = input("请输入命令:").strip()
            if op in help_list:
                if op == "q":
                    session.logger().info("程序退出!")
                    break
                if op == "h":
                    for k, v in help_list.items():
                        print(f"{k:8} {v}")
                # query
                elif op == "qa":
                    for account in session.get_all_accounts():
                        print(to_string(account))
                elif op == "qc":
                    print(session.get_all_contracts_pretty_str())
                elif op == "qm":
                    tick_data = session.get_tick(input_vt_symbol())
                    if tick_data is None:
                        print("该行情未订阅，订阅后才能获取最新行情")
                    else:
                        print(f"最近一次回调行情:{to_string(tick_data)}")
                elif op == "qp":
                    for pos_data in session.get_all_positions():
                        print(to_string(pos_data))
                # order
                elif op == "so":
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
                elif op == "co":
                    order_id = input("请输入订单号：")
                    symbol, exchange = input_symbol_exchange()
                    req = CancelRequest(orderid=order_id, symbol=symbol, exchange=exchange)
                    session.cancel_order(req)
                elif op == "lo":
                    for order_data in session.get_history_orders():
                        print(to_string(order_data))
                # strategy
                elif op == "as":
                    session.add_strategy(session.input_strategy_class_name(), input_vt_symbol(), input_interval())
                elif op == "ls":
                    print(session.get_all_strategies_pretty_str())
                elif op == "ss":
                    strategy_names = input("请输入策略名称(多个策略之间以','间隔)(输入'all'以全部停止):").split(',')
                    strategy_names = [x.strip() for x in strategy_names]
                    session.stop_strategy(strategy_names)
                # subscribe
                elif op == "sub":
                    session.subscribe(*input_symbol_exchange())
                else:
                    print(f"{op} 尚未实现!")
            else:
                print("非法指令！(输入h以查看帮助)", file=sys.stderr)
    except KeyboardInterrupt:
        print("捕捉到Ctrl+C,程序退出!", file=sys.stderr)
    except Exception as e:
        print(f"执行主程序出错: {e}", file=sys.stderr)
        traceback.print_exc()
    finally:
        session.close()
