import pytest
from telescope.fetchers.utils import (
    extract_severity_with_rules,
    apply_json_rule,
    apply_regex_rule,
    apply_remap,
)


class TestApplyJsonRule:
    def test_extract_from_simple_json(self):
        message = '{"level": "error", "msg": "test message"}'
        rule = {"type": "json", "path": ["level"]}
        result = apply_json_rule(message, rule)
        assert result == "error"

    def test_extract_from_nested_json(self):
        message = '{"log": {"level": "warn", "timestamp": "2024-01-01"}}'
        rule = {"type": "json", "path": ["log", "level"]}
        result = apply_json_rule(message, rule)
        assert result == "warn"

    def test_extract_from_deeply_nested_json(self):
        message = '{"metadata": {"log": {"severity": {"level": "info"}}}}'
        rule = {"type": "json", "path": ["metadata", "log", "severity", "level"]}
        result = apply_json_rule(message, rule)
        assert result == "info"

    def test_invalid_json_returns_none(self):
        message = "not a valid json string"
        rule = {"type": "json", "path": ["level"]}
        result = apply_json_rule(message, rule)
        assert result is None

    def test_path_not_found_returns_none(self):
        message = '{"level": "error"}'
        rule = {"type": "json", "path": ["nonexistent"]}
        result = apply_json_rule(message, rule)
        assert result is None

    def test_nested_path_not_found_returns_none(self):
        message = '{"level": "error"}'
        rule = {"type": "json", "path": ["level", "nested"]}
        result = apply_json_rule(message, rule)
        assert result is None

    def test_numeric_value_converted_to_string(self):
        message = '{"level": 1}'
        rule = {"type": "json", "path": ["level"]}
        result = apply_json_rule(message, rule)
        assert result == "1"

    def test_empty_path_returns_none(self):
        message = '{"level": "error"}'
        rule = {"type": "json", "path": []}
        result = apply_json_rule(message, rule)
        assert result is None

    def test_path_not_list_returns_none(self):
        message = '{"level": "error"}'
        rule = {"type": "json", "path": "level"}
        result = apply_json_rule(message, rule)
        assert result is None


class TestApplyRegexRule:
    def test_extract_with_square_brackets(self):
        message = "[ERROR] Connection failed"
        rule = {"type": "regex", "pattern": r"\[(\w+)\]", "group": 1}
        result = apply_regex_rule(message, rule)
        assert result == "ERROR"

    def test_extract_with_colon_separator(self):
        message = "level=ERROR msg=test"
        rule = {"type": "regex", "pattern": r"level=(\w+)", "group": 1}
        result = apply_regex_rule(message, rule)
        assert result == "ERROR"

    def test_extract_entire_match_default_group(self):
        message = "ERROR: something went wrong"
        rule = {"type": "regex", "pattern": r"ERROR"}
        result = apply_regex_rule(message, rule)
        assert result == "ERROR"

    def test_extract_entire_match_group_zero(self):
        message = "WARN something"
        rule = {"type": "regex", "pattern": r"WARN", "group": 0}
        result = apply_regex_rule(message, rule)
        assert result == "WARN"

    def test_no_match_returns_none(self):
        message = "just a regular log message"
        rule = {"type": "regex", "pattern": r"\[(\w+)\]", "group": 1}
        result = apply_regex_rule(message, rule)
        assert result is None

    def test_invalid_regex_pattern_returns_none(self):
        message = "test message"
        rule = {"type": "regex", "pattern": r"[invalid(", "group": 1}
        result = apply_regex_rule(message, rule)
        assert result is None

    def test_invalid_group_number_returns_none(self):
        message = "[ERROR] test"
        rule = {"type": "regex", "pattern": r"\[(\w+)\]", "group": 5}
        result = apply_regex_rule(message, rule)
        assert result is None

    def test_extract_from_middle_of_message(self):
        message = "2024-01-01 12:00:00 [WARN] Low memory"
        rule = {"type": "regex", "pattern": r"\[(\w+)\]", "group": 1}
        result = apply_regex_rule(message, rule)
        assert result == "WARN"

    def test_case_sensitive_extraction_no_match(self):
        message = "This is a warn level message"
        rule = {"type": "regex", "pattern": r"\b(WARN|ERROR)\b", "group": 1}
        result = apply_regex_rule(message, rule)
        assert result is None

    def test_case_insensitive_extraction_matches(self):
        message = "This is a warn level message"
        rule = {
            "type": "regex",
            "pattern": r"\b(WARN|ERROR)\b",
            "group": 1,
            "case_insensitive": True,
        }
        result = apply_regex_rule(message, rule)
        assert result == "warn"

    def test_case_insensitive_extraction_preserves_case(self):
        message = "Level: WaRn - something happened"
        rule = {
            "type": "regex",
            "pattern": r"level:\s*(\w+)",
            "group": 1,
            "case_insensitive": True,
        }
        result = apply_regex_rule(message, rule)
        assert result == "WaRn"


