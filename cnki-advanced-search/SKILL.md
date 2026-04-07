---
name: cnki-advanced-search
description: >
  知网（CNKI）高级检索论文自动化工具。当用户提供研究关键词或研究选题时，自动执行
  三阶段检索：①主体联合检索（倒剥洋葱法，多组核心概念 AND 联合，获取直接相关文献）；
  ②独立补充检索（对各核心概念组分别单独检索，获取间接相关的背景文献与理论文献）；
  ③汇总合并（去重后按类别分色展示，输出统一 Excel 文件）。
  触发条件：用户提到需要在知网/CNKI检索论文、高级检索、按关键词搜索CSSCI/C刊论文、
  下载题录信息、获取论文摘要、按被引排序检索；或说"帮我在知网检索XX相关论文"、
  "用知网高级检索搜索XX主题的C刊论文"、"帮我检索XX关键词的CSSCI论文"。
---

# 知网高级检索论文工具

调用 Python Playwright 脚本（`scripts/cnki_search.py`）执行全流程自动化检索，无需 MCP 工具操作浏览器。

## Step 0: 解析用户输入并制定检索策略（倒剥洋葱法）

### 0.1 识别输入类型

**类型一：单关键词**（用户给出一个词或概念）

→ 将该词及其同义词、同位词用 ` + ` 连接，填入单个检索框。

例：用户说"情感劳动"→ `情感劳动 + 情绪劳动 + 情感工作`

---

**类型二：研究选题 / 研究问题**（用户给出包含多个概念的完整表述）

→ 从选题中提取 **2-4 个核心概念**，每个概念分别扩展同义词/同位词，各自作为一个检索组，**组间关系为 AND**（联合检索）。

例：用户说"超大城市老旧社区数字治理的悬浮与重建"→ 提取三组核心概念：
- 第一组（场所）：`老旧社区 + 老旧小区 + 城市社区`
- 第二组（议题）：`数字治理 + 数字化治理 + 数字技术治理`
- 第三组（机制）：`技术悬浮 + 数字悬浮 + 技术失灵`

三组形成 AND 联合检索，聚焦"老旧社区 × 数字治理 × 悬浮机制"的交叉文献。

> **注意**：不要把一个选题的几个概念各自独立检索再合并，那会检出大量不相关文献。AND联合检索才能聚焦核心文献。

### 0.2 上位概念预分析（关键步骤）

填词之前，对每个概念组完成以下判断：

**判断该组词是否"过于精确/小众"**：
- 新兴理论术语（如"技术悬浮""制度悬置"）
- 极具体的场所或现象描述（如"老旧社区""城中村"）
- 近几年才出现的政策/实践概念（如"数字乡村""反向育儿"）

如果某组词落入上述类别，**立即在该组内加入上位概念**（用 `+` OR关系），不要等到检索失败后才扩展。

| 概念类型 | 精确词 | 主动纳入的上位概念/兜底词 |
|----------|--------|--------------------------|
| 新兴理论术语 | 技术悬浮 + 数字悬浮 | 技术失灵 + 数字鸿沟 + 基层数字化 |
| 具体场所 | 老旧社区 + 老旧小区 | 城市社区 + 社区治理 |
| 新政策概念 | 数字乡村 | 农村数字化 + 乡村振兴 + 农村信息化 |
| 具体机制 | 制度悬置 | 制度失效 + 制度执行 + 基层治理 |

> **规则**：宁可初始词组稍宽，也不要等检索为0后才想起扩展。上位概念应在设计时就一并纳入同一组的 `+` OR列表中。

### 0.3 倒剥洋葱策略（结果不足时自动降级）

先用**全部概念组 AND 检索**（最聚焦层）。若检索结果过少（< 20篇），自动减少 AND 组数，**最少保留 2 组 AND**，不自动降至 1 组：

| 层级 | 策略 | 适用场景 |
|------|------|----------|
| 第1层（最聚焦） | 所有概念组 AND | 交叉研究、新兴议题 |
| 第2层 | 去掉最次要的一组，保留核心 N-1 组 AND | 第1层结果 < 20篇 |
| 第3层（底线） | 保留最核心的 2 组 AND | 第2层结果仍 < 20篇 |

