from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ERROR_ENDPOINTS = {
    "runtime_exception": "/test/errors/runtime-exception",
    "database_connection_failure": "/test/errors/db-connection",
    "database_slow_query": "/test/errors/db-slow-query",
    "validation_error": "/test/errors/validation",
    "inventory_mismatch": "/test/errors/inventory-mismatch",
    "payment_timeout": "/test/errors/payment-timeout",
    "payment_declined": "/test/errors/payment-declined",
    "configuration_error": "/test/errors/config-missing",
    "background_job_failure": "/test/errors/background-job-failure",
}

NORMAL_ACTIONS = [
    "health",
    "ready",
    "list_products",
    "create_user",
    "create_product",
    "create_order",
    "simulate_payment",
    "list_orders",
]


@dataclass
class ApiResult:
    method: str
    path: str
    status_code: int | None
    body: Any
    error: str | None = None


@dataclass
class TrafficState:
    users: list[int] = field(default_factory=list)
    products: list[int] = field(default_factory=list)
    created_orders: list[int] = field(default_factory=list)
    request_sequence: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate normal and error traffic for the demo order service."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for the FastAPI backend.",
    )
    parser.add_argument(
        "--requests-per-minute",
        type=float,
        default=30,
        help="Approximate request rate.",
    )
    parser.add_argument(
        "--error-rate",
        type=float,
        default=0.25,
        help="Probability from 0.0 to 1.0 that each request is an error injection.",
    )
    parser.add_argument(
        "--duration-seconds",
        type=float,
        default=None,
        help="Stop after this many seconds. Omit for continuous mode.",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=None,
        help="Stop after this many requests. Useful for smoke tests.",
    )
    parser.add_argument(
        "--error-categories",
        default="all",
        help=(
            "Comma-separated error categories to generate, or 'all'. "
            f"Available: {', '.join(ERROR_ENDPOINTS)}"
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5,
        help="HTTP timeout per request.",
    )
    parser.add_argument(
        "--seed-users",
        type=int,
        default=2,
        help="Users to create before the main traffic loop.",
    )
    parser.add_argument(
        "--no-startup-check",
        action="store_true",
        help="Skip initial health/readiness/product checks.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every generated request.",
    )
    args = parser.parse_args()

    if args.requests_per_minute <= 0:
        parser.error("--requests-per-minute must be greater than zero")

    if not 0 <= args.error_rate <= 1:
        parser.error("--error-rate must be between 0.0 and 1.0")

    if args.max_requests is not None and args.max_requests <= 0:
        parser.error("--max-requests must be greater than zero")

    return args


def request_json(
    *,
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float,
) -> ApiResult:
    body_bytes = None
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Request-Id": f"traffic-{int(time.time() * 1000)}-{random.randint(1000, 9999)}",
    }

    if payload is not None:
        body_bytes = json.dumps(payload).encode("utf-8")

    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body_bytes,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return ApiResult(
                method=method,
                path=path,
                status_code=response.status,
                body=decode_body(response.read()),
            )
    except HTTPError as exc:
        return ApiResult(
            method=method,
            path=path,
            status_code=exc.code,
            body=decode_body(exc.read()),
        )
    except URLError as exc:
        return ApiResult(
            method=method,
            path=path,
            status_code=None,
            body=None,
            error=str(exc.reason),
        )


