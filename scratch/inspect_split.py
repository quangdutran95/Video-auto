import re

text_content = """Có một nghịch lý trong cuộc sống mà rất nhiều người từng trải qua. Chúng ta thường nghĩ rằng chỉ cần có thêm một chút tiền, một công việc tốt hơn hay một ngôi nhà lớn hơn thì mình sẽ hạnh phúc. Thế nhưng, khi đạt được điều đó, chúng ta lại nhanh chóng đặt ra một mục tiêu mới và tiếp tục cảm thấy mình vẫn còn thiếu.

Thực ra, hạnh phúc không nằm ở việc sở hữu tất cả mọi thứ. Hạnh phúc là biết trân trọng những gì mình đang có, từ sức khỏe, gia đình, những người yêu thương cho đến từng cơ hội được học hỏi và trưởng thành mỗi ngày. Khi biết biết ơn hiện tại, bạn sẽ cảm nhận được niềm vui ngay trên hành trình của mình, thay vì chỉ chờ đợi ở đích đến.

Điều đó không có nghĩa là từ bỏ ước mơ hay ngừng cố gắng. Biết đủ không phải là hài lòng với sự trì trệ, mà là không để lòng tham hay sự so sánh lấy đi sự bình yên trong tâm hồn. Bạn vẫn có thể nỗ lực để trở thành phiên bản tốt hơn của chính mình, nhưng đồng thời cũng biết tận hưởng từng bước chân trên con đường ấy. Bởi cuộc sống ý nghĩa nhất không phải là có tất cả, mà là vừa không ngừng vươn lên, vừa biết mỉm cười với những gì mình đang có."""

def split_text_by_length(text, max_len=150):
    parts = re.split(r'([.,\n!?]+)', text)
    chunks = []
    current_chunk = ""
    for part in parts:
        if re.match(r'[.,\n!?]+', part):
            current_chunk += part
            if len(current_chunk.strip()) > max_len:
                words = current_chunk.strip().split()
                temp = ""
                for w in words:
                    if len(temp + " " + w) > max_len:
                        if temp.strip():
                            chunks.append(temp.strip())
                        temp = w
                    else:
                        temp += " " + w
                if temp.strip():
                    current_chunk = temp
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = ""
        else:
            current_chunk += part
    if current_chunk.strip():
        words = current_chunk.strip().split()
        temp = ""
        for w in words:
            if len(temp + " " + w) > max_len:
                if temp.strip():
                    chunks.append(temp.strip())
                temp = w
            else:
                temp += " " + w
        if temp.strip():
            chunks.append(temp.strip())
    return [c for c in chunks if c]

sentences = split_text_by_length(text_content, max_len=150)
for i, s in enumerate(sentences):
    print(f"{i+1}: {s} (len={len(s)})")
