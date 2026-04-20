---
name: ssh-runner2
description: |
  SSH远程命令执行工具。使用此技能在远程服务器上执行命令，配置从 env.json 或环境变量读取。当用户说"在服务器上执行命令"、"SSH执行"、"远程运行"、"连接服务器运行"时使用此技能。
compatibility: 需要 SSH 客户端 (Windows下建议使用 OpenSSH 或 sshpass)
allowed-tools: Bash(ssh-run *)
---

# SSH Runner

在远程服务器上执行命令的CLI工具。

## 配置文件

在项目的 `env.json` 中添加服务器配置:

```json
{
  "ssh": {
    "servers": {
      "prod": {
        "host": "192.168.1.100",
        "port": 22,
        "username": "root",
        "password": "your-password",
        "privateKey": "~/.ssh/id_rsa"
      },
      "dev": {
        "host": "dev.server.com",
        "port": 22,
        "username": "deploy",
        "password": "dev-password"
      }
    },
    "default": "dev"
  }
}
```

## 环境变量覆盖

环境变量优先级高于 env.json:

| 环境变量 | 说明 |
|---------|------|
| SSH_HOST | 主机地址 |
| SSH_PORT | 端口 (默认22) |
| SSH_USER | 用户名 |
| SSH_PASSWORD | 密码 |
| SSH_KEY | 私钥路径 |
| SSH_SERVER | 从配置中选择服务器 |

## 使用方法

### 基本用法

```bash
# 使用默认服务器执行命令
ssh-run "ls -la"

# 使用指定服务器
ssh-run -s prod "ls -la /var/log"

# 交互式SSH会话
ssh-run --interactive
```

### 命令选项

| 选项 | 说明 |
|------|------|
| `<server>` | 服务器名称 (可选，默认使用default或环境变量) |
| `<command>` | 要执行的命令 |
| `--interactive, -i` | 启动交互式SSH会话 |
| `--server <name>` | 指定服务器 |
| `--help` | 显示帮助 |

## 示例

```bash
# 重启服务
ssh-run -s prod "systemctl restart nginx"

# 查看系统状态
ssh-run "uptime && free -h"

# 执行多条命令
ssh-run -s prod "cd /app && git pull && npm run build"

# 复制文件到远程
ssh-run -s prod "cat > /tmp/script.sh" < local-script.sh
```

## Windows 说明

Windows 需要安装 SSH 客户端:
- Windows 10+ 自带 OpenSSH
- 或安装 sshpass: `winget install hobocopy.sshpass`

## 注意事项

- 密码存储: 生产环境建议使用SSH密钥而非密码
- 安全: 敏感信息使用环境变量而非明文存储在配置文件中
