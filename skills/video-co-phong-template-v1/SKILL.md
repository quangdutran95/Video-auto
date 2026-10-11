---
name: video-co-phong-template-v1
description: Quy trình sản xuất video Cổ phong tự động phiên bản v1 kết hợp VieNeu-TTS v1 giọng Ngọc Dũng, sinh ảnh qua extension TobyFlow và kết xuất giao diện hoài cổ (Serif font, viền vàng đồng, triện đỏ).
---

# Video Cổ Phong Template Skill

Skill này điều phối và chạy toàn bộ quy trình sản xuất video phong cách hoài cổ **Cổ Phong (video-co-phong-template)** tự động kết hợp **VieNeu-TTS v1 (giọng Ngọc Dũng)** và **TobyFlow Extension (vẽ hình)** từ văn bản kịch bản đầu vào.

## Điều kiện tiên quyết (Prerequisites)

1.  **Mô hình Ngọc Dũng**: Đã được merge và nằm ở thư mục:
    `E:\VieNeu-TTS-v1\finetune\output\VieNeu-TTS-0.3B-Merged-NgocDung`
2.  **Môi trường VieNeu-TTS v1**: Đã được cài đặt đầy đủ python packages tại:
    `E:\VieNeu-TTS-v1\.venv\`
3.  **TobyFlow Bridge Server**: Phải được khởi chạy trước khi chạy pipeline:
    ```powershell
    cd E:\1.1.0_0\telegram-bridge
    node server.js
    ```
4.  **TobyFlow Extension**: Đã được bật trên Chrome và đã kết nối thành công với Bridge Server ở cổng 3000.

## Các bước của quy trình (Pipeline Workflow)

### Bước 1: Khởi tạo Job mới
Tạo thư mục dự án để chứa các file trung gian và kết quả render:
```powershell
$video-job-manager — tạo job mới "Video Cổ Phong - <Tiêu đề>", platform tiktok, vi
```
*Lưu ý:* Lấy ID của Job vừa tạo (ví dụ: `YYYY-MM-DD_01_video_co_phong`).

### Bước 2: Lưu kịch bản và sinh giọng nói (Ngọc Dũng)
1.  Ghi kịch bản text vào file: `jobs/<job_id>/source/script.txt`
2.  Chạy script để sinh file âm thanh `voice.wav` sử dụng môi trường và mô hình VieNeu-TTS v1:
    ```powershell
    & "E:\VieNeu-TTS-v1\.venv\Scripts\python.exe" scripts/generate_voice_v1.py \
      --text-file "jobs/<job_id>/source/script.txt" \
      --output "jobs/<job_id>/source/voice.wav"
    ```
3.  Trích xuất phụ đề chi tiết và timing từng từ bằng skill `$word-timestamps-extractor`:
    ```powershell
    python skills/word_timestamps_extractor/scripts/transcribe_word_timestamps.py \
      --audio "jobs/<job_id>/source/voice.wav" \
      --output "jobs/<job_id>/source/transcript_word_level.toml" \
      --env-file .env \
      --language vi
    ```
4.  **Căn chỉnh chính tả phụ đề (Spelling Alignment)**:
    Đối chiếu và sửa lỗi chính tả phụ đề từ kịch bản gốc trong khi giữ nguyên thời gian giọng nói thực tế:
    ```powershell
    python scripts/align_timestamps.py \
      --script "jobs/<job_id>/source/script.txt" \
      --transcript "jobs/<job_id>/source/transcript_word_level.toml" \
      --output "jobs/<job_id>/source/transcript_word_level.toml"
    ```

### Bước 3: Tạo kế hoạch phân cảnh và Prompts vẽ hình
1. **Đối chiếu quy tắc đồng nhất nhân vật (Character Consistency):**
   - Đọc danh sách nhân vật tại `E:\GPT VIdeo cổ phong\CHARACTER INDEX.md.txt` để chọn nhân vật phù hợp với cốt truyện (ví dụ: `Young Scholar`, `Old Master`, `Monk`...).
   - Đọc chi tiết đặc tả ngoại hình tại `E:\GPT VIdeo cổ phong\CHARACTER_DNA_LIBRARY.md.txt` và nhúng toàn bộ thông tin DNA ngoại hình đó vào các prompt vẽ ảnh.
   - Bám sát quy tắc bố cục trong `E:\GPT VIdeo cổ phong\CORE_SYSTEM_INSTRUCTION.md.txt` (Khung hình 9:16 dọc, Negative Space chiếm 70-85%, nhân vật chiếm 15-30% chiều cao khung hình, phong cách vẽ màu nước tối giản trên nền giấy da cổ).
2. **Viết Creative Plan:** Gọi hoặc soạn file `creative_plan.toml`:
   ```powershell
   $video-creative-planner — viết creative plan cho job <job_id>, ngôn ngữ vi, mood truyền cảm, style gợi ý Imagen 3 artistic.
   ```
   *Đầu ra mong muốn:* File `jobs/<job_id>/source/creative_plan.toml` chứa các phân cảnh `[[scene_intents]]` có thuộc tính `visual_intent` là các prompt tiếng Anh chi tiết chứa đầy đủ mô tả nhân vật đồng nhất và bố cục Cổ Phong.

### Bước 4: Gọi TobyFlow vẽ ảnh và tự động thu thập
Chạy script cầu nối để gửi prompt tới TobyFlow và thu thập ảnh đã vẽ về thư mục assets của job:
```powershell
python tools/tobyflow_bridge.py \
  --plan "jobs/<job_id>/source/creative_plan.toml" \
  --output-dir "jobs/<job_id>/input/raw_assets/images" \
  --ratio "9:16"
