from typing import List, Set, Tuple

from itertools import chain

from src.evaluation.case import Case, ErrorLabel
from src.evaluation.groundtruth_label import GroundtruthLabel, is_level_one
from src.evaluation.mention_type import MentionType
from src.models.entity_database import EntityDatabase
from src.models.wikidata_entity import WikidataEntity
from src.models.wikipedia_article import WikipediaArticle


def label_errors(article: WikipediaArticle, cases: List[Case], entity_db: EntityDatabase):
    text = article.text
    unknown_ground_truth_spans = {case.span for case in cases if case.has_ground_truth()
                                  and not case.is_known_entity()}
    cases = [case for case in cases if (case.is_false_positive() or case.is_known_entity())]
    label_specificity_errors(cases)
    label_demonym_errors(cases, entity_db)
    label_rare_entity_errors(text, cases, entity_db)
    label_new_rare_entity_errors(cases, entity_db)
    label_partial_name_errors(cases, entity_db)
    label_nonentity_coreference_errors(text, cases)
    label_detection_errors(cases)
    label_candidate_errors(cases)
    label_multi_candidates(cases)
    label_abstraction_and_unknown_entity_errors(cases, unknown_ground_truth_spans)
    label_hyperlink_errors(article, cases)
    label_span_errors(cases)
    label_unknown_person_errors(cases, entity_db)
    label_metonymy_errors(cases, entity_db)
    label_coreference_errors(cases)


def is_subspan(span, subspan):
    if span[0] == subspan[0] and span[1] == subspan[1]:
        return False
    return span[0] <= subspan[0] and span[1] >= subspan[1]


def label_specificity_errors(cases: List[Case]):
    """
    FN and a part of the GT mention was linked to an arbitrary entity.
    """
    false_negatives = [case for case in cases if not case.has_predicted_entity() and not case.is_true_coreference()]
    false_positives = [case for case in cases if case.is_false_positive()]
    for case in false_negatives:
        for fp in false_positives:
            if is_subspan(case.span, fp.span):
                case.add_error_label(ErrorLabel.SPECIFICITY)
                break


def label_demonym_errors(cases: List[Case], entity_db: EntityDatabase):
    for case in cases:
        if entity_db.is_demonym(case.text) and case.true_entity:
            types = set(case.true_entity.type.split("|"))
            demonym_types = {"Q27096213", "Q41710", "Q17376908"}
            if types.intersection(demonym_types):
                if case.is_correct():
                    case.add_error_label(ErrorLabel.DEMONYM_CORRECT)
                else:
                    case.add_error_label(ErrorLabel.DEMONYM_WRONG)


def label_rare_entity_errors(text: str, cases: List[Case], entity_db: EntityDatabase):
    """
    Mention was linked to a popular entity instead of the true, less popular entity.
    """
    for case in cases:
        if not case.is_correct() and case.is_known_entity() and case.predicted_entity is not None\
                and not case.is_true_coreference() and not case.is_true_quantity_or_datetime():
            mention = text[case.span[0]:case.span[1]]
            if not entity_db.is_demonym(mention):
                if entity_db.get_sitelink_count(case.true_entity.entity_id) \
                        < entity_db.get_sitelink_count(case.predicted_entity.entity_id):
                    case.add_error_label(ErrorLabel.RARE)


def label_new_rare_entity_errors(cases: List[Case], entity_db: EntityDatabase):
    for case in cases:
        if case.has_ground_truth() and case.has_predicted_entity() and case.is_named():
            if entity_db.contains_alias(case.text):
                candidates = entity_db.get_candidates(case.text)
                true_popularity = entity_db.get_sitelink_count(case.true_entity.entity_id)
                is_rare_case = False
                for candidate in candidates:
                    if entity_db.get_sitelink_count(candidate) > true_popularity:
                        is_rare_case = True
                        break
                if is_rare_case:
                    if case.is_correct():
                        case.add_error_label(ErrorLabel.RARE_CORRECT)
                    elif entity_db.get_sitelink_count(case.predicted_entity.entity_id) > true_popularity:
                        case.add_error_label(ErrorLabel.RARE_WRONG)


def label_partial_name_errors(cases: List[Case], entity_db: EntityDatabase):
    """
    FN and the GT mention is part of the entity name.
    """
    for case in cases:
        if case.has_ground_truth() and case.is_named() and not entity_db.is_demonym(case.text):
            name = case.true_entity.name
            if " " in name and case.text in name.split():
                if case.is_correct() or case.is_true_quantity_or_datetime():
                    case.add_error_label(ErrorLabel.PARTIAL_NAME_CORRECT)
                else:
                    case.add_error_label(ErrorLabel.PARTIAL_NAME_WRONG)


NONENTITY_PRONOUNS = {"it", "this", "that", "its"}


def label_nonentity_coreference_errors(text: str, cases: List[Case]):
    for case in cases:
        if case.is_optional():
            continue
        if not case.has_ground_truth():
            snippet = text[case.span[0]:case.span[1]]
            if snippet[0].lower() + snippet[1:] in NONENTITY_PRONOUNS:
                case.add_error_label(ErrorLabel.NON_ENTITY_COREFERENCE)


def label_detection_errors(cases: List[Case]):
    for case in cases:
        if not case.is_coreference() and not case.has_predicted_entity() and not case.is_optional():
            case.add_error_label(ErrorLabel.UNDETECTED)
            if not is_level_one(case.text):
                case.add_error_label(ErrorLabel.UNDETECTED_LOWERCASE)


def label_candidate_errors(cases: List[Case]):
    for case in cases:
        if case.is_false_negative() and not case.is_coreference() and case.is_detected() and \
                not case.true_entity_is_candidate():
            case.add_error_label(ErrorLabel.WRONG_CANDIDATES)


