# server.py
import os
import json
from typing import Dict, List, Optional, Union, Any
from fastmcp import FastMCP
from sqlalchemy import create_engine, text, MetaData, Table, Column
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from pydantic import Field

# 加载环境变量
load_dotenv()

# 数据库连接配置
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

# 构建连接字符串
# 添加额外的连接参数，如超时设置和信任连接
# 使用 ODBC 连接字符串格式
CONNECTION_STRING = f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?driver=SQL+Server&timeout=30&trusted_connection=no&encrypt=no"

# 如果上面的连接字符串不起作用，可以尝试下面的直接 ODBC 连接字符串
# CONNECTION_STRING = f"DRIVER={{SQL Server}};SERVER={DB_HOST},{DB_PORT};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD};Encrypt=no;TrustServerCertificate=yes;Connection Timeout=30;"

# 创建MCP服务器实例
mcp = FastMCP(name="XGJ-MSSQL-Server")

# 数据库连接管理
engine = None

def get_db_connection():
    """获取数据库连接，如果不存在则创建新连接"""
    global engine
    if engine is None:
        try:
            print("正在创建数据库连接...")
            print(f"连接到: {DB_HOST}:{DB_PORT}, 数据库: {DB_NAME}, 用户: {DB_USER}")
            print(f"连接字符串: {CONNECTION_STRING}")
            
            # 创建引擎时设置连接池选项
            engine = create_engine(
                CONNECTION_STRING,
                pool_pre_ping=True,  # 检查连接是否有效
                pool_recycle=3600,   # 每小时回收连接
                connect_args={
                    'timeout': 30     # 连接超时时间（秒）
                }
            )
            
            # 测试连接
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                print(f"测试连接结果: {result}")
                
            print("数据库连接创建成功")
        except SQLAlchemyError as e:
            error_msg = f"数据库连接失败: {str(e)}"
            print(error_msg)
            
            # 尝试获取更详细的错误信息
            if hasattr(e, 'orig') and e.orig:
                print(f"原始错误: {e.orig}")
                if hasattr(e.orig, 'args') and e.orig.args:
                    print(f"错误参数: {e.orig.args}")
            
            raise Exception(error_msg)
    return engine

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
    try:
        print(f"执行SQL查询: {sql[:100]}{'...' if len(sql) > 100 else ''}")
        # 安全检查：确保只执行SELECT语句
        sql_lower = sql.lower().strip()
        if not sql_lower.startswith("select"):
            error_msg = "安全限制：只允许执行SELECT语句"
            print(f"{error_msg}, SQL: {sql}")
            return {
                "error": error_msg,
                "sql": sql
            }
            
        # 检查是否包含危险操作
        dangerous_keywords = ["insert", "update", "delete", "drop", "alter", "create", "truncate", "exec", "execute"]
        for keyword in dangerous_keywords:
            if f" {keyword} " in f" {sql_lower} ":
                error_msg = f"安全限制：查询中包含禁止的关键字 '{keyword}'"
                print(f"{error_msg}, SQL: {sql}")
                return {
                    "error": error_msg,
                    "sql": sql
                }
        
        engine = get_db_connection()
        
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            # 获取列名
            columns = list(result.keys())
            
            # 转换结果为字典列表，使用安全的方式
            result_rows = []
            for row in result:
                try:
                    # 尝试使用字典推导式创建字典
                    row_dict = {col: row[i] for i, col in enumerate(columns)}
                    result_rows.append(row_dict)
                except Exception as row_err:
                    print(f"处理行数据时出错: {row_err}")
                    # 如果出错，尝试使用其他方式
                    try:
                        # 尝试直接将行转换为字典
                        row_dict = {}
                        for i, col in enumerate(columns):
                            try:
                                row_dict[col] = row[i]
                            except:
                                row_dict[col] = None
                        result_rows.append(row_dict)
                    except Exception as e:
                        print(f"处理行数据的备选方法也失败: {e}")
                        # 最后的备选方案，只添加原始值
                        result_rows.append({"value": str(row)})
        
        print(f"查询成功，返回 {len(result_rows)} 条记录")
        return {
            "columns": columns,
            "rows": result_rows,
            "row_count": len(result_rows)
        }
    except Exception as e:
        error_msg = f"查询执行失败: {str(e)}"
        print(f"{error_msg}, SQL: {sql}")
        return {
            "error": str(e),
            "sql": sql
        }

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
    try:
        print(f"获取表结构信息: {schema}.{table_name}")
        engine = get_db_connection()
        
        # 查询列信息，使用CAST避免类型不兼容问题
        columns_sql = f"""
        SELECT 
            c.name AS column_name,
            t.name AS data_type,
            c.max_length,
            c.precision,
            c.scale,
            c.is_nullable,
            CAST(ISNULL(CAST(ep.value AS NVARCHAR(MAX)), '') AS NVARCHAR(MAX)) AS description
        FROM 
            sys.columns c
        JOIN 
            sys.types t ON c.user_type_id = t.user_type_id
        JOIN 
            sys.tables tb ON c.object_id = tb.object_id
        JOIN 
            sys.schemas s ON tb.schema_id = s.schema_id
        LEFT JOIN 
            sys.extended_properties ep ON c.object_id = ep.major_id AND c.column_id = ep.minor_id AND ep.name = 'MS_Description'
        WHERE 
            tb.name = '{table_name}' AND s.name = '{schema}'
        ORDER BY 
            c.column_id
        """
        
        # 简化版列信息查询，不包含描述字段
        simple_columns_sql = f"""
        SELECT 
            c.name AS column_name,
            t.name AS data_type,
            c.max_length,
            c.precision,
            c.scale,
            c.is_nullable
        FROM 
            sys.columns c
        JOIN 
            sys.types t ON c.user_type_id = t.user_type_id
        JOIN 
            sys.tables tb ON c.object_id = tb.object_id
        JOIN 
            sys.schemas s ON tb.schema_id = s.schema_id
        WHERE 
            tb.name = '{table_name}' AND s.name = '{schema}'
        ORDER BY 
            c.column_id
        """
        
        try:
            with engine.connect() as conn:
                print("尝试执行带有列描述的查询...")
                columns_result = conn.execute(text(columns_sql))
                col_names = list(columns_result.keys())
                columns = []
                for row in columns_result:
                    try:
                        # 安全地将行转换为字典
                        row_dict = {}
                        for i, col in enumerate(col_names):
                            try:
                                # 将所有值转换为字符串，避免类型问题
                                value = row[i]
                                if value is not None:
                                    row_dict[col] = str(value)
                                else:
                                    row_dict[col] = ""
                            except Exception as val_err:
                                print(f"处理列 {col} 的值时出错: {val_err}")
                                row_dict[col] = ""
                        columns.append(row_dict)
                    except Exception as e:
                        print(f"处理列信息时出错: {e}")
                        # 如果出错，使用备选方案
                        try:
                            columns.append({"column_name": str(row[0]) if row and len(row) > 0 else "unknown"})
                        except:
                            columns.append({"column_name": "unknown"})
                print(f"获取到 {len(columns)} 个列信息")
        except Exception as complex_query_error:
            print(f"复杂列查询失败，尝试简化查询: {complex_query_error}")
            # 如果复杂查询失败，尝试简化查询
            with engine.connect() as conn:
                print("执行简化的列查询...")
                columns_result = conn.execute(text(simple_columns_sql))
                col_names = list(columns_result.keys())
                columns = []
                for row in columns_result:
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
                        columns.append(row_dict)
                    except Exception as e:
                        print(f"处理简化列信息时出错: {e}")
                        columns.append({"column_name": str(row[0]) if row and len(row) > 0 else "unknown"})
                print(f"获取到 {len(columns)} 个列信息")
        
        # 查询主键信息
        pk_sql = f"""
        SELECT 
            c.name AS column_name
        FROM 
            sys.indexes i
        JOIN 
            sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        JOIN 
            sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        JOIN 
            sys.tables t ON i.object_id = t.object_id
        JOIN 
            sys.schemas s ON t.schema_id = s.schema_id
        WHERE 
            i.is_primary_key = 1 AND t.name = '{table_name}' AND s.name = '{schema}'
        """
        
        with engine.connect() as conn:
            pk_result = conn.execute(text(pk_sql))
            primary_keys = []
            for row in pk_result:
                try:
                    # 安全地将行转换为字典
                    col_names = list(pk_result.keys())
                    row_dict = {}
                    for i, col in enumerate(col_names):
                        try:
                            value = row[i]
                            row_dict[col] = str(value) if value is not None else ""
                        except:
                            row_dict[col] = ""
                    primary_keys.append(row_dict)
                except Exception as e:
                    print(f"处理主键信息时出错: {e}")
                    primary_keys.append({"column_name": str(row[0]) if row and len(row) > 0 else "unknown"})
        print(f"获取到 {len(primary_keys)} 个主键信息")
        
        # 查询外键信息
        fk_sql = f"""
        SELECT 
            fk.name AS fk_name,
            COL_NAME(fc.parent_object_id, fc.parent_column_id) AS column_name,
            OBJECT_NAME(fc.referenced_object_id) AS referenced_table,
            COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS referenced_column
        FROM 
            sys.foreign_keys fk
        JOIN 
            sys.foreign_key_columns fc ON fk.object_id = fc.constraint_object_id
        JOIN 
            sys.tables t ON fk.parent_object_id = t.object_id
        JOIN 
            sys.schemas s ON t.schema_id = s.schema_id
        WHERE 
            t.name = '{table_name}' AND s.name = '{schema}'
        """
        
        with engine.connect() as conn:
            fk_result = conn.execute(text(fk_sql))
            foreign_keys = []
            for row in fk_result:
                try:
                    # 安全地将行转换为字典
                    col_names = list(fk_result.keys())
                    row_dict = {}
                    for i, col in enumerate(col_names):
                        try:
                            value = row[i]
                            row_dict[col] = str(value) if value is not None else ""
                        except:
                            row_dict[col] = ""
                    foreign_keys.append(row_dict)
                except Exception as e:
                    print(f"处理外键信息时出错: {e}")
                    foreign_keys.append({"fk_name": str(row[0]) if row and len(row) > 0 else "unknown"})
        print(f"获取到 {len(foreign_keys)} 个外键信息")
        
        # 查询索引信息
        index_sql = f"""
        SELECT 
            i.name AS index_name,
            i.type_desc AS index_type,
            i.is_unique,
            STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
        FROM 
            sys.indexes i
        JOIN 
            sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        JOIN 
            sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        JOIN 
            sys.tables t ON i.object_id = t.object_id
        JOIN 
            sys.schemas s ON t.schema_id = s.schema_id
        WHERE 
            t.name = '{table_name}' AND s.name = '{schema}' AND i.is_primary_key = 0
        GROUP BY
            i.name, i.type_desc, i.is_unique
        """
        
        with engine.connect() as conn:
            idx_result = conn.execute(text(index_sql))
            indexes = []
            for row in idx_result:
                try:
                    # 安全地将行转换为字典
                    col_names = list(idx_result.keys())
                    row_dict = {}
                    for i, col in enumerate(col_names):
                        try:
                            value = row[i]
                            row_dict[col] = str(value) if value is not None else ""
                        except:
                            row_dict[col] = ""
                    indexes.append(row_dict)
                except Exception as e:
                    print(f"处理索引信息时出错: {e}")
                    indexes.append({"index_name": str(row[0]) if row and len(row) > 0 else "unknown"})
        print(f"获取到 {len(indexes)} 个索引信息")
        
        print(f"表结构信息获取成功: {schema}.{table_name}")
        return {
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "indexes": indexes
        }
    except Exception as e:
        error_msg = f"获取表结构失败: {str(e)}"
        print(f"{error_msg}, 表: {schema}.{table_name}")
        return {
            "error": str(e),
            "table": table_name,
            "schema": schema
        }

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
                "host": DB_HOST,
                "port": DB_PORT,
                "database": DB_NAME,
                "user": DB_USER
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
    1：SQL语句必须为Microsoft SQL Server 2016支持的语句
    '''
    return ret



@mcp.prompt(
    name="introduction",          # Custom prompt name
    description="当用户问好时",  # Custom description
    tags={"hello", "你好"}             # Optional categorization tags
)
def introduction_prompt(
    user_name: str = Field(description="用户姓名，非必填") 
) -> str:
    """当用户问好时，需要生成的用户消息."""
    return f"用户名叫 '{user_name}' ，你需要友好的回复对方的问好，需要有Emoji表情，且要使用中文 ."



if __name__ == "__main__":
    # 运行服务器，默认使用STDIO传输
    mcp.run()
    
    # 使用HTTP传输的示例：
    # mcp.run(transport="streamable-http", host="127.0.0.1", port=9000)