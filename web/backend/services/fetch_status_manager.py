"""
抓取状态管理模块
"""

import json
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict, field
from enum import Enum


class FetchStatus(str, Enum):
    """抓取状态"""
    PENDING = "pending"       # 待抓取
    RUNNING = "running"       # 抓取中
    SUCCESS = "success"       # 成功
    FAILED = "failed"         # 失败
    MANUAL_REQUIRED = "manual_required"  # 需要手动操作


@dataclass
class FetchRecord:
    """抓取记录"""
    id: str
    date: str              # 抓取日期
    period: str            # AM/PM
    status: FetchStatus    # 状态
    count: int = 0          # 数据条数
    timestamp: str = ""   # 时间戳
    error_message: str = ""  # 错误信息
    requires_manual: bool = False  # 是否需要手动操作
    hash: str = ""         # 数据哈希（用于去重）


class FetchStatusManager:
    """抓取状态管理器"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.status_file = data_dir / 'fetch_status.json'
        self.records: List[FetchRecord] = []
        self._load()

    def _load(self):
        """加载状态记录"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.records = [
                        FetchRecord(**r) for r in data.get('records', [])
                    ]
            except Exception as e:
                print(f'[WARN] 加载状态失败: {e}')

    def _save(self):
        """保存状态记录"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump({
                'records': [asdict(r) for r in self.records],
                'last_updated': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

    def add_record(self, record: FetchRecord):
        """添加记录"""
        self.records.append(record)
        self._save()

    def update_record(self, record_id: str, **kwargs):
        """更新记录"""
        for r in self.records:
            if r.id == record_id:
                for key, value in kwargs.items():
                    if hasattr(r, key):
                        setattr(r, key, value)
                self._save()
                return True
        return False

    def get_today_records(self, date_str: str = None) -> List[FetchRecord]:
        """获取指定日期的记录"""
        if date_str is None:
            date_str = date.today().isoformat()
        return [r for r in self.records if r.date == date_str]

    def get_latest_record(self) -> Optional[FetchRecord]:
        """获取最新记录"""
        if not self.records:
            return None
        return self.records[-1]

    def get_period_record(self, date_str: str, period: str) -> Optional[FetchRecord]:
        """获取指定日期时段的记录"""
        for r in self.records:
            if r.date == date_str and r.period == period:
                return r
        return None

    def is_fetched_today(self, date_str: str, period: str) -> bool:
        """检查今日该时段是否已成功抓取"""
        record = self.get_period_record(date_str, period)
        return record and record.status == FetchStatus.SUCCESS

    def check_manual_required(self, date_str: str = None) -> Dict[str, FetchStatus]:
        """检查哪些时段需要手动操作"""
        if date_str is None:
            date_str = date.today().isoformat()

        result = {}
        for period in ['AM', 'PM']:
            record = self.get_period_record(date_str, period)
            if record:
                result[period] = record.status
            else:
                # 没有记录 = 待抓取
                result[period] = FetchStatus.PENDING
        return result

    def should_auto_fetch(self) -> bool:
        """判断当前时间是否应该自动抓取"""
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute

        # 上午8-10点：AM时段
        if 8 <= current_hour < 10:
            date_str = date.today().isoformat()
            # 8点开始，9点后不再自动尝试
            if current_hour == 8 and current_minute < 30:
                return True
            if current_hour == 9:
                return False
            if current_hour == 8:
                return False
            return True

        # 下午4-6点：PM时段
        if 16 <= current_hour < 18:
            date_str = date.today().isoformat()
            # 4点开始，5点后不再自动尝试
            if current_hour == 16 and current_minute < 30:
                return True
            if current_hour == 17:
                return False
            return True

        return False

    def get_manual_required_dates(self, days: int = 3) -> List[str]:
        """获取最近需要手动操作的日期"""
        result = []
        today = date.today()

        for i in range(days):
            check_date = (today - datetime.timedelta(days=i)).isoformat()
            records = self.get_today_records(check_date)

            # 检查是否有需要手动操作的时段
            has_manual = False
            for r in records:
                if r.status == FetchStatus.MANUAL_REQUIRED:
                    has_manual = True
                    break
                elif r.status == FetchStatus.FAILED:
                    has_manual = True
                    break

            if has_manual or not records:
                result.append(check_date)

        return result

    def get_summary(self) -> Dict:
        """获取抓取汇总"""
        today_records = self.get_today_records()
        am_status = FetchStatus.PENDING
        pm_status = FetchStatus.PENDING

        for r in today_records:
            if r.period == 'AM':
                am_status = r.status
            elif r.period == 'PM':
                pm_status = r.status

        latest = self.get_latest_record()
        if latest:
            latest_time = latest.timestamp
        else:
            latest_time = None

        return {
            'today_date': date.today().isoformat(),
            'am_status': am_status.value,
            'pm_status': pm_status.value,
            'latest_time': latest_time,
            'manual_required': am_status == FetchStatus.MANUAL_REQUIRED or pm_status == FetchStatus.MANUAL_REQUIRED
        }

    def clear_old_records(self, days: int = 30):
        """清理旧记录"""
        cutoff_date = (date.today() - datetime.timedelta(days=days)).isoformat()
        self.records = [r for r in self.records if r.date >= cutoff_date]
        self._save()
        print(f'[INFO] 已清理{days}天前的记录')


# 全局实例
_status_manager = None


def get_status_manager() -> FetchStatusManager:
    """获取状态管理器实例"""
    global _status_manager
    if _status_manager is None:
        data_dir = Path(__file__).parent / 'data'
        data_dir.mkdir(exist_ok=True)
        _status_manager = FetchStatusManager(data_dir)
    return _status_manager