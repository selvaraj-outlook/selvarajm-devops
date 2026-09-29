import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import smoke_test  # noqa: E402


def test_build_request_matches_open_inference_protocol():
    body = smoke_test.build_request(smoke_test.SAMPLE)
    tensor = body["inputs"][0]
    assert tensor["shape"] == [2, 13]
    assert tensor["datatype"] == "FP32"


def test_predict_parses_v2_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/models/wine-classifier/infer"
        rows = json.loads(request.content)["inputs"][0]["data"]
        return httpx.Response(200, json={"outputs": [{"name": "output-0", "data": [0] * len(rows)}]})

    client = httpx.Client(base_url="http://kserve", transport=httpx.MockTransport(handler))
    assert smoke_test.predict(client, smoke_test.SAMPLE) == [0, 0]
