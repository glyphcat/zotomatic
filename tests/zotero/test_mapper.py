from __future__ import annotations

from zotomatic.zotero import mapper


class FakeZoteroClient:
    def item(self, key: str):
        return {
            "key": key,
            "data": {
                "title": "Paper",
                "creators": [{"firstName": "Ada", "lastName": "Lovelace"}],
                "date": "2022",
                "publicationTitle": "Journal",
                "DOI": "10.1/xyz",
                "url": "https://example.com",
                "abstractNote": "Abstract",
                "collections": ["C1"],
            },
            "meta": {"citationKey": "Ada2022"},
        }

    def children(self, key: str):
        return [
            {
                "data": {
                    "itemType": "annotation",
                    "pageLabel": "1",
                    "text": "Note",
                    "comment": None,
                }
            },
            {"data": {"itemType": "attachment"}},
        ]


def test_build_paper() -> None:
    client = FakeZoteroClient()
    paper = mapper.build_paper(client, "ABC", "/tmp/file.pdf")
    assert paper.key == "ABC"
    assert paper.citekey == "Ada2022"
    assert paper.title == "Paper"
    assert paper.year == "2022"
    assert paper.annotations