def label_multi_candidates(cases: List[Case]):
    for case in cases:
        if case.has_ground_truth() and len(case.candidates) > 1 and case.true_entity_is_candidate():
            if case.is_correct():
                case.add_error_label(ErrorLabel.MULTI_CANDIDATES_CORRECT)
            elif not case.is_optional() or case.is_false_positive():
                # If the case is optional and not correct, but a "FN", don't add error label, just ignore it
                case.add_error_label(ErrorLabel.MULTI_CANDIDATES_WRONG)


def overlaps(span1, span2):
    return not (span1[0] >= span2[1] or span2[0] >= span1[1])


def contains_uppercase_word(text: str):
    for word in text.split():
        if len(word) > 0 and word[0].isupper():
            return True
    return False


def label_abstraction_and_unknown_entity_errors(cases: List[Case],
                                                unknown_ground_truth_spans: Set[Tuple[int, int]]):
    ground_truth_spans = [case.span for case in cases if case.has_ground_truth()]
    for case in cases:
        if case.is_false_positive() and case.mention_type == MentionType.NAMED:
            overlap = False
            for gt_span in chain(ground_truth_spans, unknown_ground_truth_spans):
                if overlaps(case.span, gt_span):
                    overlap = True
                    break
            contains_upper = contains_uppercase_word(case.text)
            if not overlap and not contains_upper:
                case.add_error_label(ErrorLabel.ABSTRACTION)
            elif contains_upper and (not overlap or case.span in unknown_ground_truth_spans):
                case.add_error_label(ErrorLabel.UNKNOWN_NAMED_ENTITY)


def label_hyperlink_errors(article: WikipediaArticle, cases: List[Case]):
    hyperlink_spans = set(span for span, target in article.links)
    for case in cases:
        if case.span in hyperlink_spans and case.has_ground_truth() and case.is_known_entity():
            if case.is_correct() or case.is_true_quantity_or_datetime():
                case.add_error_label(ErrorLabel.HYPERLINK_CORRECT)
            elif not case.is_optional() or case.is_false_positive():
                # If the case is optional and not correct, but a "FN", don't add error label, just ignore it
                case.add_error_label(ErrorLabel.HYPERLINK_WRONG)


def label_coreference_errors(cases: List[Case]):
    for i, case in enumerate(cases):
        if case.is_coreference() and case.is_false_negative():
            if not case.has_predicted_entity():
                case.add_error_label(ErrorLabel.COREFERENCE_NO_REFERENCE)
            else:
                true_reference = None
                for j in range(i - 1, -1, -1):
                    if cases[j].mention_type == MentionType.NAMED and cases[j].has_ground_truth() and \
                            cases[j].true_entity.entity_id == case.true_entity.entity_id:
                        true_reference = cases[j]
                        break
                if true_reference is not None:
                    if true_reference.has_predicted_entity() and \
                            true_reference.predicted_entity.entity_id == case.predicted_entity.entity_id:
                        case.add_error_label(ErrorLabel.COREFERENCE_REFERENCED_WRONG)
                    else:
                        case.add_error_label(ErrorLabel.COREFERENCE_WRONG_REFERENCE)


def label_span_errors(cases: List[Case]):
    """
    False positives, that overlap with a ground truth mention with the same entity id.
    """
    ground_truth = {case.span: case.true_entity for case in cases if case.has_ground_truth()}
    for case in cases:
        if case.is_false_positive():
            for gt_span in ground_truth:
                gt_label = ground_truth[gt_span]
                if gt_span == case.span:
                    # Span is correct -> no need to consider it
                    continue
                if overlaps(case.span, gt_span) and (case.predicted_entity.entity_id == gt_label.entity_id or
                                                     is_true_quantity_or_datetime(case.predicted_entity, gt_label)):
                    # Span is wrong and entity id is correct or it's a true quantity or datetime.
                    case.add_error_label(ErrorLabel.SPAN_WRONG)
                    break


PERSON_TYPE_QID = "Q18336849"


def label_unknown_person_errors(cases: List[Case], entity_db: EntityDatabase):
    for case in cases:
        if case.is_false_positive() and \
                (ErrorLabel.ABSTRACTION in case.error_labels or
                 case.true_entity is not None and case.true_entity.entity_id.startswith("Unknown")) \
                and PERSON_TYPE_QID in entity_db.get_entity(case.predicted_entity.entity_id).type.split("|"):
            case.add_error_label(ErrorLabel.UNKNOWN_PERSON)


LOCATION_TYPE_ID = "Q27096213"
ETHNICITY_TYPE_ID = "Q41710"


def label_metonymy_errors(cases: List[Case], entity_db: EntityDatabase):
    for case in cases:
        if case.is_false_negative() and case.is_false_positive() and \
                not case.true_entity.entity_id.startswith("Unknown"):
            n_locations = 0
            true_types = case.true_entity.type.split("|")
            predicted_types = entity_db.get_entity(case.predicted_entity.entity_id).type.split("|")
            if LOCATION_TYPE_ID in true_types:
                n_locations += 1
            if LOCATION_TYPE_ID in predicted_types:
                n_locations += 1
            if n_locations == 1 and PERSON_TYPE_QID not in true_types and PERSON_TYPE_QID not in predicted_types \
                    and ETHNICITY_TYPE_ID not in true_types and ETHNICITY_TYPE_ID not in predicted_types:
                case.add_error_label(ErrorLabel.METONYMY)


def is_true_quantity_or_datetime(predicted_entity: WikidataEntity, gt_label: GroundtruthLabel) -> bool:
    return gt_label.type == predicted_entity.type and (gt_label.is_datetime() or gt_label.is_quantity())
