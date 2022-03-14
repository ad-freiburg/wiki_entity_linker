from typing import Iterator, Tuple, Dict

from src.models.entity_database import EntityDatabase
from src.models.entity_prediction import EntityPrediction

import os
import re
import logging

from src.prediction_readers.abstract_prediction_reader import AbstractPredictionReader

logger = logging.getLogger("main." + __name__.split(".")[-1])


class WexeaPredictionReader(AbstractPredictionReader):
    _link_re = re.compile(r"\[\[([^\[].*?)\|(.*?)\|(.*?[^\]])\]\]")

    def __init__(self, input_filepath, entity_db: EntityDatabase):
        self.entity_db = entity_db
        super().__init__(input_filepath, predictions_iterator_implemented=True)

    def _get_prediction_from_file(self, file_path: str, coref: bool) -> Dict[Tuple[int, int], EntityPrediction]:
        """
        Extract entity predictions from a file that is the output of the WEXEA
        entity annotator.
        """
        linked_file = open(file_path, "r", encoding='utf8')
        linked_text = ''.join(linked_file.readlines())
        no_mapping_count = 0
        text_position = 0
        text = ""
        predictions = dict()
        for link_match in WexeaPredictionReader._link_re.finditer(linked_text):
            link_target = link_match.group(1)
            link_text = link_match.group(2)
            link_type = link_match.group(3)
            text += linked_text[text_position:link_match.start()]
            link_start_pos = len(text)
            text += link_text
            link_end_pos = len(text)
            span = (link_start_pos, link_end_pos)
            text_position = link_match.end()
            entity_id = self.entity_db.link2id(link_target)
            if entity_id is None:
                logger.warning("\nNo mapping to Wikidata found for label '%s'" % link_target)
                no_mapping_count += 1
            candidates = {entity_id}
            if link_type == "UNKNOWN":
                # These should not be added as predictions, since WEXEA considers them unlinked
                continue
            if link_type.startswith("DISAMBIGUATION"):
                # These should not be added as predictions, since they can never be a correct link
                continue
            if (coref and link_type == "COREF") or (not coref and link_type != "COREF"):
                predictions[span] = EntityPrediction(span, entity_id, candidates)
        text += linked_text[text_position:]
        if no_mapping_count > 0:
            logger.warning("\n%d entity labels could not be matched to any Wikidata ID." % no_mapping_count)
        return predictions

    def predictions_iterator(self) -> Iterator[Dict[Tuple[int, int], EntityPrediction]]:
        """
        Yields predictions for each article.

        :return: iterator over dictionaries with predictions for each article
        """
        for file in sorted(os.listdir(self.input_filepath)):
            file_path = os.path.join(self.input_filepath, file)
            predictions = self._get_prediction_from_file(file_path, coref=False)
            yield predictions

    def article_coref_predictions_iterator(self) -> Iterator[Dict[Tuple[int, int], EntityPrediction]]:
        """
        Yields coreference predictions for each WEXEA disambiguation result file
        in the given directory.
        """
        for file in sorted(os.listdir(self.input_filepath)):
            file_path = os.path.join(self.input_filepath, file)
            predictions = self._get_prediction_from_file(file_path, coref=True)
            yield predictions