```
Script sẽ tự động gọi CLI của TobyFlow cho từng cảnh, chờ ảnh được sinh ra trong thư mục Downloads của hệ thống, copy và đổi tên thành `sc_01.png`, `sc_02.png`,... vào thư mục `jobs/<job_id>/input/raw_assets/images/`.

**Quy tắc chờ ảnh (BẮT BUỘC)**:
- **Chờ ban đầu**: Chờ **5 phút (300 giây)** đầu tiên để quy trình sinh ảnh và tải về.
- **Kiểm tra định kỳ**: Nếu quy trình tạo ảnh vẫn còn chạy (chưa báo kết thúc), tiếp tục chờ thêm **3 phút (180 giây)** và kiểm tra tiếp. Nếu vẫn chưa xong, lặp lại việc chờ **3 phút** nữa và kiểm tra cho đến khi kết thúc.
- **Xử lý lỗi**: Khi quy trình kết thúc, kiểm tra thư mục đầu ra. Nếu có cảnh bị thiếu ảnh (tạo lỗi), hãy chạy lại quy trình chỉ cho các cảnh bị lỗi đó.

### Bước 5: Lập chỉ mục tài nguyên và Map timeline
1.  Đăng ký các ảnh mới vẽ vào cơ sở dữ liệu Asset Index:
    ```powershell
    $asset-semantic-extractor — phân tích jobs/<job_id>/input/raw_assets/images/
    ```
2.  Gán ảnh vào các phân cảnh tương ứng trên dòng thời gian một cách chính xác theo thứ tự và giọng nói thực tế:
    ```powershell
    .venv/bin/python skills/video-co-phong-template/scripts/map_deterministic.py \
      --creative-plan jobs/<job_id>/source/creative_plan.toml \
      --transcript jobs/<job_id>/source/transcript_word_level.toml \
      --output jobs/<job_id>/source/semantic_mapping.toml
    ```

### Bước 6: Ghép nối và Render video
1.  Xây dựng render plan TOML gom phụ đề, audio và hình ảnh:
    ```powershell
    $video-render-plan-builder — xây dựng render plan cho job <job_id>
    ```
2.  Áp dụng giao diện Cổ Phong thương hiệu (`$video-co-phong-render-template`) để tạo project Remotion:
    ```powershell
    .venv/bin/python skills/video-co-phong-render-template-v1/scripts/instantiate.py \
      --job jobs/<job_id> \
      --brand "Tri Thức Là Vàng" \
      --subtitle-top-pct 18
    ```
3.  Thực hiện render video thành phẩm:
    ```powershell
    $video-renderer — render video cho job <job_id>
    ```
    *Kết quả cuối cùng:* File video hoàn chỉnh nằm tại `jobs/<job_id>/output/final.mp4`.
