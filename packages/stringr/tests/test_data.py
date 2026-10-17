"""Lengths and first items of the stringr character vectors."""

from stringr.data import fruit, sentences, words


def test_fruit():
    assert len(fruit) == 80
    assert fruit[0] == "apple"


def test_sentences():
    assert len(sentences) == 720
    assert sentences[0] == "The birch canoe slid on the smooth planks."


def test_words():
    assert len(words) == 980
    assert words[0] == "a"
