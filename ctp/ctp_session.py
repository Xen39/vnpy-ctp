__all__ = [
    "CtpSession"
]

import configparser
import datetime
import logging
import os
import sys
import time

from vnpy.event import EventEngine, Event
from vnpy.trader.event import *
from vnpy.trader.datafeed import get_datafeed, BaseDatafeed
from vnpy.trader.engine import MainEngine, OmsEngine
from vnpy.trader.object import CancelRequest, HistoryRequest, LogData, OrderRequest, SubscribeRequest
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.setting import SETTINGS
from vnpy_ctastrategy import CtaEngine, CtaStrategyApp
from vnpy_ctastrategy.base import EVENT_CTA_STRATEGY
from vnpy_ctp import CtpGateway

from .input import input_int
from .output import to_string

SETTINGS["log.active"] = True
SETTINGS["log.level"] = logging.DEBUG
SETTINGS["log.console"] = False


class CtpSession:
    event_engine: EventEngine
    main_engine: MainEngine
    oms_engine: OmsEngine
    cta_engine: CtaEngine
    ctp_gateway: CtpGateway
    conn_settings: dict
    _logger: logging.Logger

    def __init__(self):
        pass

    def _init_engines(self) -> None:
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        self.oms_engine = self.main_engine.add_engine(OmsEngine)
        self.cta_engine = self.main_engine.add_app(CtaStrategyApp)
        self.cta_engine.init_engine()

    def _register_events(self) -> None:
        self.event_engine.register(EVENT_TICK, self._on_tick)
        self.event_engine.register(EVENT_TRADE, self._on_trade)
        self.event_engine.register(EVENT_ORDER, self._on_order)
        self.event_engine.register(EVENT_ACCOUNT, self._on_account)
        self.event_engine.register(EVENT_POSITION, self._on_position)
        self.event_engine.register(EVENT_CTA_STRATEGY, self._on_strategy)
        self.event_engine.register(EVENT_LOG, self._on_log)

    def _init_logger(self, log_dir: str, file_level: int, console_level: int, encoding: str) -> None:
        log_filename = f"ctp-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.log.txt"
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), log_dir)
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)
        elif not os.path.isdir(log_dir):
            print(f"日志输出目录 {log_dir} 已存在且不为文件夹", file=sys.stderr)
            exit(0)

        log_filepath = os.path.join(log_dir, log_filename)

        self._logger = logging.getLogger(__name__)
        self.logger().setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)

        file_handler = logging.FileHandler(log_filepath, encoding=encoding)
        file_handler.setLevel(file_level)

        formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        self.logger().addHandler(console_handler)
        self.logger().addHandler(file_handler)

    def _on_tick(self, event: Event) -> None:
        self.logger().debug(f"[回调]行情: {to_string(event.data)}")

    def _on_trade(self, event: Event) -> None:
        self.logger().info(f"[回调]成交: {to_string(event.data)}")

    def _on_order(self, event: Event) -> None:
        self.logger().info(f"[回调]订单: {to_string(event.data)}")

    def _on_account(self, event: Event) -> None:
        self.logger().debug(f"[回调]账户: {to_string(event.data)}")

    def _on_position(self, event: Event) -> None:
        self.logger().debug(f"[回调]持仓: {to_string(event.data)}")

    def _on_strategy(self, event: Event) -> None:
        self.logger().info(f"[回调]策略: {to_string(event.data)}")

    def _on_log(self, event) -> None:
        data: LogData = event.data
        if data.level == logging.DEBUG:
            self.logger().debug(data.msg)
        elif data.level == logging.INFO:
            self.logger().info(data.msg)
        elif data.level == logging.WARNING:
            self.logger().warning(data.msg)
        elif data.level == logging.ERROR:
            self.logger().error(data.msg)
        elif data.level == logging.CRITICAL:
            self.logger().critical(data.msg)

    def read_config(self, ini_filepath: str = "config.ini") -> None:
        parser = configparser.ConfigParser()
        abs_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), ini_filepath)
        if not os.path.exists(abs_filepath):
            print(f"配置文件 {ini_filepath} 不存在!", file=sys.stderr)
            exit(0)
        parser.read(abs_filepath, encoding="utf-8")
        self.conn_settings = {item[0]: item[1] for item in parser.items("connection")}
        self._init_logger(log_dir=parser.get("log", "output_dir", fallback="../log"),
                          file_level=parser.getint("log", "file_level", fallback=logging.DEBUG),
                          console_level=parser.getint("log", "console_level", fallback=logging.INFO),
                          encoding=parser.get("log", "encoding", fallback="utf-8"))
        self.logger().info(f"读取配置文件: {abs_filepath}")
        # datafeed is a singleton and will be initialized while constructing self.cta_engine,
        # so _init_datafeed() must be called before _init_engines()
        if not parser.has_section("datafeed"):
            self.logger().warning("配置文件中未找到[datafeed]数据服务,无法提供历史行情")
        else:
            if not self._init_datafeed(platform=parser.get("datafeed", "platform", fallback=""),
                                       username=parser.get("datafeed", "username", fallback=""),
                                       password=parser.get("datafeed", "password", fallback="")):
                self.logger().error(f"datafeed 初始化失败!")
        self._init_engines()
        self._register_events()
        # load our own strategy
        strategy_dir = os.path.join(__file__, "../../strategy/")
        for strategy_filepath in os.listdir(strategy_dir):
            self.cta_engine.load_strategy_class_from_module(f"strategy.{strategy_filepath.rstrip('.py')}")

    def _init_datafeed(self, platform, username, password) -> bool:
        self.logger().info(f"加载数据服务[datafeed]: {username}@{platform}")
        supported_platforms = ("rqdata", "tqsdk", "tushare")
        if platform not in supported_platforms:
            self.logger().error(f"datafeed platform 暂不支持 {platform}, 目前仅支持 {supported_platforms}")
        SETTINGS["datafeed.name"] = platform
        SETTINGS["datafeed.username"] = username
        SETTINGS["datafeed.password"] = password

        datafeed = get_datafeed()
        assert datafeed.__class__ != BaseDatafeed
        if not self._test_datafeed():
            self.logger().error("datafeed 测试失败!")
            return False
        else:
            self.logger().info("datafeed 测试通过!")
            return True

    def _test_datafeed(self) -> bool:
        start_datetime = datetime.datetime(year=2025, month=4, day=1) # 2025-4-1
        end_datetime = start_datetime + datetime.timedelta(days=7) # 2025-4-8
        req = HistoryRequest("au2506", Exchange.SHFE, start_datetime, end_datetime, interval=Interval.DAILY)
        bar_datas = get_datafeed().query_bar_history(req=req, output=self.logger().debug)
        return bar_datas != []

    def logger(self):
        return self._logger

    def connect(self):
        self.ctp_gateway = self.main_engine.add_gateway(CtpGateway)
        self.logger().info(f"正在连接至CTP, 交易服务器 {self.conn_settings['交易服务器']}, 行情服务器 {self.conn_settings['行情服务器']}")
        self.main_engine.connect(self.conn_settings, "CTP")

    def get_all_contracts(self):
        return self.oms_engine.get_all_contracts()

    def get_all_contracts_pretty_str(self, step=5):
        contracts = self.get_all_contracts()
        pretty_str = ""
        for i in range(0, len(contracts), step):
            pretty_str += "| ".join(
                f"{f'{c.symbol}.{c.exchange.value}':20} {c.product.value:4}" for c in contracts[i:i + step])
            pretty_str += "\n"
        return pretty_str.strip()

    def send_order(self, req: OrderRequest):
        self.logger().info(f"[执行]下单:{vars(req)}")
        if not self.is_existed_vt_symbol(req.vt_symbol):
            self.logger().warning(f"合约{req.vt_symbol}不在交易列表中!")
        return self.main_engine.send_order(req, "CTP")

    def cancel_order(self, req: CancelRequest):
        self.logger().info(f"[执行]撤单:{vars(req)}")
        return self.main_engine.cancel_order(req, "CTP")

    def get_all_exchanges(self):
        result = self.main_engine.get_all_exchanges()
        self.logger().info(f"[执行]查询交易所: {to_string(result)}")
        return result

    def get_all_accounts(self):
        result = self.oms_engine.get_all_accounts()
        self.logger().info(f"[执行]查询账户: {to_string(result)}")
        return result

    def get_all_positions(self):
        result = self.oms_engine.get_all_positions()
        self.logger().info(f"[执行]查询持仓: {to_string(result)}")
        return result

    def get_tick(self, vt_symbol: str):
        result = self.oms_engine.get_tick(vt_symbol)
        self.logger().debug(f"[执行]查询合约: {vt_symbol}: {to_string(result)}")
        return result

    def close(self):
        if self.main_engine is not None:
            self.logger().info("关闭连接！")
            self.main_engine.close()

    def get_history_orders(self):
        result = self.oms_engine.get_all_orders()
        self.logger().info(f"[执行]查询历史订单: {to_string(result)}")
        return result

    def subscribe(self, symbol: str, exchange: Exchange):
        self.logger().info(f"[执行]订阅行情: {symbol}.{exchange.value}")
        return self.main_engine.subscribe(SubscribeRequest(symbol=symbol, exchange=exchange), "CTP")

    def is_existed_vt_symbol(self, vt_symbol: str) -> bool:
        return vt_symbol in {c.vt_symbol for c in self.get_all_contracts()}

    def input_strategy_class_name(self) -> str:
        vnpy_strategy_class_names = {
            "AtrRsiStrategy",
            "BollChannelStrategy",
            "DoubleMaStrategy",
            "DualThrustStrategy",
            "KingKeltnerStrategy",
            "MultiSignalStrategy",
            "MultiTimeframeStrategy",
            "TestStrategy",
            "TurtleSignalStrategy",
        }
        our_strategy_class_names = list(set(self.cta_engine.get_all_strategy_class_names()) - vnpy_strategy_class_names)
        our_strategy_class_names.sort()
        strategy_dict = {i: name for i, name in enumerate(our_strategy_class_names)}
        for i, strategy_class_name in strategy_dict.items():
            print(f"{i}: {strategy_class_name}")
        idx = input_int(0, len(strategy_dict) - 1)
        return strategy_dict[idx]

    def add_strategy(self, strategy_class_name: str, vt_symbols: str | list) -> None:
        if strategy_class_name not in self.cta_engine.get_all_strategy_class_names():
            self.logger().critical(
                f"目标策略 {strategy_class_name} 不在策略列表中:{self.cta_engine.get_all_strategy_class_names()}")
            return
        if not isinstance(vt_symbols, list):
            assert isinstance(vt_symbols, str)
            vt_symbols = [vt_symbols]
        strategy_names = []
        for vt_symbol in vt_symbols:
            strategy_name = f"{strategy_class_name}-{vt_symbol}"
            if not self.is_existed_vt_symbol(vt_symbol):
                self.logger().warning(f"合约 {vt_symbol} 不在交易列表中,跳过策略{strategy_name}")
                continue
            self.logger().info(f"[执行]添加策略 {strategy_name}")
            self.cta_engine.add_strategy(strategy_class_name, strategy_name, vt_symbol, {})
            self.cta_engine.init_strategy(strategy_name)
            strategy_names.append(strategy_name)
        time.sleep(3) # waiting for strategy initialization
        for strategy_name in strategy_names:
            self.cta_engine.start_strategy(strategy_name)

    def get_all_strategy_names(self) -> list[str]:
        return list(self.cta_engine.strategies.keys())

    def stop_strategy(self, strategy_names: list[str]):
        self.logger().info(f"[执行]停止策略:{strategy_names}")
        for strategy_name in strategy_names:
            if strategy_name not in self.cta_engine.strategies:
                self.logger().warning(f"目标停止策略{strategy_name}不存在!")
                return
            else:
                self.cta_engine.stop_strategy(strategy_name)
