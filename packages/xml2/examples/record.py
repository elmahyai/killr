"""Compare xml2 with the installed R package and write the translation records."""

from __future__ import annotations

import json
import statistics
import subprocess
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = Path("/tmp/cran-xml2/xml2/NAMESPACE")

# name, python path, done, case, R value, Python value, R example, Python example
CASES = [
    ("read_xml", "xml2.read_xml", "Reads a string, file, or URL with libxml2. A string that contains < is markup.", "the document <foo><bar /></foo>",
     'as.character(read_xml("<foo><bar /></foo>"))',
     'as_character(read_xml("<foo><bar /></foo>"))',
     'paste(capture.output(read_xml("<foo><bar /></foo>")), collapse = "\\n")',
     'str(read_xml("<foo><bar /></foo>"))'),
    ("read_html", "xml2.read_html", "Reads HTML with libxml2 recovery. The default encoding is UTF-8.", "an unclosed title",
     'as.character(read_html("<html><title>Hi"))',
     'as_character(read_html("<html><title>Hi"))',
     'paste(capture.output(read_html("<html><title>Hi<title></html>")), collapse = "\\n")',
     'str(read_html("<html><title>Hi<title></html>"))'),
    ("xml_name", "xml2.xml_name", "The tag name. A namespace map qualifies it as prefix:name.", "the children of a mixed element",
     'xml_name(xml_children(read_xml("<bar><baz>1</baz>abc<foo /></bar>")))',
     'xml_name(xml_children(read_xml("<bar><baz>1</baz>abc<foo /></bar>")))',
     'flat(xml_name(read_xml("<bar>123</bar>")))',
     'print_value(xml_name(read_xml("<bar>123</bar>")))'),
    ("xml_text", "xml2.xml_text", "Concatenated descendant text. trim drops leading and trailing spaces, including a non-breaking space.", "text of a paragraph and its child",
     'c(xml_text(read_xml("<p>This is some text. This is <b>bold!</b></p>")), xml_text(read_xml("<p>   Some text    </p>"), trim = TRUE))',
     '[xml_text(read_xml("<p>This is some text. This is <b>bold!</b></p>")), xml_text(read_xml("<p>   Some text    </p>"), trim=True)]',
     'flat(xml_text(read_xml("<p>This is some text. This is <b>bold!</b></p>")))',
     'print_value(xml_text(read_xml("<p>This is some text. This is <b>bold!</b></p>")))'),
    ("xml_double", "xml2.xml_double", "xml_text parsed with R's as.numeric. A non-number is missing.", "1.5 and a word",
     'xml_double(xml_find_all(read_xml("<a><b>1.5</b><b>x</b></a>"), "//b"))',
     'xml_double(xml_find_all(read_xml("<a><b>1.5</b><b>x</b></a>"), "//b"))',
     'flat(xml_double(read_xml("<a>1.5</a>")))',
     'print_value(xml_double(read_xml("<a>1.5</a>")))'),
    ("xml_integer", "xml2.xml_integer", "xml_text parsed with R's as.integer. A decimal word is missing.", "the x attributes 1 and 2",
     'xml_integer(xml_find_all(read_xml("<plot><point x=\'1\' y=\'2\' /><point x=\'2\' y=\'1\' /></plot>"), "//@x"))',
     'xml_integer(xml_find_all(read_xml("<plot><point x=\'1\' y=\'2\' /><point x=\'2\' y=\'1\' /></plot>"), "//@x"))',
     'flat(xml_integer(xml_find_all(read_xml("<plot><point x=\'1\' /><point x=\'2\' /></plot>"), "//@x")))',
     'print_value(xml_integer(xml_find_all(read_xml("<plot><point x=\'1\' /><point x=\'2\' /></plot>"), "//@x")))'),
    ("xml_set_text", "xml2.xml_set_text", "Replaces the first text node, or appends one when the element has none.", "hi becomes yo",
     'as.character(xml_set_text(read_xml("<a>hi</a>"), "yo"))',
     'as_character(xml_set_text(read_xml("<a>hi</a>"), "yo"))',
     'paste(capture.output(xml_set_text(read_xml("<a>hi</a>"), "yo")), collapse = "\\n")',
     'str(xml_set_text(read_xml("<a>hi</a>"), "yo"))'),
    ("xml_text<-", "xml2.xml_text_assign", "The replacement form of xml_set_text.", "hi becomes yo",
     'x <- read_xml("<a>hi</a>"); xml_text(x) <- "yo"; as.character(x)',
     'x = read_xml("<a>hi</a>"); xml_text_assign(x, "yo"); as_character(x)',
     'x <- read_xml("<a>hi</a>"); xml_text(x) <- "yo"; paste(capture.output(x), collapse = "\\n")',
     'x = read_xml("<a>hi</a>"); xml_text_assign(x, "yo"); str(x)'),
    ("xml_type", "xml2.xml_type", "libxml2's node type: element, text, cdata, and the rest of that table.", "text, element, text, and cdata",
     'xml_type(xml_contents(read_xml("<foo> a <b /> <![CDATA[ blah]]></foo>")))',
     'xml_type(xml_contents(read_xml("<foo> a <b /> <![CDATA[ blah]]></foo>")))',
     'flat(xml_type(read_xml("<foo> a <b /> <![CDATA[ blah]]></foo>")))',
     'print_value(xml_type(read_xml("<foo> a <b /> <![CDATA[ blah]]></foo>")))'),
    ("xml_children", "xml2.xml_children", "Element children, de-duplicated.", "bar and baz",
     'xml_name(xml_children(read_xml("<foo> <bar><boo /></bar> <baz/> </foo>")))',
     'xml_name(xml_children(read_xml("<foo> <bar><boo /></bar> <baz/> </foo>")))',
     'paste(capture.output(xml_children(read_xml("<foo> <bar><boo /></bar> <baz/> </foo>"))), collapse = "\\n")',
     'str(xml_children(read_xml("<foo> <bar><boo /></bar> <baz/> </foo>")))'),
    ("xml_contents", "xml2.xml_contents", "Every child, including text and cdata.", "the types under foo",
     'xml_type(xml_contents(read_xml("<foo> a <b/> c <d>e</d> f</foo>")))',
     'xml_type(xml_contents(read_xml("<foo> a <b/> c <d>e</d> f</foo>")))',
     'paste(capture.output(xml_contents(read_xml("<foo> a <b/> c <d>e</d> f</foo>"))), collapse = "\\n")',
     'str(xml_contents(read_xml("<foo> a <b/> c <d>e</d> f</foo>")))'),
    ("xml_child", "xml2.xml_child", "One child by position, counting from 1, or by name.", "the second element child",
     'xml_name(xml_child(read_xml("<foo> a <b/> c <d>e</d> f</foo>"), 2))',
     'xml_name(xml_child(read_xml("<foo> a <b/> c <d>e</d> f</foo>"), 2))',
     'paste(capture.output(xml_child(read_xml("<foo> <bar><boo /></bar> <baz/> </foo>"))), collapse = "\\n")',
     'str(xml_child(read_xml("<foo> <bar><boo /></bar> <baz/> </foo>")))'),
    ("xml_siblings", "xml2.xml_siblings", "Element siblings of a node, not the node itself.", "baz beside bar",
     'paste(xml_name(xml_siblings(xml_children(read_xml("<foo> <bar><boo /></bar> <baz/> </foo>"))[[1]])), collapse = "|")',
     '"|".join(xml_name(xml_siblings(xml_children(read_xml("<foo> <bar><boo /></bar> <baz/> </foo>"))[0])))',
     'paste(capture.output(xml_siblings(xml_children(read_xml("<foo> <bar><boo /></bar> <baz/> </foo>"))[[1]])), collapse = "\\n")',
     'str(xml_siblings(xml_children(read_xml("<foo> <bar><boo /></bar> <baz/> </foo>"))[0]))'),
    ("xml_parent", "xml2.xml_parent", "The parent node.", "foo, the parent of bar",
     'xml_name(xml_parent(xml_child(read_xml("<foo><bar/></foo>"))))',
     'xml_name(xml_parent(xml_child(read_xml("<foo><bar/></foo>"))))',
     'paste(capture.output(xml_parent(xml_child(read_xml("<foo><bar/></foo>")))), collapse = "\\n")',
     'str(xml_parent(xml_child(read_xml("<foo><bar/></foo>"))))'),
    ("xml_parents", "xml2.xml_parents", "Element ancestors, nearest first.", "the parent name of baz",
     'xml_name(xml_parents(xml_find_first(read_xml("<foo><bar><baz/></bar></foo>"), ".//baz")))',
     'xml_name(xml_parents(xml_find_first(read_xml("<foo><bar><baz/></bar></foo>"), ".//baz")))',
     'paste(xml_name(xml_parents(xml_find_first(read_xml("<foo><bar><baz/></bar></foo>"), ".//baz"))), collapse = "\\n")',
     'print_value("\\n".join(xml_name(xml_parents(xml_find_first(read_xml("<foo><bar><baz/></bar></foo>"), ".//baz")))))'),
    ("xml_length", "xml2.xml_length", "How many children. only_elements is true unless you ask for every node.", "two elements and five contents",
     'c(xml_length(read_xml("<foo> a <b/> c <d>e</d> f</foo>")), xml_length(read_xml("<foo> a <b/> c <d>e</d> f</foo>"), only_elements = FALSE))',
     '[xml_length(read_xml("<foo> a <b/> c <d>e</d> f</foo>")), xml_length(read_xml("<foo> a <b/> c <d>e</d> f</foo>"), only_elements=False)]',
     'flat(xml_length(read_xml("<foo> a <b/> c <d>e</d> f</foo>")))',
     'print_value(xml_length(read_xml("<foo> a <b/> c <d>e</d> f</foo>")))'),
    ("xml_root", "xml2.xml_root", "The document element.", "foo",
     'xml_name(xml_root(xml_find_first(read_xml("<foo><bar/></foo>"), ".//bar")))',
     'xml_name(xml_root(xml_find_first(read_xml("<foo><bar/></foo>"), ".//bar")))',
     'paste(capture.output(xml_root(read_xml("<foo><bar/></foo>"))), collapse = "\\n")',
     'str(xml_root(read_xml("<foo><bar/></foo>")))'),
    ("xml_attr", "xml2.xml_attr", "One attribute. A missing attribute is NA. With a namespace map, an unqualified name is the attribute in no namespace.", "id of the root, and a missing apple",
     'c(xml_attr(read_xml("<root id=\'1\'><child id=\'a\' /></root>"), "id"), xml_attr(read_xml("<root id=\'1\'/>"), "apple"))',
     '[xml_attr(read_xml("<root id=\'1\'><child id=\'a\' /></root>"), "id"), xml_attr(read_xml("<root id=\'1\'/>"), "apple")]',
     'flat(xml_attr(read_xml("<root id=\'1\'><child id=\'a\' /></root>"), "id"))',
     'print_value(xml_attr(read_xml("<root id=\'1\'><child id=\'a\' /></root>"), "id"))'),
    ("xml_has_attr", "xml2.xml_has_attr", "True when xml_attr would not be missing. An empty value still counts.", "which children have d",
     'xml_has_attr(xml_children(read_xml("<root id=\'1\'><child id=\'a\' /><child id=\'b\' d=\'b\'/></root>")), "d")',
     'xml_has_attr(xml_children(read_xml("<root id=\'1\'><child id=\'a\' /><child id=\'b\' d=\'b\'/></root>")), "d")',
     'flat(xml_has_attr(xml_children(read_xml("<root><child id=\'a\' /><child id=\'b\' d=\'b\'/></root>")), "d"))',
     'print_value(xml_has_attr(xml_children(read_xml("<root><child id=\'a\' /><child id=\'b\' d=\'b\'/></root>")), "d"))'),
    ("xml_attrs", "xml2.xml_attrs", "Every attribute, then every namespace declaration. Duplicate local names stay in order.", "id and d on the second child",
     '{a <- xml_attrs(xml_children(read_xml("<root><child id=\'a\' /><child id=\'b\' d=\'b\'/></root>"))[[2]]); paste(names(a), a, sep = "=", collapse = "|")}',
     '"|".join(f"{k}={v}" for k, v in xml_attrs(xml_children(read_xml("<root><child id=\'a\' /><child id=\'b\' d=\'b\'/></root>"))[1]).pairs)',
     '{a <- xml_attrs(read_xml("<root id=\'1\'/>")); paste(names(a), a, sep = "=")}',
     'print_value("|".join(f"{k}={v}" for k, v in xml_attrs(read_xml("<root id=\'1\'/>")).pairs))'),
    ("xml_set_attr", "xml2.xml_set_attr", "Sets one attribute. None removes it.", "id becomes two",
     'as.character(xml_set_attr(read_xml("<a id=\'1\'/>"), "id", "two"))',
     'xml_set_attr(read_xml("<a id=\'1\'/>"), "id", "two")',
     'x <- read_xml("<a id=\'1\'/>"); xml_set_attr(x, "id", "two"); paste(capture.output(x), collapse = "\\n")',
     'x = read_xml("<a id=\'1\'/>"); xml_set_attr(x, "id", "two"); str(x)'),
    ("xml_attr<-", "xml2.xml_attr_assign", "The replacement form of xml_set_attr.", "id becomes one",
     'x <- read_xml("<a id=\'0\'/>"); xml_attr(x, "id") <- "one"; xml_attr(x, "id")',
     'x = read_xml("<a id=\'0\'/>"); xml_attr_assign(x, "id", "one"); xml_attr(x, "id")',
     'x <- read_xml("<a id=\'0\'/>"); xml_attr(x, "id") <- "one"; paste(capture.output(x), collapse = "\\n")',
     'x = read_xml("<a id=\'0\'/>"); xml_attr_assign(x, "id", "one"); str(x)'),
    ("xml_set_attrs", "xml2.xml_set_attrs", "Replaces the whole attribute set. Names that disappear are removed.", "only b remains",
     'as.character({x <- read_xml("<a id=\'1\'/>"); xml_set_attrs(x, c(b = "two")); x})',
     'x = read_xml("<a id=\'1\'/>"); xml_set_attrs(x, {"b": "two"}); as_character(x)',
     'x <- read_xml("<a id=\'1\'/>"); xml_attrs(x) <- c(b = "two"); paste(capture.output(x), collapse = "\\n")',
     'x = read_xml("<a id=\'1\'/>"); xml_set_attrs(x, {"b": "two"}); str(x)'),
    ("xml_attrs<-", "xml2.xml_attrs_assign", "The replacement form of xml_set_attrs.", "only b remains",
     'x <- read_xml("<a id=\'1\'/>"); xml_attrs(x) <- c(b = "two"); as.character(x)',
     'x = read_xml("<a id=\'1\'/>"); xml_attrs_assign(x, {"b": "two"}); as_character(x)',
     'x <- read_xml("<a id=\'1\'/>"); xml_attrs(x) <- c(b = "two"); paste(capture.output(x), collapse = "\\n")',
     'x = read_xml("<a id=\'1\'/>"); xml_attrs_assign(x, {"b": "two"}); str(x)'),
    ("xml_set_name", "xml2.xml_set_name", "Renames an element. The namespace map is ignored.", "bar becomes bar2",
     'as.character(xml_set_name(read_xml("<bar/>"), "bar2"))',
     'as_character(xml_set_name(read_xml("<bar/>"), "bar2"))',
     'paste(capture.output(xml_set_name(read_xml("<bar/>"), "bar2")), collapse = "\\n")',
     'str(xml_set_name(read_xml("<bar/>"), "bar2"))'),
    ("xml_name<-", "xml2.xml_name_assign", "The replacement form of xml_set_name.", "bar becomes baz",
     'x <- read_xml("<bar/>"); xml_name(x) <- "baz"; xml_name(x)',
     'x = read_xml("<bar/>"); xml_name_assign(x, "baz"); xml_name(x)',
     'x <- read_xml("<bar/>"); xml_name(x) <- "baz"; paste(capture.output(x), collapse = "\\n")',
     'x = read_xml("<bar/>"); xml_name_assign(x, "baz"); str(x)'),
    ("xml_path", "xml2.xml_path", "The XPath of a node, from libxml2.", "the two baz nodes",
     'xml_path(xml_find_all(read_xml("<foo><bar><baz/></bar><baz/></foo>"), ".//baz"))',
     'xml_path(xml_find_all(read_xml("<foo><bar><baz/></bar><baz/></foo>"), ".//baz"))',
     'flat(xml_path(xml_find_all(read_xml("<foo><bar><baz/></bar><baz/></foo>"), ".//baz")))',
     'print_value(xml_path(xml_find_all(read_xml("<foo><bar><baz/></bar><baz/></foo>"), ".//baz")))'),
    ("xml_find_all", "xml2.xml_find_all", "Every node an XPath returns, de-duplicated. flatten=False keeps one nodeset per input node.", "paths of baz under foo",
     'xml_path(xml_find_all(read_xml("<foo><bar><baz/></bar><baz/></foo>"), ".//baz"))',
     'xml_path(xml_find_all(read_xml("<foo><bar><baz/></bar><baz/></foo>"), ".//baz"))',
     'paste(capture.output(xml_find_all(read_xml("<foo><bar><baz/></bar><baz/></foo>"), ".//baz")), collapse = "\\n")',
     'str(xml_find_all(read_xml("<foo><bar><baz/></bar><baz/></foo>"), ".//baz"))'),
    ("xml_find_first", "xml2.xml_find_first", "The first match for each node. No match is a missing node.", "text of the first b in each paragraph",
     'xml_text(xml_find_first(xml_find_all(read_xml("<body><p>Some <b>text</b>.</p><p>No bold here!</p></body>"), ".//p"), ".//b"))',
     'xml_text(xml_find_first(xml_find_all(read_xml("<body><p>Some <b>text</b>.</p><p>No bold here!</p></body>"), ".//p"), ".//b"))',
     'paste(capture.output(xml_find_first(read_xml("<foo><bar><baz/></bar><baz/></foo>"), ".//baz")), collapse = "\\n")',
     'str(xml_find_first(read_xml("<foo><bar><baz/></bar><baz/></foo>"), ".//baz"))'),
    ("xml_find_one", "xml2.xml_find_one", "The old name of xml_find_first.", "the first baz",
     'xml_name(suppressWarnings(xml_find_one(read_xml("<foo><baz/></foo>"), ".//baz")))',
     'import warnings; warnings.filterwarnings("ignore", category=DeprecationWarning); xml_name(xml_find_one(read_xml("<foo><baz/></foo>"), ".//baz"))',
     'paste(capture.output(suppressWarnings(xml_find_one(read_xml("<foo><baz/></foo>"), ".//baz"))), collapse = "\\n")',
     'import warnings; warnings.filterwarnings("ignore", category=DeprecationWarning); str(xml_find_one(read_xml("<foo><baz/></foo>"), ".//baz"))'),
    ("xml_find_num", "xml2.xml_find_num", "An XPath number. NaN is returned as NaN.", "count of b",
     'xml_find_num(read_xml("<a><b>1</b><b>2</b></a>"), "count(//b)")',
     'xml_find_num(read_xml("<a><b>1</b><b>2</b></a>"), "count(//b)")',
     'flat(xml_find_num(read_xml("<a><b>1</b><b>2</b></a>"), "count(//b)"))',
     'print_value(xml_find_num(read_xml("<a><b>1</b><b>2</b></a>"), "count(//b)"))'),
    ("xml_find_int", "xml2.xml_find_int", "An XPath number that is a whole number, as an integer.", "count of b",
     'xml_find_int(read_xml("<a><b>1</b><b>2</b></a>"), "count(//b)")',
     'xml_find_int(read_xml("<a><b>1</b><b>2</b></a>"), "count(//b)")',
     'flat(xml_find_int(read_xml("<a><b>1</b><b>2</b></a>"), "count(//b)"))',
     'print_value(xml_find_int(read_xml("<a><b>1</b><b>2</b></a>"), "count(//b)"))'),
    ("xml_find_chr", "xml2.xml_find_chr", "An XPath string.", "the text of b",
     'xml_find_chr(read_xml("<a><b>hi</b></a>"), "string(//b)")',
     'xml_find_chr(read_xml("<a><b>hi</b></a>"), "string(//b)")',
     'flat(xml_find_chr(read_xml("<a><b>hi</b></a>"), "string(//b)"))',
     'print_value(xml_find_chr(read_xml("<a><b>hi</b></a>"), "string(//b)"))'),
    ("xml_find_lgl", "xml2.xml_find_lgl", "An XPath boolean.", "whether there is one b",
     'xml_find_lgl(read_xml("<a><b>hi</b></a>"), "count(//b) = 1")',
     'xml_find_lgl(read_xml("<a><b>hi</b></a>"), "count(//b) = 1")',
     'flat(xml_find_lgl(read_xml("<a><b>hi</b></a>"), "count(//b) = 1"))',
     'print_value(xml_find_lgl(read_xml("<a><b>hi</b></a>"), "count(//b) = 1"))'),
    ("xml_ns", "xml2.xml_ns", "Prefix to URL, first seen. Default namespaces are d1, d2, in document order.", "two default namespaces",
     '{ns <- xml_ns(read_xml("<root><doc1 xmlns=\\"http://foo.com\\"><baz /></doc1><doc2 xmlns=\\"http://bar.com\\"><baz /></doc2></root>")); paste(names(ns), ns, sep = "=", collapse = "|")}',
     '"|".join(f"{k}={v}" for k, v in xml_ns(read_xml(\'<root><doc1 xmlns="http://foo.com"><baz /></doc1><doc2 xmlns="http://bar.com"><baz /></doc2></root>\')).items())',
     'paste(capture.output(xml_ns(read_xml("<root><doc1 xmlns=\\"http://foo.com\\"><baz /></doc1><doc2 xmlns=\\"http://bar.com\\"><baz /></doc2></root>"))), collapse = "\\n")',
     'str(xml_ns(read_xml(\'<root><doc1 xmlns="http://foo.com"><baz /></doc1><doc2 xmlns="http://bar.com"><baz /></doc2></root>\')))'),
    ("xml_ns_rename", "xml2.xml_ns_rename", "Renames prefixes in place. The URL stays with the old position.", "d1 and d2 become foo and bar",
     '{x <- read_xml("<root><doc1 xmlns=\\"http://foo.com\\"><baz /></doc1><doc2 xmlns=\\"http://bar.com\\"><baz /></doc2></root>"); ns <- xml_ns_rename(xml_ns(x), d1 = "foo", d2 = "bar"); paste(names(ns), ns, sep = "=", collapse = "|")}',
     '"|".join(f"{k}={v}" for k, v in xml_ns_rename(xml_ns(read_xml(\'<root><doc1 xmlns="http://foo.com"><baz /></doc1><doc2 xmlns="http://bar.com"><baz /></doc2></root>\')), d1="foo", d2="bar").items())',
     'x <- read_xml("<root><doc1 xmlns=\\"http://foo.com\\"><baz /></doc1><doc2 xmlns=\\"http://bar.com\\"><baz /></doc2></root>"); paste(capture.output(xml_ns_rename(xml_ns(x), d1 = "foo", d2 = "bar")), collapse = "\\n")',
     'str(xml_ns_rename(xml_ns(read_xml(\'<root><doc1 xmlns="http://foo.com"><baz /></doc1><doc2 xmlns="http://bar.com"><baz /></doc2></root>\')), d1="foo", d2="bar"))'),
    ("xml_ns_strip", "xml2.xml_ns_strip", "Removes default namespace declarations so an unprefixed name matches.", "both baz nodes",
     '{x <- read_xml("<foo xmlns=\\"http://foo.com\\"><baz/><bar xmlns=\\"http://bar.com\\"><baz/></bar></foo>"); xml_ns_strip(x); length(xml_find_all(x, "//baz"))}',
     'x = read_xml(\'<foo xmlns="http://foo.com"><baz/><bar xmlns="http://bar.com"><baz/></bar></foo>\'); xml_ns_strip(x); len(xml_find_all(x, "//baz"))',
     'x <- read_xml("<foo xmlns=\\"http://foo.com\\"><baz/><bar xmlns=\\"http://bar.com\\"><baz/></bar></foo>"); xml_ns_strip(x); paste(capture.output(x), collapse = "\\n")',
     'x = read_xml(\'<foo xmlns="http://foo.com"><baz/><bar xmlns="http://bar.com"><baz/></bar></foo>\'); xml_ns_strip(x); str(x)'),
    ("xml_set_namespace", "xml2.xml_set_namespace", "Points a node at a namespace that an ancestor already declared.", "a becomes f:a",
     '{x <- read_xml("<root xmlns:f=\\"http://foo.com\\"><a/></root>"); xml_set_namespace(xml_child(x), prefix = "f"); as.character(x)}',
     'x = read_xml(\'<root xmlns:f="http://foo.com"><a/></root>\'); xml_set_namespace(xml_child(x), prefix="f"); as_character(x)',
     'x <- read_xml("<root xmlns:f=\\"http://foo.com\\"><a/></root>"); xml_set_namespace(xml_child(x), prefix = "f"); paste(capture.output(x), collapse = "\\n")',
     'x = read_xml(\'<root xmlns:f="http://foo.com"><a/></root>\'); xml_set_namespace(xml_child(x), prefix="f"); str(x)'),
    ("xml_add_child", "xml2.xml_add_child", "Appends a child. .where is the child after which to insert, counting from 1. 0 inserts first.", "a root with a cdata child",
     '{x <- xml_new_root("root"); xml_add_child(x, xml_cdata("<d/>")); as.character(x)}',
     'x = xml_new_root("root"); xml_add_child(x, xml_cdata("<d/>")); as_character(x)',
     'x <- xml_new_root("root"); xml_add_child(x, xml_cdata("<d/>")); paste(capture.output(x), collapse = "\\n")',
     'x = xml_new_root("root"); xml_add_child(x, xml_cdata("<d/>")); str(x)'),
    ("xml_add_sibling", "xml2.xml_add_sibling", "Inserts a sibling after the node, or before it.", "baz after bar",
     '{x <- read_xml("<foo><bar/></foo>"); xml_add_sibling(xml_child(x), "baz"); as.character(x)}',
     'x = read_xml("<foo><bar/></foo>"); xml_add_sibling(xml_child(x), "baz"); as_character(x)',
     'x <- read_xml("<foo><bar/></foo>"); xml_add_sibling(xml_child(x), "baz"); paste(capture.output(x), collapse = "\\n")',
     'x = read_xml("<foo><bar/></foo>"); xml_add_sibling(xml_child(x), "baz"); str(x)'),
    ("xml_add_parent", "xml2.xml_add_parent", "Wraps a node in a new parent.", "bar inside wrap",
     '{x <- read_xml("<foo><bar/></foo>"); xml_add_parent(xml_child(x), "wrap"); as.character(x)}',
     'x = read_xml("<foo><bar/></foo>"); xml_add_parent(xml_child(x), "wrap"); as_character(x)',
     'x <- read_xml("<foo><bar/></foo>"); xml_add_parent(xml_child(x), "wrap"); paste(capture.output(x), collapse = "\\n")',
     'x = read_xml("<foo><bar/></foo>"); xml_add_parent(xml_child(x), "wrap"); str(x)'),
    ("xml_replace", "xml2.xml_replace", "Replaces a node and returns the new one.", "bar becomes baz",
     '{x <- read_xml("<foo><bar/></foo>"); xml_replace(xml_child(x), "baz"); as.character(x)}',
     'x = read_xml("<foo><bar/></foo>"); xml_replace(xml_child(x), "baz"); as_character(x)',
     'x <- read_xml("<foo><bar/></foo>"); xml_replace(xml_child(x), "baz"); paste(capture.output(x), collapse = "\\n")',
     'x = read_xml("<foo><bar/></foo>"); xml_replace(xml_child(x), "baz"); str(x)'),
    ("xml_remove", "xml2.xml_remove", "Unlinks a node. free=True also frees it.", "bar is gone",
     '{x <- read_xml("<foo><bar/><baz/></foo>"); xml_remove(xml_child(x)); as.character(x)}',
     'x = read_xml("<foo><bar/><baz/></foo>"); xml_remove(xml_child(x)); as_character(x)',
     'x <- read_xml("<foo><bar/><baz/></foo>"); xml_remove(xml_child(x)); paste(capture.output(x), collapse = "\\n")',
     'x = read_xml("<foo><bar/><baz/></foo>"); xml_remove(xml_child(x)); str(x)'),
    ("xml_cdata", "xml2.xml_cdata", "Marks text that xml_add_child inserts as CDATA.", "a cdata child",
     '{x <- xml_new_root("root"); xml_add_child(x, xml_cdata("<d/>")); as.character(x)}',
     'x = xml_new_root("root"); xml_add_child(x, xml_cdata("<d/>")); as_character(x)',
     'x <- xml_new_root("root"); xml_add_child(x, xml_cdata("<d/>")); paste(capture.output(x), collapse = "\\n")',
     'x = xml_new_root("root"); xml_add_child(x, xml_cdata("<d/>")); str(x)'),
    ("xml_comment", "xml2.xml_comment", "Marks text that xml_add_child inserts as a comment.", "a comment under root",
     '{x <- xml_new_document(); r <- xml_add_child(x, "root"); xml_add_child(r, xml_comment("Hello!")); as.character(x)}',
     'x = xml_new_document(); r = xml_add_child(x, "root"); xml_add_child(r, xml_comment("Hello!")); as_character(xml_root(x))',
     'x <- xml_new_document(); r <- xml_add_child(x, "root"); xml_add_child(r, xml_comment("Hello!")); paste(capture.output(x), collapse = "\\n")',
     'x = xml_new_document(); r = xml_add_child(x, "root"); xml_add_child(r, xml_comment("Hello!")); str(xml_root(x))'),
    ("xml_dtd", "xml2.xml_dtd", "A document type declaration on a new document.", "an XHTML transitional doctype",
     'as.character(xml_new_root(xml_dtd("html", "-//W3C//DTD XHTML 1.0 Transitional//EN", "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd")))',
     'as_character(xml_new_root(xml_dtd("html", "-//W3C//DTD XHTML 1.0 Transitional//EN", "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd")))',
     'paste(capture.output({x <- xml_new_root(xml_dtd("html", "-//W3C//DTD XHTML 1.0 Transitional//EN", "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd")); x}), collapse = "\\n")',
     'str(xml_new_root(xml_dtd("html", "-//W3C//DTD XHTML 1.0 Transitional//EN", "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd")))'),
    ("xml_new_document", "xml2.xml_new_document", "An empty document with a version and encoding.", "the XML declaration",
     'as.character(xml_new_document())',
     'as_character(xml_new_document())',
     'paste(capture.output(xml_new_document()), collapse = "\\n")',
     'str(xml_new_document())'),
    ("xml_new_root", "xml2.xml_new_root", "A new document whose root is the given name or node.", "a root element",
     'as.character(xml_new_root("root"))',
     'as_character(xml_new_root("root"))',
     'paste(capture.output({x <- xml_new_root("root"); x}), collapse = "\\n")',
     'str(xml_new_root("root"))'),
    ("xml_missing", "xml2.xml_missing", "The stand-in for a node that was not found.", "missing, and its text is NA",
     'c(is.na(xml_missing()), is.na(xml_text(xml_missing())))',
     '[is_na(xml_missing()), xml_text(xml_missing()) is None]',
     'paste(capture.output(xml_missing()), collapse = "\\n")',
     'str(xml_missing())'),
    ("xml_structure", "xml2.xml_structure", "Prints the element tree without text values.", "a, b, two c, and d",
     'paste(capture.output(xml_structure(read_xml("<a><b><c/><c/></b><d/></a>"))), collapse = "\\n")',
     '_capture(lambda: xml_structure(read_xml("<a><b><c/><c/></b><d/></a>")))',
     'paste(capture.output(xml_structure(read_xml("<a><b><c/><c/></b><d/></a>"))), collapse = "\\n")',
     '_capture(lambda: xml_structure(read_xml("<a><b><c/><c/></b><d/></a>")))'),
    ("html_structure", "xml2.html_structure", "The element tree, with #id and .class on the tag.", "p#a and p.c.d",
     'paste(capture.output(html_structure(read_html("<body><p id=\\"a\\"></p><p class=\\"c d\\"></p></body>"))), collapse = "\\n")',
     '_capture(lambda: html_structure(read_html(\'<body><p id="a"></p><p class="c d"></p></body>\')))',
     'paste(capture.output(html_structure(read_html("<body><p id=\\"a\\"></p><p class=\\"c d\\"></p></body>"))), collapse = "\\n")',
     '_capture(lambda: html_structure(read_html(\'<body><p id="a"></p><p class="c d"></p></body>\')))'),
    ("as_list", "xml2.as_list", "A nested list. Element names are the names, attributes are attributes, and text is a character.", "the names under foo",
     '{z <- as_list(read_xml("<foo> a <b /><c><![CDATA[<d></d>]]></c></foo>")); paste(names(z[[1]]), collapse = "|")}',
     '"|".join(as_list(read_xml("<foo> a <b /><c><![CDATA[<d></d>]]></c></foo>"))[0].names)',
     '{z <- as_list(read_xml("<foo id=\\"a\\"></foo>")); paste0(names(z), " id=", attr(z[[1]], "id"))}',
     'z = as_list(read_xml(\'<foo id="a"></foo>\')); print_value(z.names[0] + " id=" + z[0].attrs.get("id", ""))'),
    ("as_xml_document", "xml2.as_xml_document", "A named list becomes a document. One root is required. Attributes on the list become attributes.", "foo containing bar containing baz",
     'as.character(as_xml_document(list(foo = list(bar = list(baz = list())))))',
     'as_character(as_xml_document(RList([RList([RList([RList()], names=["baz"])], names=["bar"])], names=["foo"])))',
     'paste(capture.output(as_xml_document(list(x = list()))), collapse = "\\n")',
     'str(as_xml_document(RList([RList()], names=["x"])))'),
    ("write_xml", "xml2.write_xml", "Writes a document or one node with libxml2's save flags. format is the default.", "formatted HTML read back",
     '{h <- read_html("<p>Hi!</p>"); tmp <- tempfile(fileext = ".xml"); write_xml(h, tmp, options = "format"); paste(readLines(tmp), collapse = "\\n")}',
     'import tempfile, os; h = read_html("<p>Hi!</p>"); tmp = tempfile.NamedTemporaryFile(suffix=".xml", delete=False).name; write_xml(h, tmp, options="format"); open(tmp).read().rstrip("\\n")',
     '{h <- read_html("<p>Hi!</p>"); tmp <- tempfile(fileext = ".xml"); write_xml(h, tmp, options = "format"); paste(readLines(tmp), collapse = "\\n")}',
     'import tempfile; h = read_html("<p>Hi!</p>"); tmp = tempfile.NamedTemporaryFile(suffix=".xml", delete=False).name; write_xml(h, tmp, options="format"); open(tmp).read().rstrip("\\n")'),
    ("write_html", "xml2.write_html", "Writes with the same saver as write_xml.", "the Hi paragraph",
     '{h <- read_html("<p>Hi!</p>"); tmp <- tempfile(fileext = ".xml"); write_html(h, tmp, options = "format"); paste(readLines(tmp), collapse = "\\n")}',
     'import tempfile; h = read_html("<p>Hi!</p>"); tmp = tempfile.NamedTemporaryFile(suffix=".xml", delete=False).name; write_html(h, tmp, options="format"); open(tmp).read().rstrip("\\n")',
     '{h <- read_html("<p>Hi!</p>"); tmp <- tempfile(fileext = ".xml"); write_html(h, tmp, options = "format"); paste(readLines(tmp), collapse = "\\n")}',
     'import tempfile; h = read_html("<p>Hi!</p>"); tmp = tempfile.NamedTemporaryFile(suffix=".xml", delete=False).name; write_html(h, tmp, options="format"); open(tmp).read().rstrip("\\n")'),
    ("xml_validate", "xml2.xml_validate", "Validates a document against an XML schema. Errors are kept on the result.", "the bundled order document",
     'isTRUE(xml_validate(read_xml(xml2_example("order-doc.xml")), read_xml(xml2_example("order-schema.xml"))))',
     'bool(xml_validate(read_xml(xml2_example("order-doc.xml")), read_xml(xml2_example("order-schema.xml"))))',
     'if (isTRUE(xml_validate(read_xml(xml2_example("order-doc.xml")), read_xml(xml2_example("order-schema.xml"))))) "TRUE" else "FALSE"',
     'str(xml_validate(read_xml(xml2_example("order-doc.xml")), read_xml(xml2_example("order-schema.xml"))))'),
    ("xml_serialize", "xml2.xml_serialize", "Stores the XML text and whether it was a document, a node, or a nodeset, then xml_unserialize reads it back.", "two b nodes",
     'paste(as.character(xml_unserialize(xml_serialize(xml_find_all(read_xml("<a><b><c>123</c></b><b><c>456</c></b></a>"), "//b"), NULL))), collapse = "||")',
     '"||".join(as_character(xml_unserialize(xml_serialize(xml_find_all(read_xml("<a><b><c>123</c></b><b><c>456</c></b></a>"), "//b"), None))))',
     'paste(capture.output(xml_unserialize(xml_serialize(xml_find_all(read_xml("<a><b><c>123</c></b><b><c>456</c></b></a>"), "//b"), NULL))), collapse = "\\n")',
     'str(xml_unserialize(xml_serialize(xml_find_all(read_xml("<a><b><c>123</c></b><b><c>456</c></b></a>"), "//b"), None)))'),
    ("xml_unserialize", "xml2.xml_unserialize", "Reads what xml_serialize stored.", "the two b nodes again",
     'paste(as.character(xml_unserialize(xml_serialize(xml_find_all(read_xml("<a><b><c>123</c></b><b><c>456</c></b></a>"), "//b"), NULL))), collapse = "||")',
     '"||".join(as_character(xml_unserialize(xml_serialize(xml_find_all(read_xml("<a><b><c>123</c></b><b><c>456</c></b></a>"), "//b"), None))))',
     'paste(capture.output(xml_unserialize(xml_serialize(xml_find_all(read_xml("<a><b><c>123</c></b><b><c>456</c></b></a>"), "//b"), NULL))), collapse = "\\n")',
     'str(xml_unserialize(xml_serialize(xml_find_all(read_xml("<a><b><c>123</c></b><b><c>456</c></b></a>"), "//b"), None)))'),
    ("xml_url", "xml2.xml_url", "The document URL. A literal string has none, so the result is missing.", "NA for a literal document",
     'xml_url(read_xml("<foo/>"))',
     'xml_url(read_xml("<foo/>"))',
     'flat(xml_url(read_xml("<foo/>")))',
     'print_value(xml_url(read_xml("<foo/>")))'),
    ("url_absolute", "xml2.url_absolute", "libxml2 xmlBuildURI.", "four links against one base",
     'url_absolute(c(".", "..", "/", "/x"), "http://hadley.nz/a/b/c/d")',
     'url_absolute([".", "..", "/", "/x"], "http://hadley.nz/a/b/c/d")',
     'flat(url_absolute(c(".", "..", "/", "/x"), "http://hadley.nz/a/b/c/d"))',
     'print_value(url_absolute([".", "..", "/", "/x"], "http://hadley.nz/a/b/c/d"))'),
    ("url_relative", "xml2.url_relative", "libxml2 xmlBuildRelativeURI.", "the same target against four bases",
     'c(url_relative("http://hadley.nz/a/c", "http://hadley.nz"), url_relative("http://hadley.nz/a/c", "http://hadley.nz/"), url_relative("http://hadley.nz/a/c", "http://hadley.nz/a/b"), url_relative("http://hadley.nz/a/c", "http://hadley.nz/a/b/"))',
     '[url_relative("http://hadley.nz/a/c", "http://hadley.nz"), url_relative("http://hadley.nz/a/c", "http://hadley.nz/"), url_relative("http://hadley.nz/a/c", "http://hadley.nz/a/b"), url_relative("http://hadley.nz/a/c", "http://hadley.nz/a/b/")]',
     'flat(url_relative("http://hadley.nz/a/c", "http://hadley.nz/a/b/"))',
     'print_value(url_relative("http://hadley.nz/a/c", "http://hadley.nz/a/b/"))'),
    ("url_escape", "xml2.url_escape", "libxml2 xmlURIEscapeStr. reserved lists characters that stay literal.", "a space",
     'c(url_escape("a b c"), url_escape("a b c", ""))',
     '[url_escape("a b c"), url_escape("a b c", "")]',
     'flat(url_escape("a b c"))',
     'print_value(url_escape("a b c"))'),
    ("url_unescape", "xml2.url_unescape", "libxml2 xmlURIUnescapeString.", "a space, a slash, and micro",
     'c(url_unescape("a%20b%2fc"), url_unescape("%C2%B5"))',
     '[url_unescape("a%20b%2fc"), url_unescape("%C2%B5")]',
     'flat(url_unescape("%C2%B5"))',
     'print_value(url_unescape("%C2%B5"))'),
    ("url_parse", "xml2.url_parse", "libxml2 xmlParseURI. Port 0 is missing. The query is the raw query.", "scheme, server, port, path, query, and fragment",
     '{u <- url_parse("http://had.co.nz:1234/?a=1&b=2#def"); paste(u$scheme, u$server, u$port, u$user, u$path, u$query, u$fragment, sep = "|")}',
     'r = url_parse("http://had.co.nz:1234/?a=1&b=2#def").rows[0]; "|".join("" if r[k] is None else str(r[k]) for k in ["scheme", "server", "port", "user", "path", "query", "fragment"])',
     'paste(capture.output(url_parse("http://had.co.nz:1234/?a=1&b=2#def")), collapse = "\\n")',
     'str(url_parse("http://had.co.nz:1234/?a=1&b=2#def"))'),
    ("xml2_example", "xml2.xml2_example", "The sample files shipped with the package.", "the file names",
     'paste(sort(xml2_example(NULL)), collapse = ",")',
     '",".join(xml2_example())',
     'paste(sort(xml2_example(NULL)), collapse = "\\n")',
     'print_value("\\n".join(xml2_example()))'),
    ("download_xml", "xml2.download_xml", "Downloads a URL into a file. urllib does the transfer. A curl handle is accepted and unused.", "the bundled order document via a file URL",
     '{src <- xml2_example("order-doc.xml"); dest <- tempfile(); download_xml(paste0("file://", src), dest); paste(readLines(dest), collapse = "\\n")}',
     'import tempfile; src = xml2_example("order-doc.xml"); dest = tempfile.NamedTemporaryFile(delete=False).name; download_xml("file://" + src, dest); open(dest).read().rstrip("\\n")',
     '{src <- xml2_example("order-doc.xml"); dest <- tempfile(); download_xml(paste0("file://", src), dest); paste(readLines(dest), collapse = "\\n")}',
     'import tempfile; src = xml2_example("order-doc.xml"); dest = tempfile.NamedTemporaryFile(delete=False).name; download_xml("file://" + src, dest); open(dest).read().rstrip("\\n")'),
    ("download_html", "xml2.download_html", "The same download as download_xml.", "the bundled order document via a file URL",
     '{src <- xml2_example("order-doc.xml"); dest <- tempfile(); download_html(paste0("file://", src), dest); paste(readLines(dest), collapse = "\\n")}',
     'import tempfile; src = xml2_example("order-doc.xml"); dest = tempfile.NamedTemporaryFile(delete=False).name; download_html("file://" + src, dest); open(dest).read().rstrip("\\n")',
     '{src <- xml2_example("order-doc.xml"); dest <- tempfile(); download_html(paste0("file://", src), dest); paste(readLines(dest), collapse = "\\n")}',
     'import tempfile; src = xml2_example("order-doc.xml"); dest = tempfile.NamedTemporaryFile(delete=False).name; download_html("file://" + src, dest); open(dest).read().rstrip("\\n")'),
]


