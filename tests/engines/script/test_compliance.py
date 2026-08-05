from engines.script.compliance import check_compliance, load_banned_words


def test_check_compliance_detects_single_banned_word() -> None:
    result = check_compliance("这是全网最好的产品", ["最好", "第一"])
    assert result == ("最好",)


def test_check_compliance_detects_multiple_banned_words() -> None:
    result = check_compliance("最好用、第一名的产品", ["最好用", "第一名"])
    assert set(result) == {"最好用", "第一名"}


def test_check_compliance_no_match_returns_empty_tuple() -> None:
    assert check_compliance("这是一个普通的产品介绍", ["最好", "第一"]) == ()


def test_check_compliance_is_case_insensitive_for_latin_words() -> None:
    assert check_compliance("This is the BEST product", ["best"]) == ("best",)


def test_load_banned_words_reads_config_file() -> None:
    words = load_banned_words()
    assert "最" in words
    assert isinstance(words, list)
