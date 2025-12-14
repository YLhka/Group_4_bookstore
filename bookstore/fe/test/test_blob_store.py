import pytest
import uuid
from be.model.blob_store import get_blob_store

class TestBlobStore:
    def test_mongo_connection(self):
        """
        测试 MongoDB 连接是否成功。
        如果这里失败，说明 MongoDB 服务未启动或配置错误。
        """
        store = get_blob_store()
        # 强制检查 collection 是否初始化成功
        assert store.col is not None, "MongoDB 连接失败：store.col 为 None。请检查 MongoDB 服务是否启动。"
        
        # 尝试 ping 一下数据库
        try:
            store.client.admin.command('ping')
        except Exception as e:
            pytest.fail(f"无法连接到 MongoDB 服务器: {str(e)}")

    def test_put_and_get(self):
        """
        测试数据的存取功能。
        这会直接提高 put_book_blob 和 get_book_blob 的覆盖率。
        """
        store = get_blob_store()
        book_id = "test_blob_book_{}".format(str(uuid.uuid4()))
        content = "This is a long text content for testing blob store."
        book_intro = "Intro of the book."
        author_intro = "Intro of the author."

        # 1. Put
        store.put_book_blob(book_id, content, book_intro, author_intro)

        # 2. Get
        res = store.get_book_blob(book_id)
        
        # 验证取出的数据与存入的一致
        assert res.get("book_id") == book_id
        assert res.get("content") == content
        assert res.get("book_intro") == book_intro
        assert res.get("author_intro") == author_intro

    def test_update_blob(self):
        """
        测试更新功能 (Upsert)
        """
        store = get_blob_store()
        book_id = "test_blob_update_{}".format(str(uuid.uuid4()))
        
        # 第一次写入
        store.put_book_blob(book_id, "Content 1", "Intro 1", "Author 1")
        
        # 第二次写入（更新）
        store.put_book_blob(book_id, "Content 2", "Intro 2", "Author 2")
        
        # 验证是否更新
        res = store.get_book_blob(book_id)
        assert res.get("content") == "Content 2"

    def test_get_non_exist(self):
        """
        测试读取不存在的数据
        """
        store = get_blob_store()
        res = store.get_book_blob("non_exist_id_xxxxx")
        # 应该返回空对象结构
        assert res["content"] == ""
        assert res["book_intro"] == ""