def exports() -> list[str]:
    names = []
    for line in NAMESPACE.read_text().splitlines():
        if line.startswith("export("):
            names.append(line[len("export(") : -1].strip('"'))
        elif line.startswith('export("'):
            names.append(line[len('export("') : -2])
    return names


def r_script(expr: str) -> str:
    return textwrap.dedent(
        f"""\
        .libPaths(c(path.expand("~/R/library"), .libPaths()))
        suppressPackageStartupMessages(library(xml2))
        json_str <- function(s) {{
          if (is.null(s) || length(s) == 0 || is.na(s)) return("null")
          cps <- utf8ToInt(enc2utf8(as.character(s)))
          if (length(cps) == 0) return('""')
          parts <- vapply(cps, function(cp) {{
            if (cp == 34) paste0("\\\\", '"')
            else if (cp == 92) paste0("\\\\", "\\\\")
            else if (cp == 10) paste0("\\\\", "n")
            else if (cp == 13) paste0("\\\\", "r")
            else if (cp == 9) paste0("\\\\", "t")
            else if (cp < 32 || cp == 127 || cp > 126) sprintf("\\\\u%04x", cp)
            else intToUtf8(cp)
          }}, "")
          paste0('"', paste(parts, collapse = ""), '"')
        }}
        flat <- function(x) {{
          if (is.null(x) || length(x) == 0) return("NA")
          if (is.logical(x)) return(paste(ifelse(is.na(x), "NA", ifelse(x, "TRUE", "FALSE")), collapse = " "))
          if (is.numeric(x)) {{
            txt <- ifelse(is.na(x), "NA", ifelse(abs(x - round(x)) < 1e-8 & abs(x) < 1e15, as.character(as.integer(round(x))), format(x, trim = TRUE, scientific = FALSE)))
            return(paste(txt, collapse = " "))
          }}
          paste(ifelse(is.na(x), "NA", as.character(x)), collapse = " ")
        }}
        to_json <- function(x) {{
          if (is.null(x)) return("null")
          if (is.atomic(x) && length(x) == 1) {{
            if (is.na(x)) return("null")
            if (is.logical(x)) return(if (isTRUE(x)) "true" else "false")
            if (is.numeric(x)) return(sprintf("%.17g", x))
            return(json_str(x))
          }}
          if (is.atomic(x)) {{
            parts <- vapply(seq_along(x), function(i) {{
              if (is.na(x[[i]])) "null" else to_json(x[[i]])
            }}, "")
            return(paste0("[", paste(parts, collapse = ","), "]"))
          }}
          stop("unsupported")
        }}
        one <- function() {{
          {expr}
        }}
        value <- one()
        elapsed <- numeric(20)
        for (i in seq_len(20)) {{
          t0 <- as.numeric(Sys.time())
          one()
          elapsed[[i]] <- as.numeric(Sys.time()) - t0
        }}
        cat(sprintf('{{"value":%s,"median_ms":%.17g}}\\n', to_json(value), median(elapsed) * 1000))
        """
    )


