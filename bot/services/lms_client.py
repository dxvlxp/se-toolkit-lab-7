import json
import urllib.error
import urllib.parse
import urllib.request


class BackendError(Exception):
    pass


class LMSClient:
    def __init__(self, base_url: str, api_key: str, timeout: int = 12):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout

    def request(self, method: str, path: str, params=None, body=None):
        url = self.base_url + path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        payload = None if body is None else json.dumps(body).encode('utf-8')
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        req = urllib.request.Request(url, data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode('utf-8')
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            details = e.read(250).decode('utf-8', errors='replace')
            raise BackendError(f'HTTP {e.code} {e.reason}: {details}') from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            reason = getattr(e, 'reason', e)
            raise BackendError(f'{reason} ({self.base_url}). Check backend/network.') from e
        except ValueError as e:
            raise BackendError(f'Invalid JSON from backend ({self.base_url})') from e

    def get_items(self):
        return self.request('GET', '/items/')

    def get_learners(self):
        return self.request('GET', '/learners/')

    def get_scores(self, lab):
        return self.request('GET', '/analytics/scores', {'lab': lab})

    def get_pass_rates(self, lab):
        return self.request('GET', '/analytics/pass-rates', {'lab': lab})

    def get_timeline(self, lab):
        return self.request('GET', '/analytics/timeline', {'lab': lab})

    def get_groups(self, lab):
        return self.request('GET', '/analytics/groups', {'lab': lab})

    def get_top_learners(self, lab, limit=5):
        return self.request('GET', '/analytics/top-learners', {'lab': lab, 'limit': limit})

    def get_completion_rate(self, lab):
        return self.request('GET', '/analytics/completion-rate', {'lab': lab})

    def trigger_sync(self):
        return self.request('POST', '/pipeline/sync', body={})
