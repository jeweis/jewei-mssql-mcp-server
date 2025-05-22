# server.py
"""
MCP服务器主模块，提供SQL Server查询和表结构查询功能
"""

from typing import Dict, Any
from fastmcp import FastMCP

from typing import Dict, Any
from fastmcp import FastMCP
from sqlalchemy import text
from pydantic import Field

from .app_config import config
from .core import execute_query, get_table_info, get_db_connection

# 创建MCP服务器实例
mcp = FastMCP(name=config.SERVER_NAME)

@mcp.tool()
def query_sql(sql: str) -> Dict[str, Any]:
    """执行SQL查询并返回结果集（仅支持SELECT语句）
    
    Args:
        sql: SQL查询语句（必须是SELECT语句，）
        
    Returns:
        包含查询结果的字典，格式为：
        {
            "columns": [列名列表],
            "rows": [行数据列表],
            "row_count": 结果行数
        }
    """
    return execute_query(sql)

@mcp.tool()
def get_table_structure(table_name: str, schema: str = "dbo") -> Dict[str, Any]:
    """获取指定表的结构信息
    
    Args:
        table_name: 表名
        schema: 架构名，默认为dbo
        
    Returns:
        包含表结构信息的字典，格式为：
        {
            "columns": [列信息列表],
            "primary_keys": [主键列表],
            "foreign_keys": [外键信息列表],
            "indexes": [索引信息列表]
        }
    """
    return get_table_info(table_name, schema)

@mcp.tool()
def list_tables(schema: str = "dbo") -> Dict[str, Any]:
    """列出数据库中的所有表
    
    Args:
        schema: 架构名，默认为dbo
        
    Returns:
        包含表列表的字典
    """
    try:
        print(f"列出架构 '{schema}' 中的所有表")
        engine = get_db_connection()
        
        # 修改SQL查询，避免使用可能导致类型不兼容的字段
        # 使用CAST将可能有问题的字段转换为兼容的类型
        sql = f"""
        SELECT
            t.name AS table_name,
            CAST(ISNULL(CAST(ep.value AS NVARCHAR(MAX)), '') AS NVARCHAR(MAX)) AS description,
            s.name AS schema_name
        FROM
            sys.tables t
        JOIN
            sys.schemas s ON t.schema_id = s.schema_id
        LEFT JOIN
            sys.extended_properties ep ON t.object_id = ep.major_id AND ep.minor_id = 0 AND ep.name = 'MS_Description'
        WHERE
            s.name = '{schema}'
        ORDER BY
            t.name
        """
        
        # 如果上面的查询仍然不起作用，尝试使用更简单的查询
        simple_sql = f"""
        SELECT
            t.name AS table_name,
            s.name AS schema_name
        FROM
            sys.tables t
        JOIN
            sys.schemas s ON t.schema_id = s.schema_id
        WHERE
            s.name = '{schema}'
        ORDER BY
            t.name
        """
        
        try:
            with engine.connect() as conn:
                print("尝试执行带有表描述的查询...")
                result = conn.execute(text(sql))
                col_names = list(result.keys())
                tables = []
                for row in result:
                    try:
                        # 安全地将行转换为字典
                        row_dict = {}
                        for i, col in enumerate(col_names):
                            try:
                                # 尝试将每个值转换为字符串，避免类型问题
                                value = row[i]
                                if value is not None:
                                    row_dict[col] = str(value)
                                else:
                                    row_dict[col] = ""
                            except Exception as val_err:
                                print(f"处理列 {col} 的值时出错: {val_err}")
                                row_dict[col] = ""
                        tables.append(row_dict)
                    except Exception as e:
                        print(f"处理表信息时出错: {e}")
                        tables.append({"table_name": str(row[0]) if row and len(row) > 0 else "unknown"})
        except Exception as complex_query_error:
            print(f"复杂查询失败，尝试简单查询: {complex_query_error}")
            # 如果复杂查询失败，尝试简单查询
            with engine.connect() as conn:
                print("执行简化的表查询...")
                result = conn.execute(text(simple_sql))
                col_names = list(result.keys())
                tables = []
                for row in result:
                    try:
                        row_dict = {}
                        for i, col in enumerate(col_names):
                            try:
                                value = row[i]
                                row_dict[col] = str(value) if value is not None else ""
                            except:
                                row_dict[col] = ""
                        # 添加空的描述字段
                        if "description" not in row_dict:
                            row_dict["description"] = ""
                        tables.append(row_dict)
                    except Exception as e:
                        print(f"处理简化表信息时出错: {e}")
                        tables.append({"table_name": str(row[0]) if row and len(row) > 0 else "unknown"})
        
        print(f"成功获取 {len(tables)} 个表")
        return {
            "tables": tables,
            "count": len(tables)
        }
    except Exception as e:
        error_msg = f"列出表失败: {str(e)}"
        print(f"{error_msg}, 架构: {schema}")
        return {
            "error": str(e),
            "schema": schema
        }

@mcp.tool()
def get_database_info() -> Dict[str, Any]:
    """获取数据库基本信息
    
    Returns:
        包含数据库信息的字典
    """
    try:
        print("获取数据库基本信息")
        engine = get_db_connection()
        
        # 获取数据库版本信息
        version_sql = "SELECT @@VERSION AS version"
        # 获取数据库名称
        db_name_sql = "SELECT DB_NAME() AS database_name"
        # 获取架构信息
        schema_sql = "SELECT name AS schema_name FROM sys.schemas ORDER BY name"
        
        with engine.connect() as conn:
            # 获取版本信息
            version_result = conn.execute(text(version_sql)).fetchone()
            version_info = version_result[0] if version_result else None
            
            # 获取数据库名称
            db_name_result = conn.execute(text(db_name_sql)).fetchone()
            database_name = db_name_result[0] if db_name_result else None
            
            # 获取架构信息
            schema_result = conn.execute(text(schema_sql))
            schemas = [row[0] for row in schema_result]
        
        print(f"成功获取数据库信息: {database_name}")
        return {
            "database_name": database_name,
            "version": version_info,
            "schemas": schemas,
            "connection": {
                "host": config.DB_HOST,
                "port": config.DB_PORT,
                "database": config.DB_NAME,
                "user": config.DB_USER
            }
        }
    except Exception as e:
        error_msg = f"获取数据库信息失败: {str(e)}"
        print(error_msg)
        return {
            "error": str(e)
        }



@mcp.resource(
    uri="data://sql_describe",      # Explicit URI (required)
    name="sql语句编写规范",     # Custom name
    description="sql语句编写规范和说明（在编写sql语句前必看）", # Custom description
    mime_type="text/plain", # Explicit MIME type
    tags={"必看", "规范"} # Categorization tags
)
def sql_describe() -> str:
    """sql语句编写规范和说明（在编写sql语句前必看）"""
    ret = f'''
    1：SQL语句必须

'''
    return ret

@mcp.prompt(
    name="introduction",  # Custom prompt name
    description="当用户问好时",  # Custom description
    tags={"hello", "你好"}  # Optional categorization tags
)
def introduction_prompt(
    user_name: str = Field(description="用户姓名，非必填")
) -> str:
    """当用户问好时，需要生成的用户消息."""
    return f"用户名叫 '{user_name}' ，你需要友好的回复对方的问好，需要有Emoji表情，且要使用中文 ."

def main():
    """主函数，用于启动MCP服务器"""
    print("启动 MSSQL MCP 服务器...")
    # mcp.run()
    # To use a different transport, e.g., HTTP:
    mcp.run(transport="streamable-http", host="127.0.0.1", port=9000)

if __name__ == "__main__":
    main()