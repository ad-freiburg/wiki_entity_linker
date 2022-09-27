import os
import logging

from typing import Iterator

from pynif import NIFCollection

from src.evaluation.groundtruth_label import GroundtruthLabel
from src.models.entity_database import EntityDatabase
from src.models.article import Article
from src.utils.knowledge_base_mapper import KnowledgeBaseMapper
from src.utils.nested_groundtruth_handler import NestedGroundtruthHandler

logger = logging.getLogger("main." + __name__.split(".")[-1])


class NifBenchmarkReader:
    def __init__(self, entity_db: EntityDatabase):
        self.entity_db = entity_db
        self.article_id_counter = 0

    def get_articles_from_nif(self, nif_content: str) -> Iterator[Article]:
        """
        Create articles from the given NIF content.
        """
        nif_doc = NIFCollection.loads(nif_content)

        no_mapping_count = 0

        # NIF contexts have random order by default. Make sure results are reproducible by sorting by URI
        for context in sorted(nif_doc.contexts, key=lambda c: c.uri):
            label_id_counter = 0
            text = context.mention
            if not text:
                # This happens e.g. in KORE50 for the parent context
                # <http://www.mpi-inf.mpg.de/yago-naga/aida/download/KORE50.tar.gz/AIDA.tsv>
                continue
            title = context.uri
            labels = []
            for phrase in context.phrases:
                span = phrase.beginIndex, phrase.endIndex
                entity_uri = phrase.taIdentRef
                entity_id = KnowledgeBaseMapper.get_wikidata_qid(entity_uri, self.entity_db, verbose=True)
                if not entity_id:
                    no_mapping_count += 1
                    entity_id = "Unknown"
                    entity_name = "UnknownNoMapping"
                else:
                    # The name for the GT label is Unknown for now, but is added when creating a benchmark in our format
                    entity_name = "Unknown"

                labels.append(GroundtruthLabel(label_id_counter, span, entity_id, entity_name))
                label_id_counter += 1

            # Assign parent and child ids to GT labels in case of nested GT labels
            NestedGroundtruthHandler.assign_parent_and_child_ids(labels)

            article = Article(id=self.article_id_counter, title=title, text=text, labels=labels)
            self.article_id_counter += 1

            yield article

        if no_mapping_count > 0:
            logger.info("%d entity names could not be mapped to any Wikidata QID (includes unknown entities)."
                           % no_mapping_count)

    def get_articles_from_file(self, filepath: str) -> Iterator[Article]:
        """
        Yields all articles with their GT labels from the given file.
        """
        with open(filepath, "r", encoding="utf8") as file:
            file_content = file.readlines()
            file_content = "".join(file_content)
            for article in self.get_articles_from_nif(file_content):
                yield article

    def article_iterator(self, benchmark_path: str) -> Iterator[Article]:
        """
        Yields for each document in the NIF file or directory with NIF files
        a article with labels.
        """
        # Reset article ID counter
        self.article_id_counter = 0
        if os.path.isdir(benchmark_path):
            for filename in sorted(os.listdir(benchmark_path)):
                file_path = os.path.join(benchmark_path, filename)
                articles = self.get_articles_from_file(file_path)
                for article in articles:
                    yield article
        else:
            articles = self.get_articles_from_file(benchmark_path)
            for article in articles:
                yield article