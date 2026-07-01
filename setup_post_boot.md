# Hướng dẫn Cấu hình Hệ thống Tanix W2 từ đầu (Post-Boot Setup)

Tài liệu này hướng dẫn chi tiết các bước thiết lập hệ thống từ cơ bản đến nâng cao cho **Tanix W2** ngay sau khi boot thành công vào Ubuntu lần đầu. Các bước được đúc kết trực tiếp từ lịch sử cấu hình thực tế trên thiết bị.

---

## 1. Kiểm tra Thông tin Ban đầu & Cập nhật Hệ thống

Sau khi SSH vào thiết bị với thông tin mặc định (`root` / `tvbox`), hãy kiểm tra phần cứng và cập nhật toàn bộ thư viện:

```bash
# Kiểm tra phiên bản nhân (Kernel) và hệ điều hành
uname -a
cat /etc/os-release

# Xem thông tin mạng và phân vùng đĩa
ip addr
lsblk

# Kiểm tra dung lượng RAM trống
free -h

# Cập nhật danh sách gói và nâng cấp toàn bộ hệ thống lên bản mới nhất
apt update && apt full-upgrade -y

# Khởi động lại để áp dụng thay đổi (nếu có cập nhật kernel)
reboot
```

---

## 2. Thiết lập Khởi động tự động (Multiboot)
Để Box tự động nhận diện thiết bị khởi động ngoại vi (SD Card / USB) mà không cần nhấn giữ nút Reset thủ công ở các lần sau:

```bash
cd /root
# Chạy script cấu hình nạp bootloader
./aml-multiboot-setup.sh

# Khởi động lại hệ thống
reboot
```

---

## 3. Cấu hình Mạng (WiFi & Samba Share)

Thư mục `/root` chứa sẵn các script tiện ích để thiết lập nhanh kết nối:

### Thiết lập Kết nối WiFi:
```bash
cd /root
./wifi-connect.sh
```
*Làm theo hướng dẫn trên màn hình để chọn mạng SSID và nhập mật khẩu wifi.*

### Cài đặt Samba Server (Chia sẻ file qua mạng nội bộ):
```bash
cd /root
./samba-install.sh
```
*Nhập mật khẩu truy cập thư mục chia sẻ khi được script yêu cầu.*

---

## 4. Tối ưu hóa Bộ nhớ Swap (Kết hợp zramswap và Swapfile)

Vì thiết bị TV Box thường giới hạn dung lượng RAM (thường là 2GB), tối ưu swap giúp hệ thống hoạt động mượt mà hơn và tránh lỗi tràn bộ nhớ (Out-Of-Memory).

### Bước A: Cài đặt và cấu hình Zram (Nén RAM làm bộ nhớ đệm)
```bash
# Cài đặt zram-tools
apt install zram-tools -y

# Chỉnh sửa file cấu hình zram
nano /etc/default/zramswap
```
*(Bạn có thể thiết lập lượng RAM sử dụng làm zram tại đây, ví dụ: định cấu hình `PERCENT=50` hoặc `SIZE=512`)*

Khởi động lại dịch vụ zram và kiểm tra:
```bash
systemctl restart zramswap
free -h
```

### Bước B: Tạo thêm Swapfile vật lý (512MB) đề phòng tải nặng
```bash
# Tạo file swap dung lượng 512MB
fallocate -l 512M /swapfile

# Phân quyền bảo mật chỉ cho root đọc/ghi
chmod 600 /swapfile

# Định dạng phân vùng swap
mkswap /swapfile

# Kích hoạt swapfile ngay lập tức
swapon /swapfile

# Cấu hình tự động mount swapfile khi khởi động hệ thống
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Kiểm tra lại tổng dung lượng RAM + Swap (Zram + Swapfile)
free -h
```

---

## 5. Cấu hình Bảo mật, Timezone & Quản lý Hệ thống

### Thay đổi mật khẩu Root mặc định:
```bash
passwd root
```

