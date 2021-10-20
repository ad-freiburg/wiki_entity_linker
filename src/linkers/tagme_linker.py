from typing import Dict, Tuple, Optional

import tagme

from src.models.entity_database import EntityDatabase
from src.models.entity_prediction import EntityPrediction
from src.linkers.abstract_entity_linker import AbstractEntityLinker


tagme.GCUBE_TOKEN = "56af583d-5f6e-496f-aea2-eab06673b6a3-843339462"


class TagMeLinker(AbstractEntityLinker):
    NER_IDENTIFIER = LINKER_IDENTIFIER = "TAGME"

    def __init__(self, entity_db: EntityDatabase, rho_threshold: float = 0.2):
        self.entity_db = entity_db
        self.model = None
        self.rho_threshold = rho_threshold

    def predict(self,
                text: str,
                doc=None,
                uppercase: Optional[bool] = False) -> Dict[Tuple[int, int], EntityPrediction]:
        annotations = tagme.annotate(text).get_annotations(self.rho_threshold)
        annotations = sorted(annotations, key=lambda ann: ann.score, reverse=True)
        predictions = {}
        count = 0
        for ann in annotations:
            qid = self.entity_db.link2id(ann.entity_title)
            if qid is not None:
                span = (ann.begin, ann.end)
                snippet = text[span[0]:span[1]]
                if uppercase and snippet.islower():
                    continue
                predictions[span] = EntityPrediction(span, qid, {qid})
            else:
                print("\nNo mapping to Wikidata found for label '%s'" % ann.entity_title)
                count += 1
        if count > 0:
            print("\n%d entity labels could not be matched to any Wikidata id." % count)
        return predictions

    def has_entity(self, entity_id: str) -> bool:
        return True
