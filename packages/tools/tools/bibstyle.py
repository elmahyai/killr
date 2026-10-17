"""Bibliography style environments for bibentry rendering."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, MutableMapping
from typing import Any

_add_period_re = re.compile(r"([^.?!])$")


def cleanup_latex(x: Any) -> Any:
    """Return text unchanged when parseLatex is unavailable, as R does on error."""
    if x is None:
        return x
    if isinstance(x, (list, tuple)):
        return type(x)(cleanup_latex(item) for item in x)
    return x


class StyleEnv(MutableMapping[str, Any]):
    """Environment of bibliography formatting routines."""

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = dict(initial or ())

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_data":
            super().__setattr__(name, value)
        else:
            self._data[name] = value


def _nzchar(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return len(value) > 0
    if isinstance(value, (list, tuple)):
        return any(_nzchar(item) for item in value)
    return bool(value)


def make_jss() -> StyleEnv:
    """Build the default JSS bibliography style environment."""

    def collapse(strings: Any) -> str:
        if strings is None:
            return ""
        if isinstance(strings, str):
            return strings
        parts = [item for item in strings if item is not None and item != ""]
        return "\n".join(str(item) for item in parts)

    def add_period(string: str) -> str:
        if not string:
            return string
        return _add_period_re.sub(r"\1.", string)

    def sentence(*strings: Any, sep: str = ", ") -> str | None:
        parts = [s for s in strings if s is not None and s != ""]
        if not parts:
            return None
        return add_period(sep.join(str(part) for part in parts))

    def plain(pages: Any) -> str | None:
        if pages is None or pages == "" or pages == []:
            return None
        return collapse(pages)

    def plainclean(s: Any) -> str | None:
        return plain(cleanup_latex(s))

    def emph(s: Any) -> str | None:
        if s is None or s == "" or s == []:
            return None
        return f"\\emph{{{collapse(s)}}}"

    def emphclean(s: Any) -> str | None:
        return emph(cleanup_latex(s))

    def label(prefix: str | None = None, suffix: str | None = None, style: Callable[[Any], str | None] = plain):
        prefix = prefix or ""
        suffix = suffix or ""

        def wrapped(s: Any) -> str | None:
            if s is None or s == "" or s == []:
                return None
            return style(f"{prefix}{collapse(s)}{suffix}")

        return wrapped

    def labelclean(prefix: str | None = None, suffix: str | None = None, style: Callable[[Any], str | None] = plain):
        inner = label(prefix, suffix, style)

        def wrapped(s: Any) -> str | None:
            return inner(cleanup_latex(s))

        return wrapped

    fmt_address = plainclean
    fmt_book = emphclean
    fmt_btitle = emphclean
    fmt_chapter = labelclean(prefix="chapter ")
    fmt_doi = label(prefix="\\doi{", suffix="}")
    fmt_edition = labelclean(suffix=" edition")
    fmt_eprint = plain
    fmt_howpublished = plainclean
    fmt_isbn = label(prefix="ISBN ")
    fmt_issn = label(prefix="ISSN ")
    fmt_institution = plainclean
    fmt_note = plainclean
    fmt_pages = plain
    fmt_school = plainclean
    fmt_url = label(prefix="\\url{", suffix="}")

    def fmt_title(title: Any) -> str | None:
        if title is None or title == "" or title == []:
            return None
        text = collapse(title)
        text = re.sub("%", r"\\%", text)
        cleaned = cleanup_latex(text)
        return f"\\dQuote{{{add_period(collapse(cleaned))}}}"

    def fmt_year(year: Any) -> str:
        if year is None or year == "" or year == []:
            year = "????"
        return f"({collapse(year)})"

    def fmt_type(type_value: Any, default: str) -> str | None:
        if type_value is not None and _nzchar(type_value):
            return plainclean(type_value)
        return default

    def vol_num(paper: Mapping[str, Any]) -> str | None:
        volume = paper.get("volume")
        if volume is None or volume == "" or volume == []:
            return None
        result = f"\\bold{{{collapse(volume)}}}"
        number = paper.get("number")
        if number is not None and number != "" and number != []:
            result = f"{result}({collapse(number)})"
        return result

    def short_name(person: Mapping[str, Any]) -> str:
        family = person.get("family")
        given = person.get("given")
        if family is not None and family != "" and family != []:
            result = collapse(cleanup_latex(family))
            if given is not None and given != "" and given != []:
                if isinstance(given, (list, tuple)):
                    initials = "".join(str(g)[0] for g in given if g)
                else:
                    initials = str(given)[0]
                result = f"{result} {initials}"
            return result
        if given is None:
            return ""
        if isinstance(given, (list, tuple)):
            return " ".join(collapse(cleanup_latex(g)) for g in given)
        return collapse(cleanup_latex(given))

    def author_list(paper: Mapping[str, Any]) -> str | None:
        authors = paper.get("author")
        if not authors:
            return None
        if not isinstance(authors, (list, tuple)):
            authors = [authors]
        names = [short_name(author) for author in authors]
        if len(names) > 1:
            return ", ".join(names)
        return names[0] if names else None

    def editor_list(paper: Mapping[str, Any]) -> str | None:
        editors = paper.get("editor")
        if not editors:
            return None
        if not isinstance(editors, (list, tuple)):
            editors = [editors]
        names = [short_name(editor) for editor in editors]
        if len(names) > 1:
            return f"{', '.join(names)} (eds.)"
        if names:
            return f"{names[0]} (ed.)"
        return None

    def extra_info(paper: Mapping[str, Any]) -> str | None:
        def escape_doi_percent(s: str) -> str:
            return s.replace("%", "\\" * 11 + "%")

        doi = paper.get("doi")
        if isinstance(doi, str):
            doi = escape_doi_percent(doi)
        pieces = [
            fmt_doi(doi),
            fmt_note(paper.get("note")),
            fmt_eprint(paper.get("eprint")),
            fmt_url(paper.get("url")),
        ]
        result = ", ".join(p for p in pieces if p)
        return result or None

    def book_volume(book: Mapping[str, Any]) -> str | None:
        result = ""
        volume = book.get("volume")
        if volume is not None and volume != "" and volume != []:
            result = f"volume {collapse(volume)}"
        number = book.get("number")
        if number is not None and number != "" and number != []:
            result = f"{result} number {collapse(number)}".strip()
        series = book.get("series")
        if series is not None and series != "" and series != []:
            result = f"{result} series {collapse(series)}".strip()
        return result or None

    def book_publisher(book: Mapping[str, Any]) -> str | None:
        publisher = book.get("publisher")
        if publisher is None or publisher == "" or publisher == []:
            return None
        result = collapse(publisher)
        address = book.get("address")
        if address is not None and address != "" and address != []:
            result = f"{result}, {collapse(address)}"
        return result

    def proc_organization(paper: Mapping[str, Any]) -> str | None:
        organization = paper.get("organization")
        if organization is None or organization == "" or organization == []:
            return None
        result = collapse(cleanup_latex(organization))
        address = paper.get("address")
        if address is not None and address != "" and address != []:
            result = f"{result}, {collapse(cleanup_latex(address))}"
        return result

    def fmt_techreportnumber(paper: Mapping[str, Any]) -> str | None:
        number = paper.get("number")
        if number is None or number == "" or number == []:
            return None
        return f"{fmt_type(paper.get('type'), 'Technical Report')} {plainclean(number)}"

    def fmt_prefix(paper: Mapping[str, Any]) -> str | None:
        return None

    def _parts(*chunks: Any) -> list[str]:
        out: list[str] = []
        for chunk in chunks:
            if chunk is None:
                continue
            if isinstance(chunk, (list, tuple)):
                out.extend(str(item) for item in chunk if item is not None)
            else:
                out.append(str(chunk))
        return out

    def format_article(paper: Mapping[str, Any]) -> str:
        return collapse(
            _parts(
                fmt_prefix(paper),
                sentence(author_list(paper), fmt_year(paper.get("year")), sep=" "),
                fmt_title(paper.get("title")),
                sentence(fmt_book(paper.get("journal")), vol_num(paper), fmt_pages(paper.get("pages"))),
                sentence(fmt_issn(paper.get("issn")), extra_info(paper)),
            )
        )

    def format_book(book: Mapping[str, Any]) -> str:
        authors = author_list(book)
        if not authors:
            authors = editor_list(book)
        return collapse(
            _parts(
                fmt_prefix(book),
                sentence(authors, fmt_year(book.get("year")), sep=" "),
                sentence(fmt_btitle(book.get("title")), book_volume(book), fmt_edition(book.get("edition"))),
                sentence(book_publisher(book)),
                sentence(fmt_isbn(book.get("isbn")), extra_info(book)),
            )
        )

    def format_inbook(paper: Mapping[str, Any]) -> str:
        authors = author_list(paper)
        editors = editor_list(paper)
        if not authors:
            authors = editors
            editors = None
        return collapse(
            _parts(
                fmt_prefix(paper),
                sentence(authors, fmt_year(paper.get("year")), sep=" "),
                fmt_title(paper.get("title")),
                "In "
                + (sentence(
                    editors,
                    fmt_btitle(paper.get("booktitle")),
                    book_volume(paper),
                    fmt_chapter(paper.get("chapter")),
                    fmt_edition(paper.get("edition")),
                    fmt_pages(paper.get("pages")),
                )
                or ""),
                sentence(book_publisher(paper)),
                sentence(fmt_isbn(paper.get("isbn")), extra_info(paper)),
            )
        )

    def format_incollection(paper: Mapping[str, Any]) -> str:
        return collapse(
            _parts(
                fmt_prefix(paper),
                sentence(author_list(paper), fmt_year(paper.get("year")), sep=" "),
                fmt_title(paper.get("title")),
                "In "
                + (sentence(
                    editor_list(paper),
                    fmt_btitle(paper.get("booktitle")),
                    book_volume(paper),
                    fmt_edition(paper.get("edition")),
                    fmt_pages(paper.get("pages")),
                )
                or ""),
                sentence(book_publisher(paper)),
                sentence(fmt_isbn(paper.get("isbn")), extra_info(paper)),
            )
        )

    def format_in_proceedings(paper: Mapping[str, Any]) -> str:
        return collapse(
            _parts(
                fmt_prefix(paper),
                sentence(author_list(paper), fmt_year(paper.get("year")), sep=" "),
                fmt_title(paper.get("title")),
                "In "
                + (sentence(
                    editor_list(paper),
                    fmt_btitle(paper.get("booktitle")),
                    book_volume(paper),
                    fmt_edition(paper.get("edition")),
                    fmt_pages(paper.get("pages")),
                )
                or ""),
                sentence(proc_organization(paper)),
                sentence(fmt_isbn(paper.get("isbn")), extra_info(paper)),
            )
        )

    def format_manual(paper: Mapping[str, Any]) -> str:
        return collapse(
            _parts(
                fmt_prefix(paper),
                sentence(author_list(paper), fmt_year(paper.get("year")), sep=" "),
                sentence(fmt_btitle(paper.get("title")), book_volume(paper), fmt_edition(paper.get("edition"))),
                sentence(proc_organization(paper)),
                sentence(fmt_isbn(paper.get("isbn")), extra_info(paper)),
            )
        )

    def format_mastersthesis(paper: Mapping[str, Any]) -> str:
        return collapse(
            _parts(
                fmt_prefix(paper),
                sentence(author_list(paper), fmt_year(paper.get("year")), sep=" "),
                sentence(fmt_btitle(paper.get("title"))),
                sentence(fmt_type(paper.get("type"), "Master's thesis"), fmt_school(paper.get("school")), fmt_address(paper.get("address"))),
                sentence(extra_info(paper)),
            )
        )

    def format_phdthesis(paper: Mapping[str, Any]) -> str:
        return collapse(
            _parts(
                fmt_prefix(paper),
                sentence(author_list(paper), fmt_year(paper.get("year")), sep=" "),
                sentence(fmt_btitle(paper.get("title"))),
                sentence(fmt_type(paper.get("type"), "Ph.D. thesis"), fmt_school(paper.get("school")), fmt_address(paper.get("address"))),
                sentence(extra_info(paper)),
            )
        )

    def format_misc(paper: Mapping[str, Any]) -> str:
        return collapse(
            _parts(
                fmt_prefix(paper),
                sentence(author_list(paper), fmt_year(paper.get("year")), sep=" "),
                fmt_title(paper.get("title")),
                sentence(fmt_howpublished(paper.get("howpublished"))),
                sentence(extra_info(paper)),
            )
        )

    def format_proceedings(book: Mapping[str, Any]) -> str:
        editor = editor_list(book)
        if editor is None:
            editor = "Anonymous (ed.)"
        return collapse(
            _parts(
                fmt_prefix(book),
                sentence(editor, fmt_year(book.get("year")), sep=" "),
                sentence(fmt_btitle(book.get("title")), book_volume(book)),
                sentence(proc_organization(book)),
                sentence(fmt_isbn(book.get("isbn")), fmt_issn(book.get("issn")), extra_info(book)),
            )
        )

    def format_techreport(paper: Mapping[str, Any]) -> str:
        return collapse(
            _parts(
                fmt_prefix(paper),
                sentence(author_list(paper), fmt_year(paper.get("year")), sep=" "),
                fmt_title(paper.get("title")),
                sentence(fmt_techreportnumber(paper), fmt_institution(paper.get("institution")), fmt_address(paper.get("address"))),
                sentence(extra_info(paper)),
            )
        )

    def format_unpublished(paper: Mapping[str, Any]) -> str:
        return collapse(
            _parts(
                fmt_prefix(paper),
                sentence(author_list(paper), fmt_year(paper.get("year")), sep=" "),
                fmt_title(paper.get("title")),
                sentence(extra_info(paper)),
            )
        )

    def sort_keys(bib: list[Any]) -> list[str]:
        result: list[str] = []
        for entry in bib:
            authors = author_list(entry) if isinstance(entry, Mapping) else None
            if not authors:
                authors = editor_list(entry) if isinstance(entry, Mapping) else None
            if not authors:
                authors = ""
            result.append(authors)
        return result

    def cite(key: Any, bib: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("cite requires utils.citeNatbib")

    env = StyleEnv(
        {
            "addPeriod": add_period,
            "authorList": author_list,
            "bookPublisher": book_publisher,
            "bookVolume": book_volume,
            "cite": cite,
            "collapse": collapse,
            "editorList": editor_list,
            "emph": emph,
            "emphclean": emphclean,
            "extraInfo": extra_info,
            "fmtAddress": fmt_address,
            "fmtBook": fmt_book,
            "fmtBtitle": fmt_btitle,
            "fmtChapter": fmt_chapter,
            "fmtDOI": fmt_doi,
            "fmtEdition": fmt_edition,
            "fmtEprint": fmt_eprint,
            "fmtHowpublished": fmt_howpublished,
            "fmtInstitution": fmt_institution,
            "fmtISBN": fmt_isbn,
            "fmtISSN": fmt_issn,
            "fmtNote": fmt_note,
            "fmtPages": fmt_pages,
            "fmtPrefix": fmt_prefix,
            "fmtSchool": fmt_school,
            "fmtTechreportnumber": fmt_techreportnumber,
            "fmtTitle": fmt_title,
            "fmtType": fmt_type,
            "fmtUrl": fmt_url,
            "fmtYear": fmt_year,
            "formatArticle": format_article,
            "formatBook": format_book,
            "formatInbook": format_inbook,
            "formatIncollection": format_incollection,
            "formatInProceedings": format_in_proceedings,
            "formatManual": format_manual,
            "formatMastersthesis": format_mastersthesis,
            "formatMisc": format_misc,
            "formatPhdthesis": format_phdthesis,
            "formatProceedings": format_proceedings,
            "formatTechreport": format_techreport,
            "formatUnpublished": format_unpublished,
            "label": label,
            "labelclean": labelclean,
            "plain": plain,
            "plainclean": plainclean,
            "procOrganization": proc_organization,
            "sentence": sentence,
            "shortName": short_name,
            "sortKeys": sort_keys,
            "volNum": vol_num,
        }
    )
    return env


_styles: dict[str, StyleEnv] = {"JSS": make_jss()}
_default_style = "JSS"


def bibstyle(
    style: str | None = None,
    envir: StyleEnv | None = None,
    *,
    _init: bool = False,
    _default: bool = True,
    **newfns: Callable[..., Any],
) -> StyleEnv | None:
    """Select, define, or modify a bibliography style environment."""
    global _default_style
    if style is None:
        if envir is not None or newfns or _init:
            raise ValueError("Changes require specified 'style'")
        style = _default_style
    else:
        if envir is not None:
            if _init:
                raise ValueError("envir and _init cannot both be set")
            _styles[style] = envir
        if _init:
            _styles[style] = make_jss()
        if newfns and style == "JSS":
            raise ValueError("The default JSS style may not be modified.")
        if newfns:
            target = _styles[style]
            for name, fn in newfns.items():
                target[name] = fn
        if _default:
            _default_style = style
    return _styles.get(style)


def get_bibstyle(all_styles: bool = False) -> str | list[str]:
    """Return the default style name, or every registered name."""
    if all_styles:
        return list(_styles.keys())
    return _default_style
