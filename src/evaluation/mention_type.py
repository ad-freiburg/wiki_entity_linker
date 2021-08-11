from enum import Enum

from src.utils.pronoun_finder import PronounFinder


class MentionType(Enum):
    NAMED = "NAMED"
    NOMINAL = "NOMINAL"
    PRONOMINAL = "PRONOMINAL"

    def is_coreference(self):
        return self != MentionType.NAMED


def is_nominal(mention: str) -> bool:
    return (mention.startswith("the ") or mention.startswith("The ")) and mention[4:].islower()


def get_mention_type(mention: str) -> MentionType:
    if PronounFinder.is_pronoun(mention):
        return MentionType.PRONOMINAL
    elif is_nominal(mention):
        return MentionType.NOMINAL
    else:
        return MentionType.NAMED
