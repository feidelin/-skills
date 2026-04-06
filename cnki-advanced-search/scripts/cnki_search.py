#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知网（CNKI）高级检索自动化脚本 - Playwright 版

用法:
  python3 cnki_search.py --keywords "数字化转型 + 数字化变革" --keywords "企业绩效 + 组织绩效"
  python3 cnki_search.py --keywords "平台经济 + 数字平台" --max-results 50 --port 9222
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Page, BrowserContext

OUTPUT_DIR = Path.home() / "Downloads"


# ── 自定义异常 ────────────────────────────────────────────

class CNKIError(Exception):
    pass

class CNKILoginRequired(CNKIError):
    pass

class CNKICaptchaDetected(CNKIError):
    pass

class CNKIExportFailed(CNKIError):
    pass

class CNKINoResults(CNKIError):
    pass

class CNKIParseError(CNKIError):
    pass


# ── CNKISearcher 主类 ─────────────────────────────────────

class CNKISearcher:
    def __init__(self, page: Page, delay_ms: int = 1000):
        self.page = page
        self.delay = delay_ms / 1000  # 转为秒

    async def run(self, keyword_groups: list[str], max_results: int = 100) -> list[dict]:
        print(f"\n[1/10] 导航到知网高级检索页面...")
        await self._navigate_to_advanced_search()

        print(f"[2/10] 检查验证码...")
        await self._check_captcha_and_wait()

        print(f"[3/10] 检查登录状态...")
        await self._ensure_logged_in()

        print(f"[4/10] 选择学术期刊类别...")
        await self._select_journal_category()

        print(f"[5/10] 勾选CSSCI来源...")
        await self._check_cssci_filter()

        # ── 倒剥洋葱：从全组到单组逐步降级 ──────────────────
        groups_to_try = list(keyword_groups)
        count = 0
        while len(groups_to_try) >= 1:
            layer = len(keyword_groups) - len(groups_to_try) + 1
            total_layers = len(keyword_groups)
            print(f"\n[6/10] 输入检索关键词（第{layer}层，{len(groups_to_try)}组 AND）: {groups_to_try}...")
            await self._input_keyword_groups(groups_to_try)

            print(f"[7/10] 执行检索...")
            count = await self._execute_search()
            print(f"       找到 {count} 篇论文")

            if count >= 20:
                break  # 结果足够，不降级

            if len(groups_to_try) == 1:
                break  # 已到最后一组，不再降级

            # 结果不足，降级：去掉最后一组（最次要概念）
            dropped = groups_to_try.pop()
            print(f"       结果 < 20篇，自动降至第{layer+1}层（去掉组：{dropped[:30]}...）")
            # 重新导航，清空已填关键词
            await self._navigate_to_advanced_search()
            await self._check_captcha_and_wait()
            await self._select_journal_category()
            await self._check_cssci_filter()

        if count == 0:
            raise CNKINoResults("所有层级检索结果均为0，请调整关键词后重试。")
        # ────────────────────────────────────────────────────

        print(f"[8/10] 按被引量排序...")
        await self._sort_by_citations()

        print(f"[9/10] 切换每页50条...")
        await self._set_50_per_page()

        print(f"[10/10] 逐页选中并导出（最多{max_results}篇）...")
        articles = await self._select_and_export_by_page(max_results)
        return articles

    async def _navigate_to_advanced_search(self):
        await self.page.goto("https://kns.cnki.net/kns8s/AdvSearch", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(self.delay)

    async def _check_captcha_and_wait(self):
        """使用 getComputedStyle 检测验证码是否真实可见（避免隐藏DOM误判）"""
        captcha_visible = await self.page.evaluate("""
            () => {
                const selectors = ['.tc-widget-wrapper', '.nc-lang-cnt', '#slideBg', '.geetest_widget'];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (!el) continue;
                    const style = window.getComputedStyle(el);
                    if (style.display !== 'none' && style.visibility !== 'hidden' && el.offsetHeight > 0) {
                        return true;
                    }
                }
                return false;
            }
        """)
        if captcha_visible:
            input("\n[!] 检测到验证码，请在浏览器中完成滑块验证，完成后按 Enter 继续...")
            await asyncio.sleep(1)

    async def _ensure_logged_in(self):
        """检查知网登录状态，未登录时暂停等用户"""
        try:
            logged_in = await self.page.evaluate("() => typeof islogin === 'function' ? islogin() : true")
            if not logged_in:
                raise CNKILoginRequired()
        except CNKILoginRequired:
            input("\n[!] 知网导出功能需要登录，请在浏览器中登录知网账号，完成后按 Enter 继续...")
            await asyncio.sleep(1)
            # 重新检查
            still_not_logged = await self.page.evaluate("() => typeof islogin === 'function' ? !islogin() : false")
            if still_not_logged:
                print("[!] 仍未检测到登录状态，将继续执行（登录检查可能不适用于当前页面状态）")
        except Exception:
            pass  # islogin 不存在时忽略

    async def _select_journal_category(self):
        """点击底部 .doctype-menus 中的'学术期刊'选项卡，等待 CSSCI 过滤区渲染完成"""
        await asyncio.sleep(self.delay)
        try:
            clicked = await self.page.evaluate("""
                () => {
                    // 精确定位 .doctype-menus 中 resource="JOURNAL" 的链接
                    const journalLink = document.querySelector('.doctype-menus a[resource="JOURNAL"]');
                    if (journalLink) { journalLink.click(); return 'doctype-menus:JOURNAL'; }
                    // 备用：.doctype-menus 中文字为"学术期刊"的 a
                    const menuLinks = [...document.querySelectorAll('.doctype-menus a')];
                    const byText = menuLinks.find(a => a.textContent.trim() === '学术期刊');
                    if (byText) { byText.click(); return 'doctype-menus:text'; }
                    return false;
                }
            """)
            print(f"  [i] 学术期刊点击: {clicked}")

            # 等待 CSSCI checkbox（key="CSI"）渲染出来
            try:
                await self.page.wait_for_function(
                    'function(){ return !!document.querySelector(\'input[key="CSI"]\'); }',
                    timeout=12000
                )
                print("  [i] CSSCI checkbox 已就绪")
            except Exception:
                await asyncio.sleep(3)
                print("  [!] 等待 CSSCI checkbox 超时，继续执行")

        except Exception as e:
            print(f"  [!] 选择学术期刊时出错: {e}，继续执行...")

    async def _check_cssci_filter(self):
        """勾选 CSSCI 来源类别：先取消"全部期刊"，再勾选 CSSCI。"""
        await asyncio.sleep(self.delay)
        try:
            result = await self.page.evaluate("""
                () => {
                    const cssiCb = document.querySelector('input[key="CSI"]');
                    if (!cssiCb) return 'not available';

                    // 取消"全部期刊"（name="all"）
                    const allCb = document.querySelector('input[name="all"]');
                    if (allCb && allCb.checked) {
                        allCb.click();
                    }

                    // 勾选 CSSCI
                    if (!cssiCb.checked) {
                        cssiCb.click();
                    }
                    return cssiCb.checked ? 'checked:CSI' : 'click-sent:CSI';
                }
            """)
            print(f"  [i] CSSCI勾选: {result}")
            await asyncio.sleep(self.delay)
        except Exception as e:
            print(f"  [!] 勾选CSSCI时出错: {e}，继续执行...")

    async def _input_keyword_groups(self, groups: list[str]):
        """填入关键词：主题检索区 dl#gradetxt，每组一个 dd 行，+按钮为 #gradetxt a.add-group"""
        await asyncio.sleep(self.delay)

        # 第一组：填入 #gradetxt 第一行的 input
        result0 = await self.page.evaluate(f"""
            () => {{
                const input = document.querySelector('#gradetxt dd input[type="text"]');
                if (!input) return 'not found';
                input.value = {repr(groups[0])};
                input.dispatchEvent(new Event('input', {{bubbles: true}}));
                input.dispatchEvent(new Event('change', {{bubbles: true}}));
                return 'filled: ' + input.value.substring(0, 30);
            }}
        """)
        print(f"  [i] 第1组填入: {result0}")
        await asyncio.sleep(self.delay)

        # 后续组：逐一点击 #gradetxt 内的"+"，再填入新行 input
        for i, group in enumerate(groups[1:], 2):
            # 点击 #gradetxt 的"+"按钮（不是作者区的+）
            clicked = await self.page.evaluate("""
                () => {
                    const btn = document.querySelector('#gradetxt a.add-group');
                    if (btn) { btn.click(); return true; }
                    return false;
                }
            """)
            if not clicked:
                print(f"  [!] 第{i}组：未找到 #gradetxt a.add-group，跳过")
                break
            await asyncio.sleep(self.delay)

            # 填入最新一行（dd:last-of-type 或 最后一个 dd 的 input）
            result = await self.page.evaluate(f"""
                () => {{
                    const dds = document.querySelectorAll('#gradetxt dd');
                    const lastDd = dds[dds.length - 1];
                    if (!lastDd) return 'no dd found';
                    const input = lastDd.querySelector('input[type="text"]');
                    if (!input) return 'no input in last dd';
                    input.value = {repr(group)};
                    input.dispatchEvent(new Event('input', {{bubbles: true}}));
                    input.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return 'filled: ' + input.value.substring(0, 30);
                }}
            """)
            print(f"  [i] 第{i}组填入: {result}")
            await asyncio.sleep(self.delay)

    async def _execute_search(self) -> int:
        """点击检索按钮并等待结果，返回结果数量"""
        try:
            search_btn = self.page.locator('button:has-text("检索"), input[value="检索"], .btn-search').first
            await search_btn.click(timeout=5000)
        except Exception:
            await self.page.evaluate("""
                () => {
                    const btns = [...document.querySelectorAll('button, input[type="submit"], a')];
                    const btn = btns.find(b => b.textContent.trim() === '检索' || b.value === '检索');
                    if (btn) btn.click();
                }
            """)

        # 等待结果页加载
        try:
            await self.page.wait_for_url(re.compile(r"kns.cnki.net.*(result|search)"), timeout=20000)
        except Exception:
            await asyncio.sleep(3)

        await asyncio.sleep(self.delay * 2)
        await self._check_captcha_and_wait()

        # 获取结果数量
        try:
            count_text = await self.page.evaluate("""
                () => {
                    const el = document.querySelector('.pager .count, #countPageDiv, .result-count, .total-count');
                    if (el) return el.textContent;
                    // 备用：找包含"共"和"条"的元素
                    const all = [...document.querySelectorAll('*')];
                    const el2 = all.find(e => e.children.length === 0 &&
                        e.textContent.includes('共') && e.textContent.includes('条结果'));
                    return el2 ? el2.textContent : '0';
                }
            """)
            nums = re.findall(r'[\d,]+', count_text or '0')
            count = int(nums[0].replace(',', '')) if nums else 0
            return count
        except Exception:
            return 1  # 无法解析数量时假设有结果

    async def _sort_by_citations(self):
        """点击结果页的被引排序按钮（CNKI 用 <li> 元素，不导航离开 SPA）"""
        await asyncio.sleep(self.delay)
        try:
            # 等待排序按钮出现（<li> 或 <a>，文字为"被引"）
            try:
                await self.page.wait_for_function("""
                    () => [...document.querySelectorAll('li, a, span')].some(
                        el => el.textContent.trim() === '被引' || el.textContent.trim() === '被引量'
                    )
                """, timeout=20000)
            except Exception:
                print("  [!] 等待被引按钮超时，尝试直接点击...")

            result = await self.page.evaluate("""
                () => {
                    // CNKI 排序按钮是 <li> 元素（含 class 如 DESC/ASC order）
                    const items = [...document.querySelectorAll('li, a, span')];
                    const citeItem = items.find(el => {
                        const t = el.textContent.trim();
                        if (t !== '被引' && t !== '被引量') return false;
                        // 排除搜索表单内的元素
                        if (el.closest('.search-input, .input-row, .search-form, .btn-search-wrap')) return false;
                        return true;
                    });
                    if (citeItem) {
                        citeItem.click();
                        return 'clicked: ' + citeItem.tagName + ':' + citeItem.textContent.trim() +
                               ' parent=' + (citeItem.parentElement ? citeItem.parentElement.className.substring(0,30) : '');
                    }
                    // 诊断：列出所有短文字 li/a
                    const sample = items.filter(el => {
                        const t = el.textContent.trim();
                        return t.length > 0 && t.length < 8;
                    }).slice(0, 30).map(el => el.textContent.trim()).join(' | ');
                    return 'not found | sample: ' + sample.substring(0, 200);
                }
            """)
            print(f"  [i] 排序结果: {result[:200]}")

            await asyncio.sleep(self.delay * 2)
            try:
                await self.page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                await asyncio.sleep(2)
        except Exception as e:
            print(f"  [!] 排序时出错: {e}，继续执行...")

    async def _set_50_per_page(self):
        """切换每页显示50条"""
        await asyncio.sleep(self.delay)
        try:
            result = await self.page.evaluate("""
                () => {
                    // 打印分页区域所有链接帮助调试
                    const perDiv = document.querySelector('#perPageDiv, .per-page, .page-size, [class*="perPage"]');
                    const allPageLinks = perDiv
                        ? [...perDiv.querySelectorAll('a, span')].map(e => e.textContent.trim()).join(' | ')
                        : 'perPageDiv not found';

                    // 尝试点击"50"
                    if (perDiv) {
                        const links = [...perDiv.querySelectorAll('a, span')];
                        const link50 = links.find(l => l.textContent.trim() === '50');
                        if (link50) { link50.click(); return 'clicked50 | options: ' + allPageLinks; }
                    }

                    // 全局查找包含"50"的分页链接
                    const allLinks = [...document.querySelectorAll('a')];
                    const global50 = allLinks.find(a =>
                        a.textContent.trim() === '50' &&
                        (a.href.includes('pageSize') || a.href.includes('perpage') ||
                         a.onclick || a.closest('#perPageDiv, .per-page'))
                    );
                    if (global50) { global50.click(); return 'clicked50-global | options: ' + allPageLinks; }

                    return 'not found | options: ' + allPageLinks;
                }
            """)
            print(f"  [i] 每页50条: {result[:120]}")

            # 等待页面用50条重新渲染：networkidle + 固定延迟
            try:
                await self.page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            await asyncio.sleep(3)
            print("  [i] 每页50条等待完成")
        except Exception as e:
            print(f"  [!] 切换每页50条时出错: {e}，继续执行...")

    async def _select_papers(self, max_count: int) -> int:
        """逐页全选，最多选 max_count 篇，返回实际选中数量"""
        total_selected = 0
        pages_needed = (max_count + 49) // 50  # 需要多少页

        for page_num in range(pages_needed):
            if page_num > 0:
                # 翻到下一页
                try:
                    next_btn = self.page.locator('.btn-next, a:has-text("下一页"), #PageNext').first
                    if not await next_btn.is_visible(timeout=3000):
                        break
                    await next_btn.click()
                    await asyncio.sleep(self.delay * 2)
                except Exception:
                    break

            # 全选当前页
            clicked = await self.page.evaluate("""
                () => {
                    const cb = document.querySelector('#selectCheckAll1');
                    if (cb) { cb.click(); return true; }
                    // 备用选择器
                    const cb2 = document.querySelector('input[name="selectCheckAll"]');
                    if (cb2) { cb2.click(); return true; }
                    return false;
                }
            """)
            await asyncio.sleep(self.delay)

            # 读取当前选中数量
            count_text = await self.page.evaluate("""
                () => {
                    const el = document.querySelector('#selectCount, .select-count');
                    return el ? el.textContent.trim() : '0';
                }
            """)
            try:
                selected = int(re.search(r'\d+', count_text).group())
            except Exception:
                selected = total_selected + 50

            total_selected = selected
            print(f"       第{page_num + 1}页全选完成，累计已选: {total_selected}")

            if total_selected >= max_count:
                break

        return total_selected

    async def _select_and_export_by_page(self, max_count: int) -> list[dict]:
        """逐页全选→导出→解析，拼合结果，解决 $.filenameGet() 只捕获当前页的问题。"""
        all_articles: list[dict] = []
        page_num = 0
        MAX_PAGES = 50  # 安全上限，防止无限循环

        while len(all_articles) < max_count and page_num < MAX_PAGES:
            if page_num > 0:
                # 翻到下一页
                try:
                    next_btn = self.page.locator('.btn-next, a:has-text("下一页"), #PageNext').first
                    if not await next_btn.is_visible(timeout=3000):
                        print("       没有下一页，结束翻页")
                        break
                    await next_btn.click()
                    await asyncio.sleep(self.delay * 2)
                    try:
                        await self.page.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:
                        await asyncio.sleep(2)
                except Exception:
                    break

            # 全选当前页
            await self.page.evaluate("""
                () => {
                    const cb = document.querySelector('#selectCheckAll1');
                    if (cb) { cb.click(); return; }
                    const cb2 = document.querySelector('input[name="selectCheckAll"]');
                    if (cb2) cb2.click();
                }
            """)
            await asyncio.sleep(self.delay)

            # 读取当前页选中数量（CNKI 显示的是累计跨页总数）
            count_text = await self.page.evaluate("""
                () => {
                    const el = document.querySelector('#selectCount, .select-count');
                    return el ? el.textContent.trim() : '0';
                }
            """)
            try:
                total_selected = int(re.search(r'\d+', count_text).group())
            except Exception:
                total_selected = 0

            print(f"       第{page_num + 1}页全选，累计已选: {total_selected}")

            if total_selected == 0:
                print("       无选中项，结束")
                break

            # 导出当前页（filenameGet 只捕获当前页的选中项）
            try:
                page_articles = await self._export_and_parse()
                if len(page_articles) == 0:
                    print("       本页导出为空，结束")
                    break
                # 重新编号避免序号重叠
                offset = len(all_articles)
                for a in page_articles:
                    a['num'] = offset + a.get('num', 1)
                all_articles.extend(page_articles)
                print(f"       第{page_num + 1}页导出 {len(page_articles)} 篇，累计 {len(all_articles)} 篇")
            except Exception as e:
                print(f"  [!] 第{page_num + 1}页导出失败: {e}")
                break

            page_num += 1

        return all_articles

    async def _export_and_parse(self) -> list[dict]:
        """触发导出、切换到导出页、提取数据、解析返回"""
        # 检查登录
        await self._ensure_logged_in()

        # 使用 expect_popup 捕获 $.PostWindow() 打开的新窗口
        export_page = None
        for attempt in range(2):
            try:
                async with self.page.expect_popup(timeout=15000) as popup_info:
                    result = await self.page.evaluate("""
                        () => {
                            if (typeof $ === 'undefined' || typeof $.filenameGet !== 'function') {
                                return {error: 'jQuery or CNKI functions not available'};
                            }
                            const filename = $.filenameGet();
                            const searchinfo = $.searchinfoGet();
                            const mapIndex = $.indexGet();
                            const baseUrl = document.querySelector('#hidDocumentManageUrl')?.value
                                            || 'https://kns.cnki.net/dm8';
                            const exportUrl = baseUrl + '/manage/export.html?language=CHS&uniplatform=NZKPT';
                            $.PostWindow(exportUrl, {
                                displaymode: 'NEW',
                                filename: filename,
                                searchinfo: searchinfo,
                                mapIndex: mapIndex
                            });
                            return {exportUrl, filename: String(filename).substring(0, 50)};
                        }
                    """)
                export_page = await popup_info.value
                print(f"       导出页面已打开: {export_page.url[:80]}")
                break
            except Exception as e:
                if attempt == 0:
                    print(f"  [!] 导出第一次尝试失败: {e}，等待后重试...")
                    await asyncio.sleep(3)
                else:
                    raise CNKIExportFailed(f"无法打开导出页面: {e}")

        # 检查是否跳到了登录页
        if export_page is None:
            raise CNKIExportFailed("导出页面未打开")

        await export_page.wait_for_load_state("domcontentloaded", timeout=15000)
        await asyncio.sleep(1.5)

        if "member.cnki.net" in export_page.url or "login" in export_page.url.lower():
            await export_page.close()
            input("\n[!] 导出时跳转到登录页，请在浏览器中登录知网后按 Enter 重试...")
            raise CNKILoginRequired("导出时未登录")

        # 在导出页选择"查新（引文格式）"
        await self._select_citation_format(export_page)

        # 提取文本
        raw_text = await export_page.inner_text('body')

        # 解析数据
        articles = parse_citation_text(raw_text)

        # 关闭导出弹窗，避免浏览器阻止下一次 $.PostWindow()
        try:
            await export_page.close()
        except Exception:
            pass
        await asyncio.sleep(1)

        if not articles:
            # 保存原始文本供调试
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_path = OUTPUT_DIR / f"cnki_raw_export_{ts}.txt"
            raw_path.write_text(raw_text, encoding="utf-8")
            raise CNKIParseError(f"解析失败，原始数据已保存到: {raw_path}")

        return articles

    async def _select_citation_format(self, export_page: Page):
        """在导出页面点击'查新（引文格式）'"""
        try:
            format_btn = export_page.locator('a:has-text("查新"), li:has-text("查新（引文格式）"), .format-item:has-text("查新")').first
            if await format_btn.is_visible(timeout=5000):
                await format_btn.click()
                await asyncio.sleep(2)
                return
        except Exception:
            pass

        # 备用：evaluate
        await export_page.evaluate("""
            () => {
                const items = [...document.querySelectorAll('a, li, span, div')];
                const item = items.find(i => i.textContent.includes('查新') && i.textContent.includes('引文'));
                if (item) { item.click(); return true; }
                // 也尝试只包含"查新"的选项
                const item2 = items.find(i => i.textContent.trim() === '查新（引文格式）');
                if (item2) { item2.click(); return true; }
                return false;
            }
        """)
        await asyncio.sleep(2)


# ── 数据解析 ──────────────────────────────────────────────

def parse_citation_text(raw_text: str) -> list[dict]:
    """
    将知网查新引文格式文本解析为字典列表。
    格式：[1]\n作者. 标题[J]. 期刊, 年份, 卷(期): 页码.\n摘要: ...\n
    """
    start = raw_text.find('[1]\n')
    if start < 0:
        return []

    body = raw_text[start:]
    # 按 [N]\n 分割，保留分隔符中的数字
    parts = re.split(r'\[(\d+)\]\n', body)

    articles = []
    for i in range(1, len(parts), 2):
        try:
            num = int(parts[i])
            content = parts[i + 1].strip() if i + 1 < len(parts) else ''
            if not content:
                continue

            # 分离引文行与摘要
            abs_match = re.search(r'\n摘要[：:]', content)
            if abs_match:
                citation_line = content[:abs_match.start()].strip()
                abstract = content[abs_match.start():].strip()
                abstract = re.sub(r'^摘要[：:]', '', abstract).strip()
            else:
                citation_line = content.strip()
                abstract = ''

            # 解析引文行：作者. 标题[J]. 期刊信息
            authors, title, source, date = '', '', '', ''
            m = re.match(r'^(.*?)\.\s*(.*?)\[[A-Z/]+\]\.\s*(.*)$', citation_line, re.DOTALL)
            if m:
                authors = m.group(1).strip()
                title = m.group(2).strip()
                journal_info = m.group(3).strip().rstrip('.')
                j_match = re.match(r'^(.*?),\s*(\d{4})(.*?)$', journal_info)
                if j_match:
                    source = j_match.group(1).strip()
                    date = j_match.group(2) + j_match.group(3).strip()
                else:
                    source = journal_info
            else:
                title = citation_line  # 无法解析时用原文

            articles.append({
                'num': num,
                'title': title,
                'authors': authors,
                'source': source,
                'date': date,
                'abstract': abstract,
            })
        except Exception as e:
            print(f"  [!] 解析第 {i} 条时出错: {e}")

    return articles


# ── Excel 输出 ────────────────────────────────────────────

def save_to_excel(articles: list[dict], output_path: Path, keyword_summary: str):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "检索结果"

    headers = ["序号", "标题", "作者", "来源期刊", "发表时间", "摘要"]
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, size=11, color="FFFFFF")

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')

    for i, article in enumerate(articles, 1):
        ws.cell(row=i + 1, column=1, value=i)
        ws.cell(row=i + 1, column=2, value=article.get('title', ''))
        ws.cell(row=i + 1, column=3, value=article.get('authors', ''))
        ws.cell(row=i + 1, column=4, value=article.get('source', ''))
        ws.cell(row=i + 1, column=5, value=article.get('date', ''))
        cell = ws.cell(row=i + 1, column=6, value=article.get('abstract', ''))
        cell.alignment = Alignment(wrap_text=True, vertical='top')

    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 50
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 18
    ws.column_dimensions['F'].width = 80

    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = 'A2'

    wb.save(output_path)


