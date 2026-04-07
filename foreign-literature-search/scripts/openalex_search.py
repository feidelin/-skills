#!/usr/bin/env python3
"""
OpenAlex 外文学术文献检索脚本
- 支持多关键词组 AND 联合检索（各组内 OR，组间取交集）
- 自动过滤社会科学领域
- 按被引量排序，解码摘要，输出 Excel
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.parse
from datetime import date
from pathlib import Path
from collections import Counter

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
except ImportError:
    print("[!] 请先安装: pip install openpyxl")
    sys.exit(1)

# 社会科学领域 concept IDs（用于过滤非社科文献）
SOCIAL_SCIENCE_CONCEPTS = [
    "C144024400",  # Sociology
    "C17744445",   # Political science
    "C162324750",  # Economics
    "C15744967",   # Psychology
    "C205649164",  # Geography
    "C142362112",  # Art
    "C95457728",   # History
    "C41008148",   # Computer science (数字社会学需要)
]

# 重要社会学期刊（用于优先级标注）
TOP_SOCIOLOGY_JOURNALS = {
    "american journal of sociology", "american sociological review",
    "social forces", "theory and society", "annual review of sociology",
    "british journal of sociology", "sociology", "current sociology",
    "social problems", "qualitative sociology", "work employment and society",
    "new media and society", "organization", "organization studies",
    "organization science", "administrative science quarterly",
    "journal of management studies", "human relations",
    "information communication society", "social science research",
    "journal of consumer research", "media culture society",
}


def decode_abstract(inverted_index):
    """将 OpenAlex 的倒排索引格式摘要还原为普通文本"""
    if not inverted_index:
        return ""
    words = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[k] for k in sorted(words))


def openalex_get(endpoint, params, email=None, retries=3):
    """带重试的 OpenAlex API 请求（无需 API key）"""
    if email:
        params["mailto"] = email
    query_string = urllib.parse.urlencode(params)
    url = f"https://api.openalex.org/{endpoint}?{query_string}"

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "AcademicResearchTool/1.0 (mailto:research@example.com)")
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                print(f"  [!] 请求失败（{e}），{1.5*(attempt+1):.1f}s 后重试...")
                time.sleep(1.5 * (attempt + 1))
            else:
                print(f"  [✗] 请求最终失败: {url[:80]}")
                return None


def fetch_group_ids(synonyms, social_science_filter, year_from, year_to, max_fetch=500):
    """
    检索单个关键词组（多个同义词列表），返回 ({paper_id: paper_data}, total_count)
    策略：对每个同义词单独检索，合并结果（OR 逻辑），再按被引量排序
    """
    # 构造过滤条件
    filter_parts = []
    if social_science_filter:
        # concepts.id 用 | 分隔表示 OR（任意一个社科 concept 即可）
        soc_filter = "concepts.id:" + "|".join(SOCIAL_SCIENCE_CONCEPTS)
        filter_parts.append(soc_filter)
    if year_from:
        filter_parts.append(f"from_publication_date:{year_from}-01-01")
    if year_to:
        filter_parts.append(f"to_publication_date:{year_to}-12-31")
    filter_str = ",".join(filter_parts) if filter_parts else None

    merged = {}
    total = 0

    for synonym in synonyms:
        # 多词短语加引号，单词直接用
        query = f'"{synonym}"' if " " in synonym else synonym
        params = {
            "search": query,
            "per-page": min(200, max_fetch),
            "select": "id,title,authorships,publication_year,primary_location,"
                      "cited_by_count,abstract_inverted_index,doi,open_access,topics",
            "sort": "cited_by_count:desc",
        }
        if filter_str:
            params["filter"] = filter_str

        cursor = "*"
        fetched_this = 0

        while fetched_this < max_fetch:
            params["cursor"] = cursor
            data = openalex_get("works", params)
            if not data:
                break

            items = data.get("results", [])
            meta = data.get("meta", {})
            total = max(total, meta.get("count", 0))

            for item in items:
                pid = item.get("id")
                if pid and pid not in merged:
                    merged[pid] = item

            fetched_this += len(items)
            next_cursor = meta.get("next_cursor")
            if not next_cursor or len(items) < 200 or fetched_this >= max_fetch:
                break
            cursor = next_cursor
            time.sleep(0.12)

        time.sleep(0.15)  # 同义词之间稍微间隔

    return merged, total


def search_openalex(keyword_groups, max_results=100,
                    social_science_filter=True,
                    year_from=None, year_to=None):
    """
    多组 AND 联合检索策略：
    - 以最具体的组（词数最少的组）作为主检索，获取足够多结果
    - 对结果的 title+abstract 做后置过滤：确保包含每个其他组的至少一个同义词
    - 按被引量排序输出
    """
    print(f"\n关键词分组: {keyword_groups}")
    print(f"社会科学过滤: {social_science_filter}  年份范围: {year_from or '不限'}-{year_to or '不限'}")

    # 解析每组的同义词列表
    parsed_groups = []
    for group in keyword_groups:
        synonyms = [s.strip() for s in group.split(" OR ") if s.strip()]
        parsed_groups.append([s.lower() for s in synonyms])

    # 选最具体的组作为主检索（同义词最少 = 最精确）
    primary_idx = min(range(len(parsed_groups)), key=lambda i: len(parsed_groups[i]))
    primary_synonyms = parsed_groups[primary_idx]
    filter_groups = [parsed_groups[i] for i in range(len(parsed_groups)) if i != primary_idx]

    print(f"\n主检索组（索引{primary_idx+1}）: {keyword_groups[primary_idx][:60]}...")

    # 构造 OpenAlex 过滤器
    filter_parts = []
    if social_science_filter:
        filter_parts.append("concepts.id:" + "|".join(SOCIAL_SCIENCE_CONCEPTS))
    if year_from:
        filter_parts.append(f"from_publication_date:{year_from}-01-01")
    if year_to:
        filter_parts.append(f"to_publication_date:{year_to}-12-31")
    filter_str = ",".join(filter_parts) if filter_parts else None

    # 主检索：对每个主组同义词分别检索，合并结果
    primary_map = {}
    total_ref = 0
    for syn in primary_synonyms:
        query = f'"{syn}"' if " " in syn else syn
        params = {
            "search": query,
            "per-page": 200,
            "select": "id,title,authorships,publication_year,primary_location,"
                      "cited_by_count,abstract_inverted_index,doi,open_access,topics",
            "sort": "cited_by_count:desc",
        }
        if filter_str:
            params["filter"] = filter_str

        cursor = "*"
        fetched = 0
        while fetched < 1000:  # 每个同义词最多取1000篇用于过滤
            params["cursor"] = cursor
            data = openalex_get("works", params)
            if not data:
                break
            items = data.get("results", [])
            meta = data.get("meta", {})
            total_ref = max(total_ref, meta.get("count", 0))
            for item in items:
                pid = item.get("id")
                if pid and pid not in primary_map:
                    primary_map[pid] = item
            fetched += len(items)
            next_cursor = meta.get("next_cursor")
            if not next_cursor or len(items) < 200 or fetched >= 1000:
                break
            cursor = next_cursor
            time.sleep(0.12)
        time.sleep(0.15)

    print(f"  主检索合并: {len(primary_map)} 篇")

    if not filter_groups:
        papers = sorted(primary_map.values(),
                        key=lambda x: x.get("cited_by_count", 0), reverse=True)
        return papers[:max_results], len(primary_map)

    # 后置过滤：title+abstract 必须包含每个过滤组的至少一个同义词
    def text_contains_group(paper, group_synonyms):
        title = (paper.get("title") or "").lower()
        abstract = decode_abstract(paper.get("abstract_inverted_index")).lower()
        full_text = title + " " + abstract
        return any(syn in full_text for syn in group_synonyms)

    passed = []
    for pid, paper in primary_map.items():
        if all(text_contains_group(paper, grp) for grp in filter_groups):
            passed.append(paper)

    print(f"  后置过滤后: {len(passed)} 篇（需包含所有 {len(filter_groups)} 个额外组的词）")

    # 若过滤后 < 20 篇，放宽：只要求包含任意一个额外组
    if len(passed) < 20 and len(filter_groups) > 1:
        passed_relaxed = []
        for pid, paper in primary_map.items():
            if any(text_contains_group(paper, grp) for grp in filter_groups):
                passed_relaxed.append(paper)
        print(f"  [自动放宽] 任意一个额外组匹配: {len(passed_relaxed)} 篇")
        passed = passed_relaxed

    passed.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)
    return passed[:max_results], len(passed)


def format_paper(paper, category=""):
    """将 OpenAlex paper 对象格式化为输出行"""
    title = paper.get("title") or ""

    # 作者（最多3位）
    authorships = paper.get("authorships") or []
    authors = [a.get("author", {}).get("display_name", "") for a in authorships[:3]]
    if len(authorships) > 3:
        authors.append("et al.")
    author_str = "; ".join(filter(None, authors))

    # 期刊
    primary_loc = paper.get("primary_location") or {}
    source = primary_loc.get("source") or {}
    journal = source.get("display_name") or ""

    # 顶刊标注
    is_top = journal.lower() in TOP_SOCIOLOGY_JOURNALS
    journal_display = f"⭐ {journal}" if is_top else journal

    # 年份、被引
    year = paper.get("publication_year") or ""
    cited = paper.get("cited_by_count") or 0

    # DOI
    doi = paper.get("doi") or ""

    # OA 链接
    oa_info = paper.get("open_access") or {}
    oa_url = oa_info.get("oa_url") or ""

    # 摘要
    abstract = decode_abstract(paper.get("abstract_inverted_index"))

    # 主题标签
    topics = paper.get("topics") or []
    topic_names = [t.get("display_name", "") for t in topics[:3]]
    topics_str = "; ".join(filter(None, topic_names))

    return {
        "文献类别": category,
        "标题": title,
        "作者": author_str,
        "期刊": journal_display,
        "年份": year,
        "被引量": cited,
        "DOI": doi,
        "OA全文链接": oa_url,
        "主题标签": topics_str,
        "摘要": abstract,
    }


def save_excel(all_batches, output_path, topic_label=""):
    """
    all_batches: list of (category_name, color_hex, papers)
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "文献汇总"

    headers = ["序号", "文献类别", "标题", "作者", "期刊", "年份",
               "被引量", "DOI", "OA全文链接", "主题标签", "摘要"]
    ws.append(headers)

    # 表头样式
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill(fill_type="solid", fgColor="1F4E79")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    seen_titles = set()
    seq = 1

    for category, color, papers in all_batches:
        row_fill = PatternFill(fill_type="solid", fgColor=color)
        for paper in papers:
            title = paper.get("标题", "")
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            row = [
                seq,
                category,
                paper.get("标题", ""),
                paper.get("作者", ""),
                paper.get("期刊", ""),
                paper.get("年份", ""),
                paper.get("被引量", 0),
                paper.get("DOI", ""),
                paper.get("OA全文链接", ""),
                paper.get("主题标签", ""),
                paper.get("摘要", ""),
            ]
            ws.append(row)
            for cell in ws[ws.max_row]:
                cell.fill = row_fill
                cell.alignment = Alignment(vertical="top", wrap_text=True)
            seq += 1

    # 列宽
    col_widths = [4, 28, 40, 22, 22, 6, 8, 36, 36, 30, 60]
    for i, width in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width

    # 行高
    for row in ws.iter_rows(min_row=2):
        ws.row_dimensions[row[0].row].height = 65

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    # 分类统计 sheet
    ws2 = wb.create_sheet("分类统计")
    ws2.append(["文献类别", "颜色说明", "篇数"])
    color_desc = {"D9E1F2": "蓝-直接相关", "E2EFDA": "绿-背景文献", "FFF2CC": "黄-理论文献", "FCE4D6": "橙-扩展视角"}
    for cat, color, papers in all_batches:
        valid = sum(1 for p in papers if p.get("标题"))
        ws2.append([cat, color_desc.get(color, color), valid])
    ws2.append(["合计（去重后）", "", seq - 1])
    for cell in ws2[1]:
        cell.font = Font(bold=True)
    ws2.column_dimensions["A"].width = 40
    ws2.column_dimensions["B"].width = 20

    # WoS 检索式 sheet（方便有机构账号的用户）
    ws3 = wb.create_sheet("WoS检索式参考")
    ws3.append(["说明", "本检索式可在 Web of Science 高级检索中使用，限定 SSCI 数据库"])
    ws3.append([])
    ws3.append(["本次检索主题", topic_label])

    wb.save(output_path)
    return seq - 1


