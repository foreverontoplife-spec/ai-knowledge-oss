"""转换器注册表：本目录下每个模块只要有 NAME / detect(filename, data) / convert(data) 就会被自动加载。"""
import importlib, pkgutil
REGISTRY = {}
for _m in pkgutil.iter_modules(__path__):
    if _m.name.startswith("_") or _m.name == "common": continue
    _mod = importlib.import_module(f"{__name__}.{_m.name}")
    if all(hasattr(_mod, a) for a in ("NAME", "detect", "convert")): REGISTRY[_mod.NAME] = _mod

def detect(filename, data):
    for name in ("deepseek", "claude", "grok"):  # 更具体的先判断
        if name in REGISTRY and REGISTRY[name].detect(filename, data): return name
    for name, mod in REGISTRY.items():
        if mod.detect(filename, data): return name
    return None
