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

调用 Python Playwright 脚本（`scripts/cnki_search.py`）执行全流程自动化检索，无需 MCP 工具操作浏览器。

## Step 0: 解析用户关键词

从用户输入中提取检索关键词，组织为检索表达式：

- **单组关键词**：关键词及其同义词/同位词用 ` + ` 连接（+前后各一个空格），填入同一个主题检索框
  - 例：用户说"数字化转型"→ 检索词为 `数字化转型 + 数字化变革 + 数字化`
- **多组关键词**：每组填入独立的主题检索框，组间关系保持AND（默认即为AND）
  - 例：用户说"数字化转型与企业绩效"→ 第一组 `数字化转型 + 数字化变革`，AND，第二组 `企业绩效 + 企业业绩 + 组织绩效`

向用户确认关键词分组和同义词扩展后再执行检索。

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

## Step 1: 调用 Python 脚本执行检索

根据用户确认的关键词，构造并执行以下命令。每个 `--keywords` 参数对应一个检索组：

```bash
python3 /Users/songyiping/.claude/skills/cnki-advanced-search/scripts/cnki_search.py \
  --keywords "关键词组1（同义词用 + 连接）" \
  --keywords "关键词组2（如有）" \
  --max-results 100 \
  --port 9222
```

**示例（单组）**：
```bash
python3 /Users/songyiping/.claude/skills/cnki-advanced-search/scripts/cnki_search.py \
  --keywords "数字化转型 + 数字化变革 + 数字转型" \
  --max-results 100
```

**示例（多组）**：
```bash
python3 /Users/songyiping/.claude/skills/cnki-advanced-search/scripts/cnki_search.py \
  --keywords "数字化转型 + 数字化变革" \
  --keywords "企业绩效 + 组织绩效 + 企业业绩" \
  --max-results 100
```

**脚本会自动处理**：
- 连接现有 Chrome（CDP 端口 9222）或启动新的 Chromium
- 导航到知网高级检索页面
- 验证码检测（出现时暂停，等用户在终端按 Enter 确认完成）
- 登录检查（未登录时暂停等用户登录）
- 选择学术期刊、勾选 CSSCI、填入关键词
- 执行检索、按被引量降序排列、每页50条
- 全选最多100篇论文并导出
- 解析数据、保存为 Excel

**脚本输出示例**：
```
===== 知网高级检索自动化工具 =====
关键词分组: ['数字化转型 + 数字化变革']
最大结果数: 100
...
[✓] 检索完成！共提取 87 篇论文
[✓] 文件已保存：/Users/songyiping/Downloads/知网检索_数字化转型_20260404_1523.xlsx
```

## Step 2: 报告结果

脚本执行完成后，读取终端输出，告知用户：
- 检索到的论文数量
- 实际提取数量
- 保存的文件路径

打开文件：
```bash
open "/Users/songyiping/Downloads/知网检索_*.xlsx"
```

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
