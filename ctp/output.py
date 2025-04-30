import datetime

from vnpy.trader.object import TickData,BarData,OrderData,TradeData,PositionData,AccountData,LogData,ContractData,QuoteData
from enum import Enum


def to_string(obj) -> str:
    if isinstance(obj, bool):
        return "是" if obj else "否"
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, datetime.datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(obj, list):
        return [to_string(x) for x in obj].__str__()
    elif isinstance(obj, TickData):
        return f"五档逐笔行情{{合约:{obj.symbol}.{obj.exchange.value} 时间:{to_string(obj.datetime)} 最新价: {obj.last_price} 最新交易量:{obj.last_volume} " \
               f"卖5:{obj.bid_price_5}x{obj.bid_volume_5} 卖4:{obj.bid_price_4}x{obj.bid_volume_4} 卖3:{obj.bid_price_3}x{obj.bid_volume_3} 卖2:{obj.bid_price_2}x{obj.bid_volume_2} 卖1:{obj.bid_price_1}x{obj.bid_volume_1} " \
               f"买1:{obj.ask_price_1}x{obj.ask_volume_1} 买2:{obj.ask_price_2}x{obj.ask_volume_2} 买3:{obj.ask_price_3}x{obj.ask_volume_3} 买4:{obj.ask_price_4}x{obj.ask_volume_4} 买5:{obj.ask_price_5}x{obj.ask_volume_5} " \
               f"名称:{obj.name} 交易量:{obj.volume} 交易额:{obj.turnover} 持仓量:{obj.open_interest} 最高价:{obj.high_price} 最低价:{obj.low_price} 开盘价:{obj.open_price} 昨收盘价:{obj.pre_close} 价格限制:[{obj.limit_down}, {obj.limit_up}]}}"
    elif isinstance(obj, BarData):
        return f"切片行情{{间隔:{obj.interval.value} 合约:{obj.symbol}.{obj.exchange.value} 时间:{to_string(obj.datetime)} " \
               f"交易量:{obj.volume} 交易额:{obj.turnover} 持仓量:{obj.open_interest} 最高价:{obj.high_price} 最低价:{obj.low_price} 开盘价:{obj.open_price} 收盘价:{obj.close_price}}}"
    elif isinstance(obj, OrderData):
        return f"订单信息{{合约:{obj.symbol}.{obj.exchange.value} 订单号:{obj.orderid} 时间:{to_string(obj.datetime)} 类型:{obj.type.value} 方向:{obj.offset.value}/{obj.direction.value} " \
               f"价格:{obj.price} 数量:{obj.volume} 已成交量:{obj.traded} 状态:{obj.status.value}}}"
    elif isinstance(obj, TradeData):
        return f"成交信息{{合约:{obj.symbol}.{obj.exchange.value} 订单号:{obj.orderid} 交易号:{obj.tradeid} 时间:{to_string(obj.datetime)} " \
               f"方向:{obj.offset.value}/{obj.direction.value} 价格:{obj.price} 数量:{obj.volume}}}"
    elif isinstance(obj, PositionData):
        return f"持仓信息{{合约:{obj.symbol}.{obj.exchange.value} 方向:{obj.direction.value} " \
               f"数量:{obj.volume} 冻结:{obj.frozen} 价格:{obj.price} 盈亏:{obj.pnl} 昨日数量:{obj.yd_volume}}}"
    elif isinstance(obj, AccountData):
        return f"账户信息{{id:{obj.accountid} 余额:{obj.balance} 冻结资金:{obj.frozen}}}"
    elif isinstance(obj, LogData):
        return f"日志信息{{日志等级:{obj.level} 消息:{obj.msg}}}"
    elif isinstance(obj, ContractData):
        return f"合约信息{obj.symbol}.{obj.exchange.value} 名称:{obj.name} 类型:{obj.product.value} 合约乘数:{obj.size} 最小变动价位:{obj.pricetick} " \
               f"最小下单量:{obj.min_volume} 最大下单量:{obj.max_volume} 支持停止订单?{to_string(obj.stop_supported)} 为净头寸?{to_string(obj.net_position)} 提供历史数据?{to_string(obj.history_data)}}}"
    elif isinstance(obj, QuoteData):
        return f"报价信息{{合约:{obj.symbol}.{obj.exchange.value} 行情号:{obj.quoteid} 时间:{to_string(obj.datetime)} 状态:{obj.status.value} 引用:{obj.reference} " \
               f"卖:{obj.bid_price}x{obj.bid_volume}-{obj.bid_offset.value} 买:{obj.ask_price}x{obj.ask_volume}-{obj.ask_offset.value}}}"
    else:
        return obj.__str__()
