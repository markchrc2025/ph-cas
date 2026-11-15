"""Private object storage for the tutorial videos (S3 API, signature version 4).

The videos live once, in one private bucket on the Sentire server (RustFS at
s3.sentire.solutions); every Sentire Ledger site plays from it. Nothing in the bucket is public:
the player gets a link signed for a few hours each time someone presses play.

Connection, read from the container's environment (Dokploy writes it with create_storage), or
from site config `ph_videos_s3` (a dict with the same keys in lower case, without the prefix):

    PH_VIDEOS_S3_ENDPOINT, PH_VIDEOS_S3_REGION, PH_VIDEOS_S3_BUCKET,
    PH_VIDEOS_S3_ACCESS_KEY_ID, PH_VIDEOS_S3_SECRET_ACCESS_KEY
    PH_VIDEOS_S3_PUBLIC_ENDPOINT (optional): the address browsers use, when the server reaches the
    bucket by an internal one. Playback links are signed for it.

Path-style addressing only. A small hand-written client (no boto3) so the image needs no new
dependency: presigned GET for playback, header-signed requests for uploads.
"""

import datetime
import hashlib
import hmac
import os
from urllib.parse import quote, urlsplit
from xml.etree import ElementTree

import frappe
import requests

PREFIX = "PH_VIDEOS_S3_"
KEYS = ("endpoint", "region", "bucket", "access_key_id", "secret_access_key")
UNSIGNED = "UNSIGNED-PAYLOAD"
EMPTY_SHA = hashlib.sha256(b"").hexdigest()


class NotConfigured(Exception):
    pass


def config() -> dict:
    conf = {k: os.environ.get(PREFIX + k.upper()) for k in KEYS}
    site = frappe.conf.get("ph_videos_s3") or {}
    for k in KEYS:
        conf[k] = conf[k] or site.get(k)
    conf["region"] = conf["region"] or "us-east-1"
    conf["public_endpoint"] = os.environ.get(PREFIX + "PUBLIC_ENDPOINT") or site.get("public_endpoint")
    return conf


def is_configured() -> bool:
    c = config()
    return all(c[k] for k in KEYS)


def client():
    c = config()
    missing = [PREFIX + k.upper() for k in KEYS if not c[k]]
    if missing:
        raise NotConfigured("Video storage is not set up on this server: " + ", ".join(missing))
    return S3(c["endpoint"], c["region"], c["bucket"], c["access_key_id"], c["secret_access_key"], public_endpoint=c["public_endpoint"])


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def _uri(path: str) -> str:
    return quote(path, safe="/-_.~")


def _query(params: dict) -> str:
    return "&".join(f"{quote(str(k), safe='-_.~')}={quote(str(v), safe='-_.~')}" for k, v in sorted(params.items()))


