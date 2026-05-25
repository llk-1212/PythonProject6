# myproject/settings.py
import os
BOT_NAME = "myproject"
SPIDER_MODULES = ["myproject.spiders"]
NEWSPIDER_MODULE = "myproject.spiders"

# ============================================================
#  ★★★ scrapy-redis 分布式核心配置 ★★★
# ============================================================

# ── 调度器替换为 Redis 调度器 ──
# 所有节点共享同一个调度队列
SCHEDULER = "scrapy_redis.scheduler.Scheduler"

# ── 去重过滤器替换为 Redis 版本 ──
# 所有节点共享同一份去重集合，不会重复爬取
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"

# ── Redis 连接地址 ──
# 所有节点必须指向同一个 Redis
REDIS_URL = "redis://127.0.0.1:6379/0"

# ── 请求队列是否持久化 ──
# True = Redis 重启后队列不丢失（断点续爬）
SCHEDULER_PERSIST = True

# ── 不清理 Redis 中的指纹集合 ──
# 配合 SCHEDULER_PERSIST 实现断点续爬
# DUPEFILTER_DEBUG = True

# ============================================================
#  并发配置
# ============================================================
CONCURRENT_REQUESTS = 32            # 每个节点的并发请求数
CONCURRENT_REQUESTS_PER_DOMAIN = 16
DOWNLOAD_DELAY = 0.5

# ============================================================
#  自动限速
# ============================================================
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 16.0

# ============================================================
#  反爬
# ============================================================
ROBOTSTXT_OBEY = False
RETRY_TIMES = 3
DOWNLOAD_TIMEOUT = 30

# ============================================================
#  Pipeline
# ============================================================
ITEM_PIPELINES = {
    # scrapy-redis 内置 Pipeline：将 Item 存入 Redis
    "scrapy_redis.pipelines.RedisPipeline": 300,
    # 自定义 Pipeline（可选）
     "myproject.pipelines.MongoDBPipeline": 400,
}

# ══════════════════════════════════════
#  MongoDB 配置
# ══════════════════════════════════════
MONGO_URI        = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB         = os.environ.get("MONGO_DB", "charity_db")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION", "charity_projects")

REQUEST_FINGERPRINTER_IMPLEMENTATION='2.7'
# ============================================================
#  中间件
# ============================================================
DOWNLOADER_MIDDLEWARES = {
    "myproject.middlewares.SeleniumMiddleware": 500,
    "myproject.middlewares.RandomUserAgentMiddleware": 501,
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
}

# ============================================================
#  日志
# ============================================================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"

# ============================================================
#  User-Agent 池
# ============================================================
USER_AGENT_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/17.4",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
]


# ★ 优先从环境变量读取，Docker 中自动生效
# REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