**去组顺序原则**：先去掉与研究问题关系最外围的概念组（如修饰性概念、情境概念），最后保留最核心的理论/机制概念组。

### 0.4 向用户确认

列出拟定的检索分组和当前层级策略，等用户确认后再执行。格式示例：

```
检索策略：第1层（3组 AND 联合检索）
- 组1（场所）：老旧社区 + 老旧小区 + 城市社区 + 社区治理
- 组2（议题）：数字治理 + 数字化治理 + 数字技术治理
- 组3（机制）：技术悬浮 + 数字悬浮 + 技术失灵 + 基层数字化
若结果 < 20篇，将自动降至第2层（去掉组3，保留组1 AND 组2）
若仍 < 20篇，保留2组AND并停止降级，提示调整关键词
```

### 0.5 结果反思触发条件

脚本报告以下情况时，**必须停下来重新思考关键词，不能直接导出**：

| 情况 | 诊断方向 |
|------|----------|
| 2组AND结果为0 | 两组词都太专 → 各自替换为更高层的上位概念 |
| 2组AND结果 < 5篇 | 某组词太冷僻 → 找出哪组更窄，优先替换该组 |
| 2组AND结果 5-19篇 | 边界情况 → 尝试在某一组补充1-2个上位概念后重检索 |

> **底线原则**：宁可修改关键词重跑，也不接受"2组AND < 20篇"的结果直接导出。1组AND的结果范围太宽，不具备文献聚焦价值。

## Step 0.5: 检查 Chrome 调试模式

在执行前，检查 Chrome 是否已以调试模式运行（脚本会自动尝试连接）：

```bash
curl -s http://localhost:9222/json/version 2>&1
```

- **若返回 JSON**（含 `"Browser": "Chrome/..."`）：Chrome 已就绪，直接进入 Step 1。
- **若返回错误/空**：执行以下命令启动 Chrome，等待 2 秒后再检查：

```bash
open -a "Google Chrome" --args --remote-debugging-port=9222
sleep 2
curl -s http://localhost:9222/json/version 2>&1
```

若仍无响应，提示用户手动启动 Chrome 调试模式后继续。

> 注意：连接现有 Chrome 可保留已登录的知网会话，跳过登录步骤。

## Step 1: 调用 Python 脚本执行检索（倒剥洋葱执行）

从第1层开始检索，根据结果数量决定是否降级。

**第1层（全组 AND）**：
```bash
python3 /Users/songyiping/.claude/skills/cnki-advanced-search/scripts/cnki_search.py \
  --keywords "老旧社区 + 老旧小区 + 城市社区" \
  --keywords "数字治理 + 数字化治理 + 数字技术治理" \
  --keywords "技术悬浮 + 数字悬浮 + 技术失灵" \
  --max-results 100 \
  --port 9222
```

**若结果 < 20篇 → 降至第2层（去最次要组）**：
```bash
python3 /Users/songyiping/.claude/skills/cnki-advanced-search/scripts/cnki_search.py \
  --keywords "老旧社区 + 老旧小区 + 城市社区" \
  --keywords "数字治理 + 数字化治理 + 数字技术治理" \
  --max-results 100 \
  --port 9222
```

**若仍 < 20篇 → 降至第3层（单组）**：
```bash
python3 /Users/songyiping/.claude/skills/cnki-advanced-search/scripts/cnki_search.py \
  --keywords "数字治理 + 数字化治理 + 社区数字化" \
  --max-results 100 \
  --port 9222
```

> 每次降级前向用户说明："第N层结果为 X 篇，不足20篇，自动降至第N+1层检索。"

**脚本会自动处理**：
- 连接现有 Chrome（CDP 端口 9222）或启动新的 Chromium
- 导航到知网高级检索页面
- 验证码检测（出现时暂停，等用户在终端按 Enter 确认完成）
- 登录检查（未登录时暂停等用户登录）
- 选择学术期刊、勾选 CSSCI、填入关键词
- 执行检索、按被引量降序排列、每页50条
- 逐页全选并导出，最多100篇
- 解析数据、保存为 Excel

