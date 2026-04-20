#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
import argparse
import subprocess
from pathlib import Path

# 尝试导入 paramiko
try:
    import paramiko
except ImportError:
    print("Error: paramiko is not installed. Please run: pip install paramiko", file=sys.stderr)
    sys.exit(1)

# 配置文件路径
CONFIG_FILE = "env.json"

def load_config():
    """加载 opencode.json 配置文件"""
    if not Path(CONFIG_FILE).exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def get_server_config(server_name):
    """
    获取服务器配置
    优先级：环境变量 > opencode.json
    返回：(host, port, username, password, private_key)
    """
    config = load_config()
    
    # 1. 从环境变量读取（无默认值，未设置则为 None 或空字符串）
    host = os.getenv("SSH_HOST")
    port = os.getenv("SSH_PORT", "")
    username = os.getenv("SSH_USER")
    password = os.getenv("SSH_PASSWORD", "")
    private_key = os.getenv("SSH_KEY")
    
    # 2. 环境变量缺失时，从配置文件补充
    ssh_config = config.get("ssh", {})
    servers = ssh_config.get("servers", {})
    server_conf = servers.get(server_name, {})
    
    if not host:
        host = server_conf.get("host", "")
    if not port:
        port = str(server_conf.get("port", ""))
    if not username:
        username = server_conf.get("username", "")
    if not password:
        password = server_conf.get("password", "")
    if not private_key:
        private_key = server_conf.get("privateKey", "")
    
    # 3. 端口默认 22
    if not port:
        port = "22"
    
    # 4. 处理私钥路径中的 ~
    if private_key and private_key.startswith("~"):
        private_key = os.path.expanduser(private_key)
    
    return host, port, username, password, private_key

def get_default_server():
    """获取默认服务器名称"""
    config = load_config()
    default = config.get("ssh", {}).get("default", "")
    return os.getenv("SSH_SERVER") or default or "default"

def ssh_exec(host, port, username, password, private_key, command):
    """使用 paramiko 执行远程命令"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        connect_kwargs = {
            'hostname': host,
            'port': int(port),
            'username': username,
            'timeout': 10,
            'allow_agent': False,   # 禁用 SSH 代理，避免冲突
            'look_for_keys': False,  # 不自动从 ~/.ssh 找密钥，由我们显式控制
        }
        if private_key:
            # 尝试 RSA，若失败可扩展其他类型
            key = paramiko.RSAKey.from_private_key_file(private_key)
            connect_kwargs['pkey'] = key
        elif password:
            connect_kwargs['password'] = password
        else:
            print("Error: No authentication method provided (password or private key)", file=sys.stderr)
            sys.exit(1)
        
        client.connect(**connect_kwargs)
        stdin, stdout, stderr = client.exec_command(command)
        # 输出标准输出
        for line in stdout:
            print(line, end='')
        err = stderr.read().decode()
        if err:
            print(err, file=sys.stderr, end='')
        exit_code = stdout.channel.recv_exit_status()
        sys.exit(exit_code)
    except paramiko.AuthenticationException:
        print("SSH authentication failed", file=sys.stderr)
        sys.exit(1)
    except paramiko.SSHException as e:
        print(f"SSH connection error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()

def ssh_interactive(host, port, username, password, private_key):
    """
    交互式 SSH 会话。
    paramiko 无法提供完整的终端交互，这里尝试回退到系统 ssh 命令。
    如果系统 ssh 不可用，则提示用户手动连接。
    """
    # 尝试使用系统 ssh 命令（需要用户已安装 OpenSSH 客户端）
    ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-p", port, f"{username}@{host}"]
    if private_key:
        ssh_cmd.extend(["-i", private_key])
    elif password:
        # 如果必须用密码，需要 sshpass，但跨平台复杂，提示用户改用密钥或手动连接
        print("Interactive mode with password authentication requires system 'sshpass' which may not be available.")
        print("Please use private key authentication or run manually:")
        print(f"ssh -p {port} {username}@{host}")
        sys.exit(1)
    
    try:
        subprocess.run(ssh_cmd, check=True)
    except FileNotFoundError:
        print("System SSH client not found. Please install OpenSSH client or connect manually:", file=sys.stderr)
        print(f"ssh -p {port} {username}@{host}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

def main():
    parser = argparse.ArgumentParser(
        description="SSH远程命令执行工具 (based on paramiko)",
        usage="%(prog)s [options] [server] <command>"
    )
    # parser.add_argument("-i", "--interactive", action="store_true", help="启动交互式SSH会话（需要系统ssh命令）")
    parser.add_argument("-s", "--server", help="指定服务器名称")
    parser.add_argument("args", nargs="*", help="服务器名称 + 执行命令")
    
    args = parser.parse_args()
    
    # 解析参数
    server_name = args.server
    command = ""
    positional = args.args
    
    if positional:
        if not server_name:
            server_name = positional[0]
            if len(positional) > 1:
                command = " ".join(positional[1:])
        else:
            command = " ".join(positional)
    
    if not server_name:
        server_name = get_default_server()
    
    host, port, username, password, private_key = get_server_config(server_name)
    
    if not host or not username:
        print(f"Error: Server '{server_name}' configuration not found. Please check environment variables or opencode.json.", file=sys.stderr)
        sys.exit(1)
    
    if args.interactive:
        ssh_interactive(host, port, username, password, private_key)
    elif command:
        ssh_exec(host, port, username, password, private_key, command)
    else:
        print("Error: No command specified. Use --help for usage.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()