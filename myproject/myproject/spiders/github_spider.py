# myproject/spiders/github_spider.py
import json
import platform
import scrapy
from myproject.items import GithubRepoItem


class GithubSpider(scrapy.Spider):
    """
    分布式爬取 GitHub 搜索 API
    搜索各种语言的热门仓库

    使用 GitHub REST API，无需解析 HTML
    """

    name = "github_spider"
    redis_key = "github_spider:start_urls"

    # 搜索各种语言
    LANGUAGES = [
        "python", "java", "javascript", "go",
        "rust", "typescript", "c++", "c#",
    ]

    API_URL = (
        "https://api.github.com/search/repositories"
        "?q=language:{lang}+stars:>1000"
        "&sort=stars&order=desc&per_page=50&page={page}"
    )

    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,               # GitHub 限速严格
        "CONCURRENT_REQUESTS": 8,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "application/vnd.github.v3+json",
            # 如果有 Token 可以加上，提高速率限制
            # "Authorization": "token ghp_xxxxxxxxxxxx",
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node_id = f"{platform.node()}_{id(self) % 1000}"

    def start_requests(self):
        """为每种语言生成前 3 页的请求"""
        for lang in self.LANGUAGES:
            for page in range(1, 4):
                url = self.API_URL.format(lang=lang, page=page)
                yield scrapy.Request(
                    url,
                    callback=self.parse_api,
                    meta={"language": lang, "page": page},
                )

    def parse_api(self, response):
        """解析 GitHub API JSON 响应"""
        data = json.loads(response.text)
        repos = data.get("items", [])

        for repo in repos:
            item = GithubRepoItem()
            item["repo_name"] = repo.get("full_name", "")
            item["description"] = repo.get("description", "") or ""
            item["language"] = repo.get("language", "") or ""
            item["stars"] = str(repo.get("stargazers_count", 0))
            item["forks"] = str(repo.get("forks_count", 0))
            item["url"] = repo.get("html_url", "")
            item["crawl_node"] = self.node_id
            yield item

        self.logger.info(
            f"[{self.node_id}] {response.meta['language']} "
            f"page {response.meta['page']}: {len(repos)} repos"
        )
