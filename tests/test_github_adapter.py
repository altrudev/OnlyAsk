import pytest

from onlyask.github_adapter import GitHubAdapter


class T:
    def __init__(self):
        self.calls = []

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if path.endswith('/pulls/2'):
            return {"title":"x","head":{"sha":"1234567abc","ref":"b"},"base":{"ref":"main"},"state":"open","merged":False,"mergeable":True,"html_url":"u"}
        if path.endswith('/merge'):
            return {"merged":True}
        return {"default_branch":"main","visibility":"public","archived":False,"open_issues_count":0}


def test_merge_is_sha_bound():
    t = T()
    adapter = GitHubAdapter(t)
    adapter.merge_pull('altrudev/OnlyAsk', 2, '1234567abc', 'squash')
    assert t.calls[-1][2] == {"sha":"1234567abc","merge_method":"squash"}


def test_repo_validation_blocks_endpoint_injection():
    adapter = GitHubAdapter(T())
    with pytest.raises(ValueError):
        adapter.inspect_repository('a/b?x=/repos/evil')