### Cho phép root đăng nhập qua SSH (Tùy chọn):
Nếu bạn gặp khó khăn khi SSH bằng tài khoản root:
```bash
nano /etc/ssh/sshd_config
```
*Tìm dòng `PermitRootLogin` và sửa thành `PermitRootLogin yes`, sau đó restart lại dịch vụ ssh:*
```bash
systemctl restart ssh
```

### Đổi tên thiết bị (Hostname):
Để dễ quản lý trong mạng LAN (ví dụ đặt tên là `homeserver`):
```bash
hostnamectl set-hostname homeserver

# Cấu hình lại file hosts để ánh xạ tên mới
nano /etc/hosts
```
*Thay đổi `127.0.1.1` hoặc tên cũ thành `homeserver`.*

### Cập nhật múi giờ (Timezone - Việt Nam):
```bash
timedatectl set-timezone Asia/Ho_Chi_Minh

# Kiểm tra lại thời gian thực tế của hệ thống
timedatectl status
```

### Cài đặt các công cụ tối ưu hóa log và bảo vệ hệ thống:
```bash
# 1. Fail2Ban - Ngăn chặn tấn công brute-force SSH
apt install fail2ban -y

# 2. Bật tường lửa UFW (Lưu ý: Phải cho phép cổng 22/SSH trước khi enable để tránh mất kết nối)
# ufw allow 22/tcp
# ufw enable

# 3. Log2Ram - Ghi log vào RAM để giảm chu kỳ ghi, tăng tuổi thọ cho thẻ nhớ SD
apt install log2ram -y
```

---

## 6. Cấu hình Màn hình hiển thị LED (vfd) phía trước Box

Thiết bị Tanix W2 được tích hợp màn hình LED phía trước (sử dụng IC điều khiển tm16xx). Mặc định hệ thống hiển thị đồng hồ, bạn có thể tùy biến script hiển thị thêm các thông số hệ thống quan trọng khác như: Tải CPU (Load Average), Dung lượng RAM đã dùng (%), Nhiệt độ hoặc Dung lượng ổ đĩa.

### Bước A: Xác định dịch vụ điều khiển màn hình LED
```bash
systemctl list-units --type=service | grep -iE "vfd|display|led|tm16"
```
Thông thường, dịch vụ quản lý trên bản dựng này là `tm16xx-display.service`.
Xem chi tiết file chạy chính của dịch vụ:
```bash
systemctl cat tm16xx-display.service
```

### Bước B: Thay đổi Script hiển thị (Tùy biến VFD)
Bạn có thể thay đổi cách hiển thị thông số xoay vòng bằng cách chỉnh sửa script gốc.

1. **Sao lưu script nguyên bản đề phòng lỗi:**
   ```bash
   cp /usr/lib/tm16xx-display/display_service.sh /usr/lib/tm16xx-display/display_service.sh.bak
   ```

