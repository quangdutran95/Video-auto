---
name: video-co-phong-render-template-v1
description: Khởi tạo template render video phong cách Cổ Phong phiên bản v1 (chữ Serif truyền thống, viền vàng đồng, triện đỏ thương hiệu) cho các job có sẵn render plan và timestamps.
---

# Video Cổ Phong Render Template

Skill này là **render-style template** chịu trách nhiệm tạo ra mã nguồn Remotion mang phong cách hoài cổ Cổ Phong từ render plan và timestamps có sẵn.

## Ranh giới quan trọng

Template này chỉ chịu trách nhiệm render-style, không quyết định semantic mapping hay tìm asset mới. Các dữ liệu đó thuộc về các stage upstream trong pipeline của job.

## Khi nào dùng

Dùng skill này khi job đã có:
- `source/render_plan.toml`
- `source/transcript_word_level.toml`
- Visual timeline/mapping đã được tạo sẵn.

## Inputs

```text
--job jobs/<job_id>
--brand "Tri Thức Là Vàng"
--subtitle-top-pct 45
--highlight-color "#d4af37"
```

## Instantiate

```bash
.venv/bin/python skills/video-co-phong-render-template/scripts/instantiate.py \
  --job jobs/<job_id> \
  --brand "Tri Thức Là Vàng" \
  --subtitle-top-pct 45
```

Script sẽ:
1. Copy Remotion template `templates/video-co-phong` vào `jobs/<job_id>/remotion`.
2. Copy các clip đã có trong `source/render_plan.toml` vào `remotion/public/assets`.
3. Copy voice audio đã có vào `remotion/public/assets`.
4. Chuyển word-level transcript thành `template-props.json` (ngắt dòng 2 câu/màn hình).
5. Ghi `source/template_params.toml`.

## Render

```bash
cd jobs/<job_id>/remotion
npm install
npm run still
npm run render
```

## Style knobs

- `brand`: Tên triện đỏ (con dấu đỏ truyền thống hiển thị ở đáy khung).
- `subtitleTopPct`: vị trí subtitle theo phần trăm chiều cao canvas, mặc định `45`.
- `highlightColor`: màu vàng đồng hoài cổ (`#d4af37`).

## Quality expectations

- Video output 1080x1920, 30fps, phông chữ hoài cổ Noto Serif.
- Viền khung bo góc vàng đồng (`#c5a059`).
- Triện đỏ (con dấu vuông) hiển thị tên thương hiệu nằm ở đáy khung và hơi nghiêng một góc tự nhiên.