class S3:
    def __init__(self, endpoint, region, bucket, access_key, secret_key, session=None, public_endpoint=None):
        self.endpoint = endpoint.rstrip("/")
        self.host = urlsplit(self.endpoint).netloc
        self.public_endpoint = (public_endpoint or endpoint).rstrip("/")
        self.region = region
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.http = session or requests

    # signing --------------------------------------------------------------------------------
    def _path(self, key: str) -> str:
        if not self.bucket:  # virtual-hosted endpoint (only the AWS test vectors use this)
            return "/" + key
        return "/" + self.bucket + ("/" + key if key else "")

    def _scope(self, now):
        return f"{now:%Y%m%d}/{self.region}/s3/aws4_request"

    def _signature(self, now, canonical: str) -> str:
        to_sign = "\n".join(["AWS4-HMAC-SHA256", f"{now:%Y%m%dT%H%M%SZ}", self._scope(now), hashlib.sha256(canonical.encode()).hexdigest()])
        k = _sign(("AWS4" + self.secret_key).encode(), f"{now:%Y%m%d}")
        for part in (self.region, "s3", "aws4_request"):
            k = _sign(k, part)
        return hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()

    def presign(self, key: str, expires: int = 6 * 3600, method: str = "GET", now=None, extra: dict | None = None) -> str:
        now = now or datetime.datetime.now(datetime.UTC)
        params = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self.access_key}/{self._scope(now)}",
            "X-Amz-Date": f"{now:%Y%m%dT%H%M%SZ}",
            "X-Amz-Expires": str(expires),
            "X-Amz-SignedHeaders": "host",
        }
        params.update(extra or {})
        path = self._path(key)
        host = urlsplit(self.public_endpoint).netloc
        canonical = "\n".join([method, _uri(path), _query(params), f"host:{host}\n", "host", UNSIGNED])
        return f"{self.public_endpoint}{_uri(path)}?{_query(params)}&X-Amz-Signature={self._signature(now, canonical)}"

    def signed_headers(self, method, key, params, data, headers, now=None) -> dict:
        now = now or datetime.datetime.now(datetime.UTC)
        payload_hash = EMPTY_SHA if not data else UNSIGNED
        hdrs = {"host": self.host, "x-amz-content-sha256": payload_hash, "x-amz-date": f"{now:%Y%m%dT%H%M%SZ}"}
        for k, v in (headers or {}).items():
            hdrs[k.lower()] = str(v).strip()
        names = sorted(hdrs)
        path = self._path(key)
        canonical = "\n".join(
            [method, _uri(path), _query(params), "".join(f"{n}:{hdrs[n]}\n" for n in names), ";".join(names), payload_hash]
        )
        hdrs["authorization"] = (
            f"AWS4-HMAC-SHA256 Credential={self.access_key}/{self._scope(now)}, "
            f"SignedHeaders={';'.join(names)}, Signature={self._signature(now, canonical)}"
        )
        return hdrs

    def request(self, method: str, key: str = "", params: dict | None = None, data: bytes | None = None, headers: dict | None = None):
        params = params or {}
        hdrs = self.signed_headers(method, key, params, data, headers)
        send = {k: v for k, v in hdrs.items() if k != "host"}
        url = f"{self.endpoint}{_uri(self._path(key))}" + (f"?{_query(params)}" if params else "")
        r = self.http.request(method, url, data=data, headers=send, timeout=120)
        if r.status_code >= 300 and not (method == "HEAD" and r.status_code == 404):
            raise StorageError(f"{method} {key or self.bucket}: {r.status_code} {_s3_message(r)}")
        return r

    # operations -----------------------------------------------------------------------------
    def head(self, key: str) -> dict | None:
        r = self.request("HEAD", key)
        if r.status_code == 404:
            return None
        return {"size": int(r.headers.get("Content-Length") or 0), "etag": (r.headers.get("ETag") or "").strip('"')}

    def get(self, key: str) -> bytes:
        return self.request("GET", key).content

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.request("PUT", key, data=data, headers={"content-type": content_type})

    def start_multipart(self, key: str, content_type: str) -> str:
        r = self.request("POST", key, params={"uploads": ""}, headers={"content-type": content_type})
        return _xml_text(r.content, "UploadId")

    def upload_part(self, key: str, upload_id: str, number: int, data: bytes) -> str:
        r = self.request("PUT", key, params={"partNumber": number, "uploadId": upload_id}, data=data)
        return (r.headers.get("ETag") or "").strip('"')

    def complete_multipart(self, key: str, upload_id: str, etags: list[str]) -> None:
        parts = "".join(f"<Part><PartNumber>{i}</PartNumber><ETag>\"{e}\"</ETag></Part>" for i, e in enumerate(etags, 1))
        body = f"<CompleteMultipartUpload>{parts}</CompleteMultipartUpload>".encode()
        self.request("POST", key, params={"uploadId": upload_id}, data=body, headers={"content-type": "application/xml"})

    def abort_multipart(self, key: str, upload_id: str) -> None:
        self.request("DELETE", key, params={"uploadId": upload_id})


class StorageError(Exception):
    pass


def _xml_text(content: bytes, tag: str) -> str:
    root = ElementTree.fromstring(content)
    for el in root.iter():
        if el.tag.split("}")[-1] == tag:
            return el.text or ""
    raise StorageError(f"No {tag} in the storage reply")


def _s3_message(r) -> str:
    try:
        return _xml_text(r.content, "Message")
    except Exception:
        return (r.text or "")[:200]
