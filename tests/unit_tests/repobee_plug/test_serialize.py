import collections

import pytest

import repobee_plug as plug


@pytest.fixture
def hook_result_mapping():
    hook_results = collections.defaultdict(list)
    for repo_name, hook_name, status, msg, data in [
        (
            "slarse-task-1",
            "junit4",
            plug.Status.SUCCESS,
            "All tests passed",
            {"extra": "data", "arbitrary": {"nesting": "here"}},
        ),
        (
            "slarse-task-1",
            "javac",
            plug.Status.ERROR,
            "Some stuff failed",
            None,
        ),
        (
            "glassey-task-2",
            "pylint",
            plug.Status.WARNING,
            "-10/10 code quality",
            None,
        ),
    ]:
        hook_results[repo_name].append(
            plug.Result(name=hook_name, status=status, msg=msg, data=data)
        )
    return {
        repo_name: sorted(results)
        for reponame, results in hook_results.items()
    }


def testplug_empty_mapping():
    assert plug.result_mapping_to_json({}) == "{}"


def test_desezialize_empty_json():
    assert plug.json_to_result_mapping("{}") == {}


def test_lossless_serialization(hook_result_mapping):
    """Test that serializing and then deserializing results in all data being
    recovered.
    """
    expected = dict(hook_result_mapping)

    serialized = plug.result_mapping_to_json(hook_result_mapping)
    deserialized = plug.json_to_result_mapping(serialized)
    actual = {
        repo_name: sorted(results)
        for repo_name, results in deserialized.items()
    }

    assert actual == expected
