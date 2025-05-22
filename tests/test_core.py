# tests/test_core.py
import unittest
import os
import sys

# 添加源代码目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mcp_server_jewei import __version__

class TestCore(unittest.TestCase):
    """基本测试类"""
    
    def test_version(self):
        """测试版本号是否正确"""
        self.assertTrue(__version__)
        
    def test_import(self):
        """测试是否可以正确导入模块"""
        try:
            from src.mcp_server_jewei import server
            self.assertTrue(True)
        except ImportError:
            self.fail("导入模块失败")

if __name__ == "__main__":
    unittest.main()