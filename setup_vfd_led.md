# Hướng dẫn Cấu hình Màn hình LED VFD (tm16xx) cho Tanix W2

Tài liệu này hướng dẫn cách sao lưu, chỉnh sửa, cài đặt script tùy biến hiển thị (phiên bản V5 nâng cao) và kiểm thử các hiệu ứng của màn hình LED phía trước thiết bị Tanix W2.

---

## 1. Sao lưu script nguyên bản đề phòng lỗi
Trước khi tiến hành thay đổi, hãy sao lưu lại script cấu hình mặc định. File sao lưu này sẽ được đính kèm trực tiếp tại thư mục `/usr/lib/tm16xx-display/` dưới tên `.sh.bak` để tiện cho việc khôi phục nhanh:
```bash
cp /usr/lib/tm16xx-display/display_service.sh /usr/lib/tm16xx-display/display_service.sh.bak
```

## 2. Tạo và cập nhật Script mới (Tùy biến V5 nâng cao)
Script này bao gồm:
* **Hiệu ứng khởi động:** Chạy số ngẫu nhiên dạng slot machine (`8888`) và hiệu ứng nhịp tim (`heartbeat` nhấp nháy chữ `TS2N`).
* **Hiển thị luân phiên:** Giờ (nháy dấu hai chấm) $\rightarrow$ RAM đã dùng/tổng $\rightarrow$ DISK đã dùng/tổng $\rightarrow$ Nhiệt độ CPU $\rightarrow$ Logo `TS2N`.
* **Hiệu ứng tắt nguồn (OFF):** Dịch chuyển ký tự và giảm dần độ sáng (`8888` $\rightarrow$ `0088` $\rightarrow$ `0008` $\rightarrow$ `0000` $\rightarrow$ trống hoàn toàn $\rightarrow$ tắt hẳn).

Chạy lệnh dưới đây để ghi đè cấu hình mới:
```bash
cat > /usr/lib/tm16xx-display/display_service.sh << 'SCRIPT_END'
#!/bin/bash
# (c) 2020 devmfc - customized v5
dev_path=$(dirname /sys/bus/platform/drivers/tm16xx*/*/digits)

set_icon() {
        local path="/sys/class/leds/tm16xx::$1/brightness"
        [[ -e $path ]] && echo "$2" > "$path" 2>/dev/null
}

slot_effect() {
        local final="$1"
        local delays=(0.03 0.03 0.04 0.04 0.05 0.06 0.07 0.08 0.09 0.10 0.12 0.14 0.16 0.20 0.25)
        for d in "${delays[@]}"; do
                r=$(( RANDOM % 10000 ))
                printf -v s "%04d" "$r"
                echo "$s" > $dev_path/digits
                sleep "$d"
        done
        echo "$final" > $dev_path/digits
        sleep 0.5
}

# Hiệu ứng nhịp tim: lub-dub-nghỉ, lặp lại vài lần, chữ TS2N giữ nguyên
heartbeat() {
        local cycles=$1
        echo "TS2N" > $dev_path/digits
        for ((i=0; i<cycles; i++)); do
                echo 7 > $dev_path/brightness   # lub (mạnh)
                sleep 0.08
                echo 2 > $dev_path/brightness
                sleep 0.06
                echo 7 > $dev_path/brightness   # dub (mạnh)
                sleep 0.08
                echo 1 > $dev_path/brightness
                sleep 0.06
                echo 3 > $dev_path/brightness   # nghỉ giữa 2 nhịp
                sleep 0.35
        done
        echo 7 > $dev_path/brightness
}

start() {
        touch /run/tm16xx.run
        echo 7 > $dev_path/brightness

        slot_effect "8888"
        heartbeat 3
        sleep 0.5
        echo "0000" > $dev_path/digits
        sleep 0.3

        while [[ -f $dev_path/digits && -f /run/tm16xx.run ]]; do
                lan_state=$(cat /sys/class/net/eth0/operstate 2>/dev/null)
                [[ "$lan_state" == "up" ]] && set_icon lan 1 || set_icon lan 0
                if [[ -e /sys/class/leds/tm16xx::usb ]]; then
                        ls /sys/class/block -al | grep usb &>/dev/null \
                                && set_icon usb 1 || set_icon usb 0
                fi
                set_icon sd 1

                # 1. Giờ
                count=4
                while [ $count -gt 0 ]; do
                        echo "$(date +"%H%M")+COLON" > $dev_path/digits
                        sleep 0.5
                        echo "$(date +"%H%M")-COLON" > $dev_path/digits
                        sleep 0.5
                        count=$(( count - 1 ))
                done

                # 2. RAM: đã dùng / tổng (trăm MB) - số thuần, an toàn
                read ram_used_mb ram_total_mb <<< $(free -m | awk '/Mem:/ {print $3, $2}')
                used_h=$(( ram_used_mb / 100 ))
                total_h=$(( ram_total_mb / 100 ))
                echo "$(printf "%02d%02d" $used_h $total_h)+COLON" > $dev_path/digits
                sleep 3

                # 3. DISK: đã dùng / tổng (GB, làm tròn xuống số nguyên)
                disk_used_gb=$(df -h / | awk 'NR==2 {print $3}' | sed 's/G//' | cut -d'.' -f1)
                disk_total_gb=$(df -h / | awk 'NR==2 {print $2}' | sed 's/G//' | cut -d'.' -f1)
                echo "$(printf "%02d%02d" $disk_used_gb $disk_total_gb)+COLON" > $dev_path/digits
                sleep 3

                # 4. Nhiệt độ CPU (giữ nguyên như bản gốc, đã xác nhận hoạt động)
                temp=$(cat /sys/devices/virtual/thermal/thermal_zone0/temp)
                echo "${temp:0:2}*C" > $dev_path/digits
                sleep 3

                # 5. Logo TS2N chen giữa mỗi vòng
                echo "TS2N" > $dev_path/digits
                sleep 1.5
        done
}

stop() {
        echo stopping...
        rm -f /run/tm16xx.run
        sleep 0.2

        local frames=("8888" "0088" "0008" "0000")
        for f in "${frames[@]}"; do
                echo "$f" > $dev_path/digits
                sleep 0.25
        done
        for b in 6 4 2 0; do
                echo $b > $dev_path/brightness
                sleep 0.15
        done
        echo '' > $dev_path/digits
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) stop; start ;;
    status) ;;
    *) echo "Usage: $0 {start|stop|status|restart}"
esac
exit 0
SCRIPT_END
chmod +x /usr/lib/tm16xx-display/display_service.sh
```