def _capture(fn):
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return buf.getvalue().rstrip("\n")


def with_return(expr: str) -> str:
    """Turn a statement list into a function body whose last part is returned."""
    text = expr.strip()
    if "\n" in text:
        lines = text.splitlines()
        lines[-1] = "return " + lines[-1].lstrip()
        return "\n".join(lines)
    parts = []
    buf = []
    quote = ""
    for char in text:
        if quote:
            buf.append(char)
            if char == quote and (len(buf) < 2 or buf[-2] != "\\"):
                quote = ""
            continue
        if char in ("'", '"'):
            quote = char
            buf.append(char)
            continue
        if char == ";":
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(char)
    parts.append("".join(buf).strip())
    parts = [part for part in parts if part]
    parts[-1] = "return " + parts[-1]
    return "\n".join(parts)


def py_script(expr: str) -> str:
    body = textwrap.indent(with_return(expr), "    ")
    return (
        "import json\nimport statistics\nimport time\n"
        "from xml2 import *\n"
        "def print_value(value):\n"
        "    if value is None:\n"
        "        return 'NA'\n"
        "    if isinstance(value, bool):\n"
        "        return 'TRUE' if value else 'FALSE'\n"
        "    if isinstance(value, float) and value == int(value):\n"
        "        return str(int(value)) if abs(value) < 1e15 else str(value)\n"
        "    if isinstance(value, list):\n"
        "        return ' '.join(print_value(item) for item in value)\n"
        "    return str(value)\n"
        "def _capture(fn):\n"
        "    import contextlib, io\n"
        "    buf = io.StringIO()\n"
        "    with contextlib.redirect_stdout(buf):\n"
        "        fn()\n"
        "    return buf.getvalue().rstrip('\\n')\n"
        "def one():\n"
        f"{body}\n"
        "value = one()\n"
        "elapsed = []\n"
        "for _ in range(20):\n"
        "    started = time.perf_counter()\n"
        "    one()\n"
        "    elapsed.append((time.perf_counter() - started) * 1000)\n"
        "shown = value\n"
        "if shown is None:\n"
        "    shown = None\n"
        "print(json.dumps({'value': shown, 'median_ms': statistics.median(elapsed)}))\n"
    )


