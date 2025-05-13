import pandas as pd
import numpy as np
import logging

from vnpy_ctastrategy import *
from vnpy.trader.constant import Interval

from ctp.output import to_string
from ctp.settings import SETTINGS


class C53(CtaTemplate):
    _logger: logging.Logger = None

    # 策略参数
    fund = 10_000_000  # 初始资金
    risk_ratio = 0.04  # 风险资金比例
    atr_length = 26  # ATR计算周期
    ema_length = 240  # EMA计算周期
    cl_period = 20  # 高点/低点计算周期
    cd_period = 5  # 突破确认周期
    n_atr = 3.0  # ATR倍数（用于止损）
    stop_loss = 2.0  # 百分比止损（STL）

    # 策略变量
    contract_multiplier = 0  # 合约乘数
    entry_price = 0  # 开仓价格
    highest_price = 0  # 多头最高价格
    lowest_price = 0  # 空头最低价格
    atr_value = 0  # ATR值
    mas_value = 0  # EMA值
    upper_level = 0  # 上轨
    lower_level = 0  # 下轨
    trading_size = 0  # 交易数量

    parameters = [
        "fund", "risk_ratio", "atr_length", "ema_length",
        "cl_period", "cd_period", "n_atr", "stop_loss"
    ]

    variables = [
        "contract_multiplier", "entry_price", "highest_price",
        "lowest_price", "atr_value", "mas_value", "upper_level",
        "lower_level", "trading_size"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self._logger = SETTINGS["logger"]
        assert self._logger is not None

        # 创建K线合成器
        self.bg = BarGenerator(on_bar=self.on_bar, window=1, on_window_bar=None, interval=Interval.MINUTE, daily_end=None)
        # 创建时间序列管理器
        max_period = max(self.atr_length, self.ema_length, self.cl_period)
        self.am = ArrayManager(size=max_period * 2)

        # 获取合约信息
        self.contract_multiplier = self.get_size()
        if self.contract_multiplier <= 0:
            self._logger.warning(f"{self.strategy_name} 未找到 {self.vt_symbol} 的合约乘数,设置为默认值 1")
            self.contract_multiplier = 1

    def on_init(self):
        self._logger.info(f"策略初始化中: {self.strategy_name}")
        try:
            self.load_bar(days=7, interval=Interval.MINUTE, callback=self.on_bar)
        except Exception as e:
            self._logger.info(f"策略加载历史数据出错: {self.strategy_name} {e}")

        self._logger.info(f"策略加载历史数据完成 {self.strategy_name}")

    def on_start(self):
        self._logger.info(f"策略启动: {self.strategy_name}")

    def on_stop(self):
        self._logger.info(f"策略停止: {self.strategy_name}")
        self.cancel_all()

    def on_tick(self, tick: TickData):
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        if not self.am.inited:
            self._logger.debug(f"策略正在加载数据: {self.strategy_name}, {self.am.count}/{self.am.size}")
            return

        # 计算ATR
        self.atr_value = self.am.atr(self.atr_length)
        # 计算EMA
        self.mas_value = self.am.ema(self.ema_length, array=True)[-2]
        # 计算高点和低点
        self.upper_level = self.am.high[self.cl_period:].max()
        self.lower_level = self.am.low[self.cl_period:].min()
        # 计算交易数量
        last_price = bar.close_price
        fee_per_lot = 10  # 假设每手手续费为10元，需根据实际情况调整
        risk_capital = self.fund * self.risk_ratio
        self.trading_size = int(risk_capital / (last_price * self.contract_multiplier + fee_per_lot))
        # 策略逻辑
        current_pos = self.pos
        # 多头条件
        long_condition = bar.high_price >= self.upper_level > self.am.high[-2] and self.am.close[-2] > self.mas_value
        # 空头条件
        short_condition = bar.low_price <= self.lower_level < self.am.low[-2] and self.am.close[-2] < self.mas_value
        # 多头止损条件
        long_stop_condition = (bar.close_price <= (self.highest_price - self.n_atr * self.atr_value)) or \
                              (self.am.low[-2] < self.entry_price * (1 - self.stop_loss / 100))
        # 空头止损条件
        short_stop_condition = (bar.close_price >= (self.lowest_price + self.n_atr * self.atr_value)) or \
                               (self.am.high[-2] > self.entry_price * (1 + self.stop_loss / 100))
        # 执行交易逻辑
        if current_pos == 0:
            # 无仓位时
            if long_condition:
                self.buy(bar.close_price + 5, self.trading_size)  # 买入开仓
                self.entry_price = bar.close_price
                self.highest_price = bar.high_price
            elif short_condition:
                self.short(bar.close_price - 5, self.trading_size)  # 卖出开仓
                self.entry_price = bar.close_price
                self.lowest_price = bar.low_price

        elif current_pos > 0:
            # 多头持仓时
            self.highest_price = max(self.highest_price, bar.high_price)
            if long_stop_condition:
                self.sell(bar.close_price - 5, abs(current_pos))  # 卖出平仓
        elif current_pos < 0:
            # 空头持仓时
            self.lowest_price = min(self.lowest_price, bar.low_price)
            if short_stop_condition:
                self.cover(bar.close_price + 5, abs(current_pos))  # 买入平仓

    def on_order(self, order: OrderData):
        pass

    def on_trade(self, trade: TradeData):
        self._logger.info(f"策略交易: {self.strategy_name} {to_string(trade)}")

    def on_stop_order(self, stop_order: StopOrder):
        pass
