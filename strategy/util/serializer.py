import json

from dataclasses import dataclass
from vnpy_ctastrategy import CtaTemplate

from strategy.C53 import C53
from strategy.MACD import MACD
from strategy.simple_test import SimpleTest

class StrategyJsonSerializer:
    def __init__(self):
        raise Exception("StrategyJsonSerializer should not be instantiated")

    @staticmethod
    def to_dict(strategy: CtaTemplate):
        dct={
            "class_name": strategy.__class__.__name__,
            "vt_symbol": strategy.vt_symbol,
            "interval": strategy.interval if hasattr(strategy, "interval") else None,
            "position": strategy.pos,
        }
        return {strategy.strategy_name: dct}

    @staticmethod
    def from_dict(dct: dict) -> dict:
        assert len(dct) == 1
        strategy_name = list(dct.keys())[0]
        d: dict = dct[strategy_name]
        setting = dict()
        if "interval" in d:
            setting["interval"] = d["interval"]
        if "position" in d:
            setting["pos"] = d["position"]
        return {
            "class_name": d["class_name"],
            "strategy_name": strategy_name,
            "vt_symbol": d["vt_symbol"],
            "setting": setting,
        }