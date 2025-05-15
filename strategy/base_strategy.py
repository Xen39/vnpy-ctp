import logging

from abc import abstractmethod

from vnpy.trader.constant import Interval
from vnpy.trader.object import BarData, TickData, OrderData, TradeData
from vnpy.trader.utility import BarGenerator, ArrayManager
from vnpy_ctastrategy import CtaTemplate, StopOrder

from ctp.input import split_win_interval
from ctp.output import to_string
from ctp.settings import SETTINGS

class BaseStrategy(CtaTemplate):
    _logger: logging.Logger = None
    interval: str = "1m"
    bg: BarGenerator = None
    am: ArrayManager = None

    serialize_variables = dict()

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self._logger = SETTINGS["logger"]
        assert self._logger is not None

        if "interval" in setting:
            self.interval = setting["interval"]
        else:
            self._logger.warning(f"{self.strategy_name}: interval not found in setting, using default value 1m")

        self._logger.info(f"策略已创建: {self.strategy_name}")

    def on_init(self):
        self._logger.info(f"策略初始化中: {self.strategy_name}")
        self.bg = BarGenerator(on_bar=self.on_bar,
                               window=1,
                               on_window_bar=self.on_window_bar,
                               interval=Interval.MINUTE,
                               daily_end=None)

        assert self.num_init_bars() >= 0, "加载历史k线数必须 >= 0"
        self.am = ArrayManager(size=self.num_init_bars())

        try:
            window, interval = split_win_interval(self.interval)
            self.load_bar(days=10, interval=interval, callback=self.on_bar) # TODO: calculate days
            if self.am.inited:
                self._logger.info(f"策略加载历史数据完成: {self.strategy_name}")
            else:
                self._logger.error(f"策略加载历史数据不足,无法启动交易: {self.strategy_name}, k线数: {self.am.count}/{self.am.size}")
        except Exception as e:
            self._logger.error(f"策略加载历史数据出错: {self.strategy_name}, 错误:{e}")
            raise e

    def on_start(self):
        self._logger.info(f"策略启动: {self.strategy_name}")

    def on_stop(self):
        self._logger.info(f"策略停止: {self.strategy_name}, 取消所有订单")
        self.cancel_all()

    def on_order(self, order: OrderData) -> None:
        self._logger.info(f"策略订单状态改变: {self.strategy_name} - {to_string(order)}")

    def on_trade(self, trade: TradeData) -> None:
        self._logger.info(f"策略订单成交: {self.strategy_name} - {to_string(trade)}")

    def on_stop_order(self, stop_order: StopOrder) -> None:
        self._logger.error("on_stop_order(): Unexpected calling")

    def on_tick(self, tick: TickData) -> None:
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData) -> None:
        self.bg.update_bar(bar)

    @abstractmethod
    def on_window_bar(self, bar: BarData) -> None:
        raise RuntimeError(f"on_bar(): abstractmethod called in {self.__class__.__name__},"
                           f"please make sure you're using a derived class and overrides this function")

    @abstractmethod
    def num_init_bars(self) -> int:
        """加载历史数据需要的 k 线数量"""
        raise RuntimeError(f"num_init_bars(): abstractmethod called in {self.__class__.__name__},"
                           f"please make sure you're using a derived class and overrides this function")

    @property
    def margin_ratio(self):
        return 0.2  # TODO: Implement this

    @property
    def multiplier(self) -> int:
        if not hasattr(self, "_multiplier"):
            self._multiplier = super().get_size()
            if self._multiplier is None or self._multiplier <= 0:
                self._logger.warning(f"{self.strategy_name} 未找到 {self.vt_symbol} 的合约乘数,取默认值 1")
                self._multiplier = 1
        return self._multiplier

    @property
    def tick_price(self) -> float:
        if not hasattr(self, "_tick_price"):
            contract = self.cta_engine.main_engine.get_contract(self.vt_symbol)
            if contract and contract.pricetick and contract.pricetick > 0:
                self._tick_price = contract.pricetick
            else:
                self._logger.warning(f"{self.strategy_name} 未找到 {self.vt_symbol} 的最小变动价位,取默认值 1")
                self._tick_price = 1.0  # 默认返回1个最小变动单位
        return self._tick_price
