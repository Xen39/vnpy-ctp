from vnpy_ctastrategy import *
from vnpy.trader.constant import Interval, Direction, Offset


class MACDStrategy(CtaTemplate):
    fast_period = 12
    slow_period = 26
    signal_period = 9

    parameters = ["fast_period", "slow_period", "signal_period"]
    variables = []

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar, 1, self.on_1min_bar, Interval.MINUTE)
        self.am = ArrayManager()

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.load_bar(10)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")
        self.cancel_all()

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.bg.update_bar(bar)

    def on_1min_bar(self, bar: BarData):
        """
        Callback of new 1 minute bar data update.
        """
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        macd, signal, hist = self.am.macd(self.fast_period, self.slow_period, self.signal_period)

        if hist[-1] > 0 and hist[-2] <= 0:
            # MACD 柱状线由负变正，产生买入信号
            self.buy(bar.close_price, 1, Direction.LONG, Offset.OPEN)
            self.write_log("MACD 柱状线由负变正，买入开仓")

        elif hist[-1] < 0 and hist[-2] >= 0:
            # MACD 柱状线由正变负，产生卖出信号
            if self.pos > 0:
                self.sell(bar.close_price, abs(self.pos), Direction.SHORT, Offset.CLOSE)
                self.write_log("MACD 柱状线由正变负，卖出平仓")