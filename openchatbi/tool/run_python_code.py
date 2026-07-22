"""Tool for running python code."""

import re
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from openchatbi.code.docker_executor import DockerExecutor, check_docker_status
from openchatbi.code.executor_base import ExecutorBase
from openchatbi.code.local_executor import LocalExecutor
from openchatbi.code.restricted_local_executor import RestrictedLocalExecutor
from openchatbi.config_loader import ConfigLoader
from openchatbi.utils import log


class PythonCodeInput(BaseModel):
    reasoning: str = Field(description="Reason for using this run python code tool")
    code: str = Field(description="The python code to execute")


def _create_executor() -> ExecutorBase:
    """Create appropriate executor based on configuration."""
    config_loader = ConfigLoader()
    try:
        config = config_loader.get()
        executor_type = config.python_executor.lower()
    except ValueError:
        # Configuration not loaded, use default local executor
        log("Configuration not loaded, using default LocalExecutor")
        return LocalExecutor()

    log(f"Creating executor of type: {executor_type}")

    if executor_type == "docker":
        # Check if Docker is available before creating DockerExecutor
        is_available, status_message = check_docker_status()
        if not is_available:
            log(f"Docker is not available ({status_message}), falling back to LocalExecutor")
            return LocalExecutor()
        log("Docker is available, creating DockerExecutor")
        return DockerExecutor()
    elif executor_type == "restricted_local":
        log("Creating RestrictedLocalExecutor")
        return RestrictedLocalExecutor()
    elif executor_type == "local":
        log("Creating LocalExecutor")
        return LocalExecutor()
    else:
        log(f"Unknown executor type '{executor_type}', using LocalExecutor as fallback")
        return LocalExecutor()


@tool("run_python_code", args_schema=PythonCodeInput, return_direct=False, infer_schema=True)
def run_python_code(reasoning: str, code: str) -> str:
    """Run python code string. Note: Only print outputs are visible, function return values will be ignored. Use print statements to see results.
    Returns:
        str: The print outputs of the python code
    """
    log(f"Run Python Code, Reasoning: {reasoning}")

    # ---- 新增：从配置读取正确的数据库路径 ----
    try:
        config = ConfigLoader().get()
        db_uri = config.data_warehouse_config.uri
        if db_uri.startswith("sqlite:///"):
            correct_db_path = db_uri[10:]  # 去掉 "sqlite:///"
        else:
            correct_db_path = db_uri
        log(f"Correct database path from config: {correct_db_path}")
    except Exception as e:
        log(f"Failed to get config for db path: {e}, using default")
        correct_db_path = "example/tracking_orders.sqlite"  # 硬编码兜底

    # 替换代码中所有 sqlite3.connect('...') 的路径
    # 匹配多种写法：单引号、双引号、带空格等
    pattern = r"(sqlite3\.connect\s*\(\s*)(['\"])([^'\"]+?)(['\"]\s*\))"
    def replacer(match):
        prefix = match.group(1)
        quote = match.group(2)
        original_path = match.group(3)
        suffix = match.group(4)
        # 保留 :memory: 或空字符串（内存数据库）
        if original_path in (':memory:', ''):
            return match.group(0)
        else:
            return f"{prefix}{quote}{correct_db_path}{suffix}"

    code = re.sub(pattern, replacer, code)
    # ---- 修改结束 ----

    try:
        executor = _create_executor()
        log(f"Using {executor.__class__.__name__} for code execution")
        success, output = executor.run_code(code)
        if success:
            return output
        else:
            return f"Error: {output}"
    except Exception as e:
        log(f"Failed to create executor: {e}")
        # Fallback to LocalExecutor if configuration fails
        log("Falling back to LocalExecutor")
        executor = LocalExecutor()
        success, output = executor.run_code(code)
        if success:
            return output
        else:
            return f"Error: {output}"