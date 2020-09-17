from typing import List, Tuple, Optional, Dict

import spacy
from spacy.tokens.doc import Doc

from src.entity_database import EntityDatabase
from src.abstract_entity_linker import AbstractEntityLinker
from src.entity_prediction import EntityPrediction
from src.dates import is_date


def get_split_points(text: str) -> List[int]:
    return [-1] + [i for i, c in enumerate(text) if not c.isalnum()] + [len(text)]


def contains_uppercase(text: str) -> bool:
    return any(c.isupper() for c in text)


class MaximumMatchingNER(AbstractEntityLinker):
    def predict(self, text: str, doc: Optional[Doc] = None) -> Dict[Tuple[int, int], EntityPrediction]:
        mention_spans = self.entity_mentions(text)
        predictions = {span: EntityPrediction(span, None, set()) for span in mention_spans}
        return predictions

    def has_entity(self, entity_id: str) -> bool:
        return False

    def __init__(self, entity_db: Optional[EntityDatabase] = None):
        if entity_db is None:
            entity_db = EntityDatabase()
            entity_db.load_entities_big()
            entity_db.add_name_aliases()
            entity_db.add_synonym_aliases()
            entity_db.load_mapping()
            entity_db.load_redirects()
            entity_db.load_link_frequencies()
            entity_db.add_link_aliases()
        model = spacy.load("en_core_web_sm")
        stopwords = model.Defaults.stop_words
        exclude = {"January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                   "November", "December", "The", "A", "An"}
        remove_beginnings = {"a ", "an ", "the ", "in ", "at "}
        remove_ends = {"'s"}
        self.alias_frequencies = {}
        for alias in entity_db.aliases:
            if len(alias) == 0:
                continue
            lowercased = alias[0].lower() + alias[1:]
            ignore_alias = False
            for beginning in remove_beginnings:
                if lowercased.startswith(beginning):
                    if alias[0].islower() or entity_db.contains_alias(alias[len(beginning):]):
                        ignore_alias = True
                        break
            if not alias[-1].isalnum() and entity_db.contains_alias(alias[:-1]):
                ignore_alias = True
            if is_date(alias):
                ignore_alias = True
            if alias[0].islower():
                ignore_alias = True
            if ignore_alias:
                continue
            for end in remove_ends:
                if alias.endswith(end):
                    alias = alias[:-(len(end))]
                    break
            if lowercased not in stopwords and alias not in exclude and contains_uppercase(alias):
                alias_frequency = entity_db.get_alias_frequency(alias)
                if len(alias) > 1 and alias_frequency > 0:
                    self.alias_frequencies[alias] = alias_frequency
        self.max_len = 20
        self.model = None

    def entity_mentions(self, text: str) -> List[Tuple[int, int]]:
        split_points = get_split_points(text)
        point_i = 0
        n_points = len(split_points)
        mention_spans = []
        while point_i < n_points - 1:
            start_point = split_points[point_i] + 1
            for length in reversed(range(1, min(self.max_len + 1, n_points - point_i))):
                end_point = split_points[point_i + length]
                if end_point > start_point:
                    snippet = text[start_point:end_point]
                    if snippet in self.alias_frequencies:
                        point_i += length - 1
                        mention_spans.append((start_point, end_point))
                        break
            point_i += 1
        return mention_spans

    def get_alias_frequency(self, alias: str) -> int:
        return self.alias_frequencies[alias] if alias in self.alias_frequencies else 0