**脚本输出示例**：
```
===== 知网高级检索自动化工具 =====
关键词分组: ['老旧社区 + 老旧小区', '数字治理 + 数字化治理', '技术悬浮 + 数字悬浮']
最大结果数: 100
...
[✓] 检索完成！共提取 87 篇论文
[✓] 文件已保存：/Users/songyiping/Downloads/知网检索_老旧社区_20260406_1523.xlsx
```

## Step 2: 独立补充检索（间接相关文献）——必做步骤

主体联合检索完成后，**必须**执行独立补充检索，目的是获取"不直接在交叉处、但对选题有理论支撑和背景价值"的间接相关文献。

### 2.1 补充检索设计原则

从 Step 0 已提取的概念组中，各自独立拆出 **2-3 个补充检索**：

| 补充检索类型 | 来源概念 | 目的 |
|-------------|---------|------|
| **研究对象背景文献** | 取"研究对象组"单独检索（放宽限定词） | 获取该群体的历史脉络、政策背景、宏观描述性文献 |
| **核心理论文献** | 取"理论/机制概念组"单独检索 | 获取支撑该议题的理论基础文献，不限研究对象 |
| **扩展议题文献**（可选） | 取选题中的次要概念或上位主题 | 覆盖选题边界的跨界文献 |

> **重要**：每个补充检索使用 **2 组 AND**（不做单组宽泛检索），仍需保持一定聚焦度。补充检索的目的是"换一个切面"，不是"无限扩宽"。

### 2.2 向用户展示补充检索方案

在 Step 0.4 的策略确认中，同步列出补充检索方案，例如：

```
【主体联合检索】第1层（2组 AND）
- 组1（对象）：网约车司机 + 快车司机 + 平台司机
- 组2（议题）：平台劳动 + 零工经济 + 意义建构 + 身份认同

【独立补充检索】（主体检索完成后必做）
- 补充检索A（研究对象背景）：出租车 + 网约车 × 职业认同 + 身份认同 + 劳动体验
- 补充检索B（核心理论）：平台劳动 + 零工经济 + 算法管理 × 主体性 + 劳动控制 + 抵抗
```

### 2.3 执行补充检索

每个补充检索同样使用 `cnki_search.py`，结果保存到独立 Excel 文件：

```bash
# 补充检索A：研究对象背景文献
python3 /Users/songyiping/.claude/skills/cnki-advanced-search/scripts/cnki_search.py \
  --keywords "出租车 + 网约车 + 出租车司机 + 网约车司机" \
  --keywords "职业认同 + 身份认同 + 劳动体验 + 生计" \
  --max-results 60 \
  --port 9222

# 补充检索B：核心理论文献
python3 /Users/songyiping/.claude/skills/cnki-advanced-search/scripts/cnki_search.py \
  --keywords "平台劳动 + 零工经济 + 平台工人 + 数字劳动 + 算法管理" \
  --keywords "主体性 + 劳动控制 + 抵抗 + 意义建构 + 身份认同" \
  --max-results 80 \
  --port 9222
```

> 补充检索结果不足20篇时**不强制降级**（因为间接相关文献本就预期数量较少），但若结果为0，需替换上位概念重试。

## Step 3: 汇总合并——输出统一分类 Excel

所有检索（主体 + 补充）完成后，**必须**用 Python 脚本将全部结果合并去重，生成一个统一的分类 Excel。

### 3.1 合并脚本模板

