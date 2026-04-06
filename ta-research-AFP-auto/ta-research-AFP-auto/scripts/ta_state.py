"""
ta_state.py — TA Agent 状态管理模块

管理 .ta_progress.json 的读写，支持断点续跑。
原子写入防止文件损坏。
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


INITIAL_STATE = {
    "version": "1.0",
    "project_dir": "",
    "created_at": "",
    "updated_at": "",
    "research_info": {
        "topic": "",
        "questions": "",
        "target_journal": "C刊",   # C刊 | SSCI
        "interview_files": []       # 访谈文件路径列表
    },
    "completed_cps": [],            # 已完成的 CP 编号列表（int）
    "skipped_cps": [],              # 跳过/降级的 CP 编号
    "auto_decisions": {
        "cp2_theory": None,         # "A" | "B" | "C"
        "cp8_narrative": None,      # "parallel" | "serial"
        "cp10_journal_type": None   # "C刊" | "SSCI"
    },
    "cp_outputs": {},               # {cp_num_str: [file_path, ...]}
    "cp_summaries": {},             # {cp_num_str: "一句话摘要"}
    "failures": {}                  # {cp_num_str: {"error": str, "attempts": int, "degraded": bool}}
}


class StateManager:
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir).resolve()
        self.state_file = self.project_dir / ".ta_progress.json"
        self._state = None

    @property
    def state(self) -> dict:
        if self._state is None:
            self._state = self.load()
        return self._state

    def load(self) -> dict:
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                return data
            except (json.JSONDecodeError, OSError):
                print(f"⚠️  状态文件损坏，重新初始化")

        state = INITIAL_STATE.copy()
        state["project_dir"] = str(self.project_dir)
        state["created_at"] = _now()
        state["updated_at"] = _now()
        return state

    def save(self):
        """原子写入：先写临时文件，再 rename，防止写到一半时损坏"""
        self.state["updated_at"] = _now()
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=self.project_dir, prefix=".ta_progress_tmp_", suffix=".json"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.state_file)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def set_research_info(self, topic: str, questions: str, target_journal: str, interview_files: list):
        self.state["research_info"] = {
            "topic": topic,
            "questions": questions,
            "target_journal": target_journal,
            "interview_files": interview_files
        }
        self.save()

    def mark_complete(self, cp_num: int, outputs: list, summary: str = ""):
        if cp_num not in self.state["completed_cps"]:
            self.state["completed_cps"].append(cp_num)
        self.state["cp_outputs"][str(cp_num)] = outputs
        if summary:
            self.state["cp_summaries"][str(cp_num)] = summary
        self.save()

    def mark_skipped(self, cp_num: int, reason: str):
        if cp_num not in self.state["skipped_cps"]:
            self.state["skipped_cps"].append(cp_num)
        if cp_num not in self.state["completed_cps"]:
            self.state["completed_cps"].append(cp_num)
        self.state["failures"][str(cp_num)] = {
            "error": reason,
            "attempts": 0,
            "degraded": True
        }
        self.save()

    def mark_failed(self, cp_num: int, error: str, attempts: int):
        self.state["failures"][str(cp_num)] = {
            "error": error,
            "attempts": attempts,
            "degraded": True
        }
        if cp_num not in self.state["skipped_cps"]:
            self.state["skipped_cps"].append(cp_num)
        if cp_num not in self.state["completed_cps"]:
            self.state["completed_cps"].append(cp_num)
        self.save()

    def record_decision(self, key: str, value: str):
        self.state["auto_decisions"][key] = value
        self.save()

    def is_completed(self, cp_num: int) -> bool:
        return cp_num in self.state["completed_cps"]

    def get_context(self, cp_num: int) -> str:
        """返回前序 CP 的上下文摘要，供当前 CP 的子 agent 使用"""
        lines = []
        for i in range(1, cp_num):
            summary = self.state["cp_summaries"].get(str(i))
            if summary:
                lines.append(f"CP{i}: {summary}")
        if not lines:
            return ""
        return "【前序检查点摘要】\n" + "\n".join(lines)

    def get_research_info(self) -> dict:
        return self.state["research_info"]

    def get_auto_decisions(self) -> dict:
        return self.state["auto_decisions"]

    def get_target_journal(self) -> str:
        return self.state["research_info"].get("target_journal", "C刊")

    def print_status(self):
        ri = self.state["research_info"]
        completed = self.state["completed_cps"]
        skipped = self.state["skipped_cps"]
        decisions = self.state["auto_decisions"]

        print(f"\n{'='*50}")
        print(f"研究主题：{ri.get('topic', '未知')}")
        print(f"目标期刊：{ri.get('target_journal', 'C刊')}")
        print(f"已完成CP：{sorted(completed)}")
        if skipped:
            print(f"跳过/降级：{sorted(skipped)}")
        if any(decisions.values()):
            print(f"自动决策：{decisions}")
        print(f"{'='*50}\n")
