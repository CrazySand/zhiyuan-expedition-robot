import subprocess
import sys


def run_command_live_output(command):
    """
    执行系统命令并实时打印输出，执行完成后函数才返回。
    适合耗时较长的命令（如 apt update），可实时看到执行过程。

    Args:
        command (str): 要在 Ubuntu 系统上执行的系统命令字符串（如 "sudo apt update"）

    Returns:
        int: 命令执行返回码（0 表示成功，-1 表示执行过程中出现异常）
    """
    # 启动子进程，stdout/stderr 重定向到管道
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # 将错误输出合并到标准输出，方便实时打印
        text=True,
        encoding='utf-8',
        bufsize=1  # 行缓冲，保证输出实时性
    )

    # 实时读取并打印输出
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()

    # 阻塞等待命令执行完成，获取返回码
    process.wait()
    return process.returncode
