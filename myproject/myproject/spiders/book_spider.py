# distributed_crawler/spiders/book_spider.py
import platform
import scrapy
from myproject.items import BookItem

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


class BookSpider(scrapy.Spider):
    """
    分布式爬取 books.toscrape.com
    1000 本书，50 页，多节点协同爬取

    关键点：
      - 继承 scrapy.Spider（不是 CrawlSpider）
      - 使用 lpush 将起始 URL 推入 Redis 队列
      - 所有节点从同一个 Redis 队列取任务
    """

    name = "book_spider"

    # ★ scrapy-redis 要求：使用 redis_key 定义队列名
    # 而不是 start_urls
    redis_key = "book_spider:start_urls"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 记录当前节点标识
        self.node_id = f"{platform.node()}_{id(self) % 1000}"

    def start_requests(self):
        """
        分布式模式下通常不需要重写此方法
        起始 URL 通过 Redis 推入：
          redis-cli LPUSH book_spider:start_urls "https://books.toscrape.com/"
        Scrapy-redis 会自动从 redis_key 中取出 URL 并生成请求
        这里重写仅为兼容单机调试
        """
        url = "https://books.toscrape.com/"
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        """解析图书列表页"""

        books = response.xpath("//article[@class='product_pod']")

        for book in books:
            item = BookItem()

            item["title"] = book.xpath("h3/a/@title").get("")
            item["price"] = book.xpath(
                "div[@class='product_price']/p[@class='price_color']/text()"
            ).get("")
            item["image_url"] = book.xpath(
                "div[@class='image_container']/img/@src"
            ).get("")
            item["detail_url"] = book.xpath("h3/a/@href").get("")

            # 解析评分
            rating_class = book.xpath("p/@class").get("")
            rating_text = rating_class.split()[-1] if rating_class else "Zero"
            item["rating"] = RATING_MAP.get(rating_text, 0)

            # 库存状态
            item["stock"] = "In Stock" if book.xpath(
                "div[@class='product_price']/p[contains(@class,'instock')]"
            ).get() else "Out of Stock"

            # ★ 标记是哪个节点爬取的
            item["crawl_node"] = self.node_id

            yield item

        # ★ 翻页：将下一页 URL 加入队列
        # scrapy-redis 会自动将这些 URL 存入 Redis，所有节点共享
        next_page = response.xpath("//li[@class='next']/a/@href").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
