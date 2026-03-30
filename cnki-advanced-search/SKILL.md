---
name: cnki-advanced-search
description: >
  知网（CNKI）高级检索论文自动化工具。当用户提供研究关键词（一组或多组）时，自动在知网
  高级检索页面模拟人类检索行为：选择学术期刊类别、勾选CSSCI来源、输入主题关键词（含同义词
  和同位词，用 + 连接）、多组关键词用AND关系连接，检索后按被引量排序、切换50条/页、
  逐页全选检索结果（每页50条），然后通过"导出与分析"→"导出文献"→"查新（引文格式）"
  导出完整题录和摘要信息，最终提取前100篇（不足100篇则全部）论文信息并保存为Excel文件。
  触发条件：用户提到需要在知网/CNKI检索论文、高级检索、按关键词搜索CSSCI/C刊论文、
  下载题录信息、获取论文摘要、按被引排序检索；或说"帮我在知网检索XX相关论文"、
  "用知网高级检索搜索XX主题的C刊论文"、"帮我检索XX关键词的CSSCI论文"。
---

# 知网高级检索论文工具

使用Chrome DevTools MCP工具在知网高级检索页面自动执行检索操作，提取CSSCI来源期刊论文的题录和摘要信息。

## Step 0: 解析用户关键词

从用户输入中提取检索关键词，组织为检索表达式：

- **单组关键词**：关键词及其同义词/同位词用 ` + ` 连接（+前后各一个空格），填入同一个主题检索框
  - 例：用户说"数字化转型"→ 检索词为 `数字化转型 + 数字化变革 + 数字化`
- **多组关键词**：每组填入独立的主题检索框，组间关系保持AND（默认即为AND）
  - 例：用户说"数字化转型与企业绩效"→ 第一组 `数字化转型 + 数字化变革`，AND，第二组 `企业绩效 + 企业业绩 + 组织绩效`

向用户确认关键词分组和同义词扩展后再执行检索。

## Step 1: 打开知网高级检索页面

```
navigate_page → https://kns.cnki.net/kns8s/AdvSearch
```

**验证码处理**：snapshot中可能始终存在"拖动下方拼图完成验证"或"安全验证"文本（隐藏DOM元素），**不能仅凭snapshot文本判断验证码是否出现**。必须用 `take_screenshot` 截图查看页面实际显示状态：
- 若截图中**可见**验证码滑块弹窗遮挡页面，才提示用户：
  > "知网需要安全验证，请在浏览器中完成滑块验证，完成后告诉我。"
- 若截图中页面正常显示检索表单（无遮挡），则直接继续下一步，无需提示用户。

等用户确认后继续（仅在确认验证码实际可见时）。

## Step 2: 选择"学术期刊"类别

take_snapshot查看页面，找到底部类别选项卡，点击"学术期刊"链接。

页面会刷新检索表单，出现来源类别选项（CSSCI、SCI、北大核心等）。

## Step 3: 勾选CSSCI来源类别

take_snapshot确认来源类别区域已显示，找到"CSSCI"对应的checkbox元素并点击勾选。

先取消"全部期刊"的勾选（如已勾选），再勾选"CSSCI"。

## Step 4: 输入主题检索词

### 4.1 第一组关键词

找到第一个"主题"检索框（默认已存在），用fill工具输入第一组关键词表达式。

示例：`数字化转型 + 数字化变革 + 数字化`

### 4.2 多组关键词（如有）

若有多组关键词：

1. **点击"+"按钮**添加新检索行
2. take_snapshot查看新增行
3. **修改新增行的检索字段类型**：新增行默认可能不是"主题"，需点击字段类型下拉框，选择"主题"
4. **确认逻辑运算符为AND**：两行之间的运算符下拉框默认为"AND"，保持不变即可
5. **填入第二组关键词**：在新增行的检索框中fill第二组关键词表达式

重复以上步骤添加更多组。

### 运算符说明

知网高级检索框内的运算符：
- `+`（或）：前后各留一个空格，如 `关键词A + 关键词B`
- `*`（与）：前后各留一个空格
- `-`（非）：前后各留一个空格

## Step 5: 执行检索

点击"检索"按钮，等待结果页加载。

```
wait_for → "检索结果" 或等待结果列表出现
```

若出现验证码，提示用户完成后重试。

## Step 6: 按被引量排序

在检索结果页take_snapshot，找到排序选项区域，点击"被引"排序按钮使结果按被引数量从高到低排列。

