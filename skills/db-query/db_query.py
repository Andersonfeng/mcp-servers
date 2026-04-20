#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库查询工具 - 支持 MySQL, PostgreSQL, DB2
配置文件: env.json (格式见文档)
用法: python db_query.py --server "ecrm hk uat" --query "SELECT * FROM users LIMIT 5"
"""

import json
import sys
import argparse
import os
from pathlib import Path

# 动态导入数据库驱动
def import_driver(db_type):
    if db_type == 'mysql':
        try:
            import pymysql
            return pymysql, 'pymysql'
        except ImportError:
            try:
                import mysql.connector
                return mysql.connector, 'mysql.connector'
            except ImportError:
                print("Error: MySQL driver not installed. Run: pip install pymysql", file=sys.stderr)
                sys.exit(1)
    elif db_type == 'postgresql':
        try:
            import psycopg2
            return psycopg2, 'psycopg2'
        except ImportError:
            print("Error: PostgreSQL driver not installed. Run: pip install psycopg2-binary", file=sys.stderr)
            sys.exit(1)
    elif db_type == 'db2':
        try:
            import ibm_db
            return ibm_db, 'ibm_db'
        except ImportError:
            print("Error: DB2 driver not installed. Run: pip install ibm-db", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unsupported database type: {db_type}", file=sys.stderr)
        sys.exit(1)

def load_config(config_path=None):
    """加载 env.json 配置文件"""
    if not config_path:
        # 默认查找当前目录或 skill 目录下的 env.json
        script_dir = Path(__file__).parent
        config_path = script_dir / 'env.json'
        if not config_path.exists():
            config_path = Path.cwd() / 'env.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        sys.exit(1)

def get_server_config(server_name, config):
    """从配置中提取指定服务器的连接参数"""
    servers = config.get('database', {}).get('servers', {})
    if server_name not in servers:
        print(f"Error: Server '{server_name}' not found in configuration", file=sys.stderr)
        sys.exit(1)
    return servers[server_name]

def connect_db(server_config):
    """根据配置建立数据库连接"""
    db_type = server_config['type'].lower()
    host = server_config['host']
    port = server_config['port']
    user = server_config['username']
    password = server_config['password']
    database = server_config.get('database', '')
    driver_module, driver_name = import_driver(db_type)

    try:
        if db_type == 'mysql':
            # pymysql 或 mysql.connector
            if driver_name == 'pymysql':
                conn = driver_module.connect(
                    host=host, port=port, user=user, password=password,
                    database=database, charset='utf8mb4'
                )
            else:  # mysql.connector
                conn = driver_module.connect(
                    host=host, port=port, user=user, password=password,
                    database=database
                )
        elif db_type == 'postgresql':
            conn = driver_module.connect(
                host=host, port=port, user=user, password=password,
                dbname=database
            )
        elif db_type == 'db2':
            # ibm_db 连接字符串: "DATABASE=name;HOSTNAME=host;PORT=port;PROTOCOL=TCPIP;UID=user;PWD=password;"
            conn_str = f"DATABASE={database};HOSTNAME={host};PORT={port};PROTOCOL=TCPIP;UID={user};PWD={password};"
            conn = driver_module.connect(conn_str, "", "")
        else:
            raise ValueError(f"Unsupported type: {db_type}")
        return conn, db_type, driver_module
    except Exception as e:
        print(f"Database connection failed: {e}", file=sys.stderr)
        sys.exit(1)

def execute_query(conn, db_type, driver_module, sql):
    """执行 SQL 查询并返回结果（列表[字典]）"""
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        # 获取列名
        if db_type == 'db2':
            # ibm_db 游标特殊处理
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            # 将 ibm_db 的行转换为字典
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
        else:
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
        cursor.close()
        return result
    except Exception as e:
        print(f"Query execution failed: {e}", file=sys.stderr)
        sys.exit(1)

def output_as_json(data):
    """输出 JSON 格式"""
    print(json.dumps(data, indent=2, default=str))

def output_as_table(data):
    """输出表格格式（适用于人类阅读）"""
    if not data:
        print("(No rows returned)")
        return
    # 获取所有列名
    columns = list(data[0].keys())
    # 计算每列最大宽度
    col_widths = {col: len(col) for col in columns}
    for row in data:
        for col in columns:
            width = len(str(row.get(col, '')))
            if width > col_widths[col]:
                col_widths[col] = width
    # 打印表头
    header = " | ".join(col.ljust(col_widths[col]) for col in columns)
    print(header)
    print("-" * len(header))
    for row in data:
        line = " | ".join(str(row.get(col, '')).ljust(col_widths[col]) for col in columns)
        print(line)

def main():
    parser = argparse.ArgumentParser(description="Execute SQL query on remote database")
    parser.add_argument("--server", required=True, help="Server name (as defined in env.json)")
    parser.add_argument("--query", required=True, help="SQL query to execute")
    parser.add_argument("--format", choices=["json", "table"], default="json", help="Output format")
    parser.add_argument("--config", help="Path to env.json (default: ./env.json)")
    args = parser.parse_args()

    config = load_config(args.config)
    server_config = get_server_config(args.server, config)
    conn, db_type, driver_module = connect_db(server_config)
    try:
        data = execute_query(conn, db_type, driver_module, args.query)
        if args.format == "json":
            output_as_json(data)
        else:
            output_as_table(data)
    finally:
        conn.close()

if __name__ == "__main__":
    main()