# distributed_crawler/items.py
import scrapy


class BookItem(scrapy.Item):
    """图书数据"""
    title       = scrapy.Field()
    price       = scrapy.Field()
    rating      = scrapy.Field()
    stock       = scrapy.Field()
    image_url   = scrapy.Field()
    detail_url  = scrapy.Field()
    crawl_node  = scrapy.Field()   # 记录哪个节点爬取的


class CharityProjectItem(scrapy.Item):
    project_id    = scrapy.Field()
    project_name  = scrapy.Field()
    subtitle      = scrapy.Field()
    category      = scrapy.Field()
    status        = scrapy.Field()
    org_name      = scrapy.Field()
    target_amount = scrapy.Field()
    raised_amount = scrapy.Field()
    donor_count   = scrapy.Field()
    progress      = scrapy.Field()
    start_date    = scrapy.Field()
    end_date      = scrapy.Field()
    description   = scrapy.Field()
    region        = scrapy.Field()
    detail_url    = scrapy.Field()
    image_url     = scrapy.Field()
    crawl_node    = scrapy.Field()
    crawl_time    = scrapy.Field()



class GithubRepoItem(scrapy.Item):
    """GitHub 仓库"""
    repo_name   = scrapy.Field()
    description = scrapy.Field()
    language    = scrapy.Field()
    stars       = scrapy.Field()
    forks       = scrapy.Field()
    url         = scrapy.Field()
    crawl_node  = scrapy.Field()
