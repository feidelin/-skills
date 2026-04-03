---
name: foreign-literature-search
description: >
  外文学术文献检索工具（社会科学方向）。当用户提供研究关键词时，自动构建英文检索式，
  通过 WebSearch 在 Google Scholar 及 SSCI 社会学核心期刊站点检索相关文献，
  提取题录信息（标题、作者、年份、期刊、摘要、DOI），同步生成适用于
  Web of Science / Scopus 的布尔检索式供用户在机构数据库中使用，
  最终将结果保存为 Excel 文件。
  触发条件：用户说"帮我检索外文文献""搜索英文文献""Google Scholar 检索"
  "SSCI文献检索""WoS检索式""检索外文资料""找相关英文论文"，
  或在 ta-research-AFP / ta-research-workflow 到达文献检索检查点时。
---

# 外文学术文献检索工具（社会科学方向）

通过 WebSearch 系统检索外文文献，同步生成 WoS/Scopus 布尔检索式。
无需机构账号即可运行；布尔检索式供有数据库权限时手动使用。

---

## Step 0：解析关键词与语言处理

从用户输入中提取研究关键词，执行以下处理：

### 0.1 中译英

若用户提供中文关键词，自动翻译为英文并给出同义词/近义词扩展：

| 中文 | 英文主词 | 同义词扩展 |
|------|---------|----------|
| 平台经济 | platform economy | platform labor / gig economy / digital platform |
| 数字劳动 | digital labor | platform work / crowdwork / algorithmic management |
| 社会流动 | social mobility | upward mobility / status attainment |
| 身份认同 | identity | self-concept / identification / identity construction |

### 0.2 构建检索组

多个概念之间用 AND 连接，同义词之间用 OR 连接：

```
示例：研究"平台工人的身份认同"
→ 检索式：
  ("platform worker" OR "gig worker" OR "platform labor")
  AND
  ("identity" OR "self-concept" OR "identification")
```

### 0.3 确认

向用户展示翻译结果和检索分组，确认后再执行检索。
若用户已提供英文关键词，直接构建检索组，无需翻译。

---

## Step 1：生成 WoS/Scopus 布尔检索式

在执行 WebSearch 之前，先输出布尔检索式供用户在机构数据库使用：

```
━━ Web of Science / Scopus 检索式 ━━━━━━━━━━━━━━━━━━━━━━
TS = (
  ("platform worker" OR "gig worker" OR "platform labor" OR "crowdwork")
  AND
  ("identity" OR "self-concept" OR "identification" OR "identity construction")
)

WoS 筛选建议：
  数据库：Web of Science Core Collection
  版本限定：WOS.SSCI（社会科学引文索引）
  时间范围：2015–2025（可根据需要调整）
  排序方式：Times Cited - descending（被引量降序）

Scopus 检索式（等价）：
  TITLE-ABS-KEY(("platform worker" OR "gig worker" OR "platform labor")
  AND ("identity" OR "self-concept" OR "identification"))
  AND SUBJAREA(SOCI OR PSYC OR ECON)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 2：WebSearch 多轮检索

通过 3 轮 WebSearch 系统覆盖目标文献：

### 第一轮：Google Scholar 综合检索

构建检索查询，优先找高被引综述和奠基性文献：

```
搜索词模板：
"{核心词A}" "{核心词B}" site:scholar.google.com
"{核心词A}" "{核心词B}" review sociology
"{核心词A}" "{核心词B}" seminal theory
```

### 第二轮：SSCI 社会学核心期刊定向检索

针对以下期刊站点执行定向搜索：

**顶级综合社会学期刊**
- American Journal of Sociology (AJS)：`site:journals.uchicago.edu/journal/ajs`
- American Sociological Review (ASR)：`site:journals.sagepub.com/home/asr`
- Social Forces：`site:academic.oup.com/sf`
- Theory and Society：`site:link.springer.com/journal/11186`
- Annual Review of Sociology：`site:annualreviews.org/journal/soc`

**数字社会学 / 劳工 / 组织方向**
- Work, Employment and Society：`site:journals.sagepub.com/home/wes`
- New Media & Society：`site:journals.sagepub.com/home/nms`
- Organization Studies：`site:journals.sagepub.com/home/oss`
- Information, Communication & Society：`site:tandfonline.com/journals/rics20`

**综合社会科学**
- Social Science Research：`site:sciencedirect.com/journal/social-science-research`
- Current Sociology：`site:journals.sagepub.com/home/csi`

检索词格式：`"{核心词A}" "{核心词B}" site:[期刊站点]`

### 第三轮：近5年新文献补充

针对近5年文献做补充检索，确保覆盖最新进展：

```
"{核心词A}" "{核心词B}" 2020 2021 2022 2023 2024 sociology
```

---

## Step 3：文献筛选与信息提取

### 3.1 筛选标准

从 WebSearch 结果中筛选符合以下条件的文献：

| 优先级 | 标准 |
|--------|------|
| P1（必选）| SSCI 来源期刊 + 主题高度相关 |
| P2（优先）| 被引量高（100次以上） |
| P3（补充）| 近5年发表（2020-2025） |
| 排除 | 书评、会议论文（非期刊）、非学术来源 |

### 3.2 提取字段

每篇文献提取以下信息：

| 字段 | 说明 |
|------|------|
| 序号 | 1-N |
| 标题 | 英文原标题 |
| 作者 | 所有作者（Last, F.M. 格式） |
| 年份 | 发表年份 |
| 期刊 | 完整期刊名 |
| 卷期页 | Volume(Issue): Pages |
| DOI/URL | 可访问链接（优先 DOI） |
| 摘要 | 英文摘要（如可获取） |
| 被引次数 | 若 WebSearch 结果中包含 |
| SSCI 标注 | ✅ 已确认 / ⚠️ 待核实 |

### 3.3 去重

检查三轮检索结果中的重复文献，以第一次出现的记录为准。

---

## Step 4：输出检索报告

在保存 Excel 之前，输出检索摘要：

```
━━ 外文文献检索报告 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
检索主题：[研究主题]
检索词：[英文检索组]
检索时间：[日期]
──────────────────────────────────────────────────────
检索来源：
  · Google Scholar（综合）：[N] 篇相关
  · 定向期刊检索：[N] 篇相关
  · 近5年补充：[N] 篇相关
  · 去重后总计：[N] 篇
