#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知网高级检索页面 DOM 诊断工具
用法：python3 diagnose_dom.py
"""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = await context.new_page()

        print("\n[1] 导航到知网高级检索...")
        await page.goto("https://kns.cnki.net/kns8s/AdvSearch", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        print("\n[2] 点击'学术期刊'...")
        clicked = await page.evaluate("""
            () => {
                const candidates = [...document.querySelectorAll('a, li, span, div')];
                const el = candidates.find(e => e.children.length <= 2 && e.textContent.trim() === '学术期刊');
                if (el) { el.click(); return el.tagName + ' | class=' + el.className; }
                return 'NOT FOUND';
            }
        """)
        print(f"   点击结果: {clicked}")
        await asyncio.sleep(3)

        print("\n[3] 查找所有 checkbox（来源过滤区域）...")
        checkboxes = await page.evaluate("""
            () => {
                const cbs = [...document.querySelectorAll('input[type="checkbox"]')];
                return cbs.map(cb => {
                    const label = cb.closest('label') || document.querySelector(`label[for="${cb.id}"]`);
                    const parent = cb.parentElement;
                    return {
                        id: cb.id,
                        name: cb.name,
                        key: cb.getAttribute('key'),
                        value: cb.value,
                        checked: cb.checked,
                        labelText: label ? label.textContent.trim().substring(0, 30) : null,
                        parentTag: parent ? parent.tagName + '.' + parent.className.substring(0, 30) : null,
                    };
                });
            }
        """)
        print(f"   共找到 {len(checkboxes)} 个 checkbox:")
        for cb in checkboxes:
            print(f"   - id={cb['id']} name={cb['name']} key={cb['key']} value={cb['value']} "
                  f"checked={cb['checked']} label={cb['labelText']} parent={cb['parentTag']}")

        print("\n[4] 查找 CSSCI 相关元素...")
        cssci_info = await page.evaluate("""
            () => {
                const results = [];
                // 找所有含 CSSCI 文字的元素
                const all = [...document.querySelectorAll('*')];
                for (const el of all) {
                    if (el.children.length === 0 && el.textContent.trim().includes('CSSCI')) {
                        const cb = el.previousElementSibling || el.parentElement?.querySelector('input');
                        results.push({
                            tag: el.tagName,
                            class: el.className.substring(0, 40),
                            text: el.textContent.trim().substring(0, 30),
                            hasInputSibling: !!(cb && cb.type === 'checkbox'),
                            inputKey: cb ? cb.getAttribute('key') : null,
                            inputId: cb ? cb.id : null,
                        });
                    }
                }
                return results;
            }
        """)
        if cssci_info:
            print(f"   含CSSCI文字的元素:")
            for item in cssci_info:
                print(f"   - <{item['tag']} class={item['class']}> '{item['text']}' "
                      f"sibling_input={item['hasInputSibling']} key={item['inputKey']} id={item['inputId']}")
        else:
            print("   未找到含CSSCI文字的元素（可能学术期刊tab未成功切换）")

        print("\n[5] 检索结果页排序按钮（如果在结果页）...")
        await page.goto(
            "https://kns.cnki.net/kns8s/search?classid=WA0453000&korder=&kw=%E6%83%85%E6%84%9F%E5%8A%B3%E5%8A%A8&kcode=SU",
            wait_until="domcontentloaded"
        )
        await asyncio.sleep(3)

        sort_info = await page.evaluate("""
            () => {
                // 查找排序区域
                const sortContainers = ['#sortList', '.sortList', '.sort-list', '[class*="sort"]'];
                for (const sel of sortContainers) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const links = [...el.querySelectorAll('a, span, li')];
                        return {
                            container: sel + ' | class=' + el.className,
                            items: links.map(l => ({
                                tag: l.tagName,
                                text: l.textContent.trim(),
                                class: l.className,
                                href: l.href || null,
                                dataSort: l.getAttribute('data-sort'),
                                onclick: l.getAttribute('onclick') ? l.getAttribute('onclick').substring(0, 60) : null,
                            }))
                        };
                    }
                }
                // 全局找排序相关元素
                const all = [...document.querySelectorAll('a')];
                const sortLinks = all.filter(a =>
                    a.textContent.trim().match(/^(相关度|发表时间|被引|下载|综合)$/)
                );
                return {
                    container: 'global search',
                    items: sortLinks.map(l => ({
                        tag: l.tagName,
                        text: l.textContent.trim(),
                        class: l.className,
                        href: l.href ? l.href.substring(0, 80) : null,
                        onclick: l.getAttribute('onclick') ? l.getAttribute('onclick').substring(0, 60) : null,
                    }))
                };
            }
        """)
        print(f"   排序区域: {sort_info.get('container', 'N/A')}")
        for item in sort_info.get('items', []):
            print(f"   - <{item['tag']}> '{item['text']}' class={item['class']} "
                  f"data-sort={item['dataSort']} onclick={item['onclick']}")

        print("\n[6] 检查每页条数区域...")
        per_page = await page.evaluate("""
            () => {
                const div = document.querySelector('#perPageDiv, .per-page, [class*="perPage"], [class*="pageSize"]');
                if (!div) return {found: false, html: document.querySelector('.pager, .page-tool, [class*="page"]')?.innerHTML?.substring(0, 300) || 'not found'};
                return {
                    found: true,
                    id: div.id,
                    class: div.className,
                    links: [...div.querySelectorAll('a, span, li')].map(l => ({
                        text: l.textContent.trim(),
                        class: l.className,
                        onclick: l.getAttribute('onclick'),
                    }))
                };
            }
        """)
        print(f"   每页条数区: {per_page}")

        await page.close()
        print("\n诊断完成。")


asyncio.run(main())
