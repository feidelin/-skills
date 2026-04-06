"""
ta_checkpoints.py — TA Agent 检查点配置模块

定义12个检查点的配置和 system prompt 拼装逻辑。
通过读取对应 SKILL.md 复用现有技能定义，技能升级时 agent 自动受益。
"""

from pathlib import Path

# Skill 文件根目录
SKILLS_DIR = Path.home() / ".claude" / "skills"


def get_skill_content(skill_name: str) -> str:
    """读取指定 skill 的 SKILL.md 内容（用于注入子 agent system prompt）"""
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    if skill_path.exists():
        content = skill_path.read_text(encoding="utf-8")
        # 去掉 frontmatter（--- 之间的内容），只保留实际指令部分
        lines = content.split("\n")
        if lines[0].strip() == "---":
            end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), None)
            if end:
                content = "\n".join(lines[end + 1:]).strip()
        return content
    return f"[技能 {skill_name} 的 SKILL.md 未找到，请按通用学术写作规范执行]"


# 共享基础 system prompt（所有 CP 共用前缀）
BASE_SYSTEM = """你是一位专业的社会学研究助手，正在协助完成一篇学术论文的全流程写作。

核心写作规范：
- 禁止编造文献。引用必须真实存在。不确定时标注"⚠️ 此引用需研究者核实"
- 禁止套话开头：不用"在当今社会""随着XX的发展""本文试图"等
- 理论使用要深入机制，不能只贴标签
- 引用格式遵循 APA 7th
- 所有输出文件使用 UTF-8 编码
- 只能读写 project_dir 目录内的文件

你有以下工具可以使用：
- write_file：将内容写入文件
- read_file：读取已有文件
- list_files：列出目录中的文件
- web_search：搜索网络（主要用于文献核查）

完成当前检查点的任务后，将主要产出写入指定文件，然后结束（不需要等待用户确认）。
"""


def build_system_prompt(cp_num: int, calls_skills: list) -> str:
    """拼装检查点的完整 system prompt"""
    prompt_parts = [BASE_SYSTEM]
    for skill in calls_skills:
        skill_content = get_skill_content(skill)
        prompt_parts.append(f"\n\n--- 参考技能：{skill} ---\n{skill_content}")
    return "\n".join(prompt_parts)


def build_task_message(cp_num: int, research_info: dict, context: str, decisions: dict) -> str:
    """构造发送给子 agent 的任务消息"""
    ri = research_info
    cp_config = CHECKPOINTS[cp_num]

    header = f"""
【当前任务：检查点 {cp_num}/12 — {cp_config['name']}】

研究信息：
- 研究主题：{ri.get('topic', '（未提供）')}
- 研究问题：{ri.get('questions', '（未提供）')}
- 目标期刊：{ri.get('target_journal', 'C刊')}
- 访谈文件：{', '.join(ri.get('interview_files', [])) or '（将通过 list_files 查找）'}
""".strip()

    decision_section = ""
    if decisions.get("cp2_theory"):
        decision_section += f"\n- 已确定理论定位：{decisions['cp2_theory']}（{'理论驱动' if decisions['cp2_theory']=='A' else '经验驱动' if decisions['cp2_theory']=='B' else '敏感性概念'}）"
    if decisions.get("cp8_narrative"):
        decision_section += f"\n- 已确定叙事结构：{'并列型' if decisions['cp8_narrative']=='parallel' else '串联型'}"
    if decisions.get("cp10_journal_type"):
        decision_section += f"\n- 期刊类型（用于标题/摘要）：{decisions['cp10_journal_type']}"

    if decision_section:
        header += f"\n\n已做决策：{decision_section}"

    if context:
        header += f"\n\n{context}"

    task = cp_config.get("task_instruction", "")
    return f"{header}\n\n{task}"


# ─────────────────────────────────────────────
# 12个检查点完整配置
# ─────────────────────────────────────────────

