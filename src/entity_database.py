from typing import Dict, Set, Tuple, Iterator, Optional, List

from src.gender import Gender
from src.wikidata_entity import WikidataEntity
from src.entity_database_reader import EntityDatabaseReader


class EntityDatabase:
    def __init__(self):
        self.entities = {}
        self.entities: Dict[str, WikidataEntity]
        self.entities_by_name = {}
        self.entities: Dict[str, Set[str]]
        self.aliases = {}
        self.aliases: Dict[str, Set[str]]
        self.wikipedia2wikidata = {}
        self.wikipedia2wikidata: Dict[str, str]
        self.wikidata2wikipedia = {}
        self.wikidata2wikipedia: Dict[str, str]
        self.redirects = {}
        self.redirects: Dict[str, str]
        self.link_frequencies = {}
        self.link_frequencies: Dict[str, Tuple[str, int]]
        self.entity_frequencies = {}
        self.entity_frequencies: Dict[str, int]
        self.entity2gender = {}
        self.entity2gender: Dict[str, Gender]
        self.given_names = {}
        self.given_names: Dict[str, str]
        self.family_names = {}
        self.family_names: Dict[str, str]
        self.entity2types = {}
        self.entity2types: Dict[str, List[str]]
        self.unigram_counts = {}

    def add_entity(self, entity: WikidataEntity):
        self.entities[entity.entity_id] = entity
        if entity.name not in self.entities_by_name:
            self.entities_by_name[entity.name] = {entity.entity_id}
        else:
            self.entities_by_name[entity.name].add(entity.entity_id)

    def contains_entity(self, entity_id: str) -> bool:
        return entity_id in self.entities

    def contains_entity_name(self, entity_name: str) -> bool:
        return entity_name in self.entities_by_name

    def get_entity(self, entity_id: str) -> WikidataEntity:
        return self.entities[entity_id]

    def get_score(self, entity_id: str) -> int:
        if not self.contains_entity(entity_id):
            return 0
        return self.get_entity(entity_id).score

    def load_entities_small(self, minimum_score: int = 0):
        for entity in EntityDatabaseReader.read_entity_file():
            if entity.score >= minimum_score:
                self.add_entity(entity)

    def load_entities_big(self):
        mapping = EntityDatabaseReader.get_mapping()
        for entity_name in mapping:
            entity_id = mapping[entity_name]
            entity = WikidataEntity(entity_name, 0, entity_id, [])
            self.add_entity(entity)

    def size_entities(self) -> int:
        return len(self.entities)

    def add_alias(self, alias: str, entity_id: str):
        if alias not in self.aliases:
            self.aliases[alias] = {entity_id}
        else:
            self.aliases[alias].add(entity_id)
        self.entities[entity_id].synonyms.append(alias)

    def add_synonym_aliases(self):
        for entity in EntityDatabaseReader.read_entity_file():
            if self.contains_entity(entity.entity_id):
                for alias in entity.synonyms + [entity.name]:
                    self.add_alias(alias, entity.entity_id)

    def add_name_aliases(self):
        for entity_id, name in EntityDatabaseReader.read_names():
            if self.contains_entity(entity_id) and " " in name:
                family_name = name.split()[-1]
                self.add_alias(family_name, entity_id)

    def size_aliases(self) -> int:
        return len(self.aliases)

    def contains_alias(self, alias: str) -> bool:
        return alias in self.aliases

    def load_mapping(self):
        mapping = EntityDatabaseReader.get_mapping()
        for entity_name in mapping:
            entity_id = mapping[entity_name]
            self.wikipedia2wikidata[entity_name] = entity_id
            self.wikidata2wikipedia[entity_id] = entity_name

    def load_redirects(self):
        self.redirects = EntityDatabaseReader.get_link_redirects()

    def link2id(self, link_target: str) -> Optional[str]:
        if link_target in self.wikipedia2wikidata:
            return self.wikipedia2wikidata[link_target]
        elif link_target in self.redirects and self.redirects[link_target] in self.wikipedia2wikidata:
            return self.wikipedia2wikidata[self.redirects[link_target]]
        return None

    def _iterate_link_frequencies(self) -> Iterator[Tuple[str, str, int]]:
        link_frequencies = EntityDatabaseReader.get_link_frequencies()
        for link_text in link_frequencies:
            for link_target in link_frequencies[link_text]:
                entity_id = self.link2id(link_target)
                if entity_id is not None and self.contains_entity(entity_id):
                    frequency = link_frequencies[link_text][link_target]
                    yield link_text, entity_id, frequency

    def add_link_aliases(self):
        for link_text, entity_id, frequency in self._iterate_link_frequencies():
            self.add_alias(link_text, entity_id)

    def load_link_frequencies(self):
        for link_text, entity_id, frequency in self._iterate_link_frequencies():
            if link_text not in self.link_frequencies:
                self.link_frequencies[link_text] = {}
            if entity_id not in self.link_frequencies[link_text]:
                self.link_frequencies[link_text][entity_id] = frequency
            else:
                self.link_frequencies[link_text][entity_id] += frequency
            if entity_id not in self.entity_frequencies:
                self.entity_frequencies[entity_id] = frequency
            else:
                self.entity_frequencies[entity_id] += frequency

    def get_candidates(self, alias: str) -> Set[str]:
        if alias not in self.aliases:
            return set()
        else:
            return self.aliases[alias]

    def get_link_frequency(self, alias: str, entity_id: str) -> int:
        if alias not in self.link_frequencies or entity_id not in self.link_frequencies[alias]:
            return 0
        return self.link_frequencies[alias][entity_id]

    def get_alias_frequency(self, alias: str) -> int:
        frequency = 0
        for entity_id in self.get_candidates(alias):
            frequency += self.get_link_frequency(alias, entity_id)
        return frequency

    def get_entity_frequency(self, entity_id: str):
        return self.entity_frequencies[entity_id] if entity_id in self.entity_frequencies else 0

    def load_gender(self):
        self.entity2gender = EntityDatabaseReader.get_gender_mapping()

    def is_gender_loaded(self):
        return len(self.entity2gender) > 0

    def get_gender(self, entity_id):
        if len(self.entity2gender) == 0:
            print("Warning: Tried to access gender information but gender mapping was not loaded.")
        elif entity_id in self.entity2gender:
            return self.entity2gender[entity_id]
        else:
            return Gender.NEUTRAL

    def load_names(self):
        for entity_id, name in EntityDatabaseReader.read_names():
            if " " in name:
                given_name = name.split()[0]
                family_name = name.split()[-1]
                if len(given_name) > 1:
                    self.given_names[entity_id] = given_name
                if len(family_name) > 1:
                    self.family_names[entity_id] = family_name

    def is_given_names_loaded(self):
        return len(self.given_names) > 0

    def has_given_name(self, entity_id):
        if len(self.given_names) == 0:
            print("Warning: Tried to access first names but first name mapping was not loaded.\n"
                  "Use entity_database.load_names() to load the mapping")
        if entity_id in self.given_names:
            return True
        return False

    def get_given_name(self, entity_id):
        return self.given_names[entity_id]

    def is_family_names_loaded(self):
        return len(self.family_names) > 0

    def has_family_name(self, entity_id):
        if len(self.family_names) == 0:
            print("Warning: Tried to access family names but family name mapping was not loaded.\n"
                  "Use entity_database.load_names() to load the mapping")
        if entity_id in self.family_names:
            return True
        return False

    def get_family_name(self, entity_id):
        return self.family_names[entity_id]

    def load_types(self):
        self.entity2types = EntityDatabaseReader.get_type_mapping()

    def is_types_loaded(self):
        return len(self.entity2types) > 0

    def has_types(self, entity_id):
        return entity_id in self.entity2types

    def get_types(self, entity_id):
        return self.entity2types[entity_id]

    def load_unigram_counts(self):
        self.unigram_counts = EntityDatabaseReader.get_unigram_counts()

    def get_unigram_count(self, token: str) -> int:
        if token not in self.unigram_counts:
            return 0
        return self.unigram_counts[token]
