import logging

from vnpy_ctastrategy import *
from vnpy.trader.constant import Interval
from ctp.output import to_string

from ctp.settings import SETTINGS

class MyTestStrategy(CtaTemplate):
    """测试策略"""

    _logger: logging.Logger = None

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self._logger = SETTINGS["logger"]
        assert self._logger is not None

        # 创建K线合成器
        self.bg = BarGenerator(on_bar=self.on_bar, window=1, on_window_bar=None, interval=Interval.MINUTE, daily_end=None)
        # 创建时间序列管理器
        self.am = ArrayManager(size=5)
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
        self._logger.info(f"{self.strategy_name} on_bar(): {to_string(bar)}")
        self.am.update_bar(bar)
        if not self.am.inited:
            self._logger.info(f"{self.strategy_name} initializing: count={self.am.count}, size={self.am.size}")
            return

        if self.pos == 0:
            self.buy(bar.close_price, 1)
        elif self.pos == 1:
            self.sell(bar.close_price, 1)
        else:
            self._logger.error(f"unexpected position: {self.pos}")

        self.put_event()

    def on_order(self, order: OrderData):
        """委托更新回调"""
        self._logger.info(f"{self.strategy_name} on_order()", to_string(order))

    def on_trade(self, trade: TradeData):
        """成交更新回调"""
        self._logger.info(f"{self.strategy_name} on_trade()", to_string(trade))
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """停止单更新回调"""
        self._logger.info(f"{self.strategy_name} on_stop_order()", to_string(stop_order))
