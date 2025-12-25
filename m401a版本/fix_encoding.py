# save as fix_encoding.py
import chardet

file_path = "/root/python/rainyun.py"

# 读取原始文件
with open(file_path, 'rb') as f:
    raw_data = f.read()

# 检测编码
detected = chardet.detect(raw_data)
encoding = detected['encoding']
confidence = detected['confidence']

print(f"Detected encoding: {encoding} (confidence: {confidence:.2%})")

# 如果检测到非 UTF-8，转为 UTF-8
if encoding and 'utf' not in encoding.lower():
    try:
        text = raw_data.decode(encoding)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print("✅ File converted to UTF-8 successfully!")
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
else:
    print("✅ File is already UTF-8.")