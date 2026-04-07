import base64
import hashlib
import hmac
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote, unquote, urlparse

from auth.totp_store import TotpStore

SUPPORTED_ALGORITHMS = {
    "SHA1": hashlib.sha1,
    "SHA256": hashlib.sha256,
    "SHA512": hashlib.sha512,
}


class TotpService:
    def __init__(self, totp_store: TotpStore, issuer_name: str = "Tool Hub"):
        self.totp_store = totp_store
        self.issuer_name = issuer_name

    def list_accounts(self, user_id: str, include_secret: bool = False) -> List[Dict]:
        accounts = self.totp_store.list_accounts(user_id)
        now = int(time.time())
        return [self._build_view(item, now, include_secret=include_secret) for item in accounts]

    def get_account(self, user_id: str, account_id: str, include_secret: bool = True) -> Optional[Dict]:
        accounts = self.totp_store.list_accounts(user_id)
        now = int(time.time())
        for item in accounts:
            if item["id"] == account_id:
                return self._build_view(item, now, include_secret=include_secret)
        return None

    def create_account(self, user_id: str, payload: Dict) -> Dict:
        account = self._normalize_payload(payload)
        accounts = self.totp_store.list_accounts(user_id)
        accounts.insert(0, account)
        self.totp_store.save_accounts(user_id, accounts)
        return self._build_view(account, int(time.time()), include_secret=True)

    def update_account(self, user_id: str, account_id: str, payload: Dict) -> Dict:
        normalized = self._normalize_payload(payload, existing_id=account_id)
        accounts = self.totp_store.list_accounts(user_id)
        for index, current in enumerate(accounts):
            if current["id"] == account_id:
                normalized["createdAt"] = current["createdAt"]
                accounts[index] = normalized
                self.totp_store.save_accounts(user_id, accounts)
                return self._build_view(normalized, int(time.time()), include_secret=True)
        raise ValueError("账号不存在")

    def delete_account(self, user_id: str, account_id: str) -> bool:
        accounts = self.totp_store.list_accounts(user_id)
        new_accounts = [item for item in accounts if item["id"] != account_id]
        if len(new_accounts) == len(accounts):
            raise ValueError("账号不存在")
        self.totp_store.save_accounts(user_id, new_accounts)
        return True

    def import_accounts(self, user_id: str, payload: Dict) -> Dict:
        raw_text = (payload.get("text") or "").strip()
        items = payload.get("items") or []
        merge_mode = payload.get("mergeMode") or "append"
        parsed_items = []

        if raw_text:
            parsed_items.extend(self._parse_import_text(raw_text))
        for item in items:
            parsed_items.append(self._normalize_payload(item))

        if not parsed_items:
            raise ValueError("没有可导入的账号")

        accounts = self.totp_store.list_accounts(user_id)
        if merge_mode == "replace":
            next_accounts = parsed_items
        else:
            signatures = {self._signature(item) for item in accounts}
            next_accounts = list(accounts)
            for item in parsed_items:
                signature = self._signature(item)
                if signature not in signatures:
                    next_accounts.append(item)
                    signatures.add(signature)
        self.totp_store.save_accounts(user_id, next_accounts)
        return {
            "imported": len(parsed_items),
            "total": len(next_accounts),
            "items": [self._build_view(item, int(time.time()), include_secret=True) for item in parsed_items],
        }

    def export_accounts(self, user_id: str, export_format: str) -> Dict:
        accounts = self.totp_store.list_accounts(user_id)
        if export_format == "otpauth":
            lines = [self._build_otpauth_uri(item) for item in accounts]
            return {"format": "otpauth", "content": "\n".join(lines)}
        if export_format == "json":
            items = [self._build_view(item, int(time.time()), include_secret=True) for item in accounts]
            return {"format": "json", "content": items}
        raise ValueError("不支持的导出格式")

    def _parse_import_text(self, raw_text: str) -> List[Dict]:
        stripped = raw_text.strip()
        if stripped.startswith("["):
            import json

            payload = json.loads(stripped)
            return [self._normalize_payload(item) for item in payload]

        result = []
        for line in stripped.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("otpauth-migration://"):
                result.extend(self._normalize_payload(item) for item in self._parse_migration_uri(line))
            else:
                result.append(self._normalize_payload({"otpauthUri": line}))
        return result

    def _normalize_payload(self, payload: Dict, existing_id: Optional[str] = None) -> Dict:
        if payload.get("otpauthUri"):
            uri = payload["otpauthUri"].strip()
            if uri.startswith("otpauth-migration://"):
                parsed_items = self._parse_migration_uri(uri)
                if len(parsed_items) != 1:
                    raise ValueError("Google 导出二维码包含多个账号，请使用导入功能而不是单条创建")
                parsed = parsed_items[0]
            else:
                parsed = self._parse_otpauth_uri(uri)
        else:
            parsed = dict(payload)

        secret = self._normalize_secret(parsed.get("secret", ""))
        if not secret:
            raise ValueError("secret 不能为空")

        issuer = (parsed.get("issuer") or "").strip() or self.issuer_name
        account_name = (parsed.get("accountName") or parsed.get("account_name") or "").strip()
        label = (parsed.get("label") or "").strip()
        if not label:
            label = f"{issuer} ({account_name})" if account_name else issuer

        algorithm = str(parsed.get("algorithm") or "SHA1").upper()
        if algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError("仅支持 SHA1 / SHA256 / SHA512")

        digits = int(parsed.get("digits") or 6)
        if digits not in (6, 8):
            raise ValueError("digits 仅支持 6 或 8")

        period = int(parsed.get("period") or 30)
        if period <= 0:
            raise ValueError("period 必须大于 0")

        now = datetime.now().isoformat()
        return {
            "id": existing_id or f"totp_{uuid.uuid4().hex[:10]}",
            "label": label,
            "issuer": issuer,
            "accountName": account_name,
            "secret": secret,
            "digits": digits,
            "period": period,
            "algorithm": algorithm,
            "createdAt": now,
            "updatedAt": now,
        }

    def _parse_otpauth_uri(self, uri: str) -> Dict:
        parsed = urlparse(uri.strip())
        if parsed.scheme != "otpauth" or parsed.netloc.lower() != "totp":
            raise ValueError("仅支持 otpauth://totp/ 链接")

        label_segment = unquote(parsed.path.lstrip("/"))
        issuer_from_label = ""
        account_name = label_segment
        if ":" in label_segment:
            issuer_from_label, account_name = [part.strip() for part in label_segment.split(":", 1)]

        query = parse_qs(parsed.query)
        issuer = (query.get("issuer", [issuer_from_label])[0] or issuer_from_label).strip()
        return {
            "label": label_segment or account_name or issuer,
            "issuer": issuer or self.issuer_name,
            "accountName": account_name.strip(),
            "secret": query.get("secret", [""])[0],
            "digits": query.get("digits", ["6"])[0],
            "period": query.get("period", ["30"])[0],
            "algorithm": query.get("algorithm", ["SHA1"])[0],
        }

    def _parse_migration_uri(self, uri: str) -> List[Dict]:
        parsed = urlparse(uri.strip())
        if parsed.scheme != "otpauth-migration" or parsed.netloc.lower() != "offline":
            raise ValueError("Google 导出二维码格式不正确")

        data = parse_qs(parsed.query).get("data", [""])[0]
        if not data:
            raise ValueError("Google 导出二维码缺少 data 参数")

        payload = self._urlsafe_b64decode(data)
        migration = self._parse_proto_message(payload)
        result: List[Dict] = []

        for field_no, wire_type, value in migration:
            if field_no != 1 or wire_type != 2:
                continue
            otp_fields = self._parse_proto_message(value)
            item = self._build_migration_account(otp_fields)
            if item:
                result.append(item)

        if not result:
            raise ValueError("未从 Google 导出二维码中解析到 TOTP 账号")
        return result

    def _build_migration_account(self, fields: List[Tuple[int, int, object]]) -> Optional[Dict]:
        secret = ""
        account_name = ""
        issuer = ""
        algorithm = "SHA1"
        digits = 6
        otp_type = 2

        for field_no, wire_type, value in fields:
            if field_no == 1 and wire_type == 2:
                secret = base64.b32encode(value).decode("ascii").rstrip("=")
            elif field_no == 2 and wire_type == 2:
                account_name = value.decode("utf-8", errors="ignore")
            elif field_no == 3 and wire_type == 2:
                issuer = value.decode("utf-8", errors="ignore")
            elif field_no == 4 and wire_type == 0:
                algorithm = self._map_migration_algorithm(int(value))
            elif field_no == 5 and wire_type == 0:
                digits = self._map_migration_digits(int(value))
            elif field_no == 6 and wire_type == 0:
                otp_type = int(value)

        if otp_type != 2:
            return None

        label = f"{issuer}:{account_name}".strip(":") or account_name or issuer or self.issuer_name
        return {
            "label": label,
            "issuer": issuer or self.issuer_name,
            "accountName": account_name,
            "secret": secret,
            "digits": digits,
            "period": 30,
            "algorithm": algorithm,
        }

    def _parse_proto_message(self, data: bytes) -> List[Tuple[int, int, object]]:
        index = 0
        fields: List[Tuple[int, int, object]] = []
        while index < len(data):
            key, index = self._read_varint(data, index)
            field_no = key >> 3
            wire_type = key & 0x07

            if wire_type == 0:
                value, index = self._read_varint(data, index)
            elif wire_type == 2:
                length, index = self._read_varint(data, index)
                value = data[index:index + length]
                index += length
            else:
                raise ValueError("Google 导出二维码包含暂不支持的字段类型")

            fields.append((field_no, wire_type, value))
        return fields

    def _read_varint(self, data: bytes, index: int) -> Tuple[int, int]:
        result = 0
        shift = 0
        while index < len(data):
            byte = data[index]
            index += 1
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                return result, index
            shift += 7
        raise ValueError("Google 导出二维码数据损坏")

    def _urlsafe_b64decode(self, value: str) -> bytes:
        padding = "=" * ((4 - len(value) % 4) % 4)
        try:
            return base64.urlsafe_b64decode(value + padding)
        except Exception as exc:
            raise ValueError("Google 导出二维码 data 不是合法 Base64") from exc

    def _map_migration_algorithm(self, value: int) -> str:
        mapping = {
            1: "SHA1",
            2: "SHA256",
            3: "SHA512",
            4: "SHA1",
        }
        return mapping.get(value, "SHA1")

    def _map_migration_digits(self, value: int) -> int:
        mapping = {
            1: 6,
            2: 8,
        }
        return mapping.get(value, 6)

    def _normalize_secret(self, secret: str) -> str:
        normalized = "".join(secret.strip().split()).upper().rstrip("=")
        if not normalized:
            return ""
        padding = "=" * ((8 - len(normalized) % 8) % 8)
        try:
            base64.b32decode(normalized + padding, casefold=True)
        except Exception as exc:
            raise ValueError("secret 不是合法的 Base32") from exc
        return normalized

    def _build_otpauth_uri(self, item: Dict) -> str:
        label = quote(f"{item['issuer']}:{item['accountName']}" if item["accountName"] else item["label"])
        return (
            f"otpauth://totp/{label}"
            f"?secret={item['secret']}"
            f"&issuer={quote(item['issuer'])}"
            f"&algorithm={item['algorithm']}"
            f"&digits={item['digits']}"
            f"&period={item['period']}"
        )

    def _build_view(self, item: Dict, now_ts: int, include_secret: bool) -> Dict:
        code, remaining = self._generate_code(item, now_ts)
        view = {
            "id": item["id"],
            "label": item["label"],
            "issuer": item["issuer"],
            "accountName": item["accountName"],
            "digits": item["digits"],
            "period": item["period"],
            "algorithm": item["algorithm"],
            "createdAt": item["createdAt"],
            "updatedAt": item["updatedAt"],
            "code": code,
            "secondsRemaining": remaining,
            "secretMasked": self._mask_secret(item["secret"]),
        }
        if include_secret:
            view["secret"] = item["secret"]
            view["otpauthUri"] = self._build_otpauth_uri(item)
        return view

    def _generate_code(self, item: Dict, now_ts: int) -> Tuple[str, int]:
        period = int(item["period"])
        counter = now_ts // period
        remaining = period - (now_ts % period)
        secret = item["secret"]
        padding = "=" * ((8 - len(secret) % 8) % 8)
        key = base64.b32decode(secret + padding, casefold=True)
        counter_bytes = counter.to_bytes(8, "big")
        digest = hmac.new(key, counter_bytes, SUPPORTED_ALGORITHMS[item["algorithm"]]).digest()
        offset = digest[-1] & 0x0F
        binary_code = (
                ((digest[offset] & 0x7F) << 24)
                | ((digest[offset + 1] & 0xFF) << 16)
                | ((digest[offset + 2] & 0xFF) << 8)
                | (digest[offset + 3] & 0xFF)
        )
        digits = int(item["digits"])
        code = str(binary_code % (10 ** digits)).zfill(digits)
        return code, remaining

    def _signature(self, item: Dict) -> str:
        return f"{item['issuer']}|{item['accountName']}|{item['secret']}|{item['digits']}|{item['period']}|{item['algorithm']}"

    def _mask_secret(self, secret: str) -> str:
        if len(secret) <= 8:
            return secret
        return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"
