# 学术论文评阅

对 Word（.docx）或 PDF 格式的学术论文进行专业评阅，生成带评阅标注的 Word 文档。支持两种输出模式：

- **可视化评阅**（默认推荐）：红色删除线标记删除、蓝色下划线标记新增、黄色底纹段落标记审稿意见。**兼容所有文字处理软件**（Word、WPS、LibreOffice、Pages）。
- **修订痕迹**：使用 Word OOXML tracked changes 格式。需要在 Microsoft Word 中开启「审阅→显示标记」查看。WPS 兼容性有限。

## 触发条件

当用户要求对 Word 或 PDF 文档论文进行评阅、审稿、修改、批注时触发。关键词包括：评阅论文、审稿、论文修改、Word修订、批注论文。支持 .docx 和 .pdf 格式。

## 脚本位置

所有脚本位于本 SKILL.md 同级的 `scripts/` 目录下：
- `scripts/apply_revisions.py` — 评阅标注处理引擎（支持 `visual` 和 `apply` 两种命令）

## 工作流程

### 第 1 步：获取论文文件路径

向用户确认 Word 文档的路径。如果用户只给了文件名，在常见位置搜索：
- ~/Downloads/
- ~/Documents/
- ~/Desktop/
- 当前工作目录

### 第 2 步：提取论文内容

```bash
python3 ${SKILL_DIR}/scripts/apply_revisions.py extract "<论文路径.docx或.pdf>"
```

这会输出带段落编号的 JSON，包含每段的 index、style、text。如果输入是 PDF，会自动先转为 DOCX 再提取。

### 第 3 步：逐段评阅论文

以资深社会学期刊审稿人的身份，对论文进行系统评阅。评阅维度包括：

**结构层面：**
- 标题是否精准反映研究内容
- 摘要是否包含研究问题、方法、核心发现和贡献
- 引言是否清晰建立了研究问题的合法性
- 文献综述是否展现了学术脉络而非简单罗列
- 研究方法部分是否足够透明、可信
- 分析与发现是否有充分的证据支撑
- 讨论与结论是否回应了研究问题

**语言层面：**
- 概念使用是否一致、精确
- 是否存在空话套话（如"随着XX的发展""具有重要意义"等）
- 论证是否遵循主张-证据-推理结构
- 段落是否有明确主题句

**学术规范层面：**
- 引用是否规范
- 理论使用是否深入（非贴标签式）
- 研究贡献表述是否具体

### 第 4 步：生成修订 JSON

**重要：必须通过 Python 脚本生成 JSON 文件**（不要用 Write 工具直接写 JSON，因为中文引号等特殊字符会导致编码错误）。

将评阅意见组织为 Python dict，用 `json.dump(data, f, ensure_ascii=False)` 写入临时文件。格式如下：

```python
import json
revisions = {
    "revisions": [
        {
            "type": "replace",
            "paragraph_index": 3,
            "old_text": "需要修改的原文片段（必须与文档中完全一致）",
            "new_text": "修改后的文本",
            "comment": "修改理由（中文，简明扼要）"
        },
        {
            "type": "comment",
            "paragraph_index": 5,
            "comment": "评阅意见（针对该段的问题或建议）"
        },
        {
            "type": "delete",
            "paragraph_index": 8,
            "old_text": "建议删除的文本",
            "comment": "删除理由"
        }
    ]
}
with open('/tmp/revisions.json', 'w', encoding='utf-8') as f:
    json.dump(revisions, f, ensure_ascii=False, indent=2)
```

**修订类型说明：**
- `replace`：文本替换。可视化模式显示为红色删除线（旧）+ 蓝色下划线（新）
- `comment`：仅添加审稿意见段落，不修改正文
- `delete`：标记删除。可视化模式显示为红色删除线

**重要原则：**
- `old_text` 必须与原文**完全一致**（包括标点），否则无法定位
- 每条 replace 的修改幅度要适当，不要一次替换整段
- 优先使用 `comment` 提出宏观建议（如结构调整、论证补充）
- 使用 `replace` 处理具体的语言和表述问题
- 评阅意见要专业、建设性，指出问题并给出改进方向

### 第 5 步：应用评阅标注并生成文档

**默认使用可视化模式（推荐）：**

```bash
python3 ${SKILL_DIR}/scripts/apply_revisions.py visual "<论文路径>" "<修订JSON路径>" "<输出路径>"
```

输出路径默认为 `原文件名_可视化评阅.docx`。

**如果用户明确要求 Word 修订痕迹模式：**

```bash
python3 ${SKILL_DIR}/scripts/apply_revisions.py apply "<论文路径>" "<修订JSON路径>" "<输出路径>"
```

输出路径默认为 `原文件名_评阅修订.docx`。

### 第 6 步：告知用户结果

告知用户：
1. 输出文件的位置
2. 共提出了多少条修订和批注
3. 可视化模式下的标注说明：
   - 红色删除线 = 建议删除的文字
   - 蓝色下划线 = 建议替换的新文字
   - 橙色边框黄色底纹段落 = 【审稿意见】
4. 原始文件不会被修改

## 评阅语气与标准

- 以**匿名审稿人**口吻撰写评审意见
- 批判性优先，但保持建设性
- 指出问题时要具体，给出改进方向
- 区分"必须修改"和"建议修改"
- 语言问题直接给出修改方案（replace）
- 结构和论证问题用批注说明（comment）

## 依赖

- Python 3.x
- python-docx（`pip install python-docx`）
- lxml（通常随 python-docx 安装）
- pdf2docx（`pip install pdf2docx`）— PDF 支持所需
