"""
历史数据抓取API接口
支持前端调用抓取任务
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging
import asyncio
from pathlib import Path

router = APIRouter()
logger = logging.getLogger(__name__)

# 任务状态存储
_task_status = {}


class FetchTaskRequest(BaseModel):
    """抓取任务请求"""
    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    interval: int = Field(default=5, description="抓取间隔秒数", ge=1, le=60)
    headless: bool = Field(default=True, description="无头模式")


class FetchTaskResponse(BaseModel):
    """抓取任务响应"""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress: Optional[float] = None
    current_date: Optional[str] = None
    total_dates: Optional[int] = None
    success_dates: Optional[int] = None
    inserted: Optional[int] = None
    error: Optional[str] = None


def run_fetch_task(task_id: str, start_date: str, end_date: str, interval: int, headless: bool):
    """运行抓取任务（后台任务）"""
    try:
        _task_status[task_id] = {
            'status': 'running',
            'progress': 0.0,
            'current_date': '',
            'total_dates': 0,
            'success_dates': 0,
            'inserted': 0,
            'error': None,
            'started_at': datetime.now().isoformat()
        }

        # 导入抓取模块
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from services.fetch_history_enhanced import HistoryFetcher

        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 创建抓取器
        fetcher = HistoryFetcher(start_date, end_date, interval, headless)

        # 计算总日期数
        from datetime import datetime as dt, timedelta
        current = dt.strptime(start_date, '%Y-%m-%d')
        end = dt.strptime(end_date, '%Y-%m-%d')
        total_dates = 0
        while current <= end:
            if current.weekday() < 5:
                total_dates += 1
            current += timedelta(days=1)

        _task_status[task_id]['total_dates'] = total_dates

        # 运行抓取
        result = loop.run_until_complete(fetcher.run())

        # 更新状态
        _task_status[task_id]['status'] = 'completed' if result.get('success') else 'failed'
        _task_status[task_id]['progress'] = 1.0
        _task_status[task_id]['success_dates'] = result.get('success_dates', 0)
        _task_status[task_id]['inserted'] = result.get('inserted', 0)
        _task_status[task_id]['error'] = result.get('error')
        _task_status[task_id]['completed_at'] = datetime.now().isoformat()

        loop.close()

    except Exception as e:
        logger.error(f"[run_fetch_task] 任务失败 | task_id={task_id} | error={e}", exc_info=True)
        _task_status[task_id]['status'] = 'failed'
        _task_status[task_id]['error'] = str(e)
        _task_status[task_id]['completed_at'] = datetime.now().isoformat()


@router.post("/history/start", response_model=FetchTaskResponse)
async def start_fetch_task(request: FetchTaskRequest, background_tasks: BackgroundTasks):
    """
    启动历史数据抓取任务

    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - interval: 抓取间隔秒数 (1-60)
    - headless: 无头模式 (默认True)
    """
    logger.info(f"[start_fetch_task] 启动任务 | start={request.start_date} | end={request.end_date} | interval={request.interval}")

    # 生成任务ID
    task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 添加后台任务
    background_tasks.add_task(
        run_fetch_task,
        task_id,
        request.start_date,
        request.end_date,
        request.interval,
        request.headless
    )

    return FetchTaskResponse(
        task_id=task_id,
        status="started",
        message="抓取任务已启动，请使用task_id查询进度"
    )


@router.get("/history/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    查询抓取任务状态

    - task_id: 任务ID
    """
    if task_id not in _task_status:
        raise HTTPException(status_code=404, detail="任务不存在")

    status = _task_status[task_id]

    return TaskStatusResponse(
        task_id=task_id,
        status=status.get('status', 'unknown'),
        progress=status.get('progress'),
        current_date=status.get('current_date'),
        total_dates=status.get('total_dates'),
        success_dates=status.get('success_dates'),
        inserted=status.get('inserted'),
        error=status.get('error')
    )


@router.get("/history/tasks")
async def list_tasks():
    """列出所有抓取任务"""
    tasks = []
    for task_id, status in _task_status.items():
        tasks.append({
            'task_id': task_id,
            'status': status.get('status'),
            'progress': status.get('progress'),
            'total_dates': status.get('total_dates'),
            'success_dates': status.get('success_dates'),
            'inserted': status.get('inserted'),
            'started_at': status.get('started_at'),
            'completed_at': status.get('completed_at')
        })

    return {'tasks': tasks}


