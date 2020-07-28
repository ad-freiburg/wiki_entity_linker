from typing import Iterator, Tuple, Set

from src.wikipedia_corpus import WikipediaCorpus
from src.entity_database import EntityDatabase
from src.conll_benchmark import conll_documents


def expand_span(text: str, span: Tuple[int, int]) -> Tuple[int, int]:
    begin, end = span
    while begin - 1 > 0 and text[begin - 1].isalpha():
        begin = begin - 1
    while end < len(text) and text[end].isalpha():
        end = end + 1
    return begin, end


class WikipediaExampleReader:
    def __init__(self, entity_db: EntityDatabase):
        self.entity_db = entity_db

    def iterate(self, n: int = -1) -> Iterator[Tuple[str, Set[Tuple[Tuple[int, int], str]]]]:
        for article in WikipediaCorpus.development_articles(n):
            ground_truth = set()
            for span, target in article.links:
                span = expand_span(article.text, span)
                entity_id = self.entity_db.link2id(target)
                if entity_id is None:
                    entity_id = "Unknown"
                ground_truth.add((span, entity_id))
            yield article.text, ground_truth


class ConllExampleReader:
    def __init__(self, entity_db: EntityDatabase):
        self.entity_db = entity_db

    def iterate(self, n: int = -1) -> Iterator[Tuple[str, Set[Tuple[Tuple[int, int], str]]]]:
        for i, document in enumerate(conll_documents()):
            if i == n:
                break
            ground_truth = set()
            text_pos = -1
            inside = False
            entity_id = None
            mention_start = None
            for token in document.tokens:
                if inside and token.true_label != "I":
                    span = (mention_start, text_pos)
                    ground_truth.add((span, entity_id))
                    inside = False
                text_pos += 1  # space
                if token.true_label.startswith("Q") or token.true_label == "B":
                    entity_id = token.true_label if token.true_label.startswith("Q") else "Unknown"
                    mention_start = text_pos
                    inside = True
                text_pos += len(token.text)
            if inside:
                span = (mention_start, text_pos)
                ground_truth.add((span, entity_id))
            yield document.text(), ground_truth
