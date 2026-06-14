"""
告警引擎 v2 - 高级能力
- 去重（deduplication）：相同指纹的告警在窗口期内只产生一条
- 抑制（suppression）：高等级告警触发时抑制同源低等级告警
- 静默（silence）：按时间段或规则静默
- 升级（escalation）：超时未处理自动升级严重度
- 分组（grouping）：按时间窗/标签合并相似告警
"""
import time
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy import and_, or_, func

from models.database import db, AlarmRecord, AlarmRule, User


# ---------- 去重 / 分组 内存索引 ----------
class _DedupIndex:
    """告警指纹去重索引"""
    def __init__(self, window_sec: int = 60):
        self.window_sec = window_sec
        self._index: Dict[str, datetime] = {}
        self._lock = threading.RLock()

    def fingerprint(self, user_id: int, rule_id: Optional[int],
                    device_name: str, point_name: str) -> str:
        raw = f'{user_id}:{rule_id}:{device_name}:{point_name}'
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def should_emit(self, fp: str) -> bool:
        """返回 True 表示可以发出（不在去重窗口内）"""
        with self._lock:
            now = datetime.utcnow()
            last = self._index.get(fp)
            if last and (now - last).total_seconds() < self.window_sec:
                return False
            self._index[fp] = now
            return True

    def cleanup(self):
        """清除过期指纹"""
        with self._lock:
            cutoff = datetime.utcnow() - timedelta(seconds=self.window_sec * 5)
            self._index = {k: v for k, v in self._index.items() if v > cutoff}


# ---------- 静默规则 ----------
class SilenceRule:
    """静默规则（内存实现，可持久化到 DB）"""
    def __init__(self):
        self._rules: List[dict] = []
        self._lock = threading.RLock()

    def add(self, matchers: dict, starts_at: datetime, ends_at: datetime, creator: str = 'system'):
        with self._lock:
            self._rules.append({
                'matchers': matchers,  # {'device': 'xxx', 'severity': 'warning'} 任意子集匹配
                'starts_at': starts_at,
                'ends_at': ends_at,
                'creator': creator,
                'created_at': datetime.utcnow(),
            })

    def is_silenced(self, alarm: dict) -> bool:
        with self._lock:
            now = datetime.utcnow()
            for r in self._rules:
                if not (r['starts_at'] <= now <= r['ends_at']):
                    continue
                matchers = r['matchers']
                ok = True
                for k, v in matchers.items():
                    if alarm.get(k) != v:
                        ok = False
                        break
                if ok:
                    return True
            return False

    def list(self) -> list:
        with self._lock:
            return [
                {**r, 'starts_at': r['starts_at'].isoformat(), 'ends_at': r['ends_at'].isoformat(),
                 'created_at': r['created_at'].isoformat()}
                for r in self._rules
            ]


