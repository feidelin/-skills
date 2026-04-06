# 修订标记语法速查表

本文档汇总飞书文档论文审阅中所有修订标记的精确语法，供执行审阅时快速参考。

---

## 一、正文修订（docs +update）

所有正文修订通过 `lark-cli docs +update` 执行，使用 `--mode replace_range` 或 `--mode insert_after`。

### 1. highlight — 黄色高亮标注

**用途**：标记需要作者关注但不直接改动的文本。

```bash
lark-cli docs +update --doc "<doc_id>" \
  --mode replace_range \
  --selection-with-ellipsis "<原文15-25字>" \
  --markdown '<text background-color="yellow"><原文></text>'
```

**效果**：文本变为黄色背景高亮。

### 2. suggest_delete — 红色删除线

**用途**：建议删除的冗余、空话或不当内容。

```bash
lark-cli docs +update --doc "<doc_id>" \
  --mode replace_range \
  --selection-with-ellipsis "<原文15-25字>" \
  --markdown '<text color="red">~~<原文>~~</text>'
```

**效果**：文本变为红色并加删除线。

### 3. suggest_replace — 删除线 + 蓝色替换文本

**用途**：建议用更好的表述替换原文。

```bash
lark-cli docs +update --doc "<doc_id>" \
  --mode replace_range \
  --selection-with-ellipsis "<旧文本15-25字>" \
  --markdown '<text color="red">~~<旧文本>~~</text><text color="blue">**<新文本>**</text>'
```

**效果**：旧文本红色删除线 + 新文本蓝色粗体，一目了然。

### 4. callout_insert — 插入审阅意见块

**用途**：在章节末尾或特定位置插入结构化的审阅意见。

#### 一般审阅意见（黄色）

```bash
lark-cli docs +update --doc "<doc_id>" \
  --mode insert_after \
  --selection-with-ellipsis "<定位文本>" \
  --markdown '<callout emoji="📝" background-color="light-yellow">
**【审阅意见】**：意见内容...
</callout>'
```

#### 严重问题（红色）

```bash
lark-cli docs +update --doc "<doc_id>" \
  --mode insert_after \
  --selection-with-ellipsis "<定位文本>" \
  --markdown '<callout emoji="⚠️" background-color="light-red">
**【必改】**：问题描述和修改建议...
</callout>'
```

#### 肯定之处（绿色）

```bash
lark-cli docs +update --doc "<doc_id>" \
  --mode insert_after \
  --selection-with-ellipsis "<定位文本>" \
  --markdown '<callout emoji="✅" background-color="light-green">
**【肯定】**：值得肯定的内容...
</callout>'
```

---

## 二、评论批注（drive +add-comment）

### 1. 划词评论（局部评论）

```bash
lark-cli drive +add-comment \
  --doc "<doc_id>" \
  --selection-with-ellipsis "<目标文本15-25字>" \
  --content '[{"type":"text","text":"【必改】评论内容..."}]'
```

**评论前缀约定：**
- `【必改】` — 必须修改的关键问题
- `【建议】` — 可以改善但非必须的建议
- `【肯定】` — 值得肯定的写作亮点
- `【疑问】` — 需要作者澄清的问题

### 2. 全文总评

```bash
lark-cli drive +add-comment \
  --doc "<doc_id>" \
  --full-comment \
  --content '[{"type":"text","text":"【论文总评】\n\n一、总体评价\n...\n\n二、主要优点\n1. ...\n2. ...\n\n三、主要问题\n1. 【必改】...\n2. 【建议】...\n\n四、修改建议\n...\n\n五、综合判断\n建议：大修后重审 / 小修后接受 / 建议退稿"}]'
```

---

## 三、定位技巧

### selection-with-ellipsis 用法

| 格式 | 说明 | 示例 |
|------|------|------|
| `精确文本` | 完整匹配 | `"数字治理的悬浮并非单纯的技术失败"` |
| `开头...结尾` | 范围匹配 | `"数字治理的悬浮...技术失败或制度缺陷"` |
| `\.\.\. 转义` | 匹配字面量 `...` | `"如图1\.\.\.所示"` |

### 定位建议

- 使用 **15-25 个字符**，确保唯一匹配
- 如果匹配失败，扩大上下文范围
- 避免使用标点符号开头或结尾（容易与其他标记冲突）
- 范围匹配时，开头和结尾各取 10-15 字符

---

## 四、颜色速查

### 文字颜色（color）

| 颜色 | 写法 | 审阅用途 |
|------|------|---------|
| red | `<text color="red">` | 严重问题、建议删除 |
| blue | `<text color="blue">` | 建议替换的新文本 |
| orange | `<text color="orange">` | 需注意的次要问题 |
| green | `<text color="green">` | 肯定的内容 |
| purple | `<text color="purple">` | 理论/概念相关问题 |
| gray | `<text color="gray">` | 低优先级注释 |

### 背景色（background-color）

| 颜色 | 写法 | 审阅用途 |
|------|------|---------|
| yellow | `<text background-color="yellow">` | 需关注的问题文本 |
| red | `<text background-color="red">` | 严重问题文本 |
| green | `<text background-color="green">` | 优秀段落标注 |

### Callout 背景色

| 颜色 | 写法 | 审阅用途 |
|------|------|---------|
| light-yellow | `background-color="light-yellow"` | 一般审阅意见 |
| light-red | `background-color="light-red"` | 严重问题说明 |
| light-green | `background-color="light-green"` | 肯定与表扬 |
| light-blue | `background-color="light-blue"` | 信息说明 |

---

## 五、执行顺序

1. **从文档末尾向开头**逐条执行正文修订（`docs +update`）
2. 所有正文修订完成后，逐条添加划词评论（`drive +add-comment`）
3. 最后添加全文总评（`drive +add-comment --full-comment`）

这个顺序确保：
- 正文修订不会因位置偏移而定位失败
- 评论定位基于修改后的文档状态
- 全文总评出现在评论列表最上方
