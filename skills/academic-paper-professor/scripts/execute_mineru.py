from __future__ import annotations

import argparse
import json
import os
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import requests


BASE_URL = "https://mineru.net"
URL_TASK_ENDPOINT = "/api/v4/extract/task"
URL_TASK_RESULT_ENDPOINT = "/api/v4/extract/task/{task_id}"
FILE_URLS_BATCH_ENDPOINT = "/api/v4/file-urls/batch"
EXTRACT_RESULTS_BATCH_ENDPOINT = "/api/v4/extract-results/batch/{batch_id}"
LOCAL_MINERU_TOKEN = ""

def resolve_token(cli_token: str | None) -> str:
    token = cli_token or os.environ.get("MINERU_TOKEN")
    if not token:
        raise SystemExit(
            "MinerU token is missing. Set MINERU_TOKEN or pass --token. "
            "Do not hard-code tokens in skill scripts."
        )
    return token


def headers(token: str, content_type: bool = True) -> dict:
    result = {"Authorization": f"Bearer {token}", "Accept": "*/*"}
    if content_type:
        result["Content-Type"] = "application/json"
    return result


def request_json(method: str, url: str, token: str, **kwargs) -> dict:
    response = requests.request(method, url, headers=headers(token), timeout=60, **kwargs)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") not in (0, None):
        raise RuntimeError(f"MinerU API error: {payload}")
    return payload


def redact_signed_urls(value):
    if isinstance(value, dict):
        return {key: redact_signed_urls(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_signed_urls(item) for item in value]
    if isinstance(value, str) and "?" in value and (
        "OSSAccessKeyId=" in value or "Signature=" in value or "Expires=" in value
    ):
        parsed = urlparse(value)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "<redacted-query>", ""))
    return value


def find_task_id(payload: dict) -> str:
    data = payload.get("data") or {}
    for key in ("task_id", "id"):
        if data.get(key):
            return str(data[key])
    if payload.get("task_id"):
        return str(payload["task_id"])
    raise RuntimeError(f"No task_id in response: {payload}")


def extract_result(payload: dict) -> dict:
    data = payload.get("data") or {}
    return data.get("extract_result") or data


def first_extract_result(payload: dict) -> dict:
    result = extract_result(payload)
    if isinstance(result, list):
        return result[0] if result and isinstance(result[0], dict) else {}
    return result if isinstance(result, dict) else {}


def state_of(payload: dict) -> str:
    return str(first_extract_result(payload).get("state") or payload.get("state") or "").lower()


def full_zip_url(payload: dict) -> str | None:
    result = first_extract_result(payload)
    return result.get("full_zip_url") or result.get("zip_url") or result.get("result_url")


def submit_url_task(token: str, pdf_url: str, options: dict) -> tuple[str, dict]:
    body = {"url": pdf_url, **options}
    payload = request_json("POST", BASE_URL + URL_TASK_ENDPOINT, token, json=body)
    return find_task_id(payload), payload


def poll_url_task(token: str, task_id: str, interval: int, timeout: int) -> tuple[dict, list[dict]]:
    deadline = time.time() + timeout
    history: list[dict] = []
    while True:
        payload = request_json(
            "GET",
            BASE_URL + URL_TASK_RESULT_ENDPOINT.format(task_id=task_id),
            token,
        )
        history.append(payload)
        state = state_of(payload)
        if state == "done":
            return payload, history
        if state == "failed":
            raise RuntimeError(f"MinerU task failed: {payload}")
        if time.time() >= deadline:
            raise TimeoutError(f"Timed out waiting for MinerU task {task_id}; last={payload}")
        print(f"poll {task_id}: {state or 'unknown'}")
        time.sleep(interval)


def request_batch_upload_url(
    token: str,
    pdf_path: Path,
    batch_options: dict,
    file_options: dict,
) -> tuple[str, str, dict]:
    body = {"files": [{"name": pdf_path.name, **file_options}], **batch_options}
    payload = request_json("POST", BASE_URL + FILE_URLS_BATCH_ENDPOINT, token, json=body)
    data = payload.get("data") or {}
    batch_id = data.get("batch_id")
    file_urls = data.get("file_urls") or data.get("files") or []
    if not batch_id or not file_urls:
        raise RuntimeError(f"No batch upload URL in response: {payload}")
    if isinstance(file_urls, dict):
        first = next(iter(file_urls.values()))
    else:
        first = file_urls[0]
    if isinstance(first, str):
        upload_url = first
    elif isinstance(first, dict):
        upload_url = first.get("upload_url") or first.get("url")
    else:
        raise RuntimeError(f"Unsupported upload URL entry in response: {payload}")
    if not upload_url:
        raise RuntimeError(f"No upload_url in response: {payload}")
    return str(batch_id), str(upload_url), payload


def upload_file(upload_url: str, pdf_path: Path) -> None:
    with pdf_path.open("rb") as handle:
        response = requests.put(upload_url, data=handle, timeout=300)
    response.raise_for_status()