def run_r(expr: str) -> dict:
    script = r_script(expr)
    out = subprocess.check_output(["Rscript", "-e", script], text=True, stderr=subprocess.STDOUT)
    line = [item for item in out.splitlines() if item.startswith("{")][-1]
    return json.loads(line)


def run_py(expr: str) -> dict:
    script = py_script(expr)
    out = subprocess.check_output(
        ["/home/ahmed/killr_projects/killr/.venv/bin/python", "-c", script],
        text=True,
        stderr=subprocess.STDOUT,
        cwd=str(ROOT),
    )
    line = [item for item in out.splitlines() if item.startswith("{")][-1]
    return json.loads(line)


def same(left, right) -> tuple[bool, float]:
    if isinstance(left, float) or isinstance(right, float):
        if left is None or right is None:
            return left is right, 0.0 if left is right else 1.0
        diff = abs(float(left) - float(right))
        return diff <= 1e-8, diff
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False, 1.0
        ok = True
        worst = 0.0
        for a, b in zip(left, right):
            item_ok, item_diff = same(a, b)
            ok = ok and item_ok
            worst = max(worst, item_diff)
        return ok, worst
    return left == right, 0.0 if left == right else 1.0


def python_name(qual: str) -> str:
    return qual.split(".", 1)[1]


