"""
用户认证服务
支持从Excel加载初始账号、密码验证、同一账号多人同时在线
"""
import logging
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import hashlib
import secrets

logger = logging.getLogger(__name__)

# 内存中的在线用户会话（支持同一账号多人同时在线）
# 格式: {session_id: {account, login_time, last_active, expires_at}}
ONLINE_SESSIONS: Dict[str, Dict] = {}

# 管理员权限标识（权限字段含此串即为管理员）
ADMIN_PERMISSION_KEY = '所有权限都打开，可以增加账号和管理权限'

# 会话有效期（秒）——滑动续期：每次访问刷新，空闲超过此时长则过期
SESSION_TTL_SECONDS = 24 * 3600  # 24 小时


def _hash_password(password: str) -> str:
    """PBKDF2-SHA256 加盐哈希，返回 'pbkdf2$<iter>$<salt>$<hash>' 格式。"""
    salt = secrets.token_hex(16)
    iterations = 100000
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
    return f"pbkdf2${iterations}${salt}${dk.hex()}"


def _verify_hash(password: str, stored: str) -> bool:
    """校验密码是否匹配哈希串；stored 非 pbkdf2 格式返回 False（由调用方走明文兼容）。"""
    if not stored.startswith('pbkdf2$'):
        return False
    try:
        _, iters, salt, hash_hex = stored.split('$', 3)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), int(iters))
        return secrets.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


class UserService:
    """用户服务"""

    def __init__(self):
        self.users_df = self._load_users_from_excel()
        self._update_modified_time()

    def _load_users_from_excel(self) -> pd.DataFrame:
        """从Excel加载用户数据"""
        excel_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "services", "data", "账号权限配置表.xlsx"
        )

        if not os.path.exists(excel_path):
            logger.warning(f"[UserService] Excel文件不存在 | path={excel_path}")
            return pd.DataFrame(columns=['账号', '密码', '职位', '权限'])

        try:
            df = pd.read_excel(excel_path)
            # 确保密码列是字符串类型
            df['密码'] = df['密码'].astype(str)
            logger.info(f"[UserService] 加载用户数据 | count={len(df)}")
            return df
        except Exception as e:
            logger.error(f"[UserService] 读取Excel失败 | error={e}")
            return pd.DataFrame(columns=['账号', '密码', '职位', '权限'])

    def _update_modified_time(self):
        """记录数据加载时间"""
        self._data_modified_time = datetime.now()

    def get_user(self, account: str) -> Optional[Dict]:
        """根据账号获取用户信息"""
        user = self.users_df[self.users_df['账号'] == account]
        if user.empty:
            return None
        return {
            'account': user.iloc[0]['账号'],
            'position': user.iloc[0]['职位'],
            'permissions': user.iloc[0]['权限'],
            'is_admin': ADMIN_PERMISSION_KEY in str(user.iloc[0]['权限'])
        }

    def verify_password(self, account: str, password: str) -> bool:
        """验证账号密码（支持哈希与旧明文，明文命中后自动迁移为哈希）"""
        user = self.users_df[self.users_df['账号'] == account]
        if user.empty:
            logger.warning(f"[verify_password] 账号不存在 | account={account}")
            return False

        stored = str(user.iloc[0]['密码'])
        # 哈希格式：直接校验
        if stored.startswith('pbkdf2$'):
            if _verify_hash(password, stored):
                logger.info(f"[verify_password] 密码验证成功 | account={account}")
                return True
            logger.warning(f"[verify_password] 密码错误 | account={account}")
            return False
        # 旧明文数据：明文比对，成功后迁移为哈希
        if password == stored:
            self._migrate_password_to_hash(account, password)
            logger.info(f"[verify_password] 登录成功，明文密码已迁移为哈希 | account={account}")
            return True
        logger.warning(f"[verify_password] 密码错误 | account={account}")
        return False

    def _migrate_password_to_hash(self, account: str, password: str) -> None:
        """将旧明文密码迁移为哈希存储（首次登录时触发）。"""
        try:
            idx = self.users_df[self.users_df['账号'] == account].index[0]
            self.users_df.at[idx, '密码'] = _hash_password(password)
            self._save_to_excel()
        except Exception as e:
            logger.error(f"[_migrate_password_to_hash] 迁移失败 | account={account}, error={e}")

    def update_password(self, account: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        if not self.verify_password(account, old_password):
            return False

        try:
            idx = self.users_df[self.users_df['账号'] == account].index[0]
            # 转换为字符串并保存
            self.users_df.at[idx, '密码'] = _hash_password(new_password)
            self._save_to_excel()
            logger.info(f"[update_password] 密码修改成功 | account={account}")
            return True
        except Exception as e:
            logger.error(f"[update_password] 密码修改失败 | account={account}, error={e}")
            return False

    def get_all_users(self) -> List[Dict]:
        """获取所有用户（不含密码）"""
        return [
            {
                'account': row['账号'],
                'position': row['职位'],
                'permissions': row['权限'],
                'is_admin': ADMIN_PERMISSION_KEY in str(row['权限'])
            }
            for _, row in self.users_df.iterrows()
        ]

    def get_all_users_with_password(self) -> List[Dict]:
        """获取所有用户（含密码）"""
        return [
            {
                'account': str(row['账号']),
                'password': str(row['密码']),
                'position': str(row['职位']),
                'permissions': str(row['权限'])
            }
            for _, row in self.users_df.iterrows()
        ]

    def add_user(self, account: str, password: str, position: str, permissions: str) -> bool:
        """新增用户"""
        # 检查账号是否已存在
        if account in self.users_df['账号'].values:
            logger.warning(f"[add_user] 账号已存在 | account={account}")
            return False

        try:
            new_row = pd.DataFrame([{
                '账号': account,
                '密码': _hash_password(password),
                '职位': position,
                '权限': permissions
            }])
            self.users_df = pd.concat([self.users_df, new_row], ignore_index=True)
            self._save_to_excel()
            logger.info(f"[add_user] 新增用户成功 | account={account}")
            return True
        except Exception as e:
            logger.error(f"[add_user] 新增用户失败 | account={account}, error={e}")
            return False

    def delete_user(self, account: str) -> bool:
        """删除用户"""
        if account not in self.users_df['账号'].values:
            return False

        try:
            self.users_df = self.users_df[self.users_df['账号'] != account]
            self._save_to_excel()
            logger.info(f"[delete_user] 删除用户成功 | account={account}")
            return True
        except Exception as e:
            logger.error(f"[delete_user] 删除用户失败 | account={account}, error={e}")
            return False

    def admin_update_password(self, account: str, new_password: str) -> bool:
        """管理员修改用户密码"""
        if account not in self.users_df['账号'].values:
            return False

        try:
            idx = self.users_df[self.users_df['账号'] == account].index[0]
            self.users_df.at[idx, '密码'] = _hash_password(new_password)
            self._save_to_excel()
            logger.info(f"[admin_update_password] 管理员修改密码成功 | account={account}")
            return True
        except Exception as e:
            logger.error(f"[admin_update_password] 修改密码失败 | account={account}, error={e}")
            return False

    def _save_to_excel(self):
        """保存数据到Excel"""
        try:
            excel_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "services", "data", "账号权限配置表.xlsx"
            )
            self.users_df.to_excel(excel_path, index=False)
            self._update_modified_time()
        except Exception as e:
            logger.error(f"[_save_to_excel] 保存失败 | error={e}")


