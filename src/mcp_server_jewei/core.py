# core.py
"""
核心模块，包含数据库连接和核心功能
"""

import json
from typing import Dict, List, Optional, Union, Any
from sqlalchemy import create_engine, text, MetaData, Table, Column
from sqlalchemy.exc import SQLAlchemyError

from .app_config import config

# 数据库连接管理
engine = None

def get_db_connection():
    """获取数据库连接，如果不存在则创建新连接"""
    global engine
    if engine is None:
        try:
            print("正在创建数据库连接...")
            print(f"连接到: {config.DB_HOST}:{config.DB_PORT}, 数据库: {config.DB_NAME}, 用户: {config.DB_USER}")
            print(f"连接字符串: {config.CONNECTION_STRING}")
            
            # 创建引擎时设置连接池选项
            engine = create_engine(
                config.CONNECTION_STRING,
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

def execute_query(sql: str) -> Dict[str, Any]:
    """执行SQL查询并返回结果集
    
    Args:
        sql: SQL查询语句（必须是SELECT语句）
        
    Returns:
        包含查询结果的字典
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
            
            # 转换结果为字典列表
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

def get_table_info(table_name: str, schema: str = "dbo") -> Dict[str, Any]:
    """获取指定表的结构信息
    
    Args:
        table_name: 表名
        schema: 架构名，默认为dbo
        
    Returns:
        包含表结构信息的字典
    """
    try:
        print(f"获取表结构信息: {schema}.{table_name}")
        engine = get_db_connection()
        
        # 查询列信息
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

        # 查询主键信息
        primary_keys_sql = f"""
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
        ORDER BY 
            ic.key_ordinal
        """

        # 查询外键信息
        foreign_keys_sql = f"""
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
        ORDER BY 
            fk.name, fc.constraint_column_id
        """

        # 查询索引信息
        indexes_sql = f"""
        SELECT
            i.name AS index_name,
            i.type_desc AS index_type,
            i.is_unique,
            i.is_primary_key,
            i.is_unique_constraint,
            STUFF((
                SELECT ', ' + c2.name
                FROM sys.index_columns ic2
                JOIN sys.columns c2 ON ic2.object_id = c2.object_id AND ic2.column_id = c2.column_id
                WHERE ic2.object_id = i.object_id AND ic2.index_id = i.index_id
                ORDER BY ic2.key_ordinal
                FOR XML PATH(''), TYPE
            ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') AS columns
        FROM
            sys.indexes i
        JOIN
            sys.tables t ON i.object_id = t.object_id
        JOIN
            sys.schemas s ON t.schema_id = s.schema_id
        WHERE
            t.name = '{table_name}' AND s.name = '{schema}'
        GROUP BY
            i.object_id, i.index_id, i.name, i.type_desc, i.is_unique, i.is_primary_key, i.is_unique_constraint
        ORDER BY
            i.name
        """

        # Execute and process columns_sql
        columns = []
        with engine.connect() as conn:
            columns_result = conn.execute(text(columns_sql))
            # 处理列信息
            for row in columns_result:
                column = {
                    "name": row.column_name,
                    "type": row.data_type,
                    "max_length": row.max_length,
                    "precision": row.precision,
                    "scale": row.scale,
                    "is_nullable": bool(row.is_nullable),
                    "description": row.description
                }
                columns.append(column)

        # Execute and process primary_keys_sql
        primary_keys = []
        with engine.connect() as conn:
            primary_keys_result = conn.execute(text(primary_keys_sql))
            # 处理主键信息
            primary_keys = [row.column_name for row in primary_keys_result]

        # Execute and process foreign_keys_sql
        foreign_keys = []
        with engine.connect() as conn:
            foreign_keys_result = conn.execute(text(foreign_keys_sql))
            # 处理外键信息
            for row in foreign_keys_result:
                fk = {
                    "name": row.fk_name,
                    "column": row.column_name,
                    "referenced_table": row.referenced_table,
                    "referenced_column": row.referenced_column
                }
                foreign_keys.append(fk)

        # Execute and process indexes_sql
        indexes = []
        with engine.connect() as conn:
            indexes_result = conn.execute(text(indexes_sql))
            # 处理索引信息
            for row in indexes_result:
                index = {
                    "name": row.index_name,
                    "type": row.index_type,
                    "is_unique": bool(row.is_unique),
                    "is_primary_key": bool(row.is_primary_key),
                    "is_unique_constraint": bool(row.is_unique_constraint),
                    "columns": row.columns.split(", ") if row.columns else []
                }
                indexes.append(index)

        return {
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "indexes": indexes
        }
    except Exception as e:
        error_msg = f"获取表结构失败: {str(e)}"
        print(error_msg)
        return {
            "error": str(e)
        }

def list_show_tables(schema: str = "dbo") -> Dict[str, Any]:
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