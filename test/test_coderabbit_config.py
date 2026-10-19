"""Verify that the repository's CodeRabbit policy remains valid and intentional."""

import tomllib
from pathlib import Path

import pytest
import yaml
from hamcrest import assert_that, contains_exactly, contains_inanyorder, contains_string, equal_to
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

ROOT = Path(__file__).resolve().parents[1]
CODERABBIT_CONFIG_PATH = ROOT / ".coderabbit.yaml"


class UniqueKeyLoader(yaml.SafeLoader):
    """Load safe YAML while rejecting ambiguous duplicate mapping keys."""


def _construct_unique_mapping(loader: UniqueKeyLoader, node: MappingNode, deep: bool = False) -> dict:
    """Construct a mapping and fail when the same key is declared more than once."""
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


@pytest.fixture
def coderabbit_config() -> dict:
    """Load the CodeRabbit configuration as a duplicate-key-safe mapping."""
    with CODERABBIT_CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = yaml.load(config_file, Loader=UniqueKeyLoader)

    assert_that(config, equal_to(dict(config)))
    return config


def _instructions_by_path(config: dict) -> dict[str, str]:
    """Index CodeRabbit's path-specific review instructions by glob."""
    return {entry["path"]: entry["instructions"] for entry in config["reviews"]["path_instructions"]}


def test_config_declares_the_current_coderabbit_schema(coderabbit_config):
    """Require the editor schema hint and a parseable top-level mapping."""
    first_line = CODERABBIT_CONFIG_PATH.read_text(encoding="utf-8").splitlines()[0]

    assert_that(first_line, equal_to("# yaml-language-server: $schema=https://coderabbit.ai/integrations/schema.v2.json"))
    assert_that(coderabbit_config.keys(), contains_inanyorder("language", "tone_instructions", "reviews", "code_generation"))


def test_language_settings_use_british_english_consistently(coderabbit_config):
    """Keep review comments and generated docstrings on the repository locale."""
    assert_that(coderabbit_config["language"], equal_to("en-GB"))
    assert_that(coderabbit_config["code_generation"], equal_to({"docstrings": {"language": "en-GB"}}))


def test_path_filters_exclude_only_known_generated_or_fixture_content(coderabbit_config):
    """Protect the exact review exclusions without accidentally adding broad ignores."""
    path_filters = coderabbit_config["reviews"]["path_filters"]

    assert_that(
        path_filters,
        contains_exactly(
            "!uv.lock",
            "!features/targets/invalid.py",
            "!features/targets/taut/taut_test.py",
            "!features/targets/go/node.py",
            "!test/test_data/**",
        ),
    )
    assert_that(all(path_filter.startswith("!") for path_filter in path_filters), equal_to(True))


def test_path_filters_cover_every_ruff_exclusion(coderabbit_config):
    """Keep files excluded by Ruff out of CodeRabbit review as the config promises."""
    with Path(ROOT / "pyproject.toml").open("rb") as pyproject_file:
        ruff_exclusions = tomllib.load(pyproject_file)["tool"]["ruff"]["extend-exclude"]
    path_filters = set(coderabbit_config["reviews"]["path_filters"])

    assert_that({f"!{path}" for path in ruff_exclusions}.issubset(path_filters), equal_to(True))


def test_disabled_checks_match_the_tools_already_enforced_by_ci(coderabbit_config):
    """Disable only duplicate or intentionally incompatible review checks."""
    reviews = coderabbit_config["reviews"]

    assert_that(reviews["pre_merge_checks"], equal_to({"docstrings": {"mode": "off"}}))
    assert_that(
        reviews["tools"],
        equal_to(
            {
                "pylint": {"enabled": False},
                "flake8": {"enabled": False},
                "markdownlint": {"enabled": False},
            },
        ),
    )


def test_each_supported_repository_area_has_one_instruction_block(coderabbit_config):
    """Ensure review guidance has complete, non-overlapping path coverage."""
    path_instructions = coderabbit_config["reviews"]["path_instructions"]
    paths = [entry["path"] for entry in path_instructions]

    assert_that(paths, contains_exactly("src/**/*.py", "test/**/*.py", "features/**/*.py", "docs/**/*.md"))
    assert_that(len(paths), equal_to(len(set(paths))))


@pytest.mark.parametrize(
    ("path", "required_guidance"),
    [
        (
            "src/**/*.py",
            (
                "Python 3.14",
                "type correctness",
                "never use digits as abbreviations",
                "RECHECK when <tool> is updated",
                "Docstrings describe the behaviour",
            ),
        ),
        (
            "test/**/*.py",
            (
                "PyHamcrest",
                "@pytest.mark.parametrize",
                "@pytest.fixture",
                "pytest-mock",
                "Test modules, classes and methods all need docstrings",
                "[tool.pytest.ini_options]",
            ),
        ),
        (
            "features/**/*.py",
            (
                "pytest ./test",
                "features/steps/",
                "features/targets/",
            ),
        ),
        (
            "docs/**/*.md",
            (
                "British English",
                "image-policy.md",
                "linking-policy.md",
                "docs/documentation-system/templates/",
            ),
        ),
    ],
)
def test_path_instructions_preserve_their_core_review_guidance(coderabbit_config, path, required_guidance):
    """Guard the actionable policy attached to each reviewed repository area."""
    instructions = _instructions_by_path(coderabbit_config)[path]

    for guidance in required_guidance:
        assert_that(instructions, contains_string(guidance))
