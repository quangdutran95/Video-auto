---
name: video-co-phong-template
description: Quy trình sản xuất video Cổ phong tự động kết hợp VieNeu-TTS v1 giọng Ngọc Dũng, sinh ảnh qua extension TobyFlow, kết xuất giao diện hoài cổ và tự động tạo Thumbnail thu hút (High-CTR EQ / Stickman Style & Cổ Phong Style).
---

# Video Cổ Phong Template Skill

Skill này điều phối và chạy toàn bộ quy trình sản xuất video phong cách hoài cổ **Cổ Phong (video-co-phong-template)** tự động kết hợp **VieNeu-TTS v1 (giọng Ngọc Dũng)**, **TobyFlow Extension (vẽ hình)**, và **tự động thiết kế Thumbnail thu hút lượt xem** từ văn bản kịch bản đầu vào.

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
    # QUAN TRỌNG: Bắt buộc đặt SAFETENSORS_NO_MMAP=1 để tránh lỗi paging file trên Windows
    $env:SAFETENSORS_NO_MMAP="1"
    & "E:\VieNeu-TTS-v1\.venv\Scripts\python.exe" scripts/generate_voice_v1.py `
      --text-file "jobs/<job_id>/source/script.txt" `
      --output "jobs/<job_id>/source/voice.wav"
    ```
    > ⚠️ Nếu không đặt `SAFETENSORS_NO_MMAP=1`, Windows sẽ báo lỗi `OSError: The paging file is too small` khi mô hình cố dùng memory-map để load file `.safetensors`.
3.  Trích xuất phụ đề chi tiết và timing từng từ bằng script nội bộ:
    ```powershell
    python skills/video-co-phong-template/scripts/transcribe_word_timestamps.py \
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

**Bước 3a — LLM phân cảnh theo ngữ nghĩa và viết Prompts ($video-co-phong-creative-planner):**

LLM đọc toàn bộ kịch bản (`script.txt`) và transcript, **tự quyết định nhóm câu theo ngữ nghĩa** (bài học, cảm xúc, bước ngoặt), sau đó viết `spoken_text` và `visual_intent` cho từng scene.

```powershell
$video-co-phong-creative-planner — viết creative plan cho job <job_id>:
  đọc kịch bản jobs/<job_id>/source/script.txt và transcript
  transcript jobs/<job_id>/source/transcript_word_level.toml,
  phân cảnh theo ngữ nghĩa, viết visual_intent theo phong cách Cổ Phong.
```
*Đầu ra:* File `jobs/<job_id>/source/creative_plan.toml` với đầy đủ `spoken_text`, `visual_intent`, `mood`, `narrative_role`.

**Bước 3b — Gắn timestamp chính xác từ giọng đọc thực tế (Python script):**

Script đọc `spoken_text` của từng scene, khớp với `[[words]]` trong transcript bằng fuzzy matching, gắn `start_hint`/`end_hint` chính xác vào file.

```powershell
python skills/video-co-phong-template/scripts/timestamp_resolver.py `
  --creative-plan "jobs/<job_id>/source/creative_plan.toml" `
  --transcript    "jobs/<job_id>/source/transcript_word_level.toml" `
  --output        "jobs/<job_id>/source/creative_plan.toml"