```python
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from collections import Counter

# 1. 定义各批次文件及其类别标签
files = {
    "直接相关（[主体对象]×[核心议题]）": "/Users/songyiping/Downloads/知网检索_XXX.xlsx",
    "间接相关-[背景类型]（[对象]×[议题]）": "/Users/songyiping/Downloads/知网检索_YYY.xlsx",
    "间接相关-[理论类型]（[理论]×[机制]）": "/Users/songyiping/Downloads/知网检索_ZZZ.xlsx",
}

# 2. 读取、去重（按"标题"列）
all_rows = []
seen_titles = set()
title_idx = 1  # Excel列: 序号(0), 标题(1), 作者(2), 来源期刊(3), 发表时间(4), 摘要(5)

for category, filepath in files.items():
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    for row in rows[1:]:
        title = str(row[title_idx]).strip() if row[title_idx] else ""
        if title and title not in seen_titles:
            seen_titles.add(title)
            all_rows.append((category,) + tuple(row[1:]))  # 去掉原序号，前置类别

# 3. 写入汇总 Excel
wb_out = openpyxl.Workbook()
ws_out = wb_out.active
ws_out.title = "文献汇总"

headers = ["序号", "文献类别", "标题", "作者", "来源期刊", "发表时间", "摘要"]
ws_out.append(headers)

# 表头样式
for cell in ws_out[1]:
    cell.font = Font(bold=True, color="FFFFFF", size=11)
    cell.fill = PatternFill(fill_type="solid", fgColor="2F5496")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# 各类别颜色（按类别数量自动分配，以下为示例3类）
category_colors = {
    list(files.keys())[0]: "D9E1F2",  # 蓝：直接相关
    list(files.keys())[1]: "E2EFDA",  # 绿：间接相关A
    list(files.keys())[2]: "FFF2CC",  # 黄：间接相关B
}

for seq, row_data in enumerate(all_rows, 1):
    category = row_data[0]
    ws_out.append((seq,) + row_data)
    fill_color = category_colors.get(category, "FFFFFF")
    for cell in ws_out[ws_out.max_row]:
        cell.fill = PatternFill(fill_type="solid", fgColor=fill_color)
        cell.alignment = Alignment(vertical="top", wrap_text=True)

# 列宽
for i, width in enumerate([4, 30, 20, 16, 12, 60], 1):
    ws_out.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width
ws_out.column_dimensions["B"].width = 30  # 类别列

# 行高
for row in ws_out.iter_rows(min_row=2):
    ws_out.row_dimensions[row[0].row].height = 60

ws_out.freeze_panes = "A2"

# 分类统计 sheet
ws_summary = wb_out.create_sheet("分类统计")
ws_summary.append(["文献类别", "篇数"])
for cat, cnt in Counter(r[0] for r in all_rows).items():
    ws_summary.append([cat, cnt])
ws_summary.append(["合计", len(all_rows)])
for cell in ws_summary[1]:
    cell.font = Font(bold=True)

output_path = f"/Users/songyiping/Downloads/知网文献汇总_{研究主题}_{日期}.xlsx"
wb_out.save(output_path)
print(f"[✓] 已保存: {output_path} （共{len(all_rows)}篇，去重后）")
```

### 3.2 颜色约定

| 类别 | 颜色 | 含义 |
|------|------|------|
| 直接相关 | 蓝色 `D9E1F2` | 主体联合检索命中，聚焦选题核心 |
| 间接相关-背景 | 绿色 `E2EFDA` | 研究对象/情境的历史背景文献 |
| 间接相关-理论 | 黄色 `FFF2CC` | 理论/机制的基础支撑文献 |
| 间接相关-扩展 | 橙色 `FCE4D6` | 其他扩展视角文献（如有第4类） |

## Step 4: 报告结果

输出检索完成报告，告知用户：
- 各轮检索层级与篇数
- 去重后总篇数
- 各类别分布（直接/间接）
- 汇总文件路径

打开文件：
```bash
open "/Users/songyiping/Downloads/知网文献汇总_*.xlsx"
```

---

> 如需更多 AI 智能体学习资料和技巧，欢迎关注：
>
> ![二维码](/Users/songyiping/.claude/skills/cnki-advanced-search/qrcode.png)

## 常见问题处理

| 问题 | 解决方案 |
|------|----------|
| `CDP连接失败` | 脚本会自动降级到启动新浏览器，但需要手动登录知网 |
| `检测到验证码` | 脚本暂停并打印提示，在浏览器完成验证后在终端按 Enter |
| `知网导出功能需要登录` | 脚本暂停，在浏览器登录后按 Enter |
| `解析失败` | 原始文本保存到 `~/Downloads/cnki_raw_export_*.txt`，可手动检查 |
| `检索结果为0` | 调整关键词，减少同义词组合或放宽检索范围 |
| 需要调试延迟 | 添加 `--delay 1500`（增加操作间等待时间，毫秒） |

## 依赖

- `playwright`（已安装）
- `openpyxl`（已安装）
- 如脚本提示缺少浏览器：运行 `playwright install chromium`