def poll_batch(token: str, batch_id: str, interval: int, timeout: int) -> tuple[dict, list[dict]]:
    deadline = time.time() + timeout
    history: list[dict] = []
    while True:
        payload = request_json(
            "GET",
            BASE_URL + EXTRACT_RESULTS_BATCH_ENDPOINT.format(batch_id=batch_id),
            token,
        )
        history.append(payload)
        result = first_extract_result(payload)
        state = str(result.get("state") or "").lower()
        if state == "done" and full_zip_url(payload):
            return payload, history
        if state == "failed":
            raise RuntimeError(f"MinerU batch task failed: {payload}")
        if time.time() >= deadline:
            raise TimeoutError(f"Timed out waiting for MinerU batch {batch_id}; last={payload}")
        print(f"poll batch {batch_id}: {state or 'unknown'}")
        time.sleep(interval)


def download_and_extract(url: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / "mineru_result.zip"
    with requests.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with zip_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    extract_dir = out_dir / "result"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)
    return zip_path


def find_full_markdown(out_dir: Path) -> Path | None:
    matches = sorted(out_dir.rglob("full.md"))
    if matches:
        return matches[0]
    markdowns = sorted(out_dir.rglob("*.md"))
    return markdowns[0] if markdowns else None


def infer_pdf_url(path_or_url: str) -> str | None:
    parsed = urlparse(path_or_url)
    if parsed.scheme in ("http", "https"):
        return path_or_url
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Submit a PDF to MinerU async API, poll until done, and save all parsed data locally."
    )
    parser.add_argument("--paper-dir", required=True, help="Paper directory containing paper.pdf.")
    parser.add_argument("--pdf-url", help="Public PDF URL. If omitted, upload local paper.pdf through batch upload.")
    parser.add_argument("--pdf-path", help="Local PDF path. Defaults to <paper-dir>/paper.pdf.")
    parser.add_argument("--token", help="MinerU API token. Overrides MINERU_TOKEN and LOCAL_MINERU_TOKEN.")
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--is-ocr", action="store_true", help="Pass is_ocr=true when submitting.")
    parser.add_argument("--enable-formula", action="store_true")
    parser.add_argument("--enable-table", action="store_true")
    parser.add_argument("--language", default="")
    parser.add_argument("--model-version", default="vlm", help="MinerU model_version, e.g. pipeline or vlm.")
    args = parser.parse_args()

    token = resolve_token(args.token)

    paper_dir = Path(args.paper_dir).resolve()
    pdf_path = Path(args.pdf_path).resolve() if args.pdf_path else paper_dir / "paper.pdf"
    out_dir = paper_dir / "mineru"
    out_dir.mkdir(parents=True, exist_ok=True)

    options = {
        "is_ocr": bool(args.is_ocr),
        "enable_formula": bool(args.enable_formula),
        "enable_table": bool(args.enable_table),
        "model_version": args.model_version,
    }
    if args.language:
        options["language"] = args.language

    history: list[dict]
    submit_payload: dict
    if args.pdf_url or infer_pdf_url(str(pdf_path)):
        pdf_url = args.pdf_url or str(pdf_path)
        task_id, submit_payload = submit_url_task(token, pdf_url, options)
        final_payload, history = poll_url_task(token, task_id, args.interval, args.timeout)
        identifiers = {"task_id": task_id, "mode": "url"}
    else:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        batch_options = {
            "enable_formula": bool(args.enable_formula),
            "enable_table": bool(args.enable_table),
            "model_version": args.model_version,
        }
        if args.language:
            batch_options["language"] = args.language
        file_options = {"is_ocr": bool(args.is_ocr)}
        batch_id, upload_url, submit_payload = request_batch_upload_url(
            token, pdf_path, batch_options, file_options
        )
        upload_file(upload_url, pdf_path)
        final_payload, history = poll_batch(token, batch_id, args.interval, args.timeout)
        identifiers = {"batch_id": batch_id, "mode": "batch_upload"}

    zip_url = full_zip_url(final_payload)
    if not zip_url:
        raise RuntimeError(f"MinerU completed without full_zip_url: {final_payload}")
    zip_path = download_and_extract(zip_url, out_dir)
    full_md = find_full_markdown(out_dir)
    manifest = {
        **identifiers,
        "paper_dir": str(paper_dir),
        "pdf_path": str(pdf_path) if pdf_path.exists() else None,
        "pdf_url": args.pdf_url,
        "options": options,
        "submit_response": redact_signed_urls(submit_payload),
        "final_response": redact_signed_urls(final_payload),
        "poll_count": len(history),
        "full_zip_url": zip_url,
        "zip_path": str(zip_path),
        "full_markdown": str(full_md) if full_md else None,
    }
    (out_dir / "mineru_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "poll_history.json").write_text(
        json.dumps(redact_signed_urls(history), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(out_dir / "mineru_manifest.json")


if __name__ == "__main__":
    main()