```

> Nếu thấy cảnh báo `KHÔNG KHỚP`, kiểm tra lại `spoken_text` của scene đó — LLM có thể đã viết khác một chút so với transcript Whisper thực tế.

### Bước 4: Gọi TobyFlow vẽ ảnh hàng loạt (Batch Mode) và tự động thu thập

> **⚡ Chế độ mặc định: Batch (Hàng loạt)**
> Kể từ bản cập nhật này, hệ thống mặc định sử dụng chế độ `--batch` để gửi toàn bộ prompt phân cảnh trong **1 lần gọi duy nhất**, sau đó Extension tự động xếp hàng đợi và sinh ảnh nền liên tục. Điều này nhanh hơn đáng kể so với chế độ gọi tuần tự từng ảnh.

**Bước 4a — Bật nút Multi-Prompt trên Extension (chỉ cần 1 lần):**

Đảm bảo Bridge Server đang chạy, sau đó bật chế độ Multi-Prompt qua lệnh HTTP:
```powershell
# Bật Multi-Prompt (Extension sẽ nhận và phân tách danh sách prompt tự động)
Invoke-WebRequest "http://localhost:3000/cmd?action=TOGGLE_MULTI_PROMPT&enabled=true"
```

> Hoặc nếu Extension đã được cài đặt sẵn tính năng này (đã Reload sau khi cập nhật mã nguồn), bước này có thể bỏ qua — Extension sẽ tự nhận dạng `mode: 'multi'` khi nhận từ CLI.

**Bước 4b — Gửi batch toàn bộ prompt phân cảnh tới TobyFlow:**
```powershell
.venv\Scripts\python.exe tools/tobyflow_bridge.py `
  --plan "jobs/<job_id>/source/creative_plan.toml" `
  --output-dir "jobs/<job_id>/input/raw_assets/images" `
  --ratio "9:16" `
  --batch `
  --timeout 600
```

Script thực hiện các công việc sau:
1. **Kiểm tra ảnh đã có**: Bỏ qua các phân cảnh đã có ảnh sẵn trong `output-dir`.
2. **Gộp và gửi Batch**: Gộp toàn bộ `visual_intent` của các phân cảnh còn thiếu bằng dấu `\n\n`, gửi 1 lần duy nhất tới Extension với cờ `mode: multi`.
3. **Extension xử lý**: Extension tự động tách danh sách và xếp từng prompt vào hàng đợi `PromptQueue`, sinh ảnh liên tục trong nền Chrome.
4. **Quy tắc chờ ảnh (BẮT BUỘC)**:
   - **Chờ ban đầu**: Chờ **5 phút (300 giây)** đầu tiên để quy trình sinh ảnh và tải về.
   - **Kiểm tra định kỳ**: Nếu quy trình tạo ảnh vẫn còn chạy (chưa báo kết thúc), tiếp tục chờ thêm **3 phút (180 giây)** và kiểm tra tiếp. Nếu vẫn chưa xong, lặp lại việc chờ **3 phút** nữa và kiểm tra cho đến khi kết thúc.
   - **Xử lý lỗi**: Khi quy trình kết thúc, kiểm tra thư mục đầu ra. Nếu có cảnh bị thiếu ảnh (tạo lỗi), hãy chạy lại quy trình chỉ cho các cảnh bị lỗi đó.
5. **Theo dõi & So khớp (Fuzzy Match)**: Script theo dõi thư mục `Downloads/tobyflow_bot` và tự động so khớp từng ảnh tải xuống với phân cảnh tương ứng dựa trên từ khóa trong prompt (Fuzzy Matching), sau đó copy và đổi tên chuẩn thành `sc_01.jpeg`, `sc_02.jpeg`, ... vào `output-dir`.

### Bước 5: Lập chỉ mục tài nguyên và Map timeline
1.  Đăng ký và xuất thông tin các ảnh mới vẽ từ Asset Index:
    ```powershell
    python -m tools.asset_index.exporter jobs/<job_id>/input/raw_assets/ \
      --output jobs/<job_id>/source/asset_semantics.toml
    ```
2.  Gán ảnh vào các phân cảnh tương ứng trên dòng thời gian một cách chính xác theo thứ tự và giọng nói thực tế:
    ```powershell
    .venv/bin/python skills/video-co-phong-template/scripts/map_deterministic.py \
      --creative-plan jobs/<job_id>/source/creative_plan.toml \
      --transcript jobs/<job_id>/source/transcript_word_level.toml \
      --output jobs/<job_id>/source/semantic_mapping.toml
    ```

