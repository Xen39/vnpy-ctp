from vnpy_ctastrategy import *

from .base_strategy import BaseStrategy

class C53(BaseStrategy):
    # 策略参数
    fund = 10_000_000  # 初始资金
    risk_ratio = 0.04  # 风险资金比例
    atr_length = 26  # ATR计算周期
    ema_length = 240  # EMA计算周期
    cl_period = 20  # 高低点计算周期
    cd_period = 5  # 突破确认周期
    n_atr = 3.0  # ATR止损倍数
    stop_loss = 2.0  # 百分比止损
    fee_per_lot = 10  # 每手手续费

    # 策略变量
    entry_price = 0.0  # 开仓价格
    highest_price = 0.0  # 多头持仓期间最高价
    lowest_price = 0.0  # 空头持仓期间最低价
    atr_value = 0.0  # ATR值
    mas_value = 0.0  # EMA值
    upper_levels = []  # 历史CL周期高点队列
    lower_levels = []  # 历史CL周期低点队列

    parameters = [
        "fund", "risk_ratio", "atr_length", "ema_length",
        "cl_period", "cd_period", "n_atr", "stop_loss",
        "fee_per_lot"
    ]

    variables = [
        "entry_price", "highest_price",
        "lowest_price", "atr_value", "mas_value",
        "upper_levels", "lower_levels"
    ]

    def __init__(self, cta_engine, strategy_name: str, vt_symbol: str, setting: dict):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

    def num_init_bars(self) -> int:
        return max(self.atr_length, self.ema_length, self.cl_period) + self.cd_period + 10

    def on_window_bar(self, bar: BarData) -> None:
        self.am.update_bar(bar)
        if not self.am.inited:
            self._logger.debug(f"策略正在加载数据: {self.strategy_name}, {self.am.count}/{self.am.size}")
            return

        # 计算ATR
        self.atr_value = self.am.atr(self.atr_length)
        # 计算EMA（使用前一根K线的收盘价）
        self.mas_value = self.am.ema(self.ema_length, array=True)[-2]  # 索引-2对应前一根K线
        # 计算CL周期极值（当前K线）
        self.upper_levels.append(self.am.high[-self.cl_period:].max())
        self.lower_levels.append(self.am.low[-self.cl_period:].min())

        # 获取参考极值（CD+1周期前）
        ref_upper, ref_lower = 0.0, 0.0
        try:
            if len(self.upper_levels) > self.cd_period + 1:
                ref_upper = self.upper_levels[-self.cd_period - 2]  # CD+1周期前的极值
                ref_lower = self.lower_levels[-self.cd_period - 2]
        except IndexError:
            self._logger.error(f"{self.strategy_name} 历史极值数据不足")
            return

        # 计算交易手数
        denominator = bar.close_price * self.multiplier * self.margin_ratio + self.fee_per_lot
        risk_capital = self.fund * self.risk_ratio
        trading_size = max(int(risk_capital / denominator), 1)  # 至少1手

        # 信号条件判断
        current_pos = self.pos

        # 多头开仓条件
        long_condition = all([
            bar.high_price >= ref_upper,  # 当前高点突破历史高点
            self.am.high[-2] < ref_upper,  # 前一根未突破
            self.am.close[-2] > self.mas_value  # 前收盘在EMA之上
        ])

        # 空头开仓条件
        short_condition = all([
            bar.low_price <= ref_lower,  # 当前低点跌破历史低点
            self.am.low[-2] > ref_lower,  # 前一根未跌破
            self.am.close[-2] < self.mas_value  # 前收盘在EMA之下
        ])

        # 止损条件
        # 多头止损
        long_stop = any([
            bar.close_price <= (self.highest_price - self.n_atr * self.atr_value),  # ATR吊灯
            self.am.low[-2] < self.entry_price * (1 - self.stop_loss / 100)  # 百分比止损
        ]) if current_pos > 0 else False

        # 空头止损
        short_stop = any([
            bar.close_price >= (self.lowest_price + self.n_atr * self.atr_value),  # ATR吊灯
            self.am.high[-2] > self.entry_price * (1 + self.stop_loss / 100)  # 百分比止损
        ]) if current_pos < 0 else False

        # 执行交易逻辑
        # 开仓逻辑
        if long_condition:
            price = bar.close_price + self.tick_price  # 滑点处理
            self.buy(price, trading_size)
            self.entry_price = bar.close_price
            self.highest_price = bar.high_price

        elif short_condition:
            price = bar.close_price - self.tick_price
            self.short(price, trading_size)
            self.entry_price = bar.close_price
            self.lowest_price = bar.low_price

        if current_pos > 0:
            # 更新多头持仓最高价
            self.highest_price = max(self.highest_price, bar.high_price)
            # 平仓逻辑
            if long_stop:
                price = bar.close_price - self.tick_price
                self.sell(price, abs(current_pos))

        elif current_pos < 0:
            # 更新空头持仓最低价
            self.lowest_price = min(self.lowest_price, bar.low_price)
            # 平仓逻辑
            if short_stop:
                price = bar.close_price + self.tick_price
                self.cover(price, abs(current_pos))
