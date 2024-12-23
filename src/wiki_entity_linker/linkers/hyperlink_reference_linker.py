import re
from typing import Dict, Optional, Tuple, Set
from spacy.tokens import Doc
from spacy.language import Language

import spacy
import logging

from elevant.evaluation.groundtruth_label import GroundtruthLabel
from elevant.models.entity_mention import EntityMention
from elevant.utils.offset_converter import OffsetConverter
from elevant.utils.pronoun_finder import PronounFinder
from elevant.models.article import Article
from elevant import settings
import elevant.utils.custom_sentencizer  # import is needed so Python finds the custom component

from wiki_entity_linker.models.entity_database import EntityDatabase


logger = logging.getLogger("main." + __name__.split(".")[-1])


def is_overlapping_span(covered_positions: Set[int], span: Tuple[int, int]) -> bool:
    """
    Check if the given span overlaps with an already linked mention in covered_positions.

    :param covered_positions: Set of character indices in the text that belong to an already linked mention.
    :param span: Span (start, end) for which to check for overlaps with already linked mentions.
    :return: Boolean indicating whether the given span overlaps with an already linked mention.
    """
    for i in range(span[0], span[1]):
        if i in covered_positions:
            return True
    return False


class HyperlinkReferenceLinker:
    LINKER_IDENTIFIER = "Hyperlink Reference Linker"

    def __init__(self, entity_db: EntityDatabase, model: Optional[Language] = None):
        if model is None:
            self.model = spacy.load(settings.LARGE_MODEL_NAME)
            self.model.add_pipe("custom_sentencizer", before="parser")
        else:
            self.model = model

        self.entity_db = entity_db

    def add_synonyms(self, entity_id: str, synonym_dict: Dict):
        """
        Add all aliases of the given entity to the given synonym dictionary.
        """
        synonyms = self.entity_db.get_entity_aliases(entity_id)

        for syn in synonyms:
            # Do not append lowercase synonyms (e.g. "it" for Italy)
            if not syn.islower() and syn not in synonym_dict:
                synonym_dict[syn] = entity_id

        middle_name_synonyms = self.get_middle_name_synonyms(entity_id)
        if middle_name_synonyms:
            for middle_name_synonym in middle_name_synonyms:
                synonym_dict[middle_name_synonym] = entity_id

    def get_middle_name_synonyms(self, entity_id: str) -> Set[str]:
        """
        For names that include middle names, e.g. "Habern William Archibald Freeman"
        add the following name variants as synonyms:
        "Habern Freeman", "Habern W. A. Freeman", "Habern W.A. Freeman", "Habern W A Freeman"
        """
        whitelist_types = self.entity_db.get_entity_types(entity_id)
        middle_name_synonyms = set()
        if (settings.TYPE_PERSON_QID in whitelist_types or settings.TYPE_FICTIONAL_CHARACTER_QID in whitelist_types) \
                and settings.TYPE_ORGANIZATION_QID not in whitelist_types:
            # Don't do this if the entity also has type organization, since sometimes e.g. bands are
            # of type person and organization and then something like this happens:
            # The Blackeyed Susans: {'The B. Susans', 'The B Susans', 'The Susans'}
            entity_name = self.entity_db.get_entity_name(entity_id)
            name_parts = entity_name.split(" ")
            if len(name_parts) > 2 and all([n[0].isupper() for n in name_parts if n]):
                # Don't add name variants if the potential middle names are lowercase,
                # since this is typically something like
                # "Karl I of Austria" or "William Howe, 5th Viscount Howe"
                middle_name_synonyms.add(" ".join([n[0] for n in name_parts[1:-1] if n]) + " ")
                middle_name_synonyms.add("".join([n[0] + "." for n in name_parts[1:-1] if n]) + " ")
                middle_name_synonyms.add(" ".join([n[0] + "." for n in name_parts[1:-1] if n]) + " ")
                middle_name_synonyms.add("")
                middle_name_synonyms = [name_parts[0] + " " + m + name_parts[-1] for m in middle_name_synonyms]
        return middle_name_synonyms

    def link_entities(self, article: Article, doc: Optional[Doc] = None):
        if doc is None:
            doc = self.model(article.text)

        entity_links = dict()  # Mapping from mention text to entity ID for entities that are inferred from a hyperlink
        entity_synonyms = dict()  # Mapping from synonym to entity ID
        covered_positions = set()  # Set of character indices in the text that belong to an already linked mention.
        entity_mentions = []  # List of EntityMentions that are produced by the linker
        bold_title_spans = []  # List of bold title spans as Tuple (start, end) and the article title

        # Link article entity to Wikidata id
        title_entity_id = self.entity_db.link2id(article.title)
        if title_entity_id:
            entity_links[article.title] = title_entity_id
            self.add_synonyms(title_entity_id, entity_synonyms)
            bracketless_title = re.sub(r" \([^)]*?\)", "", article.title)
            if bracketless_title != article.title:
                if bracketless_title not in entity_synonyms:
                    entity_synonyms[bracketless_title] = title_entity_id
            if article.title_synonyms:
                # Bold title spans are treated like hyperlinks. Not like synonyms of hyperlinked entities
                bold_title_spans = [((s, e), article.title) for (s, e) in article.title_synonyms]

        # Link article hyperlinks to Wikidata ids
        for span, target in bold_title_spans + article.hyperlinks:
            # Overlaps are possible due to possible overlap between link and bold title synonym
            if is_overlapping_span(covered_positions, (span[0], span[1])):
                continue

            link_text = article.text[span[0]:span[1]]
            entity_id = self.entity_db.link2id(target)
            entity_whitelist_types = self.entity_db.get_entity_types(entity_id)
            if entity_id and entity_whitelist_types != [GroundtruthLabel.OTHER]:
                entity_links[link_text] = entity_id
                self.add_synonyms(entity_id, entity_synonyms)

                end_idx = span[1]

                # A trailing 's or ' should not be included in the mention unless it's part of the target article title
                trim_endings = ["'s", "'"]
                for ending in trim_endings:
                    if link_text.endswith(ending) and not target.endswith(ending):
                        end_idx = end_idx - len(ending)

                # Expand mention if that means the mention contains the target article title
                if span[0] + len(target) > end_idx and article.text[span[0]:span[0] + len(target)] == target:
                    end_idx = span[0] + len(target)

                # Expand mention to end of word
                while end_idx + 1 < len(article.text) and article.text[end_idx].isalpha():
                    end_idx += 1

                covered_positions.update(range(span[0], end_idx))

                entity_mention = EntityMention(span=(span[0], end_idx),
                                               recognized_by=self.LINKER_IDENTIFIER,
                                               entity_id=entity_id,
                                               linked_by="HRL: Hyperlink",
                                               candidates={entity_id})
                entity_mentions.append(entity_mention)

        # Get given names for detected entity mentions and use them like aliases
        for entity_id in [title_entity_id] + [em.entity_id for em in entity_mentions]:
            if self.entity_db.has_given_name(entity_id):
                first_name = self.entity_db.get_given_name(entity_id)
                # TODO: right now, always the first entity in the article with the given name is chosen
                if first_name not in entity_synonyms:
                    entity_synonyms[first_name] = entity_id

        # Link text that has been linked to an entity before, starting with the longest text
        for link_text, entity_id in sorted(entity_links.items(), key=lambda x: len(x[0]), reverse=True) + \
                sorted(entity_synonyms.items(), key=lambda x: len(x[0]), reverse=True):
            search_start_idx = 0
            if not link_text:
                continue
            while True:
                start_idx = article.text.find(link_text, search_start_idx)

                # link text / synonym was not found in remaining article text
                if start_idx == -1:
                    break

                # Only add entity if its first character is the beginning of a word
                if start_idx != 0 and article.text[start_idx - 1].isalpha():
                    search_start_idx = start_idx + 1
                    continue

                # Expand entity span to end of word
                end_idx = start_idx + len(link_text)
                num_expansions = 0
                skip = False
                while end_idx + 1 < len(article.text) and article.text[end_idx].isalpha():
                    # Don't expand in cses like Waldeck -> Waldeckers or W (Vienna) -> War
                    if num_expansions >= 3 or num_expansions >= len(link_text):
                        skip = True
                    end_idx += 1
                    num_expansions += 1
                if skip:
                    search_start_idx = end_idx
                    continue

                # Check if the found text span does overlap with an already linked entity
                if is_overlapping_span(covered_positions, (start_idx, end_idx)):
                    search_start_idx = end_idx
                    continue

                # Can't rely on case info at sentence start, therefore only link text at sentence start if it is likely
                # to be an entity judging by its pos tag and dependency tag
                tok_sent_idx = OffsetConverter.get_token_idx_in_sent(start_idx, doc)
                if tok_sent_idx == 0 and start_idx != 0 and " " not in link_text:
                    token = OffsetConverter.get_token(start_idx, doc)
                    if not token.tag_.startswith("NN") and not token.tag_.startswith("JJ") and \
                            (not token.dep_.startswith("nsubj") or PronounFinder.is_pronoun(token.text)):
                        search_start_idx = end_idx
                        continue

                # Add text span to entity mentions
                covered_positions.update(range(start_idx, end_idx))
                entity_mention = EntityMention(span=(start_idx, end_idx),
                                               recognized_by=self.LINKER_IDENTIFIER,
                                               entity_id=entity_id,
                                               linked_by="HRL Reference",
                                               candidates={entity_id})
                entity_mentions.append(entity_mention)
                search_start_idx = end_idx

        article.add_entity_mentions(entity_mentions)