### Bước 6: Ghép nối và Render video
1.  Xây dựng render plan TOML gom phụ đề, audio và hình ảnh bằng script nội bộ:
    ```powershell
    python skills/video-co-phong-template/scripts/build_render_plan.py build \
      --mapping jobs/<job_id>/source/semantic_mapping.toml \
      --transcript jobs/<job_id>/source/transcript_word_level.toml \
      --creative-plan jobs/<job_id>/source/creative_plan.toml \
      --voice-audio jobs/<job_id>/source/voice.wav \
      --output jobs/<job_id>/source/render_plan.toml
    ```
2.  Áp dụng giao diện Cổ Phong thương hiệu (`$video-co-phong-render-template`) để tạo project Remotion:
    ```powershell
    .venv/bin/python skills/video-co-phong-render-template/scripts/instantiate.py \
      --job jobs/<job_id> \
      --brand "Tri Thức Là Vàng" \
      --subtitle-top-pct 18
    ```
3.  Thực hiện render video thành phẩm bằng lệnh npm:
    ```powershell
    cmd /c "cd /d jobs/<job_id>/remotion && npm run render"
    ```
    *Kết quả cuối cùng:* File video hoàn chỉnh nằm tại `jobs/<job_id>/output/final_video.mp4`.

### Bước 7: Khởi tạo Thumbnail độc quyền qua TobyFlow (Exclusive TobyFlow AI Thumbnail - Ultra-Strict Vietnamese Spelling & Diacritics Enforcement)

Quy trình **BẮT BUỘC sử dụng 100% TobyFlow Extension** để sinh ảnh Thumbnail chuẩn 9:16 Cổ Phong với **bộ ràng buộc ÉP TỪNG KÝ TỰ Tiếng Việt chính xác 100% không thiếu hay sai dấu**, phông chữ Montserrat cố định, kích thước chuẩn và vị trí 15% top margin:

#### Bộ Ràng Buộc Prompt Tạo Ảnh Thumbnail (BẮT BUỘC TUÂN THỦ):

1. **Ràng Buộc Ép Tiếng Việt Chuẩn Chính Tả Từng Ký Tự 100% (Ultra-Strict Vietnamese Diacritics Enforcement)**:
   - `MANDATORY VIETNAMESE SPELLING DIRECTIVE: The rendered text MUST be spelled in 100% perfectly accurate Vietnamese with EVERY single tone mark, accent symbol, circumflex, and hook explicitly drawn sharp, clear, and unblurred.`
   - Mô tả từng ký tự có dấu: `For header: '<CONTEXT_TEXT>' with exact accent marks. For seal banner: '<PUNCH_TEXT>' with exact tone marks.`
   - Negative prompt tag ép nét: `ABSOLUTELY ZERO missing accents, zero misspelled words, zero garbled letters, zero blurred diacritics, zero typos, zero English translation.`

2. **Header Context Linh Hoạt Theo Chủ Đề Video (<CONTEXT_TEXT>)**:
   - `<CONTEXT_TEXT>` là tên chuyên mục/series 2-3 từ ngắn gọn, linh hoạt biến đổi theo nội dung cốt lõi của video (ví dụ: `"BẢN LĨNH SỐNG"`, `"NHÂN CÁCH SỐNG"`, `"TƯ DUY SỐNG"`, `"ỨNG XỬ SỐNG"`, `"BÀI HỌC LẬP THÂN"`).
   - Tên Font cố định `Montserrat`, kích thước `36px font size, semi-bold 600 weight`, vị trí cố định `15% top margin offset from top edge (280px from top edge)`.

3. **Kích Thước PUNCH Khung Triện Đỏ Cố Định (<PUNCH_TEXT>)**:
   - `<PUNCH_TEXT>` là câu chốt giật thốn 2-3 từ thể hiện từ khóa chính của video (ví dụ: `"SỐNG TỬ TẾ"`, `"NGƯỜI ĐÁNG TIN"`, `"SỐNG KHÔNG THẸN"`).
   - Chữ trắng nổi bật trên nền Triện Đỏ viền vàng, font `Montserrat` cố định `60px font size, bold 700 weight`.