──────────────────────────────────────────────────────
期刊分布（前5）：
  1. [期刊名] — [N] 篇
  2. [期刊名] — [N] 篇
  ...
年份分布：
  2020-2025：[N] 篇 | 2015-2019：[N] 篇 | 2015前：[N] 篇
──────────────────────────────────────────────────────
⚠️ 提示：以下文献需通过机构数据库确认全文访问权限。
   建议将 WoS 检索式（Step 1）在机构 VPN 环境下运行以获取完整结果。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 5：保存为 Excel

### 5.1 生成 Excel 文件

```python
import json
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from datetime import date

wb = Workbook()

# Sheet 1: 文献列表
ws1 = wb.active
ws1.title = "文献列表"

headers = ["序号", "标题", "作者", "年份", "期刊", "卷期页", "DOI/URL", "摘要", "被引次数", "SSCI"]
header_fill = PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")
header_font = Font(bold=True, size=11, color="FFFFFF")

for col, h in enumerate(headers, 1):
    cell = ws1.cell(row=1, column=col, value=h)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal='center', vertical='center')

for i, article in enumerate(articles, 1):
    ws1.cell(row=i+1, column=1, value=i)
    ws1.cell(row=i+1, column=2, value=article.get('title', ''))
    ws1.cell(row=i+1, column=3, value=article.get('authors', ''))
    ws1.cell(row=i+1, column=4, value=article.get('year', ''))
    ws1.cell(row=i+1, column=5, value=article.get('journal', ''))
    ws1.cell(row=i+1, column=6, value=article.get('volume_issue_pages', ''))
    ws1.cell(row=i+1, column=7, value=article.get('doi_url', ''))
    cell = ws1.cell(row=i+1, column=8, value=article.get('abstract', ''))
    cell.alignment = Alignment(wrap_text=True, vertical='top')
    ws1.cell(row=i+1, column=9, value=article.get('citations', ''))
    ws1.cell(row=i+1, column=10, value=article.get('ssci', ''))

ws1.column_dimensions['A'].width = 6
ws1.column_dimensions['B'].width = 55
ws1.column_dimensions['C'].width = 25
ws1.column_dimensions['D'].width = 8
ws1.column_dimensions['E'].width = 30
ws1.column_dimensions['F'].width = 18
ws1.column_dimensions['G'].width = 35
ws1.column_dimensions['H'].width = 80
ws1.column_dimensions['I'].width = 10
ws1.column_dimensions['J'].width = 8

ws1.auto_filter.ref = ws1.dimensions
ws1.freeze_panes = 'A2'

# Sheet 2: 检索式留存
ws2 = wb.create_sheet("检索式")
ws2['A1'] = "WoS 检索式"
ws2['A1'].font = Font(bold=True)
ws2['A2'] = wos_query  # Step 1 生成的检索式
ws2['A2'].alignment = Alignment(wrap_text=True)
ws2.column_dimensions['A'].width = 80

today = date.today().strftime('%Y%m%d')
keyword_abbr = keywords_abbr  # 关键词缩写，如 "platform-identity"
output_path = f"~/Downloads/外文文献检索_{keyword_abbr}_{today}.xlsx"
wb.save(output_path)
```

安装依赖：`pip3 install openpyxl`

文件保存至：`~/Downloads/外文文献检索_{关键词缩写}_{日期}.xlsx`

---

## Step 6：移交 literature-verifier（可选）

若在 `ta-research-AFP` 或 `ta-research-workflow` 中调用，检索结果自动传递给后续的文献核查与综述写作步骤。

若单独使用，告知研究者：
> "外文文献检索完成，已保存至 `外文文献检索_{关键词}_{日期}.xlsx`。
> 建议将 Sheet 2 中的 WoS 检索式在机构数据库中运行，补充 WebSearch 无法触达的全文记录。
> 如需核查文献真实性，可调用 `literature-verifier`。"

---

## 注意事项

- **WebSearch 覆盖有限**：无法替代机构数据库的完整检索；WoS 检索式是对 WebSearch 结果的重要补充
- **摘要完整性**：WebSearch 返回的摘要可能被截断，完整摘要需通过 DOI 链接访问原文
- **SSCI 标注**：标注"✅ 已确认"的来自已知 SSCI 期刊站点；标注"⚠️ 待核实"的来自综合搜索结果，需研究者自行确认期刊级别
- **被引次数**：若 WebSearch 结果未提供，填"—"，可在 Google Scholar 手动查阅
- **语言**：默认检索英文文献；如需法语/德语/西班牙语文献，请在启动时声明

## 与 cnki-advanced-search 的配合使用

外文检索与知网检索互为补充，建议双轨并行：

| | cnki-advanced-search | foreign-literature-search |
|---|---|---|
| 覆盖 | CSSCI 中文期刊 | SSCI 英文期刊 |
| 检索方式 | 浏览器自动化 | WebSearch + 布尔检索式 |
| 适合 | C刊投稿文献综述 | SSCI投稿 / 理论对话 |
| 互补点 | 中国本土研究 | 国际理论与方法进展 |
