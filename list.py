import os

MOD_FILES_DIR = r"F:\Reason\Origin\GO HELL GO GO 素材\PatchOutput" # 你的文件根目录，内部应有Content文件夹
OUTPUT_TXT = r"F:\Reason\Origin\GO HELL GO GO 素材\FileList.txt"

with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
    for root, dirs, files in os.walk(MOD_FILES_DIR):
        for file in files:
            # 1. 源文件的实际磁盘路径
            full_path = os.path.join(root, file)
            # 2. 它在游戏里的虚拟路径，规则是：../../../ + 相对路径
            virtual_path = os.path.relpath(full_path, MOD_FILES_DIR)
            virtual_path = f"../../../{virtual_path}" # 关键格式
            # 写入 txt
            f.write(f'"{full_path}" "{virtual_path}"\n')