def loads_for(name: str) -> list[str]:
    if name in ("download_xml", "download_html"):
        return ["urllib"]
    return ["ctypes"]


def write_records() -> None:
    missing = [name for name in exports() if name not in {case[0] for case in CASES}]
    extra = [case[0] for case in CASES if case[0] not in exports()]
    if missing or extra:
        raise SystemExit(f"missing {missing} extra {extra}")
    docs = ROOT / "docs"
    output = docs / "output"
    proof = ROOT / "proof"
    output.mkdir(parents=True, exist_ok=True)
    proof.mkdir(parents=True, exist_ok=True)
    functions = []
    failures = []
    for case in CASES:
        name, qual, done, summary, r_value, py_value, r_example, py_example = case
        print(name, flush=True)
        try:
            r_result = run_r(r_value)
            py_result = run_py(py_value)
        except subprocess.CalledProcessError as exc:
            failures.append(f"{name} run failed\n{exc.output}")
            continue
        ok, diff = same(r_result["value"], py_result["value"])
        if not ok:
            failures.append(f"{name} differs\nR {r_result['value']!r}\nPY {py_result['value']!r}")
            continue
        try:
            r_ex = run_r(r_example)
            py_ex = run_py(py_example)
        except subprocess.CalledProcessError as exc:
            failures.append(f"{name} example run failed\n{exc.output}")
            continue
        r_text = "" if r_ex["value"] is None else str(r_ex["value"])
        py_text = "" if py_ex["value"] is None else str(py_ex["value"])
        if r_text != py_text:
            failures.append(f"{name} example differs\nR {r_text!r}\nPY {py_text!r}")
            continue
        (output / f"{name}-r.txt").write_text(r_text + ("\n" if r_text else ""), encoding="utf-8")
        (output / f"{name}-python.txt").write_text(py_text + ("\n" if py_text else ""), encoding="utf-8")
        r_proof = r_script(r_value)
        py_proof = py_script(py_value)
        (proof / f"{name}-r.R").write_text(r_proof, encoding="utf-8")
        (proof / f"{name}-py.py").write_text(py_proof, encoding="utf-8")
        speedup = r_result["median_ms"] / py_result["median_ms"] if py_result["median_ms"] else None
        doc = {
            "name": name,
            "title": done.split(".")[0],
            "origin": {
                "description": done,
                "usage": name,
                "arguments": [],
                "details": "",
                "value": summary,
                "example": r_example,
                "output": f"output/{name}-r.txt",
            },
            "translation": {
                "description": done,
                "usage": python_name(qual),
                "arguments": [],
                "details": "",
                "value": summary,
                "example": py_example,
                "output": f"output/{name}-python.txt",
            },
        }
        (docs / f"{name}.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        functions.append(
            {
                "name": name,
                "translated": True,
                "python": qual,
                "loads": loads_for(name),
                "uses": [],
                "done": done,
                "not_done": "",
                "blocked_by": [],
                "assigned": "",
                "check": {
                    "case": summary,
                    "r_ms": r_result["median_ms"],
                    "translated_ms": py_result["median_ms"],
                    "speedup": speedup,
                    "matches": True,
                    "max_abs_diff": diff,
                    "tolerance": 1e-8,
                    "proof": {"r": r_proof, "python": py_proof},
                },
            }
        )
    translation = {
        "name": "xml2",
        "cran_version": "1.6.0",
        "inventory": "complete",
        "status": "complete",
        "blocked_by": [],
        "crate_claims": [],
        "resume": "All 67 function exports are done. The four classes are the node types those functions return. Documents, XPath, schema checks, and URLs call the system libxml2 through ctypes, the library the installed package links. download_xml uses urllib. cli and rlang are not opened: their calls here are error text and one boolean. curl is suggested, and a curl handle is unused. There is no Fortran, so there is no crate.",
        "functions": functions,
    }
    if failures:
        print("\n\n".join(failures))
        raise SystemExit(f"{len(failures)} checks failed")
    (ROOT / "translation.json").write_text(json.dumps(translation, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(functions)} functions")


if __name__ == "__main__":
    write_records()