# ---------- 引擎 ----------
class AlarmEngine:
    """告警引擎 v2 - 整合去重/抑制/静默/分组/升级"""

    def __init__(self):
        self.dedup = _DedupIndex(window_sec=60)
        self.silences = SilenceRule()
        self._suppress_lock = threading.RLock()

    # ---- 核心入口：创建告警（带去重/抑制/静默）----
    def create_alarm(self, user_id: int, rule_id: Optional[int],
                     device_name: str, channel_name: str, point_name: str,
                     value: float, threshold: float, condition: str,
                     severity: str = 'warning', message: str = '') -> Optional[AlarmRecord]:
        """
        创建一条告警，自动应用去重/抑制/静默逻辑。
        返回 AlarmRecord 或 None（被抑制/静默/重复）。
        """
        # 1) 静默检查
        candidate = {
            'user_id': user_id, 'rule_id': rule_id,
            'device_name': device_name, 'point_name': point_name,
            'severity': severity
        }
        if self.silences.is_silenced(candidate):
            return None

        # 2) 去重
        fp = self.dedup.fingerprint(user_id, rule_id, device_name, point_name)
        if not self.dedup.should_emit(fp):
            return None

        # 3) 抑制：检查近 5 分钟内同源是否已有更高严重等级告警
        if self._has_higher_active(user_id, rule_id, device_name, point_name, severity):
            return None

        # 4) 持久化
        alarm = AlarmRecord(
            user_id=user_id, rule_id=rule_id,
            device_name=device_name, channel_name=channel_name, point_name=point_name,
            value=value, threshold=threshold, condition=condition,
            severity=severity, message=message or self._format_message(
                device_name, point_name, value, condition, threshold, severity
            )
        )
        db.session.add(alarm)
        db.session.commit()
        return alarm

    def _has_higher_active(self, user_id, rule_id, device_name, point_name, current_sev) -> bool:
        ranks = {'info': 1, 'warning': 2, 'critical': 3, 'emergency': 4}
        cur_rank = ranks.get(current_sev, 0)
        with self._suppress_lock:
            cutoff = datetime.utcnow() - timedelta(minutes=5)
            rows = AlarmRecord.query.filter(
                AlarmRecord.user_id == user_id,
                AlarmRecord.device_name == device_name,
                AlarmRecord.point_name == point_name,
                AlarmRecord.is_handled == False,
                AlarmRecord.created_at >= cutoff
            ).all()
            for r in rows:
                if ranks.get(r.severity, 0) > cur_rank:
                    return True
        return False

    @staticmethod
    def _format_message(device, point, value, condition, threshold, severity):
        return f'[{severity.upper()}] {device}.{point} = {value} {condition} {threshold}'

    # ---- 静默管理 ----
    def add_silence(self, matchers, minutes, creator='admin'):
        now = datetime.utcnow()
        self.silences.add(matchers, now, now + timedelta(minutes=minutes), creator=creator)
        return self.silences.list()

    def list_silences(self):
        return self.silences.list()

    def clear_silences(self):
        self.silences = SilenceRule()
        return []

    # ---- 升级（escalation）：将超时未处理告警自动升级 ----
    def escalate_overdue(self, minutes: int = 30) -> int:
        """将 N 分钟前仍未处理的 critical 以下告警升级一级"""
        ranks = {'info': 1, 'warning': 2, 'critical': 3, 'emergency': 4}
        labels = {1: 'info', 2: 'warning', 3: 'critical', 4: 'emergency'}
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        n = 0
        records = AlarmRecord.query.filter(
            AlarmRecord.is_handled == False,
            AlarmRecord.severity.in_(['info', 'warning', 'critical']),
            AlarmRecord.created_at <= cutoff
        ).all()
        for r in records:
            cur = ranks.get(r.severity, 1)
            if cur < 4:
                r.severity = labels[cur + 1]
                r.message = f'[ESCALATED] {r.message}'
                n += 1
        db.session.commit()
        return n

    # ---- 统计：按 severity / device 分组 ----
    def statistics(self, user_id: Optional[int] = None) -> dict:
        q = AlarmRecord.query
        if user_id is not None:
            q = q.filter(AlarmRecord.user_id == user_id)
        by_sev = dict(db.session.query(AlarmRecord.severity, func.count(AlarmRecord.id))
                      .group_by(AlarmRecord.severity).all())
        by_device = dict(db.session.query(AlarmRecord.device_name, func.count(AlarmRecord.id))
                         .group_by(AlarmRecord.device_name).order_by(func.count(AlarmRecord.id).desc())
                         .limit(10).all())
        total = q.count()
        unhandled = q.filter(AlarmRecord.is_handled == False).count()
        return {
            'total': total,
            'unhandled': unhandled,
            'by_severity': {k: int(v) for k, v in by_sev.items()},
            'top_devices': [{'device': k, 'count': int(v)} for k, v in by_device.items()],
        }

    # ---- 告警分组：按 (device, point, severity) 合并未处理告警，返回分组视图 ----
    def grouped_unhandled(self, user_id: Optional[int] = None, limit: int = 50) -> list:
        q = db.session.query(
            AlarmRecord.device_name, AlarmRecord.point_name, AlarmRecord.severity,
            func.count(AlarmRecord.id).label('cnt'),
            func.max(AlarmRecord.created_at).label('last_at'),
        ).filter(AlarmRecord.is_handled == False)
        if user_id is not None:
            q = q.filter(AlarmRecord.user_id == user_id)
        rows = q.group_by(
            AlarmRecord.device_name, AlarmRecord.point_name, AlarmRecord.severity
        ).order_by(func.max(AlarmRecord.created_at).desc()).limit(limit).all()
        return [
            {'device': r.device_name, 'point': r.point_name, 'severity': r.severity,
             'count': int(r.cnt), 'last_at': r.last_at.isoformat() if r.last_at else None}
            for r in rows
        ]


# 单例
_engine: Optional[AlarmEngine] = None
_engine_lock = threading.Lock()


def get_engine() -> AlarmEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AlarmEngine()
        return _engine
