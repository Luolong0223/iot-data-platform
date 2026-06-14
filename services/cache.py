"""
轻量级缓存服务
- 默认使用进程内 LRU 字典缓存（无需额外依赖）
- 如配置了 REDIS_URL 则使用 Redis
- 接口设计与 Redis 一致，方便未来切换
"""
import os
import time
import json
import hashlib
import threading
from functools import wraps
from typing import Any, Optional, Callable

# 尝试导入 redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class _MemoryCache:
    """进程内简单 LRU 缓存（带 TTL）"""
    def __init__(self, max_size: int = 1024):
        self._store: dict = {}
        self._lock = threading.RLock()
        self._max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            value, expire_at = item
            if expire_at and expire_at < time.time():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: int = 0) -> None:
        with self._lock:
            if len(self._store) >= self._max_size:
                # 简单驱逐：删最早插入的 10%
                for k in list(self._store.keys())[:max(1, self._max_size // 10)]:
                    self._store.pop(k, None)
            expire_at = time.time() + ttl if ttl else 0
            self._store[key] = (value, expire_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def delete_pattern(self, pattern: str) -> int:
        """删除匹配 pattern 的所有 key（支持 * 通配符）"""
        regex = pattern.replace('*', '.*')
        import re
        n = 0
        with self._lock:
            keys = [k for k in self._store.keys() if re.fullmatch(regex, k)]
            for k in keys:
                self._store.pop(k, None)
                n += 1
        return n

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        with self._lock:
            return {
                'backend': 'memory',
                'size': len(self._store),
                'max_size': self._max_size,
            }


class _RedisCache:
    """Redis 缓存后端"""
    def __init__(self, url: str):
        self._client = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key):
        v = self._client.get(key)
        if v is None:
            return None
        try:
            return json.loads(v)
        except (ValueError, TypeError):
            return v

    def set(self, key, value, ttl=0):
        v = json.dumps(value, ensure_ascii=False, default=str) if not isinstance(value, (str, int, float, bool)) else value
        if ttl:
            self._client.setex(key, ttl, v)
        else:
            self._client.set(key, v)

    def delete(self, key):
        self._client.delete(key)

    def delete_pattern(self, pattern):
        n = 0
        for k in self._client.scan_iter(match=pattern, count=200):
            self._client.delete(k)
            n += 1
        return n

    def clear(self):
        self._client.flushdb()

    def stats(self):
        return {'backend': 'redis', 'size': self._client.dbsize()}


# 选择后端
_backend: Optional[Any] = None
USE_REDIS = False


def init_cache(app=None) -> None:
    """初始化缓存后端（按环境变量决定）"""
    global _backend, USE_REDIS
    redis_url = os.getenv('REDIS_URL', '').strip()
    if redis_url and REDIS_AVAILABLE:
        try:
            _backend = _RedisCache(redis_url)
            _backend._client.ping()  # 探活
            USE_REDIS = True
            if app:
                app.logger.info(f'[Cache] Redis ready: {redis_url}')
        except Exception as e:
            if app:
                app.logger.warning(f'[Cache] Redis init failed: {e}; fall back to memory')
            _backend = _MemoryCache()
    else:
        _backend = _MemoryCache()
        if app:
            app.logger.info('[Cache] using in-memory LRU')


def get_cache():
    global _backend
    if _backend is None:
        init_cache()
    return _backend


def make_key(*parts) -> str:
    """生成缓存 key"""
    raw = ':'.join(str(p) for p in parts)
    return 'iot:' + hashlib.md5(raw.encode('utf-8')).hexdigest()[:24]


def cached(key_func: Callable, ttl: int = 60):
    """
    缓存装饰器
    key_func: 接收与被装饰函数相同的参数，返回字符串 key（或 None 表示不缓存）
    ttl: 过期时间（秒），0 表示永不过期
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                key = key_func(*args, **kwargs)
            except Exception:
                return f(*args, **kwargs)
            if not key:
                return f(*args, **kwargs)
            cache = get_cache()
            hit = cache.get(key)
            if hit is not None:
                return hit
            result = f(*args, **kwargs)
            try:
                cache.set(key, result, ttl=ttl)
            except Exception:
                pass
            return result
        return wrapper
    return decorator


def invalidate(pattern: str) -> int:
    """按 pattern 清除缓存（用于写后失效）"""
    return get_cache().delete_pattern(pattern)
