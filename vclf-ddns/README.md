# vclf-ddns (Cloudflare DDNS Service)

Service Python nhỏ gọn để tự động cập nhật IP cho domain trên Cloudflare (Dynamic DNS).
Chỉ cần khai báo **token** + **domain**, tái sử dụng cho nhiều domain cùng lúc.

## 1. Tạo Cloudflare API Token

Vào **Cloudflare Dashboard → My Profile → API Tokens → Create Token**, chọn quyền:
- `Zone.DNS` → **Edit**
- Áp dụng cho zone (domain) bạn muốn cập nhật

## 2. Cài đặt trên server

```bash
sudo mkdir -p /opt/vclf-ddns
sudo cp vclf_ddns.py config.example.json requirements.txt /opt/vclf-ddns/
cd /opt/vclf-ddns
sudo mv config.example.json config.json

python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Sửa `config.json`:

```json
{
  "api_token": "TOKEN_CUA_BAN",
  "domains": ["home.example.com", "vpn.example.com"],
  "record_type": "A",
  "proxied": false,
  "ttl": 1,
  "check_interval": 300,
  "state_file": "last_ip.json"
}
```

- `check_interval`: số giây giữa mỗi lần **kiểm tra** IP hiện tại (60 = 1 phút). Có thể để `30` nếu muốn phát hiện đổi IP gần như ngay lập tức — an toàn vì Cloudflare API chỉ được gọi khi IP thực sự đổi. Đặt `0` nếu chỉ muốn chạy 1 lần rồi thoát (dùng với cron).
- `state_file`: nơi lưu IP lần cập nhật gần nhất. Mặc định tự đặt cạnh `config.json`.

**Cơ chế hoạt động:** mỗi lần check, script lấy IP public hiện tại và so với IP đã lưu trong `state_file`.
- Nếu **giống nhau** → bỏ qua hoàn toàn, **không gọi Cloudflare API**.
- Nếu **khác nhau** → mới gọi Cloudflare API để cập nhật DNS, rồi lưu IP mới vào `state_file`.

→ Nhờ vậy có thể đặt `check_interval` rất ngắn (VD: 60 giây) mà không lo bị Cloudflare rate-limit, vì phần lớn thời gian IP không đổi và script không gọi API gì cả.

## 3. Chạy thử

```bash
./.venv/bin/python3 vclf_ddns.py --config config.json
```

Nếu `check_interval` trong config > 0, script sẽ tự chạy như daemon (lặp mãi, Ctrl+C để dừng).
Muốn ép chạy đúng 1 lần bất kể config (VD: test nhanh): thêm `--once`.

## 4. Chạy nền tự động

### Cách A — Daemon liên tục (khuyên dùng, kết hợp `check_interval`)

```bash
sudo cp vclf-ddns.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vclf-ddns.service

# Kiểm tra
systemctl status vclf-ddns.service
journalctl -u vclf-ddns.service -f
```

Service sẽ tự lặp kiểm tra IP theo đúng `check_interval` khai báo trong `config.json`.

### Cách B — Chạy 1 lần theo lịch (cron hoặc systemd timer)

Đặt `check_interval: 0` trong config, rồi để cron/timer gọi `--once` định kỳ:

```bash
crontab -e
# Chạy mỗi 5 phút:
*/5 * * * * /opt/vclf-ddns/.venv/bin/python3 /opt/vclf-ddns/vclf_ddns.py --config /opt/vclf-ddns/config.json --once >> /var/log/vclf-ddns.log 2>&1
```

Hoặc dùng `vclf-ddns.timer` đi kèm (chỉnh `ExecStart` trong `vclf-ddns.service` thêm `--once`, đổi `Type=simple` thành `Type=oneshot`, bỏ `Restart=always`, rồi enable `vclf-ddns.timer` thay vì `vclf-ddns.service`).

## 5. Dùng lại trong code khác (import trực tiếp)

```python
from vclf_ddns import CloudflareDNSUpdater

updater = CloudflareDNSUpdater(api_token="TOKEN_CUA_BAN")
updater.sync(["home.example.com", "vpn.example.com"])
```

## Ghi chú
- `proxied: false` — dùng cho DDNS (IP nhà/server thay đổi), vì Cloudflare Proxy (đám mây cam) không hợp với DDNS thường xuyên đổi IP.
- `record_type` hỗ trợ `A` (IPv4) hoặc `AAAA` (IPv6).
- Script tự tạo bản ghi DNS mới nếu domain chưa có, hoặc chỉ cập nhật khi IP thực sự thay đổi.
