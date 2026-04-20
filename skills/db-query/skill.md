---
name: db-query
description: 查询多种数据库（MySQL, PostgreSQL, DB2）。根据配置中的服务器名称执行 SQL 语句。
tools:
  - name: query
    description: 执行 SQL 查询
    parameters:
      - name: server
        type: string
        description: 数据库服务器名称（在 env.json 中定义）
        required: true
      - name: sql
        type: string
        description: 要执行的 SQL 语句（建议只读查询，如 SELECT）
        required: true
    command: python3 {{SKILL_PATH}}/db_query.py --server "{{server}}" --query "{{sql}}"
---

# 数据库查询工具

## 使用说明

本工具允许你通过自然语言查询配置好的数据库服务器。需要先在 `env.json` 中定义服务器连接信息。

### 示例

- "查询 ecrm hk uat 数据库中的用户表"  
  实际执行：`query` 工具，参数 `server="ecrm hk uat"`, `sql="SELECT * FROM users LIMIT 10"`

- "统计 sg 环境订单数量"  
  实际执行：`query` 工具，参数 `server="ecrm sg uat"`, `sql="SELECT COUNT(*) FROM orders"`

### 注意事项

- 仅支持 SELECT 查询，不执行修改数据的语句（为安全起见，可在脚本中限制）。
- 结果以 JSON 格式返回，便于进一步处理。
- 支持的数据库类型：`mysql`, `postgresql`, `db2`。
- 确保已安装对应数据库驱动：
  - MySQL: `pip install pymysql`
  - PostgreSQL: `pip install psycopg2-binary`
  - DB2: `pip install ibm-db`