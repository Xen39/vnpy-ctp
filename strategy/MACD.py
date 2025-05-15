from vnpy_ctastrategy import *

from strategy.base_strategy import BaseStrategy


class MACD(BaseStrategy):

    # 策略参数
    fixed_size = 1  # 每次交易数量

    # 策略变量
    macd_value = 0  # MACD值
    signal_value = 0  # 信号线值
    hist_value = 0  # 柱状图值

    parameters = ["fixed_size"]
    variables = ["macd_value", "signal_value", "hist_value"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

    def num_init_bars(self) -> int:
        return 26 + 9 # slow window + signal window

    def on_window_bar(self, bar: BarData):
        self.am.update_bar(bar)
        if not self.am.inited:
            self._logger.debug(f"策略正在加载数据: {self.strategy_name}, {self.am.count}/{self.am.size}")
            return

        # 计算MACD指标
        macd, signal, hist = self.am.macd(12, 26, 9, array=True)
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