**注意**：可能需要点击两次（第一次升序，第二次降序）。点击后take_snapshot确认排序方向为降序（被引最多的在前，第一篇论文的被引数应最大）。

## Step 7: 切换每页显示50条

take_snapshot查看分页区域，找到每页显示数量的下拉选项或链接（默认20条），切换为50条。

**实操要点**：
- 页面底部有 `#perPageDiv` 区域，包含 `20 | 50` 的选项
- 点击"50"后等待页面重新加载
- take_snapshot确认页面已显示50条结果

## Step 8: 逐页全选检索结果

在检索结果页面，逐页勾选论文，直到选满100篇或全部论文被选中。

### 8.1 第一页全选

**关键：使用evaluate_script操作全选checkbox，比MCP click更稳定。**

```javascript
// 全选checkbox的ID为 selectCheckAll1
evaluate_script → () => {
  const cb = document.querySelector('#selectCheckAll1');
  if (cb) { cb.click(); return 'clicked'; }
  return 'not found';
}
```

点击后验证选中数量：
```javascript
evaluate_script → () => {
  const el = document.querySelector('#selectCount');
  return el ? el.textContent : 'not found';
}
```

应显示"50"（或当前页实际结果数）。

### 8.2 翻页并继续全选

1. 若总结果超过50篇且已选数量不足100篇，点击"下一页"按钮翻到第二页
2. 等待页面加载完成（take_snapshot确认新一页内容已显示，页码变为"2/N"）
3. 再次用evaluate_script点击 `#selectCheckAll1` 全选第二页
4. 验证 `#selectCount` 显示"100"

若总结果不足100篇，则有多少页就全选多少页，全部选中即可。

**注意**：每次翻页后，之前页面的选中状态会被知网保留，无需担心丢失。

## Step 9: 导出文献（查新引文格式）——关键步骤

> **重要警告**：此步骤是整个流程中最容易出错的环节。知网导出菜单使用jQuery委托事件，
> 普通的MCP click或JS `.click()` 无法触发导出操作。必须按照下方的JS直接调用方式执行。

### 9.1 检查登录状态（前置条件）

**导出功能要求用户已登录知网**。在尝试导出前，必须先检查登录状态：

```javascript
evaluate_script → () => { return typeof islogin === 'function' ? islogin() : 'no islogin'; }
```

- 若返回 `true`：已登录，继续导出
- 若返回 `false`：**必须提示用户先登录**：
  > "知网导出功能需要登录，请在浏览器中登录知网账号，完成后告诉我。"

  等用户确认后，重新检查 `islogin()` 返回 `true` 再继续。

**若出现登录弹窗遮挡页面**，用以下方式关闭：
```javascript
evaluate_script → () => {
  const panel = document.querySelector('.ecp_header_login_area');
  if (panel) panel.style.display = 'none';
  return 'done';
}
```

### 9.2 通过JS直接调用导出（推荐方式，绕过UI交互）

**不要尝试通过hover/click操作下拉菜单**，直接用evaluate_script调用知网内部函数：

```javascript
evaluate_script → () => {
  // 获取导出所需的三个参数
  const filename = $.filenameGet();
  const searchinfo = $.searchinfoGet();
  const mapIndex = $.indexGet();

  // 获取导出管理URL（隐藏input中存储）
  const baseUrl = document.querySelector('#hidDocumentManageUrl')?.value
                  || 'https://kns.cnki.net/dm8';
  const exportUrl = baseUrl + '/manage/export.html?language=CHS&uniplatform=NZKPT';

  // 调用知网内置的PostWindow函数打开导出页面
  $.PostWindow(exportUrl, {
    displaymode: 'NEW',
    filename: filename,
    searchinfo: searchinfo,
    mapIndex: mapIndex
  });

  return JSON.stringify({ exportUrl, filename: filename?.substring(0, 50), mapIndex });
}
```

**注意事项**：
- `$.PostWindow()` 会创建一个隐藏form并submit到新窗口，导出页面会在新标签页打开
- 如果 `$.filenameGet` 等函数不存在，说明页面JS未完全加载，需等待后重试
- 若 `islogin()` 为 `false` 时调用，会打开 `member.cnki.net` 登录页而非导出页

### 9.3 切换到导出页面

导出页面在新窗口中打开，需要找到并切换到它：

```
list_pages → 查看所有打开的页面
```

