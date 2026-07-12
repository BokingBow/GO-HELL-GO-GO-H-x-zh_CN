import os

# ======= 配置区域 =======
TARGET_TEXT = "日付を進めますか"  # 你要找的残留日文/文本
SEARCH_DIR = r"./gohellgo/Content"  # 换成你的子文件夹相对路径或绝对路径
# =======================

# 虚幻引擎中硬编码字符串常用的两种字节编码
bytes_u16 = TARGET_TEXT.encode('utf-16-le') 
bytes_utf8 = TARGET_TEXT.encode('utf-8')

print(f"正在全量扫描文件夹，寻找包含【{TARGET_TEXT}】的 uasset/uexp 文件...")

found_count = 0
for root, dirs, files in os.walk(SEARCH_DIR):
    for file in files:
        if file.endswith('.uasset') or file.endswith('.uexp'):
            path = os.path.join(root, file)
            try:
                with open(path, 'rb') as f:
                    content = f.read()
                    if bytes_u16 in content or bytes_utf8 in content:
                        print(f"【命中目标】: {path}")
                        found_count += 1
            except Exception as e:
                pass

print(f"扫描结束，共找到 {found_count} 个可疑文件。")