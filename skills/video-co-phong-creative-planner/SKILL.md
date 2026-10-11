---
name: video-co-phong-creative-planner
description: Phân cảnh kịch bản theo quy tắc MỖI CÂU = MỘT SCENE. Mỗi câu trong kịch bản tạo ra một [[scene_intents]] riêng biệt với visual_intent là hình ảnh ẩn dụ thể hiện tinh thần của câu đó. timestamp_resolver.py sẽ gắn timestamp chính xác sau khi có transcript.
---


# Video Cổ Phong Creative Planner

## Mục tiêu

Skill này phân cảnh kịch bản theo quy tắc **MỖI CÂU = MỘT SCENE**.

> [!IMPORTANT]
> **Quy tắc phân cảnh cốt lõi — BẮT BUỘC:**
> - Mỗi câu trong kịch bản (kết thúc bằng `.`, `!`, `?`, `…`) tạo ra **một `[[scene_intents]]` riêng biệt**.
> - **Cấm gộp nhiều câu vào chung một scene** — dù nội dung có liên quan đến nhau.
> - Lý do: mỗi hình ảnh chỉ có thể thể hiện đúng và đủ nội dung của **một câu duy nhất**. Gộp nhiều câu vào một hình ảnh sẽ khiến hình ảnh không thể hiện hết ý nghĩa.

Với mỗi câu, LLM thực hiện:
1. **Viết `spoken_text`** — trích nguyên văn câu đó từ kịch bản (không paraphrase).
2. **Viết `visual_intent`** — prompt vẽ ảnh tiếng Anh, là hình ảnh ẩn dụ thể hiện tinh thần của câu đó.
3. **Điền `mood`, `narrative_role`** phù hợp.

> **`timestamp_resolver.py` sẽ chạy sau** để khớp `spoken_text` với `[[words]]` trong transcript và gắn `start_hint`/`end_hint` chính xác. LLM chỉ cần ước tính `start_hint`/`end_hint` sơ bộ (~3 từ/giây).

## Quy tắc viết `spoken_text` (BẮT BUỘC)

> [!IMPORTANT]
> `spoken_text` phải được **trích nguyên văn từ `[[sentences]]`** trong `transcript_word_level.toml` — không được viết lại, paraphrase, hay tổng hợp.
> Mục đích: để `timestamp_resolver.py` có thể khớp chính xác với `[[words]]` trong transcript.
> Nếu LLM viết khác dù chỉ một vài từ, script sẽ không tìm được timestamp và cảnh báo `KHÔNG KHỚP`.


## Quy tắc viết `visual_intent` — Nguyên tắc Cốt lõi (BẮT BUỘC)

> [!IMPORTANT]
> **`visual_intent` phải thể hiện đầy đủ ý nghĩa và tinh thần của toàn bộ `spoken_text` trong phân cảnh đó.**
>
> - **Cấm vẽ một khoảnh khắc đơn lẻ:** Nếu `spoken_text` nói về nhiều ý (ví dụ: "chăm chỉ học hành rồi trưởng thành, đối mặt với thất bại, nhưng vẫn kiên cường đứng dậy"), prompt phải tìm một **hình ảnh ẩn dụ hoặc biểu tượng bao trùm** toàn bộ ý đó (ví dụ: cây trúc uốn cong trong gió nhưng không gãy, đứng thẳng bên bờ vực).
> - **Dùng biểu tượng hoặc cảnh ẩn dụ:** Hình ảnh không cần literal minh họa từng câu nói — thay vào đó, nó phải chứa đựng **tinh thần, bài học, hoặc cảm xúc** bao trùm của cả đoạn thoại.
> - **Chiều sâu thay vì bề mặt:** Một cảnh vẽ người đọc sách không đủ để thể hiện "người học không ngừng vươn lên bất chấp gian khó". Hãy vẽ: Thư sinh gầy gò ngồi dưới ngọn nến leo lét, bên ngoài mưa giông, một tay ôm sách, một tay che mắt đọc — hình ảnh thể hiện sự kiên trì vượt khó trọn vẹn hơn.
>
> **Quy trình bắt buộc trước khi viết visual_intent:**
> 1. Đọc toàn bộ `spoken_text` của phân cảnh.
> 2. Tóm tắt nội trong 1 câu: "Đoạn này muốn truyền đạt điều gì?"
> 3. Hỏi: "Một hình ảnh màu nước nào có thể thể hiện điều đó mà không cần chú thích?"
> 4. Từ câu trả lời đó, viết `visual_intent` bằng tiếng Anh mô tả hình ảnh đó chi tiết kèm nhân vật, hành động, bối cảnh, ánh sáng, cảm xúc.

## Quy tắc đặc tả Prompts vẽ ảnh (Character Consistency & Style)

1. **Đồng nhất nhân vật (Character Consistency):**
   - Đọc danh sách nhân vật tại `E:\GPT VIdeo cổ phong\CHARACTER INDEX.md.txt` để chọn nhân vật phù hợp với cốt truyện (ví dụ: `Young Scholar`, `Old Master`, `Monk`...).
   - Đọc chi tiết đặc tả ngoại hình tại `E:\GPT VIdeo cổ phong\CHARACTER_DNA_LIBRARY.md.txt` và nhúng toàn bộ thông tin DNA ngoại hình đó vào các prompt vẽ ảnh của scene tương ứng.
