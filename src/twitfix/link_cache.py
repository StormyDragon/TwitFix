import json
from contextlib import suppress
from itertools import islice
from typing import Any, List, Optional
from uuid import UUID, uuid5

from sanic.log import logger

with suppress(ImportError):
    import pymongo

with suppress(ImportError):
    import google.cloud.firestore


class LinkCacheBase:
    def __init__(self, config) -> None:
        pass

    async def add_link_to_cache(self, video_link: str, vnf) -> bool:
        pass

    async def get_link_from_cache(self, video_link: str) -> Optional[Any]:
        pass

    async def get_links_from_cache(self, field: str, count: int, offset: int) -> List[Any]:
        pass


class MongoDBCache(LinkCacheBase):
    def __init__(self, config) -> None:
        self.client = pymongo.MongoClient(config.MONGO_DB, connect=False)
        table = config.MONGO_DB_TABLE
        self.db = self.client[table]

    async def add_link_to_cache(self, video_link: str, vnf):
        try:
            out = self.db.linkCache.insert_one(vnf)
            logger.info(" ➤ [ + ] Link added to DB cache ")
            return True
        except Exception:
            logger.info(" ➤ [ X ] Failed to add link to DB cache")
        return False

    async def get_link_from_cache(self, video_link: str):
        collection = self.db.linkCache
        vnf = collection.find_one({"tweet": video_link})
        if vnf != None:
            hits = vnf.get("hits", 0) + 1
            logger.info(
                f" ➤ [ ✔ ] Link located in DB cache. hits on this link so far: [{hits}]"
            )
            query = {"tweet": video_link}
            change = {"$inc": {"hits": 1}}
            out = self.db.linkCache.update_one(query, change)
            return vnf
        else:
            logger.info(" ➤ [ X ] Link not in DB cache")

    async def get_links_from_cache(self, field: str, count: int, offset: int):
        collection = self.db.linkCache
        return list(
            collection.find(sort=[(field, pymongo.DESCENDING)])
            .skip(offset)
            .limit(count)
        )


class FirestoreCache(LinkCacheBase):
    # Maybe extract, not really sensitive information.
    namespace = UUID("135679dc-738a-4596-8bd2-9a70c1cea8c2")

    def __init__(self, config) -> None:
        self.fire = google.cloud.firestore.AsyncClient()
        self.links = self.fire.collection("links")

    def _hash(self, link: str):
        # Links may contain weirdnesses unsuitable for storing as a key, so we namespace hash it
        # This allows us to lookup video links directly in the database.
        return uuid5(self.namespace, link).hex

    async def add_link_to_cache(self, video_link: str, vnf):
        id_ = self._hash(video_link)
        await self.links.document(id_).set(
            {**vnf, "_id": id_, "created_at": google.cloud.firestore.SERVER_TIMESTAMP}
        )

    async def get_link_from_cache(self, video_link: str):
        ref = self.links.document(self._hash(video_link))
        doc = await ref.get()
        if not doc.exists:
            return None
        await ref.update({"hits": google.cloud.firestore.Increment(1)})
        return doc.to_dict()

    async def get_links_from_cache(self, field: str, count: int, offset: int):
        docs = (
            await self.links.order_by(field, direction="DESCENDING")
            .offset(offset)
            .limit(count)
            .get()
        )
        return [doc.to_dict() for doc in docs]


# This might be fine to use under local development, but once you got a huge site running or you need
# to spread the load, this local-only system will not be useful.
class JSONCache(LinkCacheBase):
    def __init__(self, config) -> None:
        self.links_cache_filename = "links.json"
        try:
            with open(self.links_cache_filename) as f:
                self.link_cache = json.load(f)
        except FileNotFoundError:
            self.link_cache = {}

    def _write_cache(self):
        with open(self.links_cache_filename, "w") as outfile:
            json.dump(self.link_cache, outfile, indent=4, sort_keys=True)

    async def add_link_to_cache(self, video_link, vnf):
        self.link_cache[video_link] = vnf
        self._write_cache()

    async def get_link_from_cache(self, video_link):
        if video_link in self.link_cache:
            logger.info(" ➤ [ ✔ ] Link located in json cache")
            vnf = self.link_cache[video_link]
            vnf["hits"] += 1
            self._write_cache()
            return vnf
        else:
            logger.info(" ➤ [ X ] Link not in json cache")
            return None

    async def get_links_from_cache(self, field: str, count: int, offset: int):
        sorted_cache = sorted(
            self.link_cache.values(), key=lambda l: l.get(field), reverse=True
        )
        return list(islice(sorted_cache, offset, offset + count))


def initialize_link_cache(link_cache_type: str, config) -> LinkCacheBase:
    if link_cache_type == "db":
        if not globals().get("pymongo"):
            raise LookupError("the pymongo library was not included during build.")
        return MongoDBCache(config)

    if link_cache_type == "firestore":
        if not globals().get("google"):
            raise LookupError("the pymongo library was not included during build.")
        return FirestoreCache(config)

    if link_cache_type == "json":
        return JSONCache(config)

    raise LookupError("Cache system not recognized.")