找到URL包含 `export.html` 的页面（通常是 `https://kns.cnki.net/dm8/manage/export.html`），然后：

```
select_page → 选择该页面的pageId
```

**异常处理**：
- 若出现 `member.cnki.net` 页面：说明未登录，关闭该页面，提示用户登录后重新执行 Step 9
- 若没有新页面出现：等待2-3秒后再次 `list_pages`，或重新执行 Step 9.2

### 9.4 在导出页面选择"查新（引文格式）"

切换到导出页面后：

1. take_snapshot 查看导出页面的格式选项
2. 找到"查新（引文格式）"标签/选项并点击
3. 等待页面刷新显示查新引文格式的完整内容（包含摘要信息）

### 9.5 提取导出数据

使用以下evaluate_script提取所有论文数据，**返回base64编码的JSON**（避免中文字符传输问题）：

```javascript
evaluate_script → () => {
  const body = document.body.innerText;
  const startIdx = body.indexOf('[1]\n');
  if (startIdx < 0) return JSON.stringify({error: 'not found', preview: body.substring(0, 300)});

  const articleText = body.substring(startIdx);
  const parts = articleText.split(/\[(\d+)\]\n/);

  const articles = [];
  for (let i = 1; i < parts.length; i += 2) {
    const num = parseInt(parts[i]);
    const content = parts[i + 1] ? parts[i + 1].trim() : '';
    if (!content) continue;

    // 分离引文行和摘要
    const abstractIdx = content.indexOf('\n摘要:');
    const abstractIdx2 = content.indexOf('\n摘要：');
    const absIdx = abstractIdx >= 0 ? abstractIdx : abstractIdx2;

    const citationLine = absIdx >= 0 ? content.substring(0, absIdx).trim() : content.trim();
    const abstract = absIdx >= 0 ? content.substring(absIdx).replace(/^\n摘要[:：]/, '').trim() : '';

    // 解析引文行：作者. 标题[J]. 期刊, 年份, 卷(期): 页码.
    let authors = '', title = '', source = '', date = '';
    const jMatch = citationLine.match(/^(.*?)\.\s*(.*?)\[([A-Z\/]+)\]\.\s*(.*?)$/s);
    if (jMatch) {
      authors = jMatch[1].trim();
      title = jMatch[2].trim();
      const journalInfo = jMatch[4].trim().replace(/\.\s*$/, '');
      const jInfoMatch = journalInfo.match(/^(.*?),\s*(\d{4}),?\s*(.*?)$/);
      if (jInfoMatch) {
        source = jInfoMatch[1].trim();
        date = jInfoMatch[2].trim() + (jInfoMatch[3].trim() ? ', ' + jInfoMatch[3].trim() : '');
      } else {
        source = journalInfo;
      }
    }

    articles.push({ num, authors, title, source, date, abstract });
  }

  // 用base64编码返回，避免中文字符在传输中出错
  const jsonStr = JSON.stringify(articles);
  return btoa(unescape(encodeURIComponent(jsonStr)));
}
```

**关键要点**：
- **必须用 `split(/\[(\d+)\]\n/)` 而不是正则 `matchAll`**：实测中 `matchAll` 模式无法正确匹配知网导出的文本格式，`split` 方式可靠地将文本按 `[序号]` 分割
- **必须用 base64 编码返回**：中文JSON直接通过shell heredoc传递给Python时会因特殊字符（引号、反斜杠、Unicode）导致解析失败。使用 `btoa(unescape(encodeURIComponent(jsonStr)))` 编码后，在Python端用 `base64.b64decode().decode('utf-8')` 解码
- **查新引文格式不包含"关键词"字段**：该格式只提供作者、标题、来源期刊、发表时间、摘要，不含关键词

### 9.6 数据结构

每篇论文提取以下字段：
| 字段 | 说明 |
|------|------|
| 序号 | 1-100 |
| 标题 | 论文标题 |
| 作者 | 所有作者 |
| 来源期刊 | 期刊名称 |
| 发表时间 | 年份, 卷(期): 页码 |
| 摘要 | 完整摘要文本 |

> 注意：查新引文格式不含关键词字段，Excel中不设关键词列。

## Step 10: 保存为Excel

### 10.1 解码数据并保存JSON

evaluate_script返回的是base64字符串，输出可能很大会被保存到tool-results文件。需要用Python读取并解码：