2. **Quy tắc bố cục màu nước Cổ Phong:**
   - Prompt vẽ phải luôn mô tả bố cục tranh dọc 9:16.
   - Sử dụng phong cách: **minimalist watercolor illustration on aged parchment paper background**.
   - Bố cục: **Negative Space (khoảng trống nghệ thuật) chiếm 70-85%**, nhân vật nằm gọn chiếm **15-30%** chiều cao khung hình, không che khuất phần phụ đề ở trên (18% top).

## Ví dụ minh họa cách viết `visual_intent` đúng

| `spoken_text` (tóm tắt) | ❌ Sai — prompt cụ thể nhưng rỗng ý nghĩa | ✅ Đúng — prompt bao trùm tinh thần toàn đoạn |
|---|---|---|
| "Dù thất bại liên tiếp, người học thật sự không bỏ cuộc" | Young Scholar reading a book by candlelight | Thin young scholar kneeling alone in an empty stone room, candle nearly burned out, scattered crumpled papers around him, yet hands firmly gripping an open book — watercolor, serene determination |
| "Kiến thức tích lũy từ nhỏ giọt, không ai giỏi ngay từ đầu" | Old master writing calligraphy | A lone pine seedling growing from a crack in an ancient stone wall, small but upright, vast empty sky above — minimalist watercolor, metaphor of patient growth |
| "Những lúc cô đơn nhất là lúc ta hiểu mình nhất" | Scholar sitting alone at night | Young scholar sitting at the edge of a moonlit cliff, facing the vast dark mountains alone, small figure in immense silence — watercolor, deep introspection |

## Đầu ra TOML

File đầu ra ghi vào:
```text
jobs/<job_id>/source/creative_plan.toml
```

### Cấu trúc Hợp đồng TOML

```toml
[metadata]
title = "Tiêu đề mô tả ngắn"
language = "vi"
platform = "tiktok"
target_duration_seconds = 45
aspect_ratio = "9:16"

[creative]
audience = "..."
goal = "..."
emotional_arc = ["hook", "tension", "turn", "resolution"]
tone = "reflective"
cta = "..."

[voiceover]
script = """
Toàn bộ kịch bản đọc.
"""
delivery = "ấm, rõ, trầm lắng, giọng Cổ Phong"

[thumbnail]
context_text = "BÍ MẬT THÀNH CÔNG"
punch_text = "HỌC NGƯỜI ĐI TRƯỚC"
# Prompt cấu trúc chuẩn TobyFlow AI (Fixed font Montserrat, 36px/60px font size, 15% top margin offset, chuẩn tiếng Việt 100%):
prompt = "High-CTR 9:16 vertical video thumbnail in traditional Cổ Phong minimalist oriental watercolor style on aged parchment paper background. 80% negative space. Positioned at exact 15% top margin offset from top edge (280px from top edge): at the top center, clean modern highly legible fixed 'Montserrat' font header text in 36px font size reads 'BÍ MẬT THÀNH CÔNG'. Directly 20px below it, a rich crimson red stamp seal banner with gold borders contains clean modern bold fixed 'Montserrat' white font text in 60px font size reading 'HỌC NGƯỜI ĐI TRƯỚC'. The text MUST be rendered in 100% accurate Vietnamese language with exact spelling, correct accents, and proper tone marks. DO NOT use calligraphy, brush script, or complex decorative fonts. Use clean straight plain 'Montserrat' lettering only. At the bottom center, an old respected master and a young scholar sit at an ancient wooden Weiqi chess board. Serene, inspiring, high contrast legible typography, aesthetic oriental art masterpiece, 9:16 aspect ratio."

# Mỗi câu = 1 scene — KHÔNG gộp
[[scene_intents]]
id = "SC_01"
start_hint = 0.0
end_hint = 6.0         # ước tính: ~18 từ / 3 từ/giây
narrative_role = "hook"
spoken_text = "Để đối đãi với người mình không thích, bạn không cần phải lật mặt hay lớn tiếng."
# visual_intent: Hình ảnh ẩn dụ của riêng câu này.
visual_intent = "Old Master seated still, one closed fist slowly relaxing into an open palm — the gesture of choosing restraint over reaction. Vast aged parchment background, 80% negative space, minimalist watercolor, 9:16 vertical."
mood = "serene"
preferred_shot_types = ["medium-shot", "still"]
asset_requirements = ["ai_generated"]

[[scene_intents]]
id = "SC_02"
start_hint = 6.0
end_hint = 9.0
narrative_role = "hook"
spoken_text = "Hãy khắc cốt ghi tâm bốn điều sau đây."
visual_intent = "A single open scroll on an empty surface, blank parchment waiting. An ink brush rests beside it, not yet touching. Mood: quiet readiness before wisdom is written. Minimalist watercolor, aged parchment, 9:16 vertical."
mood = "anticipation"
preferred_shot_types = ["still"]
asset_requirements = ["ai_generated"]
```

## Giới hạn độ dài Text Overlay (1080×1920 dọc)

Mỗi `style_ref` có ngưỡng `max_chars` để text vừa 1–2 dòng:

| `style_ref`      | `max_chars` | vai trò điển hình         |
| ---------------- | ----------: | ------------------------- |
| `MAIN_TITLE`     |          22 | hook, reveal callout      |
| `PUNCH_TAG`      |          18 | punchline, viết hoa       |
| `SUBTITLE_BOLD`  |          32 | callout phụ               |
