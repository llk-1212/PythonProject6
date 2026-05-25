# distributed_crawler/pipelines.py
import json
import logging

import redis
import pymongo
import logging
from datetime import datetime
from pymongo import MongoClient, ASCENDING,TEXT
from pymongo.errors import DuplicateKeyError, BulkWriteError

logger = logging.getLogger(__name__)


class StatsPipeline:
    """统计每个节点的爬取数量"""

    def __init__(self):
        self.node_stats = {}

    def process_item(self, item, spider):
        node = item.get("crawl_node", "unknown")
        self.node_stats[node] = self.node_stats.get(node, 0) + 1
        return item

    def close_spider(self, spider):
        logger.info("=" * 50)
        logger.info("分布式爬取统计：")
        total = 0
        for node, count in sorted(self.node_stats.items()):
            logger.info(f"  节点 {node}: {count} 条")
            total += count
        logger.info(f"  合计: {total} 条")
        logger.info("=" * 50)


class MongoDBPipeline:
    """
    分布式 MongoDB Pipeline

    特性：
      1. 按 project_id 去重（upsert 模式）
      2. 自动建索引
      3. 支持断点续爬（重复数据自动更新）
      4. 统计每个节点写入量
    """

    def __init__(self, mongo_uri, mongo_db, collection_name):
        self.mongo_uri      = mongo_uri
        self.mongo_db       = mongo_db
        self.collection_name = collection_name
        self.count          = 0
        self.insert_count   = 0
        self.update_count   = 0
        self.error_count    = 0

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri       = crawler.settings.get("MONGO_URI", "mongodb://localhost:27017"),
            mongo_db        = crawler.settings.get("MONGO_DB", "charity_db"),
            collection_name = crawler.settings.get("MONGO_COLLECTION", "projects"),
        )

    def open_spider(self, spider):
        """连接 MongoDB，建索引"""
        self.client     = MongoClient(self.mongo_uri)
        self.db         = self.client[self.mongo_db]
        self.collection = self.db[self.collection_name]

        # ── 建索引 ──
        self.collection.create_index(
            [("project_id", ASCENDING)],
            unique=True,
            name="idx_project_id",
        )
        self.collection.create_index(
            [("category", ASCENDING)],
            name="idx_category",
        )
        self.collection.create_index(
            [("crawl_time", ASCENDING)],
            name="idx_crawl_time",
        )
        self.collection.create_index(
            [("raised_amount", ASCENDING)],
            name="idx_raised_amount",
        )
        self.collection.create_index(
            [("project_name", TEXT), ("description", TEXT)],
            name="idx_text_search",
        )

        logger.info(
            f"[MongoDB] 已连接 {self.mongo_uri}\n"
            f"  数据库: {self.mongo_db}\n"
            f"  集合:   {self.collection_name}\n"
            f"  索引:   project_id(唯一), category, crawl_time, "
            f"raised_amount, 全文搜索"
        )

    def process_item(self, item, spider):
        """写入 MongoDB，用 upsert 实现去重"""

        data = dict(item)
        data["updated_at"] = datetime.now()

        # 首次爬取的文档加上 created_at
        filter_query = {"project_id": data.get("project_id", "")}
        update_data = {
            "$set": data,
            "$setOnInsert": {"created_at": datetime.now()},
        }

        try:
            result = self.collection.update_one(
                filter_query,
                update_data,
                upsert=True,       # 不存在则插入，存在则更新
            )

            if result.upserted_id:
                self.insert_count += 1
            elif result.modified_count > 0:
                self.update_count += 1

            self.count += 1

        except DuplicateKeyError:
            # 并发写入时的竞态条件，安全忽略
            self.update_count += 1
            self.count += 1

        except Exception as e:
            self.error_count += 1
            logger.error(
                f"[MongoDB] 写入失败: {e}\n"
                f"  project_id={data.get('project_id')}\n"
                f"  project_name={data.get('project_name')}"
            )

        return item

    def close_spider(self, spider):
        """爬虫结束，输出统计"""

        logger.info("=" * 60)
        logger.info("[MongoDB] 爬取完成统计：")
        logger.info(f"  总处理:   {self.count} 条")
        logger.info(f"  新增:     {self.insert_count} 条")
        logger.info(f"  更新:     {self.update_count} 条")
        logger.info(f"  失败:     {self.error_count} 条")
        logger.info(f"  集合总量: {self.collection.count_documents({})} 条")
        logger.info("=" * 60)

        # ── 输出分类统计 ──
        pipeline = [
            {"$group": {
                "_id": "$category",
                "count": {"$sum": 1},
                "total_raised": {"$sum": {"$toDouble": {
                    "$ifNull": ["$raised_amount", "0"]
                }}},
            }},
            {"$sort": {"count": -1}},
        ]

        results = list(self.collection.aggregate(pipeline))
        if results:
            logger.info("\n分类统计：")
            for r in results:
                logger.info(
                    f"  {r['_id'] or '未知':<12} "
                    f"{r['count']:>5} 个  "
                    f"¥{r['total_raised']:>14,.2f}"
                )

        self.client.close()



class ConsolePipeline:
    """控制台实时输出"""

    def process_item(self, item, spider):
        name = (item.get("project_name") or "未知")[:22]
        raised = item.get("raised_amount", "0") or "0"
        progress = item.get("progress", "-")
        org = (item.get("org_name") or "")[:15]

        logger.info(
            f"  {name:<22} | "
            f"¥{raised:<12} | "
            f"{progress:<7} | "
            f"{org}"
        )
        return item

