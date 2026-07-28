from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request_json(
    *,
    method: str,
    url: str,
    token: str,
    timeout: float,
) -> tuple[int, Any]:
    request = Request(
        url=url,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
            return response.status, json.loads(raw_body)
    except HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        try:
            body: Any = json.loads(raw_body)
        except json.JSONDecodeError:
            body = raw_body
        return exc.code, body
    except URLError as exc:
        raise RuntimeError(f"API 연결 실패: {exc}") from exc


def run_prediction(
    *,
    barrier: Barrier,
    base_url: str,
    token: str,
    record_id: int,
    timeout: float,
) -> tuple[int, Any]:
    barrier.wait()
    return request_json(
        method="POST",
        url=(
            f"{base_url.rstrip('/')}"
            f"/api/v1/medical-records/{record_id}/ai-predictions"
        ),
        token=token,
        timeout=timeout,
    )


def fail(message: str, payload: Any | None = None) -> int:
    print(f"실패: {message}", file=sys.stderr)
    if payload is not None:
        print(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            file=sys.stderr,
        )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "같은 진료기록에 AI 예측 요청 두 개를 동시에 보내 "
            "단일 DB 결과로 수렴하는지 확인합니다."
        )
    )
    parser.add_argument(
        "--token",
        required=True,
        help="STAFF 또는 ADMIN access token",
    )
    parser.add_argument(
        "--record-id",
        required=True,
        type=int,
        help="X-Ray가 있으며 가능하면 아직 예측하지 않은 진료기록 ID",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--model-name",
        default="simple-cnn-state-dict-v1",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
    )
    args = parser.parse_args()

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                run_prediction,
                barrier=barrier,
                base_url=args.base_url,
                token=args.token,
                record_id=args.record_id,
                timeout=args.timeout,
            )
            for _ in range(2)
        ]
        responses = [future.result() for future in futures]

    print("동시 POST 응답:")
    print(json.dumps(responses, ensure_ascii=False, indent=2, default=str))

    statuses = [status for status, _ in responses]
    if statuses != [200, 200]:
        return fail("두 POST 요청이 모두 200이어야 합니다.", responses)

    bodies = [body for _, body in responses]
    if not all(isinstance(body, dict) for body in bodies):
        return fail("예측 응답이 JSON 객체가 아닙니다.", bodies)

    prediction_ids = {body.get("id") for body in bodies}
    if None in prediction_ids or len(prediction_ids) != 1:
        return fail(
            "동시 요청이 서로 다른 prediction id를 반환했습니다.",
            bodies,
        )

    record_ids = {body.get("record_id") for body in bodies}
    if record_ids != {args.record_id}:
        return fail("record_id가 예상과 다릅니다.", bodies)

    model_names = {body.get("ai_model") for body in bodies}
    if model_names != {args.model_name}:
        return fail("ai_model이 예상과 다릅니다.", bodies)

    query = urlencode({"page": 1, "size": 100})
    list_status, list_body = request_json(
        method="GET",
        url=(
            f"{args.base_url.rstrip('/')}"
            f"/api/v1/medical-records/{args.record_id}/ai-predictions"
            f"?{query}"
        ),
        token=args.token,
        timeout=args.timeout,
    )

    print("\n예측 목록 응답:")
    print(
        json.dumps(
            {"status": list_status, "body": list_body},
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    if list_status != 200 or not isinstance(list_body, dict):
        return fail("예측 목록 조회에 실패했습니다.", list_body)

    predictions = list_body.get("predictions")
    if not isinstance(predictions, list):
        return fail("목록 응답에 predictions 배열이 없습니다.", list_body)

    matching = [
        prediction
        for prediction in predictions
        if isinstance(prediction, dict)
        and prediction.get("record_id") == args.record_id
        and prediction.get("ai_model") == args.model_name
    ]

    if len(matching) != 1:
        return fail(
            "record_id + ai_model 조합의 DB 결과가 정확히 한 행이어야 합니다.",
            matching,
        )

    returned_id = next(iter(prediction_ids))
    if matching[0].get("id") != returned_id:
        return fail(
            "POST 응답과 목록 조회의 prediction id가 다릅니다.",
            {"post_id": returned_id, "list_row": matching[0]},
        )

    cached_values = [body.get("cached") for body in bodies]
    print("\n성공: 동시 요청이 하나의 예측 결과로 수렴했습니다.")
    print(f"prediction id: {returned_id}")
    print(f"cached 값: {cached_values}")

    if cached_values == [True, True]:
        print(
            "참고: 두 요청 모두 cached=True입니다. "
            "이 record_id에는 테스트 전에 이미 결과가 있었을 가능성이 큽니다."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