2. **Chỉnh sửa script:**
   ```bash
   nano /usr/lib/tm16xx-display/display_service.sh
   ```

   *Dưới đây là nội dung script tùy biến nâng cao (tự động luân chuyển hiển thị giữa: Giờ phút -> Tải CPU (L) -> Dung lượng RAM đã dùng (r) -> Phần trăm Disk đã dùng (d) -> Xung nhịp CPU (MHz) nếu có):*

   ```bash
   #!/bin/bash
   # (c) 2020 devmfc (Tùy biến bởi SherwinVN)
   dev_path=$(dirname /sys/bus/platform/drivers/tm16xx*/*/digits)

   set_icon() {
           local path="/sys/class/leds/tm16xx::$1/brightness"
           [[ -e $path ]] && echo "$2" > "$path" 2>/dev/null
   }

   fmt_metric() {
           local label=$1 value=$2
           if [ "$value" -ge 100 ]; then
                   printf "%s%03d" "$label" "$value"
           else
                   printf "%s-%02d" "$label" "$value"
           fi
   }

   start() {
           touch /run/tm16xx.run
           echo 'none' > /sys/class/leds/tm16xx::power/trigger 2>/dev/null
           echo 1 > /sys/class/leds/tm16xx::power/brightness 2>/dev/null
           echo 7 > $dev_path/brightness

           echo "WINK" > $dev_path/digits 2>/dev/null
           sleep 1.5
           for i in 1 2; do
                   echo 0 > $dev_path/brightness
                   sleep 0.15
                   echo 7 > $dev_path/brightness
                   sleep 0.15
           done
           sleep 0.5

           while [[ -f $dev_path/digits && -f /run/tm16xx.run ]]; do
                   lan_state=$(cat /sys/class/net/eth0/operstate 2>/dev/null)
                   [[ "$lan_state" == "up" ]] && set_icon lan 1 || set_icon lan 0

                   if [[ -e /sys/class/leds/tm16xx::usb ]]; then
                           ls /sys/class/block -al | grep usb &>/dev/null \
                                   && set_icon usb 1 || set_icon usb 0
                   fi
                   set_icon sd 1

                   # Hiển thị đồng hồ trong vòng 4 giây (nháy dấu hai chấm mỗi 0.5s)
                   count=4
                   while [ $count -gt 0 ]; do
                           echo "$(date +"%H%M")+COLON" > $dev_path/digits
                           sleep 0.5
                           echo "$(date +"%H%M")-COLON" > $dev_path/digits
                           sleep 0.5
                           count=$(( count - 1 ))
                   done

                   # Hiển thị Tải CPU (Load Average - Lxxx) trong 3 giây
                   load=$(cut -d' ' -f1 /proc/loadavg)
                   load_disp=$(echo "$load * 100" | bc | cut -d'.' -f1)
                   echo "$(fmt_metric L $load_disp)" > $dev_path/digits
                   sleep 3

                   # Hiển thị Phần trăm RAM đã dùng (rxx) trong 3 giây
                   ram_pct=$(free | awk '/Mem:/ {printf "%.0f", $3/$2*100}')
                   echo "$(fmt_metric r $ram_pct)" > $dev_path/digits
                   sleep 3

                   # Hiển thị % Disk phân vùng Root đã dùng (dxx) trong 3 giây
                   disk_pct=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
                   echo "$(fmt_metric d $disk_pct)" > $dev_path/digits
                   sleep 3

                   # Hiển thị Xung nhịp hiện tại của CPU (MHz) trong 3 giây (nếu có hỗ trợ)
                   freq_khz=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null)
                   if [[ -n "$freq_khz" ]]; then
                           freq_mhz=$(( freq_khz / 1000 ))
                           echo "$freq_mhz" > $dev_path/digits
                           sleep 3
                   fi
           done
           echo '' > $dev_path/digits
           echo "stop"
   }

   stop() {
           echo stopping...
           rm -f /run/tm16xx.run
           sleep 0.2
           echo 0 > $dev_path/brightness
   }

   case "$1" in
       start) start ;;
       stop) stop ;;
       restart) stop; start ;;
       status) ;;
       *) echo "Usage: $0 {start|stop|status|restart}"
   esac
   exit 0
   ```

3. **Cấp quyền thực thi và khởi động lại dịch vụ:**
   ```bash
   chmod +x /usr/lib/tm16xx-display/display_service.sh
   
   # Kiểm tra cú pháp script xem có lỗi không
   bash -n /usr/lib/tm16xx-display/display_service.sh && echo "Cấu pháp OK"
   
   # Khởi động lại service để áp dụng màn hình LED mới
   systemctl restart tm16xx-display.service
   
   # Theo dõi log hoạt động của dịch vụ màn hình LED
   journalctl -u tm16xx-display.service -f
   ```

*Lưu ý: Nếu màn hình LED không sáng hoặc hiển thị không như ý muốn, bạn luôn có thể khôi phục lại file gốc bằng lệnh:*
```bash
cp /usr/lib/tm16xx-display/display_service.sh.bak /usr/lib/tm16xx-display/display_service.sh
systemctl restart tm16xx-display.service
```
