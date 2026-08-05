from pathlib import Path

from data.vector_store import get_client, get_collection, get_embeddings, query_top_n, upsert_texts


class _FakeEmbeddingFunction:
    """基于字符频次的假 embedding，确定性、不需要下载真实模型。

    只用于验证 upsert/query 的排序逻辑，不追求语义质量。
    """

    def __init__(self, dims: int = 32) -> None:
        self._dims = dims

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [self._to_vector(text) for text in input]

    @staticmethod
    def name() -> str:
        # chromadb >=1.x 在存 collection 配置时会调用 embedding_function.name()
        return "fake-embedding-function"

    def embed_query(self, input: str | list[str]) -> list[float] | list[list[float]]:
        # collection.query() 内部专门调这个方法算查询文本的向量，跟 __call__ 分开
        if isinstance(input, list):
            return [self._to_vector(text) for text in input]
        return self._to_vector(input)

    def _to_vector(self, text: str) -> list[float]:
        vector = [0.0] * self._dims
        for ch in text:
            vector[ord(ch) % self._dims] += 1.0
        return vector


def _collection(tmp_path: Path, name: str = "test_collection"):
    client = get_client(persist_directory=tmp_path)
    return get_collection(client, name, embedding_function=_FakeEmbeddingFunction())


def test_query_top_n_ranks_closer_text_first(tmp_path: Path) -> None:
    collection = _collection(tmp_path)
    upsert_texts(
        collection,
        ids=["a", "b", "c"],
        texts=["美妆护肤 精致人设 成分党", "数码手机 极客科技 性能党", "美妆彩妆 国货性价比"],
    )

    results = query_top_n(collection, query_text="美妆护肤 精致成分", top_n=3)

    ids_in_order = [id_ for id_, _ in results]
    assert ids_in_order[0] in {"a", "c"}
    assert "b" == ids_in_order[-1]


def test_query_top_n_respects_top_n_limit(tmp_path: Path) -> None:
    collection = _collection(tmp_path)
    upsert_texts(collection, ids=["a", "b", "c"], texts=["文本一", "文本二", "文本三"])

    results = query_top_n(collection, query_text="文本一", top_n=2)

    assert len(results) == 2


def test_get_embeddings_returns_vectors_for_requested_ids(tmp_path: Path) -> None:
    collection = _collection(tmp_path)
    upsert_texts(collection, ids=["a", "b"], texts=["文本一", "文本二"])

    embeddings = get_embeddings(collection, ["a", "b"])

    assert set(embeddings.keys()) == {"a", "b"}
    assert len(embeddings["a"]) > 0


def test_get_embeddings_empty_ids_returns_empty_dict(tmp_path: Path) -> None:
    collection = _collection(tmp_path)
    assert get_embeddings(collection, []) == {}
