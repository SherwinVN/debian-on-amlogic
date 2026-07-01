# Hướng dẫn Triển khai Ubuntu Minimal trên Tanix W2 (S905W2)

Tài liệu này hướng dẫn chi tiết từng bước (step-by-step) để cài đặt, cấu hình và tối ưu hóa hệ điều hành **Ubuntu Resolute 26.04 LTS (Kernel 6.18.34-meson64 Minimal)** sử dụng file ảnh `Devmfc_Ubuntu-Resolute_6.18.34-meson64_Minimal-26.06.01.img.xz` lên thiết bị **Tanix W2**.

---

## A. GHI ẢNH HỆ ĐIỀU HÀNH RA THẺ SD (Thực hiện trên máy tính/Mac)

Bạn có thể chọn một trong hai cách dưới đây để ghi file ảnh `.img.xz` vào thẻ nhớ SD.

### Cách 1: Sử dụng phần mềm balenaEtcher (Khuyên dùng và trực quan)

1. Tải và cài đặt phần mềm **balenaEtcher** từ trang chủ [balena.io/etcher](https://balena.io/etcher).
2. Cắm thẻ nhớ SD vào máy tính (Lưu ý sao lưu dữ liệu quan trọng vì quá trình này sẽ xóa sạch thẻ).
3. Mở **balenaEtcher**:
   - Chọn **Flash from file** và trỏ đến file ảnh `Devmfc_Ubuntu-Resolute_6.18.34-meson64_Minimal-26.06.01.img.xz` (Không cần giải nén trước).
   - Chọn **Select target** và tick chọn đúng thẻ SD của bạn.
   - Nhấn nút **Flash!** và nhập mật khẩu của máy tính nếu được yêu cầu.
4. Đợi quá trình ghi dữ liệu (**Flashing**) và kiểm tra lỗi (**Validating**) hoàn tất 100%.

---

### Cách 2: Sử dụng dòng lệnh Terminal (dành cho macOS)

Nếu bạn muốn sử dụng dòng lệnh trực tiếp trên macOS:

1. **Xác định phân vùng thẻ SD:**
   Mở Terminal và chạy lệnh sau để tìm tên ổ đĩa của thẻ nhớ:
   ```bash
   diskutil list
   ```
   *Xác định chính xác ổ đĩa thẻ SD (ví dụ: `/dev/disk4`, `/dev/disk5`). Ký hiệu tổng quát bên dưới sẽ là `/dev/diskN`.*

2. **Unmount thẻ nhớ:**
   Hủy liên kết thẻ nhớ để hệ thống cho phép ghi đè (không eject hoàn toàn thẻ):
   ```bash
   diskutil unmountDisk /dev/diskN
   ```
   *(Thay `diskN` bằng số ổ đĩa đã xác định ở Bước 1, ví dụ: `disk4`)*

3. **Ghi file ảnh ra thẻ:**
   Sử dụng lệnh kết hợp giải nén `xz` và ghi dữ liệu `dd`. Nên sử dụng đường dẫn raw disk (`rdiskN` thay vì `diskN`) để tốc độ ghi nhanh hơn gấp nhiều lần:
   ```bash
   xz -dc Devmfc_Ubuntu-Resolute_6.18.34-meson64_Minimal-26.06.01.img.xz | sudo dd of=/dev/rdiskN bs=4m status=progress
   ```
   *Lưu ý: Lệnh `sudo` sẽ yêu cầu nhập mật khẩu của máy Mac.*

4. **Eject thẻ nhớ an toàn:**
   Sau khi Terminal báo thành công, tiến hành ngắt kết nối thẻ trước khi rút ra:
   ```bash
   diskutil eject /dev/diskN
   ```

---

## B. CẤU HÌNH PHÂN VÙNG BOOT & KHỞI ĐỘNG LẦN ĐẦU TRÊN TV BOX

1. **Cấu hình thiết bị Tanix W2:**
   - Sau khi ghi đĩa xong, cắm lại thẻ nhớ vào máy tính. Một phân vùng định dạng FAT32 có tên là `boot` hoặc `BOOT` sẽ xuất hiện.
   - Mở thư mục này ra, tìm và mở file cấu hình `boot.config` (hoặc `boot.ini` tùy theo cấu trúc phân vùng boot) bằng một trình soạn thảo text (như TextEdit trên Mac hoặc Notepad trên Windows).
   - Tìm dòng chứa cấu hình dành cho thiết bị Tanix W2:
     ```text
     #box=tanixw2
     ```
   - Xóa bỏ dấu `#` ở đầu dòng để kích hoạt cấu hình Device Tree (DTB) cho Tanix W2:
     ```text
     box=tanixw2
     ```
   - Lưu file lại và rút thẻ nhớ ra.

2. **Ép xung kích hoạt Khởi động (Boot) lần đầu trên Box:**
   - Đảm bảo thiết bị Tanix W2 đã được **rút nguồn điện hoàn toàn**.
   - Cắm thẻ nhớ SD đã cấu hình vào khe cắm thẻ của Box.
   - Dùng một que tăm nhỏ hoặc cổng chọc sim, nhấn và giữ nút **Reset** nằm ẩn sâu bên trong **cổng AV (Jack 3.5mm)** hoặc dưới lỗ đáy của Box.
   - Trong khi vẫn đang giữ nút Reset, hãy **cắm dây nguồn** vào Box.
   - Tiếp tục giữ nút Reset trong khoảng **7 đến 10 giây**, sau đó thả ra.
   - Thiết bị sẽ tự động nhận diện thẻ SD boot và khởi động vào hệ điều hành Ubuntu.

---

## C. CẤU HÌNH HOÀN THIỆN TRÊN SERVER (SSH & Cài đặt Multiboot)

Sau khi Box đã khởi động thành công vào Ubuntu, bạn sẽ thao tác trực tiếp trên giao diện dòng lệnh (qua cáp mạng Ethernet/Wifi hoặc kết nối SSH).

### 1. Truy cập SSH vào Server
Tìm IP của Box trên router hoặc quét mạng nội bộ, sau đó mở Terminal trên máy tính và kết nối qua giao thức SSH:
```bash
ssh root@<IP_CUA_BOX>
```
*   **Username:** `root`
*   **Password mặc định:** `tvbox`
*   *Lưu ý: Ở lần boot đầu tiên, quá trình tạo lại khóa bảo mật (encryption keys) có thể mất 1-2 phút trước khi dịch vụ SSH sẵn sàng phản hồi.*

### 2. Thiết lập Khởi động tự động từ Bộ nhớ trong (eMMC) hoặc kích hoạt Multiboot
Mặc định, bạn phải cắm thẻ và giữ nút reset để boot. Để hệ thống tự động nhận diện khởi động từ thẻ SD/USB hoặc nạp hệ thống trực tiếp vào eMMC của TV Box mà không cần nhấn Reset thủ công nữa, hãy chạy công cụ cài đặt có sẵn trong thư mục gốc `/root`:

1. Di chuyển vào thư mục `/root` và cấp quyền thực thi (nếu cần):
   ```bash
   cd /root
   chmod +x aml-multiboot-setup.sh
   ```
2. Khởi chạy script cấu hình nạp bootloader:
   ```bash
   ./aml-multiboot-setup.sh
   ```
   > [!WARNING]
   > Lệnh này sẽ can thiệp và thay đổi môi trường biến (environment setup) của bootloader trên phân vùng của Box Android. Mặc dù tỉ lệ lỗi rất thấp, việc ghi đè phân vùng bootloader nguyên bản luôn đi kèm rủi ro nhỏ có thể gây lỗi gạch (brick) thiết bị nếu mất điện đột ngột hoặc phần cứng không tương thích hoàn toàn.

3. Sau khi script chạy xong, bạn có thể khởi động lại hệ thống để áp dụng thiết lập:
   ```bash
   reboot
   ```
   Từ nay, mỗi khi cắm thẻ SD có chứa HĐH vào và bật nguồn, Box sẽ tự động ưu tiên boot trực tiếp vào Ubuntu.

---

## D. QUY TRÌNH SAO LƯU (BACKUP) & PHỤC HỒI (RESTORE) THẺ SD TRÊN MACOS

### I. SAO LƯU HỆ THỐNG (Backup)
Nên thực hiện sao lưu sau khi bạn cấu hình xong hệ thống server (cài Docker, cài phần mềm, cấu hình IP tĩnh...) để tránh mất mát dữ liệu khi thẻ nhớ hỏng vật lý.

1. **Tắt Box an toàn để tránh hỏng File System:**
   ```bash
   shutdown -h now
   ```
   Đợi Box tắt hẳn đèn tín hiệu, rút thẻ SD ra và cắm vào máy Mac.

2. **Xác định phân vùng thẻ SD trên Mac:**
   ```bash
   diskutil list
   ```
   *(Tìm đúng ký hiệu ổ đĩa của thẻ SD, giả sử là `/dev/disk4`)*

3. **Unmount thẻ SD:**
   ```bash
   diskutil unmountDisk /dev/diskN
   ```
   *(Thay `diskN` bằng ổ đĩa của bạn)*

4. **Sao chép dữ liệu từ thẻ ra file ảnh `.img`:**
   Sử dụng lệnh `dd` với raw disk (`rdiskN`) để tăng tốc độ sao lưu:
   ```bash
   sudo dd if=/dev/rdiskN of=~/Desktop/tanixw2-backup-$(date +%Y%m%d).img bs=4m status=progress
   ```
   *Quá trình này sẽ tạo ra 1 file clone nguyên bản dung lượng bằng đúng dung lượng thẻ nhớ trên Desktop của bạn.*

5. **Nén file ảnh để tiết kiệm dung lượng lưu trữ (Tùy chọn):**
   ```bash
   gzip -k ~/Desktop/tanixw2-backup-*.img
   ```
   *Lệnh này giữ lại file gốc `.img` và tạo thêm một bản nén `.img.gz`.*

6. **Eject thẻ nhớ an toàn:**
   ```bash
   diskutil eject /dev/diskN
   ```

---

### II. PHỤC HỒI HỆ THỐNG (Restore)
Khi thẻ nhớ cũ bị hỏng hoặc bạn muốn nhân bản cấu hình sang một thẻ nhớ mới:

1. **Giải nén file backup (nếu đã nén dạng `.gz` trước đó):**
   ```bash
   gunzip -k ~/Desktop/tanixw2-backup-XXXXXXXX.img.gz
   ```
2. **Cắm thẻ nhớ mới vào Mac và Unmount:**
   ```bash
   diskutil list
   diskutil unmountDisk /dev/diskN
   ```
3. **Ghi đè file Backup vào thẻ nhớ mới:**
   ```bash
   sudo dd if=~/Desktop/tanixw2-backup-XXXXXXXX.img of=/dev/rdiskN bs=4m status=progress
   ```
   *(Hoặc bạn có thể dùng **balenaEtcher**, chọn trực tiếp file `.img` hoặc `.img.gz` vừa backup để ghi đè trực tiếp qua giao diện đồ họa).*
4. **Eject thẻ nhớ an toàn:**
   ```bash
   diskutil eject /dev/diskN
   ```
   Cắm thẻ nhớ mới vào Box Tanix W2 và cấp nguồn để khởi động lại bình thường.
