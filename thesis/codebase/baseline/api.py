from datetime import datetime

_hits: dict = {}
_CAP = 100
_PG = 20


def authenticate(req: dict) -> dict:
    tok = req.get("headers", {}).get("Authorization", "")
    if not tok.startswith("Bearer "):
        raise ValueError("Unauthorized")
    return {"uid": "u_123", "role": "user"}


def throttle(key: str) -> None:
    now = datetime.now()
    k = f"{key}:{now.year}{now.month}{now.day}{now.hour}{now.minute}"
    n = _hits.get(k, 0)
    if n >= _CAP:
        raise ValueError("Rate limit exceeded")
    _hits[k] = n + 1


def paginate(items: list, page: int = 1) -> dict:
    start = (page - 1) * _PG
    return {
        "items": items[start:start + _PG],
        "page": page,
        "per_page": _PG,
        "total": len(items),
    }


def ep_invoices(req: dict, data: list) -> dict:
    user = authenticate(req)
    key = req.get("headers", {}).get("X-Key", "default")
    throttle(key)
    pg = int(req.get("q", {}).get("page", 1))
    return paginate([x for x in data if x.get("cid") == user["uid"]], pg)


def ep_payment(req: dict, data: list) -> dict:
    user = authenticate(req)
    key = req.get("headers", {}).get("X-Key", "default")
    throttle(key)
    body = req.get("body", {})
    rec = {"pid": f"p_{len(data)+1}", "cid": user["uid"],
           "val": body.get("val"), "ts": datetime.now().isoformat()}
    data.append(rec)
    return rec
