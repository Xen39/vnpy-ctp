from vnpy_ctastrategy import *

from ctp.output import to_string

from .base_strategy import BaseStrategy

class SimpleTest(BaseStrategy):
    """测试策略"""

    bought: bool = False
    sold: bool = False

    variables = ["bought", "sold"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

    def num_init_bars(self) -> int:
        return 3

    def on_window_bar(self, bar: BarData):
        """K线数据更新回调"""
        self.am.update_bar(bar)
        if not self.am.inited:
            self._logger.info(f"{self.strategy_name} initializing: {self.am.count}/{self.am.size}")
            return
        if not self.trading:
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
