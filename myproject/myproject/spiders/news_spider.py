# charity_distributed/spiders/charity_spider.py
import re
import os
import json
import time
import platform
import scrapy
from myproject.items import CharityProjectItem


class CharitySpider(scrapy.Spider):
    """
    腾讯乐捐分布式爬虫（Selenium 版）

    URL: https://gongyi.qq.com/succor/project_list.htm#s_status=1&s_tid=73&p=1
    SPA 单页应用，Hash 路由，Selenium 渲染 JS
    """

    name = "charity"
    redis_key = "charity:start_urls"
    allowed_domains = ["gongyi.qq.com"]

    BASE_URL = "https://gongyi.qq.com/succor/project_list.htm"

    CATEGORIES = {
        "all":       "900",
        "poverty":   "72",    # 扶贫
        "education": "74",    # 教育
        "medical":   "75",    # 医疗
        "child":     "73",    # 儿童
        "env":       "71",    # 环保
    }

    def __init__(self, category="all", max_pages=5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = category
        self.max_pages = int(max_pages)
        self.node_id = f"{platform.node()}_{id(self) % 10000}"

    def start_requests(self):
        cat_id = self.CATEGORIES.get(self.category, "0")

        for page in range(1, self.max_pages + 1):
            hash_url = (
                f"{self.BASE_URL}"
                f"#s_status=1"
                f"&s_tid={cat_id}"
                f"&p={page}"
            )

            self.logger.info(f"[{self.node_id}] 请求: {hash_url}")

            yield scrapy.Request(
                hash_url,
                callback=self.parse,
                meta={
                    "category_id": cat_id,
                    "page": page,
                    "use_selenium": True,    # ★ 用 Selenium 渲染
                },
                dont_filter=True,
            )

    def parse(self, response):
        page_num = response.meta["page"]
        cat_id   = response.meta["category_id"]
        cat_name = {v: k for k, v in self.CATEGORIES.items()}.get(cat_id, "未知")

        self.logger.info(
            f"[{self.node_id}] 解析 {cat_name} 第{page_num}页 "
            f"状态={response.status} HTML={len(response.text)}"
        )

        # ★ 保存调试 HTML
        os.makedirs("output", exist_ok=True)
        debug_file = f"output/debug_{cat_name}_{page_num}.html"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(response.text)
        self.logger.info(f"  调试: {debug_file}")

        # ── 尝试多种选择器 ──
        cards = (
            response.css("[class*='pro_li_img']")
            or response.css("[class*='fund-card']")
            or response.css("[class*='project-item']")
            or response.css("[class*='card-item']")
            or response.css("[class*='card']")
            or response.css("[class*='project']")
            or response.css("[class*='item']")
        )

        if not cards:
            # 备用：查找所有指向详情页的链接
            all_links = response.css("a[href]")
            project_links = [
                a for a in all_links
                if any(kw in (a.css("::attr(href)").get("") or "")
                       for kw in ["succor/detail", "project/detail", "/detail"])
            ]
            if project_links:
                self.logger.info(f"  使用备用方式: 找到 {len(project_links)} 个详情链接")
                for a_tag in project_links:
                    href = a_tag.css("::attr(href)").get("")
                    text = self._clean(" ".join(a_tag.css("::text").getall()))
                    if href and text:
                        item = CharityProjectItem()
                        item["project_name"] = text[:100]
                        item["category"] = cat_name
                        item["crawl_node"] = self.node_id
                        item["crawl_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        item["image_url"] = a_tag.css("img::attr(src)").get("")
                        detail_url = response.urljoin(href)
                        yield scrapy.Request(
                            detail_url,
                            callback=self.parse_detail,
                            meta={"item": item, "use_selenium": True},
                            priority=10,
                        )
                return

            self.logger.warning(
                f"  第{page_num}页未找到项目！请打开 {debug_file} 查看"
            )
            return

        self.logger.info(f"  找到 {len(cards)} 个项目")

        for card in cards:
            detail_link = (
                card.css("a::attr(href)").get("")
                or card.css("::attr(href)").get("")
            )
            if not detail_link:
                continue
            detail_link = response.urljoin(detail_link)

            if not any(kw in detail_link for kw in ["succor", "project", "detail"]):
                continue

            item = CharityProjectItem()
            item["project_name"] = self._clean(
                card.css(
                    "[class*='title']::text, "
                    "[class*='name']::text, "
                    "h3::text, h2::text, "
                    "a::text"
                ).get("")
            )
            item["raised_amount"] = self._parse_amount(
                card.css(
                    "[class*='money']::text, "
                    "[class*='amount']::text, "
                    "[class*='raised']::text"
                ).get("")
            )
            item["image_url"] = card.css("img::attr(src)").get("")
            item["category"] = cat_name
            item["crawl_node"] = self.node_id
            item["crawl_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

            yield scrapy.Request(
                detail_link,
                callback=self.parse_detail,
                meta={"item": item, "use_selenium": True},
                priority=10,
            )

        # ── 翻页 ──
        if page_num < self.max_pages:
            next_url = (
                f"{self.BASE_URL}"
                f"#s_status=1"
                f"&s_tid={cat_id}"
                f"&p={page_num + 1}"
            )
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                meta={
                    "category_id": cat_id,
                    "page": page_num + 1,
                    "use_selenium": True,
                },
                dont_filter=True,
            )

    def parse_detail(self, response):
        item = response.meta["item"]
        item["detail_url"] = response.url

        pid = re.search(r"/(\d+)", response.url)
        item["project_id"] = pid.group(1) if pid else response.url

        name = response.css(
            "h1::text, [class*='title'] h1::text, [class*='detail-title']::text"
        ).get("")
        if name:
            item["project_name"] = self._clean(name)

        item["org_name"] = self._clean(
            response.css("[class*='org'] a::text, [class*='org-name']::text").get("")
        )

        raised = response.css(
            "[class*='raised'] em::text, [class*='current'] em::text, "
            "[class*='money'] em::text"
        ).get("")
        if raised:
            item["raised_amount"] = self._parse_amount(raised)

        target = response.css(
            "[class*='target'] em::text, [class*='goal'] em::text"
        ).get("")
        if target:
            item["target_amount"] = self._parse_amount(target)

        donors = response.css(
            "[class*='donor'] em::text, [class*='people'] em::text"
        ).get("")
        if donors:
            item["donor_count"] = re.sub(r"[^\d]", "", donors)

        desc_parts = response.css(
            "[class*='desc'] p::text, [class*='content'] p::text"
        ).getall()
        item["description"] = "\n".join(
            p.strip() for p in desc_parts if p.strip()
        )[:5000]

        self._calc_progress(item)

        self.logger.info(
            f"  ✓ {item.get('project_name', '?')[:30]} "
            f"¥{item.get('raised_amount', '0')}"
        )
        yield item

    @staticmethod
    def _clean(text):
        if isinstance(text, list):
            text = " ".join(text)
        return re.sub(r"\s+", " ", str(text)).strip() if text else ""

    @staticmethod
    def _parse_amount(text):
        if not text:
            return ""
        text = str(text).replace(",", "").replace("，", "")
        text = re.sub(r"[¥￥$元]", "", text)
        wan = re.search(r"([\d.]+)\s*万", text)
        if wan:
            return str(float(wan.group(1)) * 10000)
        num = re.search(r"([\d.]+)", text)
        return num.group(1) if num else ""

    @staticmethod
    def _calc_progress(item):
        try:
            t = float(item.get("target_amount", 0) or 0)
            r = float(item.get("raised_amount", 0) or 0)
            item["progress"] = f"{r / t * 100:.1f}%" if t > 0 else "0%"
        except (ValueError, ZeroDivisionError, TypeError):
            item["progress"] = "0%"
