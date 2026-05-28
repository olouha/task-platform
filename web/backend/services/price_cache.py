"""
Excel 价格数据缓存服务
减少重复读取Excel文件的IO开销
"""

import os
import json
import time
import threading
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
from functools import lru_cache

logger = logging.getLogger(__name__)

# 缓存配置
CACHE_DIR = Path(__file__).parent / 'data' / 'cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 缓存有效期（秒）
PRICE_CACHE_TTL = 300  # 5分钟
SUMMARY_CACHE_TTL = 60   # 1分钟


class PriceCache:
    """
    价格数据缓存管理器

    使用内存缓存 + 文件备份，支持多线程访问
    """

    def __init__(self):
        self._memory_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._initialized = False

    def _get_cache_key(self, data_type: str, params: dict = None) -> str:
        """生成缓存键"""
        if params:
            param_str = json.dumps(params, sort_keys=True, default=str)
            return f"{data_type}:{hash(param_str)}"
        return data_type

    def get(self, data_type: str, params: dict = None) -> Optional[Any]:
        """
        获取缓存数据

        Args:
            data_type: 数据类型（如 'all_prices', 'latest', 'trend'）
            params: 查询参数

        Returns:
            缓存数据或None（缓存过期或不存在）
        """
        cache_key = self._get_cache_key(data_type, params)

        with self._lock:
            if cache_key not in self._memory_cache:
                logger.debug(f"[PriceCache] 缓存未命中 | key={cache_key}")
                return None

            # 检查是否过期
            timestamp = self._cache_timestamps.get(cache_key, 0)
            ttl = self._get_ttl(data_type)
            if time.time() - timestamp > ttl:
                logger.debug(f"[PriceCache] 缓存已过期 | key={cache_key}")
                del self._memory_cache[cache_key]
                del self._cache_timestamps[cache_key]
                return None

            logger.debug(f"[PriceCache] 缓存命中 | key={cache_key}")
            return self._memory_cache[cache_key]

    def set(self, data_type: str, data: Any, params: dict = None) -> None:
        """
        设置缓存数据

        Args:
            data_type: 数据类型
            data: 要缓存的数据
            params: 查询参数
        """
        cache_key = self._get_cache_key(data_type, params)

        with self._lock:
            self._memory_cache[cache_key] = data
            self._cache_timestamps[cache_key] = time.time()
            logger.debug(f"[PriceCache] 缓存已设置 | key={cache_key}, ttl={self._get_ttl(data_type)}s")

    def _get_ttl(self, data_type: str) -> int:
        """获取数据类型对应的TTL"""
        ttl_map = {
            'all_prices': PRICE_CACHE_TTL,
            'latest': PRICE_CACHE_TTL,
            'trend': PRICE_CACHE_TTL,
            'summary': SUMMARY_CACHE_TTL,
            'stats': SUMMARY_CACHE_TTL,
        }
        return ttl_map.get(data_type, PRICE_CACHE_TTL)

    def invalidate(self, data_type: str = None, params: dict = None) -> None:
        """
        使缓存失效

        Args:
            data_type: 数据类型（为None时清除所有）
            params: 查询参数
        """
        with self._lock:
            if data_type is None:
                self._memory_cache.clear()
                self._cache_timestamps.clear()
                logger.info("[PriceCache] 清除所有缓存")
            else:
                cache_key = self._get_cache_key(data_type, params)
                if cache_key in self._memory_cache:
                    del self._memory_cache[cache_key]
                    del self._cache_timestamps[cache_key]
                    logger.info(f"[PriceCache] 清除缓存 | key={cache_key}")

    def get_stats(self) -> Dict:
        """获取缓存统计"""
        with self._lock:
            total_count = len(self._memory_cache)
            expired_count = 0
            now = time.time()

            for key, timestamp in self._cache_timestamps.items():
                ttl = self._get_ttl(key.split(':')[0])
                if now - timestamp > ttl:
                    expired_count += 1

            return {
                'total_cached_items': total_count,
                'expired_items': expired_count,
                'active_items': total_count - expired_count,
                'memory_usage_mb': sum(
                    len(str(v)) for v in self._memory_cache.values()
                ) / (1024 * 1024)
            }


# 全局缓存实例
_price_cache: Optional[PriceCache] = None


def get_price_cache() -> PriceCache:
    """获取价格缓存实例（单例）"""
    global _price_cache
    if _price_cache is None:
        _price_cache = PriceCache()
    return _price_cache


# ========== 便捷缓存函数 ==========

def cache_all_prices(data: Dict) -> None:
    """缓存所有价格数据"""
    get_price_cache().set('all_prices', data)


def get_cached_all_prices() -> Optional[Dict]:
    """获取缓存的所有价格数据"""
    return get_price_cache().get('all_prices')


def cache_latest_prices(data: Dict, date: str = None) -> None:
    """缓存最新价格数据"""
    params = {'date': date} if date else None
    get_price_cache().set('latest', data, params)


def get_cached_latest_prices(date: str = None) -> Optional[Dict]:
    """获取缓存的最新价格数据"""
    params = {'date': date} if date else None
    return get_price_cache().get('latest', params)


def cache_trend_data(data: List, material: str = None, spec: str = None) -> None:
    """缓存趋势数据"""
    params = {'material': material, 'spec': spec}
    get_price_cache().set('trend', data, params)


def get_cached_trend_data(material: str = None, spec: str = None) -> Optional[List]:
    """获取缓存的趋势数据"""
    params = {'material': material, 'spec': spec}
    return get_price_cache().get('trend', params)


def invalidate_price_cache(data_type: str = None) -> None:
    """
    使价格缓存失效

    Args:
        data_type: 要清除的缓存类型（None=全部）
    """
    get_price_cache().invalidate(data_type)


# ========== 缓存装饰器 ==========

def cached(cache_key: str, ttl: int = PRICE_CACHE_TTL):
    """
    缓存装饰器

    Usage:
        @cached('my_data', ttl=300)
        def get_data():
            return heavy_computation()
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_price_cache()

            # 生成缓存键
            params = {'args': args, 'kwargs': kwargs}
            cached_data = cache.get(cache_key, params)

            if cached_data is not None:
                return cached_data

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, params)
            return result

        return wrapper
    return decorator


if __name__ == '__main__':
    # 测试
    print("测试价格缓存...")

    cache = get_price_cache()

    # 测试设置和获取
    cache.set('test', {'data': 'value'})
    result = cache.get('test')
    print(f"缓存测试: {result}")

    # 获取统计
    stats = cache.get_stats()
    print(f"缓存统计: {stats}")

    print("测试完成")