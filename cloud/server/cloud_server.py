"""
云端服务端
Flask API + SQLite/MySQL 数据库
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 数据库文件
DB_FILE = 'cloud_data.json'
os.makedirs('data', exist_ok=True)


def load_db():
    """加载数据库"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'tasks': [], 'logs': [], 'data': {}, 'config': {}}


def save_db(db):
    """保存数据库"""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


# ========== 任务 API ==========

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取所有任务"""
    db = load_db()
    return jsonify({'success': True, 'data': db['tasks']})


@app.route('/api/tasks', methods=['POST'])
def create_task():
    """创建任务"""
    data = request.json
    db = load_db()

    task = {
        'id': str(uuid.uuid4())[:8],
        'name': data.get('name', ''),
        'description': data.get('description', ''),
        'task_type': data.get('task_type', 'custom'),
        'cron_expr': data.get('cron_expr', ''),
        'interval_seconds': data.get('interval_seconds', 0),
        'enabled': data.get('enabled', True),
        'status': 'pending',
        'config': data.get('config', {}),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

    db['tasks'].append(task)
    save_db(db)

    return jsonify({'success': True, 'data': task})


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取单个任务"""
    db = load_db()
    task = next((t for t in db['tasks'] if t['id'] == task_id), None)

    if task:
        return jsonify({'success': True, 'data': task})
    return jsonify({'success': False, 'error': 'Task not found'}), 404


@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务"""
    data = request.json
    db = load_db()

    for task in db['tasks']:
        if task['id'] == task_id:
            task.update(data)
            task['updated_at'] = datetime.now().isoformat()
            save_db(db)
            return jsonify({'success': True, 'data': task})

    return jsonify({'success': False, 'error': 'Task not found'}), 404


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    db = load_db()
    db['tasks'] = [t for t in db['tasks'] if t['id'] != task_id]
    save_db(db)

    return jsonify({'success': True})


@app.route('/api/tasks/<task_id>/run', methods=['POST'])
def run_task(task_id):
    """立即执行任务"""
    db = load_db()
    task = next((t for t in db['tasks'] if t['id'] == task_id), None)

    if task:
        # 添加执行日志
        log = {
            'id': str(uuid.uuid4())[:8],
            'task_id': task_id,
            'status': 'running',
            'message': 'Task started',
            'executed_at': datetime.now().isoformat()
        }
        db['logs'].append(log)
        save_db(db)

        return jsonify({'success': True, 'data': log})

    return jsonify({'success': False, 'error': 'Task not found'}), 404


# ========== 日志 API ==========

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志"""
    db = load_db()
    task_id = request.args.get('task_id')

    if task_id:
        logs = [l for l in db['logs'] if l['task_id'] == task_id]
    else:
        logs = db['logs']

    return jsonify({'success': True, 'data': logs})


# ========== 数据存储 API ==========

@app.route('/api/data/<key>', methods=['GET'])
def get_data(key):
    """获取数据"""
    db = load_db()
    data = db['data'].get(key)

    if data:
        return jsonify({'success': True, 'data': data})
    return jsonify({'success': False, 'error': 'Data not found'}), 404


@app.route('/api/data/<key>', methods=['POST'])
def save_data(key):
    """保存数据"""
    data = request.json
    db = load_db()
    db['data'][key] = data
    save_db(db)

    return jsonify({'success': True})


# ========== 配置 API ==========

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    db = load_db()
    return jsonify({'success': True, 'data': db['config']})


@app.route('/api/config', methods=['POST'])
def save_config():
    """保存配置"""
    data = request.json
    db = load_db()
    db['config'].update(data)
    save_db(db)

    return jsonify({'success': True})


# ========== 系统 API ==========

@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})


@app.route('/api/stats', methods=['GET'])
def stats():
    """获取统计"""
    db = load_db()
    return jsonify({
        'success': True,
        'data': {
            'total_tasks': len(db['tasks']),
            'enabled_tasks': sum(1 for t in db['tasks'] if t.get('enabled')),
            'total_logs': len(db['logs']),
            'stored_data_keys': len(db['data'])
        }
    })


if __name__ == '__main__':
    print("=" * 50)
    print("TaskPlatform 云端服务")
    print("=" * 50)
    print("启动地址: http://localhost:5000")
    print("API 文档:")
    print("  GET    /api/tasks        - 获取任务")
    print("  POST   /api/tasks        - 创建任务")
    print("  GET    /api/tasks/<id>   - 获取任务详情")
    print("  PUT    /api/tasks/<id>   - 更新任务")
    print("  DELETE /api/tasks/<id>  - 删除任务")
    print("  POST   /api/tasks/<id>/run - 执行任务")
    print("  GET    /api/logs         - 获取日志")
    print("  GET    /api/stats        - 统计信息")
    print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=True)