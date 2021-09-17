import os

from typing import Dict, Tuple, Iterator
from xml.etree import ElementTree

from src.models.entity_database import EntityDatabase
from src.models.entity_prediction import EntityPrediction


class WikifierPredictionReader:
    def __init__(self, entity_db: EntityDatabase):
        self.entity_db = entity_db

    @staticmethod
    def is_same_title(unicode_error_title: str, title: str) -> bool:
        if title is None:
            return False
        error_indices = [i for i, char in enumerate(unicode_error_title) if char == "?"]
        new_title = ''.join([char for i, char in enumerate(title) if i not in error_indices])
        return new_title == unicode_error_title.replace("?", "")

    def get_correct_wikipedia_title(self, wiki_title: str, wiki_id: int) -> str:
        """
        For the Wikipedia title and Wikipedia page ID predicted by Wikifier
        retrieve the corresponding Wikidata ID.
        """
        wiki_title_by_id = self.entity_db.get_wikipedia_title_by_wikipedia_id(wiki_id)
        # The Wikifier output labels contain encoding errors indicated by the character "?".
        # Use the Wikipedia page ID to try to map the linked entity to a Wikidata QID anyway.
        if wiki_title != wiki_title_by_id and "?" in wiki_title:
            if wiki_id != 3658264 and wiki_title_by_id is not None:
                # There is an error in the Wikifier output: many page ids in the Wikifier result
                # are 3658264 which corresponds to the Wikipedia title "Williams Lake Water Aerodrome"
                # Others point to an empty page. Keep the WikiTitle in this case, otherwise use
                # the title extracted via the page ID
                wiki_title = wiki_title_by_id
            else:
                print("\nCould not resolve missing characters in '%s', title by page ID: '%s', ID: %d"
                      % (wiki_title, wiki_title_by_id, wiki_id))
        return wiki_title

    def _get_prediction_from_file(self, file_path: str) -> Dict[Tuple[int, int], EntityPrediction]:
        """
        Yields all predictions in the given wikifier disambiguation result file

        :param file_path: path to the wikifier result file
        :return: dictionary that contains all predictions for the given file
        """
        predictions = {}
        spans = []
        xml_tree = ElementTree.parse(file_path)
        root = xml_tree.getroot()
        count = 0
        for entity_prediction in root.iter('Entity'):
            start = int(entity_prediction.find('EntityTextStart').text)
            end = int(entity_prediction.find('EntityTextEnd').text)
            span = start, end

            wiki_title = entity_prediction.find('TopDisambiguation').find('WikiTitle').text
            wiki_title = wiki_title.replace("_", " ")
            wiki_id = int(entity_prediction.find('TopDisambiguation').find('WikiTitleID').text)
            wiki_title = self.get_correct_wikipedia_title(wiki_title, wiki_id)
            entity_id = self.entity_db.link2id(wiki_title)
            if not entity_id:
                print("\nNo mapping to Wikidata found for label '%s'" % wiki_title)
                count += 1

            candidates = set()
            for candidate in entity_prediction.find('DisambiguationCandidates').iter('Candidate'):
                candidate_wiki_title = candidate.find('WikiTitle').text
                candidate_wiki_title = candidate_wiki_title.replace("_", " ")
                candidate_wiki_id = int(entity_prediction.find('TopDisambiguation').find('WikiTitleID').text)
                candidate_wiki_title = self.get_correct_wikipedia_title(candidate_wiki_title, candidate_wiki_id)
                candidate_entity_id = self.entity_db.link2id(candidate_wiki_title)
                if candidate_entity_id:
                    candidates.add(candidate_entity_id)

            # Avoid overlapping spans: Keep the larger one.
            # Assume that Wikifier predictions are sorted by span start (but not by span end)
            if spans and spans[-1][1] > span[0]:
                # Overlap detected.
                previous_span_length = spans[-1][1] - spans[-1][0]
                current_span_length = span[1] - span[0]
                if previous_span_length >= current_span_length:
                    # Previous span is longer than current span, so discard current prediction
                    continue
                else:
                    del predictions[spans[-1]]
                    del spans[-1]

            predictions[span] = EntityPrediction(span, entity_id, candidates)
            spans.append(span)

        if count > 0:
            print("\n%d entity labels could not be matched to any Wikidata id." % count)

        return predictions

    def article_predictions_iterator(self, disambiguation_dir: str) -> Iterator[Dict[Tuple[int, int], EntityPrediction]]:
        """
        Yields predictions for each wikfier disambiguation result file in the given directory

        :param disambiguation_dir: path to the directory that contains the wikifier disambiguation results
        :return: iterator over predictions for each file in the given directory
        """
        for file in sorted(os.listdir(disambiguation_dir)):
            if file.endswith(".full.xml"):
                file_path = os.path.join(disambiguation_dir, file)
                predictions = self._get_prediction_from_file(file_path)
                yield predictions
