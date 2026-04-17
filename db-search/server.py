#!/usr/bin/env python3
import os
import json
import asyncio
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from mcp.types import ServerCapabilities, ToolsCapability

# ---------- 数据库类型判断 ----------
DB_TYPE = os.getenv("DB_TYPE", "mysql").lower()  # mysql, postgres, oracle, db2

# 读取通用连接参数（不同数据库可能使用不同的字段名）
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "")          # MySQL/PostgreSQL/DB2 的数据库名
DB_SERVICE = os.getenv("DB_SERVICE", "")    # Oracle 的 service_name

# 可选：Oracle 的 SID (如果未提供 service_name)
DB_SID = os.getenv("DB_SID", "")

# 将端口转为 int（如果提供）
if DB_PORT:
    DB_PORT = int(DB_PORT)

# ---------- 创建 MCP 服务器 ----------
server = Server(f"db-search-{DB_TYPE}")

def get_db_connection():
    """根据 DB_TYPE 返回对应的数据库连接对象"""
    if DB_TYPE == "mysql":
        import pymysql
        from pymysql.cursors import DictCursor
        return pymysql.connect(
            host=DB_HOST, port=DB_PORT or 3306, user=DB_USER,
            password=DB_PASSWORD, database=DB_NAME,
            cursorclass=DictCursor, autocommit=True
        )
    elif DB_TYPE == "postgres":
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT or 5432, user=DB_USER,
            password=DB_PASSWORD, dbname=DB_NAME
        )
        conn.autocommit = True
        return conn
    elif DB_TYPE == "oracle":
        import oracledb
        # 构建 DSN
        if DB_SERVICE:
            dsn = oracledb.makedsn(DB_HOST, DB_PORT or 1521, service_name=DB_SERVICE)
        elif DB_SID:
            dsn = oracledb.makedsn(DB_HOST, DB_PORT or 1521, sid=DB_SID)
        else:
            raise ValueError("Oracle 需要 DB_SERVICE 或 DB_SID")
        conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)
        return conn
    elif DB_TYPE == "db2":
        import ibm_db_dbi
        conn_str = (
            f"DATABASE={DB_NAME};"
            f"HOSTNAME={DB_HOST};"
            f"PORT={DB_PORT or 50000};"
            f"PROTOCOL=TCPIP;"
            f"UID={DB_USER};"
            f"PWD={DB_PASSWORD};"
        )
        ibm_conn = ibm_db_dbi.connect(conn_str, "", "")
        return ibm_conn
    else:
        raise ValueError(f"不支持的数据库类型: {DB_TYPE}")

def execute_query(conn, sql: str) -> List[Dict]:
    """执行查询并返回字典列表"""
    cursor = conn.cursor()
    cursor.execute(sql)
    # 判断是否有结果集
    if cursor.description:
        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    else:
        rows = []
    cursor.close()
    return rows

# ---------- MCP 工具 ----------
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="query",
            description=f"在 {DB_TYPE.upper()} 数据库上执行只读 SQL 查询。",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "要执行的 SQL 语句，例如 SELECT * FROM users LIMIT 10"
                    }
                },
                "required": ["sql"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if name != "query":
        raise ValueError(f"未知工具: {name}")

    if not arguments or "sql" not in arguments:
        raise ValueError("缺少参数: sql")

    sql = arguments["sql"].strip()
    if not sql:
        raise ValueError("SQL 语句不能为空")

    # 简单安全检查：禁止 DDL/DML
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
    sql_upper = sql.upper()
    for kw in forbidden:
        if sql_upper.startswith(kw) or f" {kw} " in sql_upper:
            raise ValueError(f"不允许执行修改数据的语句: {kw}")

    try:
        conn = get_db_connection()
        rows = execute_query(conn, sql)
        conn.close()
        result = {
            "row_count": len(rows),
            "rows": rows
        }
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)
        )]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=f"db-search-{DB_TYPE}",
                server_version="0.3.0",
                capabilities=ServerCapabilities(tools=ToolsCapability(list_changed=True))
            )
        )

if __name__ == "__main__":
    asyncio.run(main())