def main():
    parser = argparse.ArgumentParser(description="OpenAlex 学术文献检索工具")
    parser.add_argument("--keywords", action="append", required=True,
                        help="关键词组（每个 --keywords 为一组，组内用 + 分隔同义词，组间取 AND 交集）")
    parser.add_argument("--max-results", type=int, default=100, help="最多返回篇数（默认100）")
    parser.add_argument("--year-from", type=int, help="发表年份下限（如 2015）")
    parser.add_argument("--year-to", type=int, help="发表年份上限（如 2025）")
    parser.add_argument("--no-soc-filter", action="store_true", help="关闭社会科学概念过滤")
    parser.add_argument("--category", default="直接相关", help="文献类别标签（用于分类汇总）")
    parser.add_argument("--color", default="D9E1F2", help="Excel 行颜色（十六进制，默认蓝色）")
    parser.add_argument("--output-dir", default="~/Downloads", help="输出目录")
    parser.add_argument("--output-file", help="指定输出文件路径（覆盖 --output-dir）")
    parser.add_argument("--topic", default="", help="检索主题描述（用于文件名和 WoS sheet）")
    args = parser.parse_args()

    print("\n===== OpenAlex 学术文献检索工具 =====")

    # 解析关键词组（+ 分隔同义词，各组内 OR，组间 AND 交集）
    keyword_groups = []
    for kw_str in args.keywords:
        synonyms = [k.strip() for k in kw_str.split("+") if k.strip()]
        # 转成 "syn1 OR syn2 OR syn3" 格式供 search_openalex 解析
        query = " OR ".join(synonyms)
        keyword_groups.append(query)

    soc_filter = not args.no_soc_filter

    # 执行检索
    papers, count = search_openalex(
        keyword_groups,
        max_results=args.max_results,
        social_science_filter=soc_filter,
        year_from=args.year_from,
        year_to=args.year_to,
    )

    print(f"\n[✓] 检索完成，获取 {len(papers)} 篇")

    # 格式化
    formatted = [format_paper(p, args.category) for p in papers]

    # 输出路径
    if args.output_file:
        output_path = Path(args.output_file).expanduser()
    else:
        today = date.today().strftime("%Y%m%d")
        topic_slug = (args.topic or args.keywords[0])[:20].replace(" ", "_").replace('"', '').replace("/", "_")
        filename = f"外文文献检索_{topic_slug}_{today}.xlsx"
        output_path = Path(args.output_dir).expanduser() / filename

    # 保存 Excel
    batches = [(args.category, args.color, formatted)]
    total_saved = save_excel(batches, output_path, topic_label=args.topic)

    print(f"[✓] 已保存: {output_path}（共 {total_saved} 篇）")
    print(f"OUTPUT_FILE:{output_path}")  # 供 shell 脚本解析路径


if __name__ == "__main__":
    main()
