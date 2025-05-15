import numpy as np
import logging

from vnpy_ctastrategy import *
from vnpy.trader.constant import Interval

from ctp.output import to_string
from ctp.settings import SETTINGS


class HaiYing6(CtaTemplate):
    _logger: logging.Logger = None

    # 策略参数
    fund = 10_000_000  # 初始资金
    risk_ratio = 0.04  # 风险资金比例
    atr_length = 26  # ATR计算周期
    len_period = 120  # 计算LEN的最大周期
    n_multiplier = 3.0  # ATR止损倍数
    fee_per_lot = 10  # 每手手续费

    # 策略变量
    contract_multiplier = 0  # 合约乘数
    entry_price = 0  # 开仓价格
    highest_price = 0  # 多头最高价格
    lowest_price = 0  # 空头最低价格
    atr_value = 0  # ATR值
    diff = 0  # MACD DIFF值
    dea = 0  # MACD DEA值
    macd = 0  # MACD柱状图值
    len_value = 0  # 金叉到死叉的K线数
    dd_k = 0  # 多空带鱼判断
    trading_size = 0  # 交易数量

    parameters = [
        "fund", "risk_ratio", "atr_length",
        "len_period", "n_multiplier", "fee_per_lot"
    ]

    variables = [
        "contract_multiplier", "entry_price", "highest_price",
        "lowest_price", "atr_value", "diff", "dea", "macd",
        "len_value", "dd_k", "trading_size"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self._logger = SETTINGS["logger"]
        assert self._logger is not None

        # 创建K线合成器
        self.bg = BarGenerator(on_bar=self.on_bar, window=1, on_window_bar=None, interval=Interval.MINUTE, daily_end=None)
        # 创建时间序列管理器
        self.am = ArrayManager(size=self.len_period * 2 + 10)
        self._logger.info(f"策略创建: {self.strategy_name}")
        # 获取合约信息
        self.contract_multiplier = self.get_size()
        if self.contract_multiplier <= 0:
            self._logger.warning(f"{self.strategy_name} 未找到 {self.vt_symbol} 的合约乘数,设置为默认值 1")
            self.contract_multiplier = 1

        # 初始化MACD相关变量
        self.last_golden_cross = -1  # 上次金叉位置
        self.last_golden_cross_value = 0
        self.last_death_cross = -1  # 上次死叉位置
        self.last_death_cross_value = 0
        self.last_ddai = -1  # 上次多带鱼位置
        self.last_kdai = -1  # 上次空带鱼位置

    def on_init(self):
        self._logger.info(f"策略初始化中: {self.strategy_name}")
        try:
            self.load_bar(days=7, interval=Interval.MINUTE, callback=self.on_bar)
            if self.am.count >= self.am.size:
                self._logger.info(f"策略加载历史数据完成 {self.strategy_name}")
            else:
                self._logger.warning(f"策略加载历史数据不足,无法开启 {self.strategy_name}")
        except Exception as e:
            self._logger.info(f"策略加载历史数据出错: {self.strategy_name} {e}")

    def on_start(self):
        self._logger.info(f"策略启动: {self.strategy_name}")

    def on_stop(self):
        self._logger.info(f"策略停止: {self.strategy_name}")

    def on_tick(self, tick: TickData):
        self.bg.update_tick(tick)

    def get_margin_ratio(self):
        return 0.2

    def llv(self, period: int, array: np.ndarray) -> np.ndarray:
        """计算指定周期内的最低价数组"""
        if len(array) < period:
            return np.full_like(array, np.nan)

        result = np.zeros_like(array)
        for i in range(len(array)):
            if i < period - 1:
                result[i] = np.nan  # 不足period周期时返回nan
            else:
                result[i] = np.min(array[i - period + 1:i + 1])
        return result

    def hhv(self, period: int, array: np.ndarray) -> np.ndarray:
        """计算指定周期内的最高价数组"""
        if len(array) < period:
            return np.full_like(array, np.nan)

        result = np.zeros_like(array)
        for i in range(len(array)):
            if i < period - 1:
                result[i] = np.nan  # 不足period周期时返回nan
            else:
                result[i] = np.max(array[i - period + 1:i + 1])
        return result

    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        if not self.am.inited:
            self._logger.debug(f"策略正在加载数据: {self.strategy_name}, {self.am.count}/{self.am.size}")
            return

        self.cancel_all()  # 取消所有未成交订单

        # 更新技术指标
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        # 计算ATR
        self.atr_value = self.am.atr(self.atr_length)

        # 计算MACD
        self.diff, self.dea, self.macd = self.am.macd(12, 26, 9, array=True)

        # 计算金叉死叉
        cross_up = self.diff[-2] <= self.dea[-2] and self.diff[-1] > self.dea[-1]  # 金叉
        cross_down = self.diff[-2] >= self.dea[-2] and self.diff[-1] < self.dea[-1]  # 死叉

        # 更新金叉死叉位置
        if cross_down:
            if bar.close_price > self.last_golden_cross_value:
                self.last_ddai = self.am.count
        if cross_up:
            if bar.close_price < self.last_death_cross_value:
                self.last_kdai = self.am.count

        # 计算LEN：金叉到死叉的K线数
        if cross_down and self.last_golden_cross > 0:
            self.len_value = self.last_death_cross - self.last_golden_cross

        # 计算带鱼条件
        if cross_down and bar.close_price > self.last_death_cross_value:
            self.last_ddai = self.am.count  # 多带鱼
        if cross_up and bar.close_price < self.last_death_cross_value:
            self.last_kdai = self.am.count  # 空带鱼

        # 计算DDK
        if self.last_ddai > 0 and self.last_kdai > 0:
            self.dd_k = 1 if self.last_ddai < self.last_kdai else -1

        # 计算交易数量
        margin_ratio = self.get_margin_ratio()  # 需实现获取保证金率
        risk_capital = self.fund * self.risk_ratio
        denominator = bar.close_price * self.contract_multiplier * margin_ratio + self.fee_per_lot
        self.trading_size = int(risk_capital / denominator)

        # 计算额外条件
        dbp = any(self.diff[i] == self.llv(120, self.diff)[i] for i in range(-3, 0))
        cmsp = any(self.diff[i] == self.hhv(120, self.diff)[i] for i in range(-3, 0))

        # 策略逻辑
        current_pos = self.pos

        # 开仓条件
        bky67 = cross_up and self.dd_k == 1  # 金叉且多带鱼次数大于空带鱼
        sky67 = cross_down and self.dd_k == -1  # 死叉且空带鱼次数大于多带鱼
        bkh15 = bar.close_price == self.am.high[-self.len_period:].max()  # 当前K线是N周期最高价
        skh15 = bar.close_price == self.am.low[-self.len_period:].min()  # 当前K线是N周期最低价

        # 平仓条件
        bpy67 = cross_up and self.dd_k == -1  # 金叉但空带鱼次数大于多带鱼
        spy67 = cross_down and self.dd_k == 1  # 死叉但多带鱼次数大于空带鱼
        sph15 = ((bar.low_price == self.am.low[-self.len_period + 5].min()) or cmsp) and \
                (bar.close_price < self.highest_price - self.atr_value * self.n_multiplier / 10)
        bph15 = ((bar.high_price == self.am.high[-self.len_period + 5].max()) or dbp) and \
                (bar.close_price > self.lowest_price + self.atr_value * self.n_multiplier / 10)

        # 执行交易逻辑
        if current_pos == 0:
            if bky67 or bkh15:
                self.buy(bar.close_price + 5, self.trading_size)
                self.entry_price = bar.close_price
                self.highest_price = bar.high_price
            elif sky67 or skh15:
                self.short(bar.close_price - 5, self.trading_size)
                self.entry_price = bar.close_price
                self.lowest_price = bar.low_price

        elif current_pos > 0:
            self.highest_price = max(self.highest_price, bar.high_price)
            if spy67 or sph15:
                self.sell(bar.close_price - 5, abs(current_pos))

        elif current_pos < 0:
            self.lowest_price = min(self.lowest_price, bar.low_price)
            if bpy67 or bph15:
                self.cover(bar.close_price + 5, abs(current_pos))

    def on_order(self, order: OrderData):
        pass

    def on_trade(self, trade: TradeData):
        self._logger.info(f"策略交易: {self.strategy_name} {to_string(trade)}")

    def on_stop_order(self, stop_order: StopOrder):
        pass
