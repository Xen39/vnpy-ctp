import logging

from vnpy_ctastrategy import *
from vnpy.trader.constant import Interval

from ctp.output import to_string
from ctp.settings import SETTINGS

class MACDStrategy(CtaTemplate):
    """MACD策略"""

    _logger: logging.Logger = None

    # 策略参数
    fast_window = 12  # 快速EMA周期
    slow_window = 26  # 慢速EMA周期
    signal_window = 9  # 信号线周期
    fixed_size = 1  # 每次交易数量

    # 策略变量
    macd_value = 0  # MACD值
    signal_value = 0  # 信号线值
    hist_value = 0  # 柱状图值

    parameters = ["fast_window", "slow_window", "signal_window", "fixed_size"]
    variables = ["macd_value", "signal_value", "hist_value"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self._logger = SETTINGS["logger"]
        assert self._logger is not None

        # 创建K线合成器
        self.bg = BarGenerator(on_bar=self.on_bar, window=1, on_window_bar=None, interval=Interval.MINUTE, daily_end=None)
        # 创建时间序列管理器
        self.am = ArrayManager(size=self.slow_window + self.signal_window)
        self._logger.info(f"策略创建: {self.strategy_name}")

    def on_init(self):
        """策略初始化回调"""
        self._logger.info(f"策略初始化中: {self.strategy_name}")
        try:
            self.load_bar(days=1,interval=Interval.MINUTE, callback=self.on_bar)
        except Exception as e:
            self._logger.error(f"策略加载历史数据时出错: {self.strategy_name}, {e}")

    def on_start(self):
        """策略启动回调"""
        self._logger.info(f"策略启动: {self.strategy_name}")

    def on_stop(self):
        """策略停止回调"""
        self._logger.info(f"策略停止: {self.strategy_name}")

    def on_tick(self, tick: TickData):
        """Tick数据更新回调"""
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """K线数据更新回调"""
        self.am.update_bar(bar)
        self._logger.info(f"{self.strategy_name} on_bar(): {self.am.count}/{self.am.size} {to_string(bar)}")
        if not self.am.inited:
            self._logger.debug(f"策略正在加载数据: {self.strategy_name}, {self.am.count}/{self.am.size}")
            return

        # 计算MACD指标
        macd, signal, hist = self.am.macd(
            self.fast_window,
            self.slow_window,
            self.signal_window,
            array=True
        )
        self.macd_value = macd[-1]
        self.signal_value = signal[-1]
        self.hist_value = hist[-1]
        # 如果没有持仓
        if self.pos == 0:
            # MACD线在信号线上方且柱状图由负变正，做多
            if self.macd_value > self.signal_value and self.hist_value > 0 and self.hist_value * hist[-2] <= 0:
                self.buy(bar.close_price, self.fixed_size)
            # MACD线在信号线下方且柱状图由正变负，做空
            elif self.macd_value < self.signal_value and self.hist_value < 0 and self.hist_value * hist[-2] <= 0:
                self.short(bar.close_price, self.fixed_size)
        # 持有多头仓位
        elif self.pos > 0:
            # MACD线在信号线下方且柱状图由正变负，平多
            if self.macd_value < self.signal_value and self.hist_value < 0 and self.hist_value * hist[-2] <= 0:
                self.sell(bar.close_price, abs(self.pos))
        # 持有空头仓位
        elif self.pos < 0:
            # MACD线在信号线上方且柱状图由负变正，平空
            if self.macd_value > self.signal_value and self.hist_value > 0 and self.hist_value * hist[-2] <= 0:
                self.cover(bar.close_price, abs(self.pos))

    def on_order(self, order: OrderData):
        """委托更新回调"""
        pass

    def on_trade(self, trade: TradeData):
        """成交更新回调"""
        self._logger.info(f"策略成交: {self.strategy_name}, {to_string(trade)}")

    def on_stop_order(self, stop_order: StopOrder):
        """停止单更新回调"""
        pass
