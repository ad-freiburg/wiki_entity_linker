from typing import Tuple, List, Iterator

import os
import spacy
import pickle

from src import settings


class VectorGenerator:
    def __init__(self):
        self.model = spacy.load(settings.LARGE_MODEL_NAME)

    def get_vector(self, text: str):
        return self.model(text).vector


class VectorLoader:
    @staticmethod
    def iterate(vector_directory: str = settings.VECTORS_DIRECTORY) -> Iterator[Tuple[str, List[int]]]:
        for file in os.listdir(vector_directory):
            with open(settings.VECTORS_DIRECTORY + file, "rb") as f:
                vectors = pickle.load(f)
            for entity_id, vector in vectors:
                yield entity_id, vector

    @staticmethod
    def load_old():
        with open(settings.VECTORS_FILE, "rb") as f:
            vectors = pickle.load(f)
        return vectors