4. **Phông Chữ Thường Phẳng Dễ Đọc (Tuyệt đối CẤM chữ thư pháp / Calligraphy)**:
   - Ràng buộc cấm thư pháp: `DO NOT use calligraphy, brush script, handwritten cursive, or complex decorative fonts. Use clean straight plain 'Montserrat' lettering only.`

5. **Hình Ảnh Ẩn Dụ Biến Đổi Theo Nội Dung Video (Dynamic Visual Metaphor)**:
   - Bối cảnh hình ảnh nghệ thuật (`<DYNAMIC_SCENE_METAPHOR_PROMPT>`) phản ánh đúng bài học/chủ đề cốt lõi của video đó.

6. **Cấu Trúc Master Prompt Siêu Ép Chính Tả**:
   ```text
   High-CTR 9:16 vertical video thumbnail in traditional Cổ Phong minimalist oriental watercolor style on aged parchment paper background. 80% negative space. Positioned at exact 15% top margin offset from top edge (280px from top edge): at the top center, clean modern highly legible fixed 'Montserrat' font header text in 36px font size reads Vietnamese text '<CONTEXT_TEXT>'. Directly 20px below it, a rich crimson red stamp seal banner with gold borders contains clean modern bold fixed 'Montserrat' white font text in 60px font size reading Vietnamese text '<PUNCH_TEXT>'. MANDATORY VIETNAMESE SPELLING DIRECTIVE: All rendered text MUST be spelled in 100% perfectly accurate Vietnamese language with EVERY single tone mark, accent, circumflex, and hook explicitly drawn sharp, clear, and unblurred. Absolutely zero missing accents, zero misspelled words, zero garbled letters, zero blurred diacritics, zero typos, zero English translation. DO NOT use calligraphy, brush script, or complex decorative fonts. Use clean straight plain 'Montserrat' lettering only. At the bottom center, <DYNAMIC_SCENE_METAPHOR_PROMPT>. Serene, inspiring, high contrast legible typography, aesthetic oriental art masterpiece, 9:16 aspect ratio.
   ```

6. **Lệnh sinh ảnh Thumbnail độc quyền qua TobyFlow Bridge**:
   ```powershell
   # Xóa file thumbnail cũ (nếu có) để ép sinh mới
   Remove-Item "jobs/<job_id>/output/thumbnail.*" -Force -ErrorAction SilentlyContinue

   $env:PYTHONIOENCODING="utf-8"
   .venv\Scripts\python.exe tools/tobyflow_bridge.py `
     --prompt "<PROMPT_THUMBNAIL_DYNAMIC>" `
     --scene-id thumbnail `
     --output-dir "jobs/<job_id>/output" `
     --ratio "9:16"
   ```

7. **Quy Tắc Kiểm Tra Nối Tiếp Chuẩn Chính Tả & Tự Động Re-roll (Automated Vision Inspection & Auto Re-roll)**:
   - **BẮT BUỘC**: Sau khi sinh `jobs/<job_id>/output/thumbnail.jpeg`, agent thực hiện bước kiểm tra hình ảnh qua Vision LLM để đọc (OCR) chữ tiêu đề Tiếng Việt trên hình.
   - **So sánh đối chiếu**: Đọc hai chuỗi chữ trên hình đối chiếu với `<CONTEXT_TEXT>` và `<PUNCH_TEXT>`.
   - **Xử lý tự động khi sai**: Nếu phát hiện chữ bị vẽ sai chính tả, thiếu dấu sắc/hỏi/ngã/mũ/móc, hoặc biến dạng nét -> Agent BẮT BUỘC xóa file `thumbnail.jpeg` và tự động kích hoạt lại lệnh sinh ảnh TobyFlow (`re-roll`) cho đến khi bức ảnh đạt chuẩn 100% chính tả (tối đa 3 lần re-roll).
   *Thành phẩm:* File `jobs/<job_id>/output/thumbnail.jpeg` (và copy sang `thumbnail.png`) sinh độc quyền 100% từ TobyFlow Extension được nghiệm thu tự động chuẩn 100% chính tả đầy đủ dấu.


