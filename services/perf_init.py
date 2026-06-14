"""
性能优化启动器：gzip 压缩 + 请求计时 + 慢查询日志
"""
import time
import logging

_slow_logger = logging.getLogger('perf.slow')


def init_perf(app):
    """初始化性能优化（gzip + 计时）"""
    try:
        from flask_compress import Compress
        Compress(app)
    except Exception as e:
        app.logger.warning(f'[perf] Compress init failed: {e}')

    @app.before_request
    def _t0():
        from flask import g
        g._t_start = time.perf_counter()

    @app.after_request
    def _t1(resp):
        try:
            from flask import g, request
            dt = (time.perf_counter() - getattr(g, '_t_start', time.perf_counter())) * 1000
            # 慢请求 >500ms 写日志
            if dt > 500:
                _slow_logger.warning(
                    f'SLOW {request.method} {request.path} {int(dt)}ms status={resp.status_code}'
                )
            # 开发模式：响应头附带耗时
            if app.debug:
                resp.headers['X-Response-Time-ms'] = f'{dt:.1f}'
        except Exception:
            pass
        return resp