@router.post("/history/login")
async def manual_login():
    """
    启动手动登录模式

    打开浏览器等待用户手动登录，登录成功后保存Cookie
    """
    logger.info("[manual_login] 启动手动登录模式")

    task_id = f"login_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def run_login():
        try:
            _task_status[task_id] = {
                'status': 'running',
                'message': '等待用户登录...',
                'started_at': datetime.now().isoformat()
            }

            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))

            from services.fetch_history_enhanced import HistoryFetcher

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            fetcher = HistoryFetcher('2024-01-01', '2024-01-02')
            loop.run_until_complete(fetcher.init_browser())
            success = loop.run_until_complete(fetcher.manual_login())
            loop.run_until_complete(fetcher.close_browser())
            loop.close()

            _task_status[task_id]['status'] = 'completed' if success else 'failed'
            _task_status[task_id]['message'] = '登录成功' if success else '登录失败或超时'
            _task_status[task_id]['completed_at'] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"[manual_login] 登录失败 | error={e}", exc_info=True)
            _task_status[task_id]['status'] = 'failed'
            _task_status[task_id]['message'] = str(e)
            _task_status[task_id]['completed_at'] = datetime.now().isoformat()

    import asyncio
    asyncio.create_task(asyncio.to_thread(run_login))

    return {
        'task_id': task_id,
        'status': 'started',
        'message': '登录任务已启动，请在弹出的浏览器中完成登录'
    }


@router.post("/history/check")
async def check_completeness(start_date: str = None, end_date: str = None):
    """
    检查数据完整性

    - start_date: 开始日期 (YYYY-MM-DD)，默认从最早数据开始
    - end_date: 结束日期 (YYYY-MM-DD)，默认到今天
    """
    logger.info(f"[check_completeness] 检查完整性 | start={start_date} | end={end_date}")

    try:
        from services.price.yantai_db_service import YantaiDBService
        from datetime import datetime as dt, timedelta

        db_service = YantaiDBService()
        stats = db_service.get_stats()

        # 如果没有指定日期范围，使用数据库范围
        if not start_date and stats.get('date_range', {}).get('start'):
            start_date = stats['date_range']['start']
        if not end_date:
            end_date = dt.now().strftime('%Y-%m-%d')

        # 生成应该有的日期
        missing_dates = []
        incomplete_dates = []

        current = dt.strptime(start_date, '%Y-%m-%d') if start_date else dt.strptime(stats['date_range']['start'], '%Y-%m-%d')
        end = dt.strptime(end_date, '%Y-%m-%d')

        while current <= end:
            if current.weekday() < 5:  # 工作日
                date_str = current.strftime('%Y-%m-%d')
                count = db_service.get_latest(date_str, limit=1000).get('count', 0)

                if count == 0:
                    missing_dates.append(date_str)
                elif count < 22:  # AM和PM各11条
                    incomplete_dates.append({'date': date_str, 'count': count})

            current += timedelta(days=1)

        return {
            'success': True,
            'date_range': {'start': start_date, 'end': end_date},
            'total_workdays': len(missing_dates) + len(incomplete_dates),
            'missing_dates': missing_dates[:20],  # 只返回前20个
            'missing_count': len(missing_dates),
            'incomplete_dates': incomplete_dates[:20],
            'incomplete_count': len(incomplete_dates),
            'total_records': stats.get('total_count', 0)
        }

    except Exception as e:
        logger.error(f"[check_completeness] 检查失败 | error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/database-stats")
async def get_database_stats():
    """获取数据库统计信息"""
    try:
        from services.price.yantai_db_service import YantaiDBService

        db_service = YantaiDBService()
        stats = db_service.get_stats()

        return {
            'success': True,
            'total_count': stats.get('total_count', 0),
            'dates_count': stats.get('dates_count', 0),
            'date_range': stats.get('date_range', {}),
            'materials': stats.get('materials', {}),
            'specs': dict(list(stats.get('specs', {}).items())[:10])  # 只返回前10个
        }

    except Exception as e:
        logger.error(f"[get_database_stats] 获取统计失败 | error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
