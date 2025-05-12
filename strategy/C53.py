import pandas as pd
import logging

from vnpy_ctastrategy import *
from vnpy.trader.constant import Interval

from ctp.output import to_string
from ctp.settings import SETTINGS

class C53(CtaTemplate):

    _logger: logging.Logger = None

    # 策略参数
    short_param = 26
    long = 240
    # buy = False
    # sell = False
    CL = 35
    CD = 0
    STL = 5
    N = 6
    interval = None

    # 策略变量
    only_sell: bool = False
    only_buy: bool = False
    dataFrame = None
    close = None
    TR = None  # 真实波幅
    ATR = None  # 平均真实波幅
    MAS = None  # 240周期的指数移动平均
    UPPERC = None  # 周期性最高价
    LOWERC = None  # 周期性最低价
    bkhigh = float('-inf')  # 记录每个品种的最高价
    sklow = float('inf')  # 记录每个品种的最低价
    price = 0  # 记录开仓价格
    position = 0 # 仓位

    parameters = ["short_param", "long", "CL", "CD", "STL", "N", "interval"]
    variables = ["only_buy", "only_sell", "dataFrame", "close", "TR", "ATR", "MAS", "UPPERC", "LOWERC", "bkhigh", "sklow", "price"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self._logger = SETTINGS["logger"]
        assert self._logger is not None

        # 创建K线合成器
        self.bg = BarGenerator(on_bar=self.on_bar, window=1, on_window_bar=None, interval=Interval.MINUTE, daily_end=None)
        # 创建时间序列管理器
        self.am = ArrayManager(size=max(self.long, self.CL) + 10)
        self._logger.info(f"策略创建: {self.strategy_name}")

    def on_init(self):
        """策略初始化回调"""
        self._logger.info(f"策略初始化中: {self.strategy_name}")
        try:
            self.load_bar(days=7, interval=Interval.MINUTE, callback=self.on_bar)
        except Exception as e:
            self._logger.info(f"策略加载历史数据出错: {self.strategy_name} {e}")
        if self.pos != 0:
            # 获取当前价格
            if self.pos > 0:
                self.bkhigh = self.price
            else:
                self.sklow = self.price
        self.position = self.pos
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
        if not self.am.inited:
            self._logger.debug(f"策略正在加载数据: {self.strategy_name}, {self.am.count}/{self.am.size}")
            return

        self.close = pd.Series(self.am.close)
        self.high = pd.Series(self.am.high)
        self.low = pd.Series(self.am.low)

        # 计算真实波幅TR
        close_shift = self.close.shift(1)
        tr1 = self.high - self.low
        tr2 = abs(self.high - close_shift)
        tr3 = abs(self.low - close_shift)
        self.TR = tr1.combine(tr2, max).combine(tr3, max)

        # 计算平均真实波幅ATR
        self.ATR = self.TR.rolling(window=self.short_param).mean()

        # 计算MAS (240周期的指数移动平均)
        self.MAS = self.close.ewm(span=self.long, adjust=False).mean()

        # 计算周期性最高价和最低
        self.UPPERC = self.high.rolling(window=self.CL).max()
        self.LOWERC = self.low.rolling(window=self.CL).min()

        if not self.trading:
            return

        # 做多做空指标计算
        DUO = (self.high.iloc[-1] >= self.UPPERC.iloc[-self.CD - 2]) & \
              (self.high.iloc[-2] < self.UPPERC.iloc[-self.CD - 2]) & \
              (self.close.iloc[-2] > self.MAS.iloc[-2])

        KONG = (self.low.iloc[-1] <= self.LOWERC.iloc[-self.CD - 2]) & \
               (self.low.iloc[-2] > self.LOWERC.iloc[-self.CD - 2]) & \
               (self.close.iloc[-2] < self.MAS.iloc[-2])
        print(self.strategy_name, DUO, KONG)
        # 平仓指标计算
        DUO_STOP = False
        DUO_STOP1 = False
        KONG_STOP = False
        KONG_STOP1 = False

        if self.position > 0:
            self.bkhigh = max(self.bkhigh, self.high.iloc[-1])
            DUO_STOP = self.close.iloc[-1] <= (self.bkhigh - self.N * self.ATR.iloc[-1])
            DUO_STOP1 = self.low.iloc[-2] < self.price * (1 - 0.01 * self.STL)
        elif self.position < 0:
            self.sklow = min(self.sklow, self.low.iloc[-1])
            KONG_STOP = self.close.iloc[-1] >= (self.sklow + self.N * self.ATR.iloc[-1])
            KONG_STOP1 = self.high.iloc[-2] > self.price * (1 + 0.01 * self.STL)
        else:  # 空仓时重置
            self.bkhigh = float('-inf')
            self.sklow = float('inf')
            self.price = 0

        # 短上穿长 做多
        if self.only_sell is False and DUO:
            if self.position <= 0:
                self._logger.info(f"{self.strategy_name} 做多")
                order = self.buy(bar.close_price, self.position)
                self.position = self.pos
                self.bkhigh = self.high.iloc[-1]
                self.price = self.close.iloc[-1]

        # 短下穿长 做空
        elif self.only_buy is False and KONG:
            if self.position >= 0:
                self._logger.info(f"{self.strategy_name} 做空")
                order = self.short(bar.close_price, self.position)
                self.position = -self.pos
                self.sklow = self.low.iloc[-1]
                self.price = self.close.iloc[-1]

        if self.position > 0 and DUO_STOP or DUO_STOP1:
            self.sell(bar.close_price, self.position)
            self.position = 0

        elif self.position < 0 and KONG_STOP or KONG_STOP1:
            self.cover(bar.close_price, self.position)
            self.position = 0

        if self.position > 0:
            self.sell(bar.close_price, self.position)
        elif self.position < 0:
            self.cover(bar.close_price, self.position)
        self.position = 0

    def on_order(self, order: OrderData):
        """委托更新回调"""
        pass

    def on_trade(self, trade: TradeData):
        """成交更新回调"""
        self._logger.info(f"策略交易: {self.strategy_name} {to_string(trade)}")

    def on_stop_order(self, stop_order: StopOrder):
        """停止单更新回调"""
        pass