# ── 主函数 ────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description='知网CNKI高级检索自动化工具')
    parser.add_argument('--keywords', action='append', required=True,
                        metavar='KEYWORD_GROUP',
                        help='关键词组（可重复多次，每次为一组，同义词用" + "连接）')
    parser.add_argument('--max-results', type=int, default=100,
                        help='最多导出论文数量（默认100，最大100）')
    parser.add_argument('--port', type=int, default=9222,
                        help='Chrome CDP 调试端口（默认9222）')
    parser.add_argument('--delay', type=int, default=1000,
                        help='操作间延迟（毫秒，默认1000）')
    parser.add_argument('--output-dir', type=str, default=str(OUTPUT_DIR),
                        help='输出目录（默认~/Downloads/）')
    args = parser.parse_args()

    max_results = min(args.max_results, 100)
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n===== 知网高级检索自动化工具 =====")
    print(f"关键词分组: {args.keywords}")
    print(f"最大结果数: {max_results}")
    print(f"输出目录: {output_dir}")
    print(f"===================================\n")

    async with async_playwright() as p:
        browser = None
        connected_via_cdp = False

        # 优先连接现有 Chrome（保留登录会话）
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{args.port}")
            context = browser.contexts[0] if browser.contexts else None
            if context is None:
                raise Exception("No browser context found")
            connected_via_cdp = True
            print(f"[✓] 已连接到现有 Chrome（端口 {args.port}）")
        except Exception as e:
            print(f"[!] 无法连接到 Chrome CDP（{e}），启动新浏览器...")
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                locale="zh-CN",
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            print("[✓] 新浏览器已启动（有头模式）")
            print("[!] 提示：如需使用已登录的知网账号，请通过 Chrome 调试模式连接。")
            print("    启动命令：open -a 'Google Chrome' --args --remote-debugging-port=9222\n")

        # 始终新开标签页，不干扰已有页面
        page = await context.new_page()

        try:
            searcher = CNKISearcher(page, delay_ms=args.delay)
            articles = await searcher.run(args.keywords, max_results=max_results)

            # 生成文件名
            keyword_summary = "_".join(args.keywords[0].split()[:2])[:20]
            # 清理文件名中的特殊字符
            keyword_summary = re.sub(r'[^\w\u4e00-\u9fff]', '_', keyword_summary)
            date_str = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"知网检索_{keyword_summary}_{date_str}.xlsx"
            output_path = output_dir / filename

            save_to_excel(articles, output_path, keyword_summary)

            print(f"\n[✓] 检索完成！共提取 {len(articles)} 篇论文")
            print(f"[✓] 文件已保存：{output_path}")

        except CNKINoResults as e:
            print(f"\n[!] {e}")
            sys.exit(1)
        except CNKIExportFailed as e:
            print(f"\n[✗] 导出失败: {e}")
            sys.exit(2)
        except CNKIParseError as e:
            print(f"\n[✗] 数据解析失败: {e}")
            sys.exit(3)
        except KeyboardInterrupt:
            print("\n[!] 用户中断")
            sys.exit(0)
        finally:
            if connected_via_cdp:
                await page.close()  # 关闭新开的标签页，不影响其他已有页面
            else:
                await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