## 3. Kiểm tra cú pháp
Trước khi khởi động lại dịch vụ hiển thị, hãy chạy lệnh sau để kiểm tra xem script có lỗi cú pháp nào không:
```bash
bash -n /usr/lib/tm16xx-display/display_service.sh && echo "Cú pháp OK"
```

## 4. Áp dụng cấu hình và Chạy thử
* **Nạp lại (Reload) cấu hình hệ thống quản lý dịch vụ (Systemd):**
  Nếu bạn có chỉnh sửa file service (như `tm16xx-display.service`), cần chạy lệnh sau để systemd cập nhật:
  ```bash
  systemctl daemon-reload
  ```
* **Áp dụng cấu hình và khởi chạy lại dịch vụ LED:**
  ```bash
  systemctl restart tm16xx-display.service
  ```
* **Test riêng hiệu ứng tắt nguồn (OFF):**
  Chạy lệnh tắt dịch vụ và quan sát màn hình LED sẽ hiển thị dịch chuyển ký tự giảm dần độ sáng: `8888` $\rightarrow$ `0088` $\rightarrow$ `0008` $\rightarrow$ `0000` $\rightarrow$ trống rồi mờ dần $\rightarrow$ tắt.
  ```bash
  systemctl stop tm16xx-display.service
  ```
* **Bật lại màn hình hiển thị:**
  ```bash
  systemctl start tm16xx-display.service
  ```

---

## 5. Xử lý khi cắm/gắn lại LED (Reload vật lý)
Nếu bạn rút màn hình LED ra hoặc cắm lại thiết bị, hoặc driver `tm16xx` bị treo đột ngột, hãy khởi động lại service để hệ thống nhận diện và nạp lại thông số driver:
```bash
systemctl restart tm16xx-display.service
```

---

## 6. Khôi phục lại trạng thái ban đầu (Restore)
Nếu gặp lỗi hoặc muốn quay lại script gốc của hệ thống, chỉ cần ghi đè file backup đính kèm trước đó và restart lại service:
```bash
cp /usr/lib/tm16xx-display/display_service.sh.bak /usr/lib/tm16xx-display/display_service.sh
systemctl restart tm16xx-display.service
```
