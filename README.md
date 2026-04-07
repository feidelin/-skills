# 学术志 Skills 仓库 | Academic Skills Repository

学术志联合创始人一平博士的公开 skills 仓库，涵盖学术科研各领域，包含论文选题、研究设计、研究方法、文献检索与核查、文献阅读、文献综述、资料分析、期刊论文写作、博士论文写作等。

A public skills repository by Dr. Yiping, co-founder of AcademicZhi (学术志). Covers all stages of academic research, including topic selection, research design, methodology, literature search & verification, literature review, data analysis, journal paper writing, and doctoral dissertation writing.

## 安装方法 | Installation

需先安装 [Claude Code](https://claude.ai/code)，然后在终端运行对应命令即可。

Requires [Claude Code](https://claude.ai/code). Run the corresponding command in your terminal to install any skill.

---

## TA 研究全流程一键安装 | TA Research Full Workflow — One-Click Install

**主题分析（TA）研究全流程工作流**，涵盖文献检索、理论框架建构、主题编码、综述写作、引言、方法、发现、讨论与结论、标题摘要关键词共12个检查点，完成后自动合成 Word 初稿。

The **Thematic Analysis (TA) full research workflow** covers 12 checkpoints: literature search, theoretical framework, thematic coding, literature review, introduction, methods, findings, discussion & conclusion, and title/abstract/keywords — with automatic Word draft assembly at the end.

**两个版本 | Two Versions**

| 版本 / Version | 说明 / Description | 适合场景 |
|---|---|---|
| `ta-research-AFP` | 逐步确认版，每个检查点等待用户确认 / Step-by-step with user confirmation at each checkpoint | 研究者全程参与，精细控制每一步 |
| `ta-research-AFP-auto` | 全自动版，一键跑完全部12个检查点 / Fully automated, runs all 12 checkpoints without interruption | 快速生成草稿，事后审阅修改 |

**一次性全部安装（复制粘贴到终端）| Install Everything (copy & paste to terminal)**

```bash
claude skill install https://github.com/yipng05-max/-skills/tree/main/ta-research-AFP && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/ta-research-AFP-auto && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/cnki-advanced-search && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/foreign-literature-search && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/ta-framework-builder && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/thematic-analysis && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/literature-review-writer && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/literature-verifier && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/ta-methods-writer && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/introduction-writer && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/ta-framework-writer && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/ta-findings-writer && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/ta-discussion-writer && \
claude skill install https://github.com/yipng05-max/-skills/tree/main/paper-title-abstract-keywords && \
pip install python-docx
```

**各检查点对应子技能 | Sub-skills by Checkpoint**

| 检查点 / Checkpoint | Skill | 安装 / Install |
|---|---|---|
| CP1 中文文献检索 | `cnki-advanced-search` | `claude skill install https://github.com/yipng05-max/-skills/tree/main/cnki-advanced-search` |
| CP1 外文文献检索 | `foreign-literature-search` | `claude skill install https://github.com/yipng05-max/-skills/tree/main/foreign-literature-search` |
| CP2 理论框架建构 | `ta-framework-builder` | `claude skill install https://github.com/yipng05-max/-skills/tree/main/ta-framework-builder` |
| CP3 主题分析编码 | `thematic-analysis` | `claude skill install https://github.com/yipng05-max/-skills/tree/main/thematic-analysis` |
| CP4 文献综述写作 | `literature-review-writer` | `claude skill install https://github.com/yipng05-max/-skills/tree/main/literature-review-writer` |
| CP4/6/7/9/11 引用核查 | `literature-verifier` | `claude skill install https://github.com/yipng05-max/-skills/tree/main/literature-verifier` |
| CP5 研究方法章节 | `ta-methods-writer` | `claude skill install https://github.com/yipng05-max/-skills/tree/main/ta-methods-writer` |
| CP6 引言写作 | `introduction-writer` | `claude skill install https://github.com/yipng05-max/-skills/tree/main/introduction-writer` |
| CP7 理论框架章节 | `ta-framework-writer` | `claude skill install https://github.com/yipng05-max/-skills/tree/main/ta-framework-writer` |
| CP8 研究发现写作 | `ta-findings-writer` | `claude skill install https://github.com/yipng05-max/-skills/tree/main/ta-findings-writer` |
| CP9 讨论与结论 | `ta-discussion-writer` | `claude skill install https://github.com/yipng05-max/-skills/tree/main/ta-discussion-writer` |
| CP10 标题/摘要/关键词 | `paper-title-abstract-keywords` | `claude skill install https://github.com/yipng05-max/-skills/tree/main/paper-title-abstract-keywords` |
| CP12 Word 初稿合成 | `python-docx`（Python 库） | `pip install python-docx` |

---

## Skills 列表 | Skills List

### 论文写作与审阅 | Paper Writing & Review

| Skill | 功能 / Description | 安装 / Install |
|---|---|---|
| `feishu-paper-reviewer` | 在飞书云文档上直接进行论文审阅，支持高亮、删除线、划词批注 / Review papers directly in Feishu docs with highlighting, strikethrough, and inline comments | `claude skill install https://github.com/yipng05-max/-skills/tree/main/feishu-paper-reviewer` |
| `paper-reviewer` | 对 Word/PDF 论文进行评阅，生成带标注的 Word 文档 / Review Word/PDF papers and generate an annotated Word document | `claude skill install https://github.com/yipng05-max/-skills/tree/main/paper-reviewer` |
| `paper-analyzer` | 基于12个阅读要素对论文进行结构化拆解与分析 / Structured paper analysis based on 12 reading elements | `claude skill install https://github.com/yipng05-max/-skills/tree/main/paper-analyzer` |
| `paper-formatter` | 按目标期刊格式规范排版论文 / Format manuscripts to match a target journal's style | `claude skill install https://github.com/yipng05-max/-skills/tree/main/paper-formatter` |

### 文献综述 | Literature Review

| Skill | 功能 / Description | 安装 / Install |
|---|---|---|
| `literature-review-writer` | 顶刊风格文献综述写作，自动检索并核实真实文献 / Top-journal-style literature review with automatic retrieval and verification of real references | `claude skill install https://github.com/yipng05-max/-skills/tree/main/literature-review-writer` |
| `phd-literature-review` | 博士论文文献综述（约2万字）工程化写作系统 / Systematic PhD dissertation literature review (~20,000 words) with multi-stage workflow | `claude skill install https://github.com/yipng05-max/-skills/tree/main/phd-literature-review` |
| `literature-verifier` | 文献真实性核查，检测幻觉引用，支持中英文数据库 / Verify reference authenticity and detect hallucinated citations; supports Chinese and English databases | `claude skill install https://github.com/yipng05-max/-skills/tree/main/literature-verifier` |

### 文献检索与管理 | Literature Search & Management

| Skill | 功能 / Description | 安装 / Install |
|---|---|---|
| `cnki-advanced-search` | 知网三阶段检索：①主体联合检索（倒剥洋葱法）②独立补充检索（背景+理论文献）③汇总去重分类 Excel / Three-phase CNKI search: joint search with onion-peeling, supplementary independent searches, and deduplicated categorized Excel output | `claude skill install https://github.com/yipng05-max/-skills/tree/main/cnki-advanced-search` |
| `foreign-literature-search` | 外文三阶段检索（OpenAlex API，无需机构账号）：①主体联合检索②独立补充检索③汇总分类Excel，同步生成WoS/Scopus布尔检索式 / Three-phase foreign literature search via OpenAlex API (no institutional access needed): joint search, supplementary searches, categorized Excel + WoS/Scopus boolean queries | `claude skill install https://github.com/yipng05-max/-skills/tree/main/foreign-literature-search` |
| `cjournal-analyzer` | C刊期刊全面分析，自动抓取近5年文章目录与作者信息 / Comprehensive CSSCI journal analysis — auto-fetches article lists and author data from the past 5 years | `claude skill install https://github.com/yipng05-max/-skills/tree/main/cjournal-analyzer` |
| `pdf-bib-import` | 批量提取PDF论文题录并导入飞书多维表格 / Batch extract bibliographic metadata from PDFs and import into Feishu Base | `claude skill install https://github.com/yipng05-max/-skills/tree/main/pdf-bib-import` |

### 研究设计与分析 | Research Design & Analysis

| Skill | 功能 / Description | 安装 / Install |
|---|---|---|
| `conceptual-framework-builder` | 引导式概念框架建构，基于Ravitch & Riggan方法论 / Guided conceptual framework construction based on Ravitch & Riggan's methodology | `claude skill install https://github.com/yipng05-max/-skills/tree/main/conceptual-framework-builder` |
| `grounded-coding` | 扎根理论编码工具，支持开放编码、主轴编码，输出Excel / Grounded theory coding tool supporting open coding, axial coding, and Excel output | `claude skill install https://github.com/yipng05-max/-skills/tree/main/grounded-coding` |

### 数据处理 | Data Processing

| Skill | 功能 / Description | 安装 / Install |
|---|---|---|
| `text-to-excel` | 将结构化文本（表格/列表/JSON等）生成Excel文件 / Convert structured text (tables, lists, JSON, CSV, etc.) into formatted Excel files | `claude skill install https://github.com/yipng05-max/-skills/tree/main/text-to-excel` |

---

## 许可证 | License

MIT License © 一平博士 / Dr. Yiping · 学术志 / AcademicZhi