```python
import json, base64

# 方式1：如果base64字符串直接可用
json_str = base64.b64decode(b64_string).decode('utf-8')
articles = json.loads(json_str)

# 方式2：如果数据被保存到了tool-results文件（输出过大时）
with open('tool-results文件路径', 'r') as f:
    data = json.load(f)
text = data[0]['text']
import re
m = re.search(r'```json\n"(.+?)"\n```', text, re.DOTALL)
if m:
    b64str = m.group(1)
    json_str = base64.b64decode(b64str).decode('utf-8')
    articles = json.loads(json_str)
```

### 10.2 生成Excel文件

```python
import json
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

wb = Workbook()
ws = wb.active
ws.title = "检索结果"

# 表头（无关键词列）
headers = ["序号", "标题", "作者", "来源期刊", "发表时间", "摘要"]
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
header_font = Font(bold=True, size=11, color="FFFFFF")

for col, h in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=h)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal='center', vertical='center')

# 数据行
for i, article in enumerate(articles, 1):
    ws.cell(row=i+1, column=1, value=i)
    ws.cell(row=i+1, column=2, value=article.get('title', ''))
    ws.cell(row=i+1, column=3, value=article.get('authors', ''))
    ws.cell(row=i+1, column=4, value=article.get('source', ''))
    ws.cell(row=i+1, column=5, value=article.get('date', ''))
    cell = ws.cell(row=i+1, column=6, value=article.get('abstract', ''))
    cell.alignment = Alignment(wrap_text=True, vertical='top')

# 列宽
ws.column_dimensions['A'].width = 6
ws.column_dimensions['B'].width = 50
ws.column_dimensions['C'].width = 20
ws.column_dimensions['D'].width = 20
ws.column_dimensions['E'].width = 15
ws.column_dimensions['F'].width = 80

ws.auto_filter.ref = ws.dimensions
ws.freeze_panes = 'A2'

wb.save(output_path)
```

文件保存至 `~/Downloads/知网检索结果_{关键词摘要}_{日期}.xlsx`。

安装依赖：`pip3 install openpyxl`

## 已知问题与解决方案速查表

| 问题 | 症状 | 解决方案 |
|------|------|----------|
| **导出菜单点击无效** | hover/click下拉菜单项后无反应 | 不操作UI，直接用 `$.PostWindow()` 调用导出（见Step 9.2） |
| **导出需要登录** | 点导出后弹出登录框或打开member.cnki.net | 先用 `islogin()` 检查，返回false则提示用户登录（见Step 9.1） |
| **登录弹窗遮挡页面** | `.ecp_header_login_area` 面板覆盖检索页 | `evaluate_script` 设置 `panel.style.display='none'`（见Step 9.1） |
| **member.cnki.net页面打开** | 导出操作后打开登录页而非导出页 | 关闭该页面 `close_page`，确认登录后重新导出 |
| **导出页面未出现** | `list_pages` 看不到export.html页面 | 等待2-3秒后重试 `list_pages`；确认 `$.PostWindow` 返回值无报错 |
| **论文解析0条结果** | evaluate_script返回空数组 | 使用 `split(/\[(\d+)\]\n/)` 替代正则matchAll（见Step 9.5） |
| **JSON传输到Python失败** | heredoc中特殊字符导致JSONDecodeError | 浏览器端base64编码，Python端解码（见Step 9.5和10.1） |
| **全选checkbox无效** | MCP click `#selectCheckAll1` 无反应 | 改用 `evaluate_script` 执行 `document.querySelector('#selectCheckAll1').click()`（见Step 8.1） |
| **排序不生效** | 点击"被引"后列表顺序未变化 | 点击后take_snapshot确认，可能需点击两次切换升降序 |
| **验证码拦截** | 页面出现"拖动下方拼图完成验证" | 提示用户手动完成验证，等确认后继续 |
| **evaluate_script输出过大** | 返回数据被截断到tool-results文件 | 从tool-results JSON文件中读取完整数据（见Step 10.1方式2） |

## 注意事项

- 知网有反爬机制，每步操作间隔1-2秒，避免频繁请求
- 验证码出现时必须请用户手动完成
- 检索前向用户确认关键词分组和同义词扩展
- 全程向用户报告进度
- **导出前务必确认登录状态**，这是最常见的失败原因
- **导出操作务必使用JS直接调用**，不要尝试操作UI下拉菜单
- **数据传输务必使用base64编码**，避免中文字符问题
- 若总结果不足100篇，告知用户实际数量并全部提取
