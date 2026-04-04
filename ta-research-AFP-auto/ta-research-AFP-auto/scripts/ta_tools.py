"""
ta_tools.py — TA Agent 工具模块

定义提供给 Claude API 子 agent 使用的工具（tool_use 格式）。
工具执行逻辑在此处实现，确保文件操作限制在 project_dir 内。
"""

import os
import json
from pathlib import Path


# ─────────────────────────────────────────────
# 工具定义（传给 Anthropic API 的 tools 参数）
# ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "write_file",
        "description": "将内容写入项目目录中的文件。用于保存每个检查点的输出。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径（相对路径，基于项目目录）"
                },
                "content": {
                    "type": "string",
                    "description": "要写入文件的内容"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "read_file",
        "description": "读取项目目录中的文件内容。用于读取访谈材料、前序输出等。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径（相对路径，基于项目目录）"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_files",
        "description": "列出项目目录（或子目录）中的文件。用于发现访谈文件等。",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "目录路径（相对路径，基于项目目录）。留空则列出根目录。"
                },
                "pattern": {
                    "type": "string",
                    "description": "文件名匹配模式，如 '*.md'、'*.txt'。留空则列出所有文件。"
                }
            },
            "required": []
        }
    },
    {
        "name": "web_search",
        "description": "搜索网络，用于核查文献真实性。返回搜索结果摘要。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询词，如论文标题、作者名、期刊名"
                }
            },
            "required": ["query"]
        }
    }
]


# ─────────────────────────────────────────────
# 工具执行器
# ─────────────────────────────────────────────

class ToolExecutor:
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir).resolve()

    def execute(self, tool_name: str, tool_input: dict) -> str:
        """执行工具调用，返回结果字符串"""
        handlers = {
            "write_file": self._write_file,
            "read_file": self._read_file,
            "list_files": self._list_files,
            "web_search": self._web_search,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return f"错误：未知工具 '{tool_name}'"
        try:
            return handler(**tool_input)
        except Exception as e:
            return f"工具执行错误（{tool_name}）：{e}"

    def _resolve_path(self, relative_path: str) -> Path:
        """解析路径并确保在 project_dir 内（安全约束）"""
        target = (self.project_dir / relative_path).resolve()
        if not str(target).startswith(str(self.project_dir)):
            raise PermissionError(f"禁止访问项目目录外的路径：{relative_path}")
        return target

    def _write_file(self, path: str, content: str) -> str:
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"✅ 文件已写入：{path}（{len(content)} 字符）"

    def _read_file(self, path: str) -> str:
        target = self._resolve_path(path)
        if not target.exists():
            return f"❌ 文件不存在：{path}"
        content = target.read_text(encoding="utf-8")
        if len(content) > 20000:
            # 超长文件截断，避免 token 超限
            content = content[:20000] + f"\n\n[⚠️ 文件过长，已截断至前 20000 字符，完整内容请查看文件]"
        return content

    def _list_files(self, directory: str = "", pattern: str = "") -> str:
        target_dir = self._resolve_path(directory) if directory else self.project_dir
        if not target_dir.exists():
            return f"❌ 目录不存在：{directory}"

        glob_pattern = pattern if pattern else "*"
        files = sorted(target_dir.glob(glob_pattern))
        # 只列出文件，不包括隐藏文件和 .ta_progress.json
        visible = [
            f.relative_to(self.project_dir)
            for f in files
            if f.is_file() and not f.name.startswith(".")
        ]
        if not visible:
            return f"目录 '{directory or '.'}' 中没有找到文件"
        return "\n".join(str(p) for p in visible)

    def _web_search(self, query: str) -> str:
        """
        Web 搜索，用于文献核查。
        策略：优先使用 duckduckgo-search 包；降级时返回提示。
        """
        # 尝试 duckduckgo-search
        try:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=3):
                    results.append(f"**{r['title']}**\n{r['body']}\n来源：{r['href']}")
            if results:
                return "\n\n---\n\n".join(results)
            return f"搜索 '{query}' 未返回结果"
        except ImportError:
            pass

        # 降级：提示手动核查
        return (
            f"⚠️  web_search 工具不可用（未安装 duckduckgo-search 包）。\n"
            f"请手动搜索以核查以下引用：\n{query}\n"
            f"建议搜索路径：Google Scholar / 知网 / CrossRef"
        )


# ─────────────────────────────────────────────
# 工具调用结果格式化（供 tool_use 循环使用）
# ─────────────────────────────────────────────

def format_tool_result(tool_use_id: str, content: str) -> dict:
    """格式化 tool_use 结果为 Anthropic API 期望的格式"""
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content
    }
