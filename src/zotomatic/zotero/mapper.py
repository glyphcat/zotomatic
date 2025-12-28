from zotomatic.zotero.formatters import authors_str, extract_year
from zotomatic.zotero.types import ZoteroAnnotation, ZoteroPaper


def build_paper(zot_client, item_key: str, pdf_path: str) -> ZoteroPaper:
    item = zot_client.item(item_key)
    data, meta = item.get("data", {}), item.get("meta", {})
    creators = data.get("creators", [])
    citekey = meta.get("citationKey")
    year = extract_year(data.get("date"))
    annotations: list[ZoteroAnnotation] = []
    try:
        children = zot_client.children(item_key)
    except Exception:  # pragma: no cover
        children = []
    for ch in children:
        if ch.get("data", {}).get("itemType") == "annotation":
            d = ch["data"]
            annotations.append(
                ZoteroAnnotation(
                    pageLabel=d.get("pageLabel"),
                    text=d.get("text") or "",
                    comment=d.get("comment"),
                )
            )
    return ZoteroPaper(
        key=item["key"],
        citekey=citekey,
        title=data.get("title") or "",
        year=year,
        authors=authors_str(creators),
        publicationTitle=data.get("publicationTitle"),
        DOI=data.get("DOI"),
        url=data.get("url"),
        abstractNote=data.get("abstractNote"),
        collections=data.get("collections") or [],
        zoteroSelectURI=f"zotero://select/library/items/{item['key']}",
        filePath=pdf_path,
        annotations=annotations,
    )
