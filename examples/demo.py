# examples/demo.py
"""
示例脚本，展示如何使用mcp-server-qiwei包

此示例演示如何连接到MCP服务器并执行SQL查询和获取表结构信息
"""

from mcp import Client
import json

def main():
    # 连接到MCP服务器
    # 注意：实际使用时需要替换为真实的服务器地址
    client = Client("http://localhost:9000")
    
    print("连接到MCP服务器...")
    
    try:
        # 示例1：执行SQL查询
        print("\n示例1：执行SQL查询")
        query = "SELECT TOP 5 * FROM Users"
        print(f"执行查询: {query}")
        
        result = client.call("query_sql", sql=query)
        
        # 打印结果
        print(f"查询结果 ({result['row_count']} 行):")
        print(f"列名: {result['columns']}")
        for row in result['rows'][:3]:  # 只显示前3行
            print(row)
        
        # 示例2：获取表结构
        print("\n示例2：获取表结构")
        table_name = "Users"
        print(f"获取表结构: {table_name}")
        
        structure = client.call("get_table_structure", table_name=table_name)
        
        # 打印表结构信息
        print(f"表 {table_name} 的结构:")
        print(f"列数: {len(structure['columns'])}")
        print(f"主键: {structure['primary_keys']}")
        print(f"索引数: {len(structure['indexes'])}")
        print(f"外键数: {len(structure['foreign_keys'])}")
        
        # 显示前3个列的详细信息
        print("\n列信息 (前3个):")
        for column in structure['columns'][:3]:
            print(f"  - {column['name']}: {column['type']}")
            print(f"    可空: {column['is_nullable']}")
            if column['description']:
                print(f"    描述: {column['description']}")
    
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    main()