"""
敏感凭据加密存储模块
用于安全存储密码、API Key等敏感信息
"""

import os
import json
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = __import__('logging').getLogger(__name__)

# 密钥派生
def _derive_key(password: str, salt: bytes) -> bytes:
    """从密码派生加密密钥"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


class SecureStorage:
    """
    安全存储加密类

    使用 Fernet 对称加密存储敏感凭据
    密钥通过环境变量或机器特征派生
    """

    def __init__(self):
        self.storage_dir = Path(__file__).parent / 'data'
        self.storage_dir.mkdir(exist_ok=True)
        self.key_file = self.storage_dir / '.key'
        self.data_file = self.storage_dir / 'secrets.json'

    def _get_encryption_key(self) -> bytes:
        """获取加密密钥"""
        # 优先使用环境变量
        master_password = os.environ.get('TASKPLATFORM_MASTER_KEY')

        if not master_password:
            # 回退：使用机器特征 + 默认密码派生
            # 注意：这不如使用强密码安全，仅用于开发环境
            machine_id = os.environ.get('COMPUTERNAME', 'default') + os.environ.get('USERNAME', 'user')
            master_password = hashlib.sha256(machine_id.encode()).hexdigest()[:32]

        if not self.key_file.exists():
            # 生成盐值并保存
            salt = os.urandom(16)
            self.key_file.write_bytes(salt)
        else:
            salt = self.key_file.read_bytes()

        return _derive_key(master_password, salt)

    def _get_fernet(self) -> Fernet:
        """获取 Fernet 加密实例"""
        key = self._get_encryption_key()
        return Fernet(key)

    def save_secret(self, key: str, value: str) -> bool:
        """
        保存加密凭据

        Args:
            key: 凭据标识（如 'mysteel_password'）
            value: 凭据值（将加密存储）

        Returns:
            是否保存成功
        """
        try:
            logger.info(f"[save_secret] 保存凭据 | key={key}")

            # 加载现有数据
            secrets = self._load_all()

            # 加密值
            fernet = self._get_fernet()
            encrypted = fernet.encrypt(value.encode()).decode()

            secrets[key] = {
                'encrypted': encrypted,
                'type': 'fernet'
            }

            # 保存
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(secrets, f, ensure_ascii=False)

            logger.info(f"[save_secret] 保存成功 | key={key}")
            return True

        except Exception as e:
            logger.error(f"[save_secret] 保存失败 | key={key}, error={e}", exc_info=True)
            return False

    def get_secret(self, key: str) -> Optional[str]:
        """
        获取解密后的凭据

        Args:
            key: 凭据标识

        Returns:
            解密后的凭据值，失败返回 None
        """
        try:
            secrets = self._load_all()

            if key not in secrets:
                logger.warning(f"[get_secret] 凭据不存在 | key={key}")
                return None

            secret_data = secrets[key]
            encrypted = secret_data['encrypted']

            # 解密
            fernet = self._get_fernet()
            decrypted = fernet.decrypt(encrypted.encode()).decode()

            logger.info(f"[get_secret] 获取成功 | key={key}")
            return decrypted

        except Exception as e:
            logger.error(f"[get_secret] 获取失败 | key={key}, error={e}", exc_info=True)
            return None

    def delete_secret(self, key: str) -> bool:
        """删除凭据"""
        try:
            secrets = self._load_all()
            if key in secrets:
                del secrets[key]
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(secrets, f)
                logger.info(f"[delete_secret] 删除成功 | key={key}")
            return True
        except Exception as e:
            logger.error(f"[delete_secret] 删除失败 | key={key}, error={e}", exc_info=True)
            return False

    def _load_all(self) -> Dict:
        """加载所有凭据"""
        if self.data_file.exists():
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}


# 全局实例
_secrets_storage: Optional[SecureStorage] = None


def get_secrets_storage() -> SecureStorage:
    """获取凭据存储实例（单例）"""
    global _secrets_storage
    if _secrets_storage is None:
        _secrets_storage = SecureStorage()
    return _secrets_storage


# ========== 便捷方法 ==========

def save_credential(service: str, username: str, password: str) -> bool:
    """
    保存服务凭据

    Args:
        service: 服务名称（如 'mysteel'）
        username: 用户名
        password: 密码（将被加密存储）
    """
    storage = get_secrets_storage()
    username_key = f"{service}_username"
    password_key = f"{service}_password"

    storage.save_secret(username_key, username)
    storage.save_secret(password_key, password)

    return True


def get_credential(service: str) -> Optional[Dict[str, str]]:
    """
    获取服务凭据

    Args:
        service: 服务名称

    Returns:
        {'username': xxx, 'password': xxx} 或 None
    """
    storage = get_secrets_storage()
    username_key = f"{service}_username"
    password_key = f"{service}_password"

    username = storage.get_secret(username_key)
    password = storage.get_secret(password_key)

    if username and password:
        return {'username': username, 'password': password}
    return None


def save_api_key(service: str, api_key: str) -> bool:
    """保存 API Key"""
    storage = get_secrets_storage()
    key_name = f"{service}_api_key"
    return storage.save_secret(key_name, api_key)


def get_api_key(service: str) -> Optional[str]:
    """获取 API Key"""
    storage = get_secrets_storage()
    key_name = f"{service}_api_key"
    return storage.get_secret(key_name)


if __name__ == '__main__':
    # 测试
    print("测试加密存储...")

    # 保存凭据
    save_credential('mysteel', 'test_user', 'test_password123')

    # 读取凭据
    cred = get_credential('mysteel')
    print(f"读取结果: {cred}")

    # 删除
    storage = get_secrets_storage()
    storage.delete_secret('mysteel_username')
    storage.delete_secret('mysteel_password')

    print("测试完成")