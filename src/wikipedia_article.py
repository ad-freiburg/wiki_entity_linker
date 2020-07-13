from typing import List, Dict, Tuple

import json


class WikipediaArticle:
    def __init__(self,
                 id: int,
                 title: str,
                 text: str,
                 links: List[Tuple[Tuple[int, int], str]]):
        self.id = id
        self.title = title
        self.text = text
        self.links = links

    def to_dict(self) -> Dict:
        data = {"id": self.id,
                "title": self.title,
                "text": self.text,
                "links": self.links}
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return str(self)


def article_from_dict(data: Dict):
    return WikipediaArticle(id=int(data["id"]),
                            title=data["title"],
                            text=data["text"],
                            links=data["links"])


def article_from_json(dump: str):
    return article_from_dict(json.loads(dump))