class TestApplyRemap:
    def test_remap_exact_match(self):
        extracted = "error"
        remap = [
            {"pattern": "error", "value": "ERROR"},
            {"pattern": "warn", "value": "WARNING"},
        ]
        result = apply_remap(extracted, remap)
        assert result == "ERROR"

    def test_remap_regex_pattern(self):
        extracted = "warn"
        remap = [
            {"pattern": "warn.*", "value": "WARNING"},
            {"pattern": "err.*", "value": "ERROR"},
        ]
        result = apply_remap(extracted, remap)
        assert result == "WARNING"

    def test_remap_regex_with_alternation(self):
        extracted = "error"
        remap = [
            {"pattern": "(error|err|e)", "value": "ERROR"},
            {"pattern": "warn", "value": "WARNING"},
        ]
        result = apply_remap(extracted, remap)
        assert result == "ERROR"

    def test_remap_numeric_pattern(self):
        extracted = "1"
        remap = [
            {"pattern": "[0-3]", "value": "ERROR"},
            {"pattern": "[4-6]", "value": "WARN"},
            {"pattern": "[7-9]", "value": "INFO"},
        ]
        result = apply_remap(extracted, remap)
        assert result == "ERROR"

    def test_no_remap_match_returns_original(self):
        extracted = "DEBUG"
        remap = [
            {"pattern": "error", "value": "ERROR"},
            {"pattern": "warn", "value": "WARNING"},
        ]
        result = apply_remap(extracted, remap)
        assert result == "DEBUG"

    def test_empty_remap_list_returns_original(self):
        extracted = "ERROR"
        remap = []
        result = apply_remap(extracted, remap)
        assert result == "ERROR"

    def test_none_remap_returns_original(self):
        extracted = "ERROR"
        remap = None
        result = apply_remap(extracted, remap)
        assert result == "ERROR"

    def test_case_sensitive_matching(self):
        extracted = "error"
        remap = [
            {"pattern": "ERROR", "value": "CRITICAL"},
            {"pattern": "error", "value": "WARNING"},
        ]
        result = apply_remap(extracted, remap)
        assert result == "WARNING"

    def test_case_insensitive_matching(self):
        extracted = "Error"
        remap = [
            {"pattern": "error", "value": "ERROR", "case_insensitive": True},
            {"pattern": "warn", "value": "WARNING"},
        ]
        result = apply_remap(extracted, remap)
        assert result == "ERROR"

    def test_case_insensitive_regex_pattern(self):
        extracted = "WARNING"
        remap = [
            {"pattern": "warn.*", "value": "WARNING", "case_insensitive": True},
            {"pattern": "err.*", "value": "ERROR"},
        ]
        result = apply_remap(extracted, remap)
        assert result == "WARNING"

    def test_invalid_regex_pattern_skipped(self):
        extracted = "error"
        remap = [
            {"pattern": "[invalid(", "value": "BAD"},
            {"pattern": "error", "value": "ERROR"},
        ]
        result = apply_remap(extracted, remap)
        assert result == "ERROR"

    def test_first_matching_pattern_wins(self):
        extracted = "error"
        remap = [
            {"pattern": "e.*", "value": "E_STAR"},
            {"pattern": "error", "value": "ERROR"},
        ]
        result = apply_remap(extracted, remap)
        assert result == "E_STAR"

    def test_missing_pattern_skipped(self):
        extracted = "error"
        remap = [{"value": "BAD"}, {"pattern": "error", "value": "ERROR"}]
        result = apply_remap(extracted, remap)
        assert result == "ERROR"

    def test_missing_value_skipped(self):
        extracted = "error"
        remap = [{"pattern": "error"}, {"pattern": "error", "value": "ERROR"}]
        result = apply_remap(extracted, remap)
        assert result == "ERROR"

    def test_per_rule_case_insensitive(self):
        extracted = "Error"
        remap = [
            {"pattern": "error", "value": "ERROR_CASE_SENS"},
            {
                "pattern": "error",
                "value": "ERROR_CASE_INSENS",
                "case_insensitive": True,
            },
        ]
        result = apply_remap(extracted, remap)
        assert result == "ERROR_CASE_INSENS"


