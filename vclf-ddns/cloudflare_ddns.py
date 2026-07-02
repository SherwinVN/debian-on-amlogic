#!/usr/bin/env python3
"""
cloudflare_ddns.py
-------------------
Service cập nhật IP (Dynamic DNS) cho domain trên Cloudflare.

Cách dùng nhanh:
    updater = CloudflareDNSUpdater(api_token="xxx")
    updater.sync(["home.example.com", "vpn.example.com"])

Hoặc chạy trực tiếp qua CLI:
    python3 cloudflare_ddns.py --config config.json
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("cf-ddns")

CF_API_BASE = "https://api.cloudflare.com/client/v4"

# Các dịch vụ trả về IP public của server, thử lần lượt nếu cái đầu lỗi
IP_ECHO_SERVICES = {
    "A": ["https://api.ipify.org", "https://ipv4.icanhazip.com"],
    "AAAA": ["https://api6.ipify.org", "https://ipv6.icanhazip.com"],
}


class CloudflareAPIError(Exception):
    """Lỗi khi gọi Cloudflare API."""


class IPStateCache:
    """
    Lưu lại IP lần cập nhật gần nhất vào 1 file JSON local.
    Dùng để so sánh trước khi gọi Cloudflare API -> tránh gọi API liên tục
    khi IP không đổi.
    """

    def __init__(self, path: str = "last_ip.json"):
        self.path = Path(path)

    def load(self, record_type: str) -> Optional[str]:
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return data.get(record_type)

    def save(self, record_type: str, ip: str) -> None:
        data = {}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
        data[record_type] = ip
        data[f"{record_type}_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class CloudflareDNSUpdater:
    """
    Service tái sử dụng để cập nhật bản ghi DNS (IP) cho domain trên Cloudflare.

    Chỉ cần truyền vào api_token khi khởi tạo, sau đó gọi update()/sync()
    cho bất kỳ domain nào (miễn domain đó thuộc tài khoản Cloudflare của token).
    """

    def __init__(self, api_token: str, timeout: int = 10):
        if not api_token:
            raise ValueError("api_token không được để trống")
        self.api_token = api_token
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            }
        )
        self._zone_cache: dict[str, str] = {}

    # ---------- Public IP ----------

    def get_public_ip(self, record_type: str = "A") -> str:
        """Lấy IP public hiện tại của server (IPv4 mặc định, IPv6 nếu record_type=AAAA)."""
        errors = []
        for url in IP_ECHO_SERVICES.get(record_type, IP_ECHO_SERVICES["A"]):
            try:
                resp = requests.get(url, timeout=self.timeout)
                resp.raise_for_status()
                ip = resp.text.strip()
                if ip:
                    return ip
            except requests.RequestException as e:
                errors.append(f"{url}: {e}")
        raise CloudflareAPIError(f"Không lấy được IP public. Chi tiết: {errors}")

    # ---------- Cloudflare helpers ----------

    def _root_domain(self, fqdn: str) -> str:
        """home.example.com -> example.com (giả định zone là 2 phần cuối, TLD phổ biến)."""
        parts = fqdn.strip(".").split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else fqdn

    def get_zone_id(self, domain: str) -> str:
        """Lấy Zone ID theo domain gốc, có cache lại để tránh gọi API lặp."""
        root = self._root_domain(domain)
        if root in self._zone_cache:
            return self._zone_cache[root]

        resp = self.session.get(f"{CF_API_BASE}/zones", params={"name": root}, timeout=self.timeout)
        data = self._handle_response(resp)
        results = data.get("result") or []
        if not results:
            raise CloudflareAPIError(f"Không tìm thấy zone cho domain '{root}' trong tài khoản Cloudflare này")

        zone_id = results[0]["id"]
        self._zone_cache[root] = zone_id
        return zone_id

    def get_record(self, domain: str, record_type: str = "A") -> Optional[dict]:
        """Lấy bản ghi DNS hiện tại của domain (None nếu chưa tồn tại)."""
        zone_id = self.get_zone_id(domain)
        resp = self.session.get(
            f"{CF_API_BASE}/zones/{zone_id}/dns_records",
            params={"type": record_type, "name": domain},
            timeout=self.timeout,
        )
        data = self._handle_response(resp)
        results = data.get("result") or []
        return results[0] if results else None

    def update(
        self,
        domain: str,
        ip: Optional[str] = None,
        record_type: str = "A",
        proxied: bool = False,
        ttl: int = 1,
    ) -> bool:
        """
        Cập nhật (hoặc tạo mới nếu chưa có) bản ghi DNS cho domain.
        - ip=None -> tự động lấy IP public hiện tại của server.
        - Trả về True nếu có thay đổi, False nếu IP không đổi (bỏ qua).
        """
        ip = ip or self.get_public_ip(record_type)
        zone_id = self.get_zone_id(domain)
        record = self.get_record(domain, record_type)

        payload = {
            "type": record_type,
            "name": domain,
            "content": ip,
            "ttl": ttl,
            "proxied": proxied,
        }

        if record is None:
            # Chưa có bản ghi -> tạo mới
            resp = self.session.post(
                f"{CF_API_BASE}/zones/{zone_id}/dns_records", json=payload, timeout=self.timeout
            )
            self._handle_response(resp)
            log.info(f"[{domain}] Đã tạo bản ghi {record_type} mới -> {ip}")
            return True

        if record["content"] == ip:
            log.info(f"[{domain}] IP không đổi ({ip}), bỏ qua")
            return False

        resp = self.session.put(
            f"{CF_API_BASE}/zones/{zone_id}/dns_records/{record['id']}",
            json=payload,
            timeout=self.timeout,
        )
        self._handle_response(resp)
        log.info(f"[{domain}] Cập nhật IP: {record['content']} -> {ip}")
        return True

    def sync(self, domains: list[str], record_type: str = "A", proxied: bool = False, ttl: int = 1) -> dict:
        """Cập nhật IP cho nhiều domain cùng lúc, dùng chung 1 token."""
        ip = self.get_public_ip(record_type)
        results = {}
        for domain in domains:
            try:
                results[domain] = self.update(domain, ip=ip, record_type=record_type, proxied=proxied, ttl=ttl)
            except CloudflareAPIError as e:
                log.error(f"[{domain}] Lỗi: {e}")
                results[domain] = False
        return results

    def check_and_sync(
        self,
        domains: list[str],
        cache: IPStateCache,
        record_type: str = "A",
        proxied: bool = False,
        ttl: int = 1,
    ) -> dict:
        """
        So sánh IP hiện tại với IP đã lưu trong cache local.
        - Nếu IP KHÔNG đổi -> không gọi Cloudflare API (kể cả get_record), chỉ log rồi bỏ qua.
        - Nếu IP đổi -> gọi sync() để cập nhật tất cả domain, rồi lưu IP mới vào cache.
        """
        current_ip = self.get_public_ip(record_type)
        cached_ip = cache.load(record_type)

        if cached_ip == current_ip:
            log.info(f"IP hiện tại ({current_ip}) không đổi so với lần trước -> bỏ qua, không gọi Cloudflare API")
            return {}

        log.info(f"Phát hiện IP thay đổi: {cached_ip} -> {current_ip}. Đang cập nhật {len(domains)} domain...")
        results = self.sync(domains, record_type=record_type, proxied=proxied, ttl=ttl)
        cache.save(record_type, current_ip)
        return results

    # ---------- internal ----------

    @staticmethod
    def _handle_response(resp: requests.Response) -> dict:
        try:
            data = resp.json()
        except ValueError:
            resp.raise_for_status()
            raise CloudflareAPIError("Cloudflare trả về dữ liệu không hợp lệ")

        if not data.get("success", False):
            errors = data.get("errors")
            raise CloudflareAPIError(f"Cloudflare API lỗi: {errors}")
        return data


# ---------------- CLI ----------------

def load_config(path: str) -> dict:
    cfg_path = Path(path)
    if not cfg_path.exists():
        log.error(f"Không tìm thấy file config: {path}")
        sys.exit(1)
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cập nhật IP cho domain trên Cloudflare (Dynamic DNS)")
    parser.add_argument("--config", default="config.json", help="Đường dẫn file config JSON")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Chỉ chạy 1 lần rồi thoát, bỏ qua check_interval trong config (dùng cho cron/systemd timer)",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    updater = CloudflareDNSUpdater(api_token=cfg["api_token"])

    domains = cfg["domains"]
    record_type = cfg.get("record_type", "A")
    proxied = cfg.get("proxied", False)
    ttl = cfg.get("ttl", 1)
    check_interval = int(cfg.get("check_interval", 0))  # giây; 0 = chỉ chạy 1 lần

    # File cache lưu IP gần nhất, mặc định đặt cạnh config.json
    default_state_path = str(Path(args.config).resolve().parent / "last_ip.json")
    cache = IPStateCache(cfg.get("state_file", default_state_path))

    def run_once():
        updater.check_and_sync(domains, cache, record_type=record_type, proxied=proxied, ttl=ttl)

    if args.once or check_interval <= 0:
        run_once()
    else:
        log.info(f"Chạy dạng daemon, kiểm tra IP mỗi {check_interval} giây (Ctrl+C để dừng)")
        while True:
            try:
                run_once()
            except CloudflareAPIError as e:
                log.error(f"Lỗi trong lần check: {e}")
            time.sleep(check_interval)


if __name__ == "__main__":
    main()