class SessionManager:
    """会话管理器 - 支持同一账号多人同时在线"""

    def __init__(self):
        self.sessions = ONLINE_SESSIONS

    def create_session(self, account: str) -> str:
        """创建新会话，返回session_id（含过期时间）"""
        session_id = secrets.token_urlsafe(32)
        now = datetime.now()
        self.sessions[session_id] = {
            'account': account,
            'login_time': now,
            'last_active': now,
            'expires_at': now + timedelta(seconds=SESSION_TTL_SECONDS),
        }
        logger.info(f"[create_session] 创建会话 | session_id={session_id[:8]}..., account={account}, online_count={len(self.get_user_sessions(account))}")
        return session_id

    def verify_session(self, session_id: str) -> Optional[str]:
        """验证会话有效性（含过期检查 + 滑动续期），返回账号"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        now = datetime.now()
        if now > session.get('expires_at', now):
            account = session.get('account')
            del self.sessions[session_id]
            logger.info(f"[verify_session] 会话已过期 | account={account}")
            return None

        session['last_active'] = now
        session['expires_at'] = now + timedelta(seconds=SESSION_TTL_SECONDS)  # 滑动续期
        return session['account']

    def remove_session(self, session_id: str) -> bool:
        """移除会话"""
        if session_id in self.sessions:
            account = self.sessions[session_id]['account']
            del self.sessions[session_id]
            logger.info(f"[remove_session] 移除会话 | session_id={session_id[:8]}..., account={account}, remaining={len(self.get_user_sessions(account))}")
            return True
        return False

    def get_user_sessions(self, account: str) -> List[str]:
        """获取用户的所有会话"""
        return [sid for sid, s in self.sessions.items() if s['account'] == account]

    def get_online_count(self, account: str) -> int:
        """获取用户在线人数"""
        return len(self.get_user_sessions(account))

    def get_all_online_count(self) -> int:
        """获取总在线人数"""
        return len(self.sessions)


# 全局单例
user_service = UserService()
session_manager = SessionManager()
