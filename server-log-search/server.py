# server.py
import os
import sys
import paramiko
from fastmcp import FastMCP

# 全局变量：保存 SSH 配置和客户端实例
_ssh_config = None
_ssh_client = None


def load_ssh_config_from_env():
    """从环境变量加载 SSH 连接配置"""
    config = {
        
        "host": os.getenv("SSH_HOST", "SSH_HOST"),
        "port": os.getenv("SSH_PORT", "SSH_PORT"),
        "username": os.getenv("SSH_USER", "SSH_USER"),
        "password": os.getenv("SSH_PASSWORD", "SSH_PASSWORD"),
    }
    return config

def create_ssh_client(config):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = {
        "hostname": config["host"],
        "port": config["port"],
        "username": config["username"],
        "password": config["password"],
        "timeout": 10,
    }
    client.connect(**connect_kwargs)
    return client

def get_ssh_client():
    global _ssh_client, _ssh_config
    if _ssh_config is None:
        raise RuntimeError("SSH 配置未初始化")
    if _ssh_client is None:
        print(f"正在建立到 {_ssh_config['host']}:{_ssh_config['port']} 的 SSH 连接...", file=sys.stderr)
        _ssh_client = create_ssh_client(_ssh_config)
        print("SSH 连接已建立", file=sys.stderr)
    return _ssh_client

# 初始化 FastMCP 服务
mcp = FastMCP("SSHCommandServer")

@mcp.tool()
def execute_remote_command(command: str) -> str:
    """在远程服务器上执行一条命令并返回输出（按需建立 SSH 连接）"""
    try:
        client = get_ssh_client()
        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        if exit_status != 0:
            return f"命令执行失败 (退出码 {exit_status}):\n{error or output}"
        return output or "命令执行成功，但无输出内容。"
    except Exception as e:
        global _ssh_client
        if _ssh_client is not None and isinstance(e, (paramiko.SSHException, EOFError)):
            print("SSH 连接失效，尝试重新连接...", file=sys.stderr)
            _ssh_client = None
            try:
                client = get_ssh_client()
                stdin, stdout, stderr = client.exec_command(command, timeout=30)
                exit_status = stdout.channel.recv_exit_status()
                output = stdout.read().decode('utf-8', errors='ignore')
                error = stderr.read().decode('utf-8', errors='ignore')
                if exit_status != 0:
                    return f"命令执行失败 (退出码 {exit_status}):\n{error or output}"
                return output or "命令执行成功，但无输出内容。"
            except Exception as retry_e:
                return f"重连后仍失败: {str(retry_e)}"
        return f"执行命令时发生错误: {str(e)}"

if __name__ == "__main__":
    try:
        _ssh_config = load_ssh_config_from_env()
    except ValueError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        sys.exit(1)
    # 启动 stdio 模式的 MCP 服务
    mcp.run()