class TestExtractSeverityWithRules:
    def test_json_extraction_success(self):
        message = '{"level": "error"}'
        rules = {"extract": [{"type": "json", "path": ["level"]}], "remap": []}
        result = extract_severity_with_rules(message, rules)
        assert result == "error"

    def test_json_extraction_with_remap(self):
        message = '{"level": "warn"}'
        rules = {
            "extract": [{"type": "json", "path": ["level"]}],
            "remap": [
                {"pattern": "warn", "value": "WARNING"},
                {"pattern": "error", "value": "ERROR"},
            ],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "WARNING"

    def test_regex_extraction_success(self):
        message = "[ERROR] Connection failed"
        rules = {
            "extract": [{"type": "regex", "pattern": r"\[(\w+)\]", "group": 1}],
            "remap": [],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "ERROR"

    def test_regex_extraction_with_remap(self):
        message = "[WARN] Low disk space"
        rules = {
            "extract": [{"type": "regex", "pattern": r"\[(\w+)\]", "group": 1}],
            "remap": [
                {"pattern": "WARN", "value": "WARNING"},
                {"pattern": "ERROR", "value": "CRITICAL"},
            ],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "WARNING"

    def test_first_match_wins_both_match(self):
        message = '{"level": "info"}'
        rules = {
            "extract": [
                {"type": "json", "path": ["level"]},
                {"type": "regex", "pattern": r"level", "group": 0},
            ],
            "remap": [],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "info"

    def test_first_match_wins_first_fails(self):
        message = "[ERROR] not json"
        rules = {
            "extract": [
                {"type": "json", "path": ["level"]},
                {"type": "regex", "pattern": r"\[(\w+)\]", "group": 1},
            ],
            "remap": [],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "ERROR"

    def test_no_rules_match_returns_unknown(self):
        message = "plain log message"
        rules = {
            "extract": [
                {"type": "json", "path": ["level"]},
                {"type": "regex", "pattern": r"\[(\w+)\]", "group": 1},
            ],
            "remap": [],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "UNKNOWN"

    def test_empty_rules_returns_unknown(self):
        message = "test message"
        rules = {}
        result = extract_severity_with_rules(message, rules)
        assert result == "UNKNOWN"

    def test_none_rules_returns_unknown(self):
        message = "test message"
        rules = None
        result = extract_severity_with_rules(message, rules)
        assert result == "UNKNOWN"

    def test_no_extract_key_returns_unknown(self):
        message = "test message"
        rules = {"remap": [{"pattern": "error", "value": "ERROR"}]}
        result = extract_severity_with_rules(message, rules)
        assert result == "UNKNOWN"

    def test_empty_extract_list_returns_unknown(self):
        message = "test message"
        rules = {"extract": [], "remap": []}
        result = extract_severity_with_rules(message, rules)
        assert result == "UNKNOWN"

    def test_invalid_rule_type_returns_unknown(self):
        message = "test message"
        rules = {"extract": [{"type": "unknown_type", "pattern": "test"}], "remap": []}
        result = extract_severity_with_rules(message, rules)
        assert result == "UNKNOWN"

    def test_remap_without_extract_field(self):
        message = "test"
        rules = {"remap": [{"pattern": "test", "value": "TEST"}]}
        result = extract_severity_with_rules(message, rules)
        assert result == "UNKNOWN"

    def test_complex_nested_json_with_remap(self):
        message = '{"metadata": {"severity": {"level": "3"}}}'
        rules = {
            "extract": [{"type": "json", "path": ["metadata", "severity", "level"]}],
            "remap": [
                {"pattern": "1", "value": "CRITICAL"},
                {"pattern": "2", "value": "ERROR"},
                {"pattern": "3", "value": "WARNING"},
                {"pattern": "4", "value": "INFO"},
            ],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "WARNING"

    def test_multiple_rules_second_matches(self):
        message = "timestamp [INFO] application started"
        rules = {
            "extract": [
                {"type": "json", "path": ["level"]},
                {"type": "regex", "pattern": r"\[(\w+)\]", "group": 1},
            ],
            "remap": [{"pattern": "INFO", "value": "INFORMATION"}],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "INFORMATION"

    def test_multiple_rules_all_fail(self):
        message = "no severity information"
        rules = {
            "extract": [
                {"type": "json", "path": ["level"]},
                {"type": "regex", "pattern": r"\[(\w+)\]", "group": 1},
                {"type": "regex", "pattern": r"level=(\w+)", "group": 1},
            ],
            "remap": [],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "UNKNOWN"

    def test_remap_not_in_dict_preserves_value(self):
        message = '{"level": "debug"}'
        rules = {
            "extract": [{"type": "json", "path": ["level"]}],
            "remap": [
                {"pattern": "error", "value": "ERROR"},
                {"pattern": "warn", "value": "WARNING"},
            ],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "debug"

    def test_remap_with_regex_pattern(self):
        message = '{"level": "warning"}'
        rules = {
            "extract": [{"type": "json", "path": ["level"]}],
            "remap": [
                {"pattern": "warn.*", "value": "WARNING"},
                {"pattern": "err.*", "value": "ERROR"},
            ],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "WARNING"

    def test_remap_case_insensitive(self):
        message = '{"level": "Error"}'
        rules = {
            "extract": [{"type": "json", "path": ["level"]}],
            "remap": [
                {"pattern": "error", "value": "ERROR", "case_insensitive": True},
                {"pattern": "warn", "value": "WARNING"},
            ],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "ERROR"

    def test_remap_case_sensitive_default(self):
        message = '{"level": "Error"}'
        rules = {
            "extract": [{"type": "json", "path": ["level"]}],
            "remap": [
                {"pattern": "error", "value": "ERROR"},
                {"pattern": "warn", "value": "WARNING"},
            ],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "Error"

    def test_remap_numeric_range(self):
        message = '{"level": "3"}'
        rules = {
            "extract": [{"type": "json", "path": ["level"]}],
            "remap": [
                {"pattern": "[0-3]", "value": "ERROR"},
                {"pattern": "[4-6]", "value": "WARN"},
                {"pattern": "[7-9]", "value": "INFO"},
            ],
        }
        result = extract_severity_with_rules(message, rules)
        assert result == "ERROR"