CHECKPOINTS = {
    1: {
        "name": "文献检索",
        "calls_skills": ["cnki-advanced-search", "foreign-literature-search"],
        "max_turns": 20,
        "expected_outputs": ["literature_cn.md", "literature_en.md"],
        "chrome_required": True,  # CNKI 需要 Chrome MCP，可降级
        "task_instruction": """
请执行文献检索任务：

1. **外文文献检索**：使用 web_search 工具，基于研究主题构建英文检索词（含同义词扩展），
   检索 Google Scholar 及社会学核心期刊。生成 WoS/Scopus 布尔检索式。
   将结果写入 literature_en.md（含题录、摘要摘要、WoS检索式）。

2. **中文文献检索（知网）**：
   ⚠️ 注意：当前运行环境为 Python API 调用模式，Chrome DevTools 工具不可用（仅 Claude Code 交互模式支持）。
   请直接在 literature_cn.md 中输出详细的知网手动检索步骤，具体包括：
   - 知网高级检索入口 URL
   - 关键词分组和同义词扩展建议（基于研究主题自动生成）
   - CSSCI 筛选步骤
   - 导出格式建议（查新引文格式）
   标注"⚠️ 需手动执行：在浏览器中按以下步骤操作"

检索完成后，在 literature_cn.md 结尾写一行摘要：
`[检索摘要] 中文文献：需手动检索（步骤已附）；外文文献：N篇；主要主题关键词：XXX`
""".strip()
    },

    2: {
        "name": "理论框架建构",
        "calls_skills": ["ta-framework-builder"],
        "max_turns": 20,
        "expected_outputs": ["framework.md"],
        "pre_decision": "cp2_theory_decision",  # Python 函数处理 A/B/C 决策
        "task_instruction": """
请基于研究问题和研究主题，建构理论框架。

理论定位已由系统自动确定（见上方"已做决策"部分），请据此执行：
- A（理论驱动）：选定1-2个主理论，操作化3-5个核心概念，说明概念间关系
- B（经验驱动）：保持归纳开放性，说明理论将在讨论阶段引入
- C（敏感性概念）：选定2-3个敏感性概念作为分析透镜，说明其指导意义

输出格式（写入 framework.md）：
1. 理论定位选择及依据
2. 核心理论/概念介绍（重点：机制而非标签）
3. 概念操作化定义
4. 框架对编码和写作的指导意义
""".strip()
    },

    3: {
        "name": "主题分析编码",
        "calls_skills": ["thematic-analysis"],
        "max_turns": 40,  # 多份访谈，轮次更多
        "expected_outputs": ["themes.md"],
        "task_instruction": """
请执行主题分析编码任务：

1. 首先用 list_files 查找项目目录中的访谈文件（.txt、.md 格式）
2. 对每份访谈文件：
   - 用 read_file 读取内容
   - 逐句识别意义单元并编码（贴近数据语言，in-vivo 优先）
   - 将编码结果写入 coding_[被访者编号].md
3. 所有访谈编码完成后，将全部编码汇总，进行主题聚类（5-8个候选主题）
4. 对每个候选主题进行审查（内部一致性、外部区分度、与研究问题相关性）
5. 为每个主题提供命名建议，自动采用描述性命名

将最终主题结构写入 themes.md，格式：
- 主题编号、名称、核心含义、包含编码数
- 每个主题1-2条代表性原文引语

若未找到访谈文件，在 themes.md 中说明"访谈文件未找到，请将访谈文本文件放入项目目录后重新执行本检查点"。
""".strip()
    },

    4: {
        "name": "文献综述写作 + 引用核查",
        "calls_skills": ["literature-review-writer", "literature-verifier"],
        "max_turns": 25,
        "expected_outputs": ["literature_review.md"],
        "task_instruction": """
请执行文献综述写作任务（在已知主题结构的基础上写作）：

步骤：
1. 读取 themes.md（了解研究发现主题，以便精准选材）
2. 读取 literature_en.md 和 literature_cn.md（文献池）
3. 先用 web_search 对拟引用的重要文献进行真实性核查（至少核查5篇）
   - 核查规则：✅ 确认 / ⚠️ 存疑 / ❌ 无法确认
   - 存疑引用统一标注，不删除，不阻断
4. 基于已核实文献，写作文献综述全文（含研究空白导出）
   - 展现学术脉络，禁止主题公园式罗列
   - 结尾自然导出研究空白，呼应研究问题
5. 将综述全文写入 literature_review.md

在文末附：`[引用核查摘要] 核查N篇，✅N篇，⚠️N篇，❌N篇`
""".strip()
    },

    5: {
        "name": "研究方法章节写作",
        "calls_skills": ["ta-methods-writer"],
        "max_turns": 15,
        "expected_outputs": ["methods.md"],
        "task_instruction": """
请写作研究方法章节。

步骤：
1. 读取项目目录中的 coding_*.md 文件（获取访谈份数、被访者信息）
2. 读取 framework.md（获取理论定位 A/B/C）
3. 基于以上信息，推断已知内容，无法推断的填"[待补充]"
4. 生成完整研究方法章节，包含：
   - 研究设计与方法论立场
   - 研究场域与抽样策略
   - 数据收集（访谈形式、时间、份数）
   - 分析方法（主题分析，Braun & Clarke 2006/2019）
   - 研究质量保障（Lincoln & Guba 1985 框架）
   - 研究伦理

默认值（无法推断时使用）：
- 访谈形式：半结构化深度访谈
- 抽样策略：目的性抽样
- 数据收集时间：[待补充]

写入 methods.md。
""".strip()
    },

    6: {
        "name": "引言写作 + 增量核查",
        "calls_skills": ["introduction-writer", "literature-verifier"],
        "max_turns": 15,
        "expected_outputs": ["introduction.md"],
        "task_instruction": """
请写作论文引言章节。

步骤：
1. 读取 literature_review.md（获取研究空白和文献脉络）
2. 基于研究问题和研究空白，写作引言（800-1200字，C刊标准）
   结构：研究背景 → 既有研究不足 → 本研究问题 → 研究贡献简述 → 论文结构安排
3. 对引言中新引入的引用（未在综述中出现的）用 web_search 增量核查
4. 写入 introduction.md

质量要求：
- 开头句禁止套话
- 研究空白从文献脉络自然导出
- 贡献表述具体指向理论对话，不用"丰富了XX研究"
""".strip()
    },

    7: {
        "name": "理论框架章节写作 + 增量核查",
        "calls_skills": ["ta-framework-writer", "literature-verifier"],
        "max_turns": 15,
        "expected_outputs": ["framework_section.md"],
        "task_instruction": """
请将理论框架建构结果转化为论文正文章节。

步骤：
1. 读取 framework.md（获取框架内容和理论定位）
2. 根据理论定位（见上方"已做决策"）生成对应形态的章节：
   - A型：独立章节（1500-2500字），放在方法论之前
   - B型：方法章节嵌入（300-500字简述）
   - C型：方法章节嵌入（600-1000字取向说明）
3. 对新引入的理论文献进行 web_search 增量核查
4. 写入 framework_section.md

写作要求：
- 理论要展示解释机制，不只是堆砌观点
- 核心概念界定回到原著，不引二手解读
""".strip()
    },

    8: {
        "name": "研究发现写作",
        "calls_skills": ["ta-findings-writer"],
        "max_turns": 25,
        "expected_outputs": ["findings.md"],
        "pre_decision": "cp8_narrative_decision",  # Claude 分析主题关系后 Python 记录
        "task_instruction": """
请写作研究发现章节。

步骤：
1. 读取 themes.md（获取主题结构、核心含义和代表性引语）
2. 分析主题之间的关系：
   - 若各主题相互独立 → 并列型叙事结构
   - 若主题间有因果链/递进/对立张力 → 串联型叙事结构
   在输出内容开头标注叙事结构选择及理由（格式：`[叙事结构] 并列型/串联型 | 依据：XXX`）
3. 按照确定的叙事结构，对每个主题写作发现小节：
   - 主题阐释（捕捉了什么现象/机制）
   - 2-3条引语证据（含分析性解释，不只是堆砌引语）
   - 主题内部张力或变体（如有）
4. 写入 findings.md

理论一致性：参照已确定的理论定位（A/B/C）调整理论阐释深度。
""".strip()
    },

    9: {
        "name": "讨论与结论写作 + 增量核查",
        "calls_skills": ["ta-discussion-writer", "literature-verifier"],
        "max_turns": 20,
        "expected_outputs": ["discussion.md"],
        "task_instruction": """
请写作讨论与结论章节。

步骤：
1. 读取 findings.md（研究发现）、framework_section.md（理论框架）、literature_review.md（文献综述要点）
2. 根据理论定位（见"已做决策"）分配理论工作：
   - A：深化和检验框架（验证/修正/挑战了哪些命题）
   - B：承担全部理论建构（归纳机制→与既有理论对话）
   - C：在发现与理论之间来回，理论对话最丰富
3. 写作六部分：跨主题综合 → 理论对话 → 理论贡献 → 研究局限 → 未来方向 → 结论
4. 对新引入的引用进行 web_search 增量核查（讨论章节是高风险区）
5. 写入 discussion.md

质量红线：
- 理论对话指向具体概念，不泛化
- 贡献通过三重检验：理论对话、So What、新颖性
- 结论回扣引言的研究问题
""".strip()
    },

    10: {
        "name": "标题 / 摘要 / 关键词",
        "calls_skills": ["paper-title-abstract-keywords"],
        "max_turns": 15,
        "expected_outputs": ["title_abstract_keywords.md"],
        "task_instruction": """
请生成论文标题、摘要和关键词。

目标期刊类型已由系统确定（见"已做决策"中的期刊类型）。

步骤：
1. 读取 introduction.md、literature_review.md、findings.md（了解论文核心内容）
2. 根据目标期刊类型选择方案：

   **C刊方案**：
   - 标题：现象聚焦型（直接点明研究对象和核心发现）
   - 摘要：标准顺序结构（背景→问题→方法→发现→贡献，300字以内）
   - 关键词：议题检索型（5个词，覆盖研究主题核心词和方法词）

   **SSCI方案**：
   - 标题：理论对话型（包含理论概念或框架名称）
   - 摘要：贡献前置结构（先说贡献再说背景，250词以内，英文）
   - 关键词：理论+方法型（5词，含1-2个理论术语）

3. 写入 title_abstract_keywords.md，包含标题、摘要、关键词三部分
""".strip()
    },

    11: {
        "name": "全文引用核查",
        "calls_skills": ["literature-verifier"],
        "max_turns": 25,
        "expected_outputs": ["citation_check_final.md"],
        "task_instruction": """
请对全文所有引用进行最终综合核查。

步骤：
1. 依次读取：literature_review.md、introduction.md、framework_section.md、
   methods.md、findings.md、discussion.md
2. 提取所有引用（作者、年份、标题、期刊）
3. 对每条引用使用 web_search 核查真实性：
   - ✅ 已核实：找到可信来源
   - ⚠️ 存疑：信息部分匹配或来源不够可信
   - ❌ 无法确认：未找到相关信息
4. 生成核查报告，写入 citation_check_final.md

格式：
```
## 引用核查报告（最终版）

### ✅ 已核实（N篇）
- [作者年份] 标题 | 期刊 | 核查来源

### ⚠️ 存疑（N篇，建议研究者自行确认）
- [作者年份] 标题 | 存疑原因

### ❌ 无法确认（N篇，建议删除或替换）
- [作者年份] 标题
```
""".strip()
    },

    12: {
        "name": "完稿汇总与决策报告",
        "calls_skills": [],  # 协调器直接执行，无需外部技能
        "max_turns": 10,
        "expected_outputs": ["final_report.md"],
        "task_instruction": """
请生成完稿汇总报告。

步骤：
1. 用 list_files 列出项目目录中的所有 .md 文件
2. 读取 citation_check_final.md（核查报告摘要）
3. 生成完整的完稿报告，写入 final_report.md

报告结构：
```
# TA 研究全自动流程 — 完稿报告

## 已生成文件清单
[列出所有产出文件及对应章节]

## 论文章节装配清单
一、引言 → introduction.md
二、文献综述 → literature_review.md
三、理论框架 → framework_section.md
四、研究方法 → methods.md
五、研究发现 → findings.md
六、讨论与结论 → discussion.md
论文信息 → title_abstract_keywords.md

## 自动决策日志
[列出 CP2/CP8/CP10 的决策及依据]

## 降级/跳过记录
[若有，列出原因；无则写"无"]

## 建议研究者重点审阅
- ⚠️ citation_check_final.md 中存疑和无法确认的引用
- ⚠️ themes.md 中的主题命名（命名权归研究者）
- ⚠️ methods.md 中标注"[待补充]"的信息
- ⚠️ 自动决策的理论定位是否符合研究意图
```
""".strip()
    }
}
