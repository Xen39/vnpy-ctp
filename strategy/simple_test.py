import logging

from vnpy_ctastrategy import *
from vnpy.trader.constant import Interval, Offset
from ctp.output import to_string

from ctp.settings import SETTINGS

class SimpleTest(CtaTemplate):
    """测试策略"""

    _logger: logging.Logger = None
    bought: bool = False
    sold: bool = False

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self._logger = SETTINGS["logger"]
        assert self._logger is not None

        # 创建K线合成器
        self.bg = BarGenerator(on_bar=self.on_bar, window=1, on_window_bar=None, interval=Interval.MINUTE, daily_end=None)
        # 创建时间序列管理器
        self.am = ArrayManager(size=3)
        self._logger.info(f"{self.strategy_name} __init__()")

    def on_init(self):
        """策略初始化回调"""
        self._logger.info(f"{self.strategy_name} on_init()")

    def on_start(self):
        """策略启动回调"""
        self._logger.info(f"{self.strategy_name} on_start()")
        self.put_event()

    def on_stop(self):
        """策略停止回调"""
        self._logger.info(f"{self.strategy_name} on_stop()")
        self.put_event()

    def on_tick(self, tick: TickData):
        """Tick数据更新回调"""
        # self._logger.info(f"{self.strategy_name} on_tick()")
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """K线数据更新回调"""
        self.am.update_bar(bar)
        if not self.am.inited:
            self._logger.info(f"{self.strategy_name} initializing: {self.am.count}/{self.am.size}")
            return

        if not self.bought:
            self._logger.info(f"{self.strategy_name} 正在买入")
            self.buy(bar.close_price, 1)
        elif not self.sold and self.pos > 0:
            self._logger.info(f"{self.strategy_name} 正在卖出")
            self.sell(bar.close_price, 1)

    def on_order(self, order: OrderData):
        """委托更新回调"""
        self._logger.info(f"{self.strategy_name} on_order(): {to_string(order)}")

    def on_trade(self, trade: TradeData):
        """成交更新回调"""
        if not self.bought and trade.direction == Direction.LONG and trade.volume == 1:
            self.bought = True
            self._logger.info(f"{self.strategy_name} 买入测试成功! {to_string(trade)}")
        elif not self.sold and trade.direction == Direction.SHORT and trade.volume == 1:
            self.sold = True
            self._logger.info(f"{self.strategy_name} 卖出测试成功! {to_string(trade)}")
        else:
            self._logger.warning(f"{self.strategy_name} unexpected on_trade(): {to_string(trade)}")
    def on_stop_order(self, stop_order: StopOrder):
        """停止单更新回调"""
        self._logger.info(f"{self.strategy_name} on_stop_order(): {to_string(stop_order)}")
