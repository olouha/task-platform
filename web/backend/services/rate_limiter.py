"""
API 限流中间件
防止API被滥用
"""

import time
import threading
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps

from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    滑动窗口限流器

    支持：
    - 按IP限流
    - 按用户ID限流
    - 自定义限流阈值
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10
    ):
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self.burst = burst_size

        self._ip_requests: Dict[str, list] = defaultdict(list)
        self._user_requests: Dict[str, list] = defaultdict(list)
        self._lock = threading.RLock()

    def _clean_old_requests(self, requests_list: list, window_seconds: int) -> list:
        """清理过期的请求记录"""
        now = time.time()
        cutoff = now - window_seconds
        return [t for t in requests_list if t > cutoff]

    def _check_rate_limit(
        self,
        identifier: str,
        request_type: str = 'ip'
    ) -> Tuple[bool, str]:
        """
        检查是否超过限流阈值

        Returns:
            (是否允许, 原因信息)
        """
        requests_dict = self._user_requests if request_type == 'user' else self._ip_requests

        with self._lock:
            requests_list = requests_dict.get(identifier, [])

            # 清理过期请求
            requests_list = self._clean_old_requests(requests_list, 3600)
            requests_dict[identifier] = requests_list

            now = time.time()

            # 检查分钟级限制
            recent_requests = [t for t in requests_list if now - t < 60]
            if len(recent_requests) >= self.rpm:
                logger.warning(f"[RateLimiter] 分钟限流 | identifier={identifier[:20]}")
                return False, f"请求过于频繁，请稍后再试 (限制: {self.rpm}/分钟)"

            # 检查小时级限制
            if len(requests_list) >= self.rph:
                logger.warning(f"[RateLimiter] 小时限流 | identifier={identifier[:20]}")
                return False, f"请求超过限制，请稍后再试 (限制: {self.rph}/小时)"

            # 检查突发限制
            if len(recent_requests) >= self.burst:
                wait_time = 60 - (now - recent_requests[-self.burst])
                if wait_time > 0:
                    logger.warning(f"[RateLimiter] 突发限流 | identifier={identifier[:20]}, wait={wait_time:.1f}s")
                    return False, f"请求过于频繁，请等待 {wait_time:.1f} 秒"

            # 记录请求
            requests_list.append(now)
            requests_dict[identifier] = requests_list

            return True, "允许"

    def check_ip(self, ip: str) -> Tuple[bool, str]:
        """检查IP限流"""
        return self._check_rate_limit(ip, 'ip')

    def check_user(self, user_id: str) -> Tuple[bool, str]:
        """检查用户限流"""
        return self._check_rate_limit(user_id, 'user')

    def get_stats(self) -> Dict:
        """获取限流统计"""
        with self._lock:
            return {
                'tracked_ips': len(self._ip_requests),
                'tracked_users': len(self._user_requests),
                'rpm': self.rpm,
                'rph': self.rph
            }


# 全局限流器实例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取限流器实例（单例）"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_size=10
        )
    return _rate_limiter


# ========== FastAPI 中间件 ==========

async def rate_limit_middleware(request: Request, call_next):
    """限流中间件"""
    limiter = get_rate_limiter()

    # 获取客户端标识
    client_ip = request.client.host if request.client else 'unknown'

    # 检查IP限流
    allowed, message = limiter.check_ip(client_ip)
    if not allowed:
        logger.warning(f"[RateLimit] 拒绝请求 | ip={client_ip}, reason={message}")
        raise HTTPException(status_code=429, detail=message)

    response = await call_next(request)
    return response


# ========== 依赖注入 ==========

def rate_limit_dependency(request: Request):
    """
    FastAPI 依赖注入限流检查

    使用方式：
    @app.get("/api/endpoint")
    async def endpoint(request: Request, _: None = Depends(rate_limit_dependency)):
        ...
    """
    limiter = get_rate_limiter()
    client_ip = request.client.host if request.client else 'unknown'

    allowed, message = limiter.check_ip(client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=message)

    return True


# ========== 装饰器 ==========

def rate_limit(rpm: int = 60, rph: int = 1000):
    """
    限流装饰器

    Usage:
        @rate_limit(rpm=30, rph=500)
        async def my_endpoint():
            ...
    """
    limiter = RateLimiter(
        requests_per_minute=rpm,
        requests_per_hour=rph
    )

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 尝试从kwargs或request获取IP
            ip = 'default'
            for arg in args:
                if isinstance(arg, Request):
                    ip = arg.client.host if arg.client else 'unknown'
                    break

            allowed, message = limiter.check_ip(ip)
            if not allowed:
                raise HTTPException(status_code=429, detail=message)

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ========== 限流配置 ==========

# 不同API的限流配置
RATE_LIMIT_CONFIGS = {
    # 普通API
    'default': {'rpm': 60, 'rph': 1000, 'burst': 10},

    # 价格查询（可稍微放宽）
    'price_query': {'rpm': 120, 'rph': 2000, 'burst': 20},

    # 写操作（更严格）
    'write': {'rpm': 30, 'rph': 200, 'burst': 5},

    # 抓取操作（最严格）
    'fetch': {'rpm': 10, 'rph': 50, 'burst': 3},

    # AI对话（资源密集型）
    'ai_chat': {'rpm': 20, 'rph': 100, 'burst': 5},
}


def create_limiter_for_purpose(purpose: str) -> RateLimiter:
    """
    根据用途创建限流器

    Args:
        purpose: 用途标识，取值见 RATE_LIMIT_CONFIGS
    """
    config = RATE_LIMIT_CONFIGS.get(purpose, RATE_LIMIT_CONFIGS['default'])
    return RateLimiter(**config)


if __name__ == '__main__':
    # 测试
    print("测试限流器...")

    limiter = RateLimiter(requests_per_minute=5, requests_per_hour=20, burst_size=2)

    # 模拟5个请求
    for i in range(6):
        allowed, msg = limiter.check_ip('192.168.1.1')
        print(f"请求 {i+1}: {'通过' if allowed else '拒绝'} - {msg}")

    print("测试完成")