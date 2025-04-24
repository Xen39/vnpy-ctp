__all__ = [
    "CtpSession"
]

import datetime
import os
import logging
import configparser
from vnpy.event import EventEngine, Event
from vnpy.trader.event import *
from vnpy.trader.engine import MainEngine, OmsEngine
from vnpy.trader.object import *

from vnpy_ctp import CtpGateway


class CtpSession:
    event_engine: EventEngine
    main_engine: MainEngine
    oms_engine: OmsEngine
    conn_settings: dict
    _logger: logging.Logger

    def __init__(self):
        self._init_engines()
        self._register_events()

    def _init_engines(self) -> None:
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        self.oms_engine = self.main_engine.add_engine(OmsEngine)

    def _register_events(self) -> None:
        self.event_engine.register(EVENT_TICK, self._on_tick)
        self.event_engine.register(EVENT_TRADE, self._on_trade)
        self.event_engine.register(EVENT_ORDER, self._on_order)
        self.event_engine.register(EVENT_ACCOUNT, self._on_account)
        self.event_engine.register(EVENT_POSITION, self._on_position)

    def _on_tick(self, event: Event) -> None:
        self._logger.debug(f"切片行情: {event.data}")

    def _on_trade(self, event: Event) -> None:
        self._logger.info(f"已成交: {event.data}")

    def _on_order(self, event: Event) -> None:
        self._logger.info(f"已下单: {event.data}")

    def _on_account(self, event: Event) -> None:
        self._logger.debug(f"账户: {event.data}")

    def _on_position(self, event: Event) -> None:
        self._logger.debug(f"持仓: {event.data}")

    def read_config(self, ini_filepath: str = "config.ini") -> None:
        parser = configparser.ConfigParser()
        abs_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), ini_filepath)
        parser.read(abs_filepath, encoding="utf-8")
        self.conn_settings = {item[0]: item[1] for item in parser.items("connection")}
        self._init_logger(log_dir=parser.get("log", "output_dir"),
                          file_level=parser.getint("log", "file_level"),
                          console_level=parser.getint("log", "console_level"))
        self._logger.info(f"正在读取配置文件: {abs_filepath}")

    def _init_logger(self, log_dir: str, file_level: int = logging.DEBUG, console_level: int = logging.INFO) -> None:
        log_filename = f"ctp-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log.txt"
        log_filepath = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), log_dir), log_filename)

        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)

        file_handler = logging.FileHandler(log_filepath)
        file_handler.setLevel(file_level)

        formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)


        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)

    def connect(self):
        self.main_engine.add_gateway(CtpGateway)
        self._logger.info(
            f"正在连接至CTP, 交易服务器 {self.conn_settings['交易服务器']}, 行情服务器 {self.conn_settings['行情服务器']}")
        self.main_engine.connect(self.conn_settings, "CTP")

    def get_all_contracts(self):
        return self.oms_engine.get_all_contracts()

    def get_all_contracts_pretty_str(self, step=5):
        contracts = self.get_all_contracts()
        pretty_str = ""
        for i in range(0, len(contracts), step):
            pretty_str += "|| ".join(f"{c.symbol:15} {c.exchange.value:6}" for c in contracts[i:i+step])
            pretty_str += "\n"
        return pretty_str.strip()

    def send_order(self, req: OrderRequest):
        return self.main_engine.send_order(req, "CTP")

    def cancel_order(self, req: CancelRequest):
        return self.main_engine.cancel_order(req, "CTP")

    def get_all_exchanges(self):
        return self.main_engine.get_all_exchanges()

    def get_all_accounts(self):
        return self.oms_engine.get_all_accounts()

    def get_all_positions(self):
        return self.oms_engine.get_all_positions()

    def query_contract(self, symbol: str, exchange:Exchange):
        return self.oms_engine.get_tick(f"{symbol}.{exchange.value}")

    def close(self):
        return self.main_engine.close()

    def get_history_orders(self):
        return self.oms_engine.get_all_orders()