def decode_body(raw_body: bytes) -> Any:
    if not raw_body:
        return None

    text = raw_body.decode("utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def selected_error_categories(value: str) -> list[str]:
    if value.strip().lower() == "all":
        return list(ERROR_ENDPOINTS)

    categories = [item.strip() for item in value.split(",") if item.strip()]
    unknown_categories = sorted(set(categories) - set(ERROR_ENDPOINTS))
    if unknown_categories:
        raise ValueError(f"Unknown error categories: {', '.join(unknown_categories)}")

    if not categories:
        raise ValueError("At least one error category is required")

    return categories


def create_user(args: argparse.Namespace, state: TrafficState) -> ApiResult:
    state.request_sequence += 1
    suffix = f"{int(time.time() * 1000)}-{state.request_sequence}"
    result = request_json(
        base_url=args.base_url,
        method="POST",
        path="/users",
        payload={
            "email": f"traffic-{suffix}@example.com",
            "name": f"Traffic User {state.request_sequence}",
        },
        timeout_seconds=args.timeout_seconds,
    )
    if result.status_code == 201 and isinstance(result.body, dict):
        state.users.append(result.body["id"])
    return result


def create_product(args: argparse.Namespace, state: TrafficState) -> ApiResult:
    state.request_sequence += 1
    suffix = f"{int(time.time() * 1000)}-{state.request_sequence}"
    result = request_json(
        base_url=args.base_url,
        method="POST",
        path="/products",
        payload={
            "sku": f"SKU-TRAFFIC-{suffix}",
            "name": f"Traffic Product {state.request_sequence}",
            "price_cents": random.randint(500, 5000),
            "inventory_count": random.randint(25, 150),
        },
        timeout_seconds=args.timeout_seconds,
    )
    if result.status_code == 201 and isinstance(result.body, dict):
        state.products.append(result.body["id"])
    return result


def list_products(args: argparse.Namespace, state: TrafficState) -> ApiResult:
    result = request_json(
        base_url=args.base_url,
        method="GET",
        path="/products",
        timeout_seconds=args.timeout_seconds,
    )
    if result.status_code == 200 and isinstance(result.body, list):
        state.products = [product["id"] for product in result.body if "id" in product]
    return result


def create_order(args: argparse.Namespace, state: TrafficState) -> ApiResult:
    if not state.users:
        create_user(args, state)
    if not state.products:
        list_products(args, state)

    if not state.users or not state.products:
        return ApiResult(
            method="POST",
            path="/orders",
            status_code=None,
            body=None,
            error="Cannot create order without user and product state",
        )

    result = request_json(
        base_url=args.base_url,
        method="POST",
        path="/orders",
        payload={
            "user_id": random.choice(state.users),
            "product_id": random.choice(state.products),
            "quantity": random.randint(1, 2),
        },
        timeout_seconds=args.timeout_seconds,
    )
    if result.status_code == 201 and isinstance(result.body, dict):
        state.created_orders.append(result.body["id"])
    return result


def list_orders(args: argparse.Namespace, _: TrafficState) -> ApiResult:
    return request_json(
        base_url=args.base_url,
        method="GET",
        path="/orders",
        timeout_seconds=args.timeout_seconds,
    )


def simulate_payment(args: argparse.Namespace, _: TrafficState) -> ApiResult:
    return request_json(
        base_url=args.base_url,
        method="POST",
        path="/payments/simulate",
        payload={
            "amount_cents": random.randint(500, 10000),
            "outcome": "success",
        },
        timeout_seconds=args.timeout_seconds,
    )


def normal_action(args: argparse.Namespace, state: TrafficState) -> tuple[str, ApiResult]:
    action = random.choice(NORMAL_ACTIONS)

    if action == "health":
        result = request_json(
            base_url=args.base_url,
            method="GET",
            path="/health",
            timeout_seconds=args.timeout_seconds,
        )
    elif action == "ready":
        result = request_json(
            base_url=args.base_url,
            method="GET",
            path="/ready",
            timeout_seconds=args.timeout_seconds,
        )
    elif action == "list_products":
        result = list_products(args, state)
    elif action == "create_user":
        result = create_user(args, state)
    elif action == "create_product":
        result = create_product(args, state)
    elif action == "create_order":
        result = create_order(args, state)
    elif action == "simulate_payment":
        result = simulate_payment(args, state)
    else:
        result = list_orders(args, state)

    return action, result


def error_action(
    args: argparse.Namespace,
    error_categories: list[str],
) -> tuple[str, ApiResult]:
    category = random.choice(error_categories)
    result = request_json(
        base_url=args.base_url,
        method="POST",
        path=ERROR_ENDPOINTS[category],
        payload={},
        timeout_seconds=args.timeout_seconds,
    )
    return category, result


def startup_check(args: argparse.Namespace, state: TrafficState) -> None:
    checks = [
        request_json(
            base_url=args.base_url,
            method="GET",
            path="/health",
            timeout_seconds=args.timeout_seconds,
        ),
        request_json(
            base_url=args.base_url,
            method="GET",
            path="/ready",
            timeout_seconds=args.timeout_seconds,
        ),
        list_products(args, state),
    ]
    failed_checks = [
        check for check in checks if check.status_code is None or check.status_code >= 400
    ]
    if failed_checks:
        failure_details = ", ".join(
            f"{check.method} {check.path} status={check.status_code or 'connection_error'}"
            for check in failed_checks
        )
        raise RuntimeError(
            f"Startup checks failed against {args.base_url}. "
            f"Failures: {failure_details}. Ensure the FastAPI server is running."
        )


def print_result(label: str, result: ApiResult) -> None:
    status = result.status_code if result.status_code is not None else "connection_error"
    print(f"{datetime.now(timezone.utc).isoformat()} {label} {result.method} {result.path} {status}")


def run() -> int:
    args = parse_args()
    try:
        error_categories = selected_error_categories(args.error_categories)
    except ValueError as exc:
        print(f"Invalid configuration: {exc}")
        return 2

    state = TrafficState()
    stats: Counter[str] = Counter()
    interval_seconds = 60 / args.requests_per_minute
    started_at = time.monotonic()

    print(
        "Starting traffic generation "
        f"base_url={args.base_url} rpm={args.requests_per_minute} "
        f"error_rate={args.error_rate} duration={args.duration_seconds or 'continuous'} "
        f"max_requests={args.max_requests or 'none'}"
    )

    if not args.no_startup_check:
        startup_check(args, state)
        stats["startup_checks"] += 1

    for _ in range(args.seed_users):
        result = create_user(args, state)
        stats["seed_user_attempts"] += 1
        if result.status_code == 201:
            stats["seed_users_created"] += 1
        if args.verbose:
            print_result("seed_user", result)

    request_count = 0
    try:
        while True:
            if args.duration_seconds is not None:
                if time.monotonic() - started_at >= args.duration_seconds:
                    break
            if args.max_requests is not None and request_count >= args.max_requests:
                break

            should_inject_error = random.random() < args.error_rate
            if should_inject_error:
                label, result = error_action(args, error_categories)
                stats[f"error.{label}"] += 1
            else:
                label, result = normal_action(args, state)
                stats[f"normal.{label}"] += 1

            request_count += 1
            stats["requests"] += 1

            if result.error:
                stats["connection_errors"] += 1
            elif result.status_code is not None and result.status_code >= 500:
                stats["http_5xx"] += 1
            elif result.status_code is not None and result.status_code >= 400:
                stats["http_4xx"] += 1
            else:
                stats["http_2xx_3xx"] += 1

            if args.verbose:
                print_result(label, result)

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nTraffic generation interrupted.")
    finally:
        elapsed_seconds = round(time.monotonic() - started_at, 2)
        print("\nTraffic generation summary")
        print(f"elapsed_seconds={elapsed_seconds}")
        print(f"requests={stats['requests']}")
        print(f"users_cached={len(state.users)}")
        print(f"products_cached={len(state.products)}")
        print(f"orders_created={len(state.created_orders)}")
        for key in sorted(stats):
            print(f"{key}={stats[key]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
