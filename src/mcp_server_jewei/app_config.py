# app_config.py
"""
配置模块，用于管理应用程序配置
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """配置类，用于管理应用程序配置"""
    
    # 数据库配置
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "sa")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "master")
    DB_PORT = os.getenv("DB_PORT", "1433")
    
    # 服务器配置
    SERVER_NAME = os.getenv("SERVER_NAME", "JEWEI-MSSQL-Server")
    
    # 连接字符串
    @property
    def CONNECTION_STRING(self):
        """构建数据库连接字符串"""
        return f"mssql+pyodbc://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?driver=SQL+Server&timeout=30&trusted_connection=no&encrypt=no"

# 创建默认配置实例
config = Config()