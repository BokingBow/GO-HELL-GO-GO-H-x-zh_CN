"""
UE4 本地化工作流工具集 — 合并简化版
======================================
13 个原始脚本合并为统一 CLI，子命令驱动。

工作流:
  export → txt2csv → filter → [外部翻译编辑] → restore → pad → csv2txt → import

工具:
  prepare      复制 .txt+.uasset+.uexp 配对文件到补丁目录
  clean-txt    删除目录下所有 .txt
  rename-new   重命名 _NEW.uasset→.uasset, _NEW.uexp→.uexp
  gen-filelist 生成 PAK 打包文件清单
  patch-analysis 分析补丁与已翻译文件差异
  search-text  在 .uasset/.uexp 中搜索文本

示例:
  python ue4_localization_toolkit.py export --dir ./gohellgo_1_4 --out ./Extract --tool path/to/UE4localizationsTool.exe
  python ue4_localization_toolkit.py txt2csv --input ./Extract --output ./Batch
  python ue4_localization_toolkit.py filter --input ./Batch --output ./Batch2
  python ue4_localization_toolkit.py restore --input ./Batch3 --output ./Fixed --original ./Batch
  python ue4_localization_toolkit.py pad --original ./Batch --fixed ./Fixed --output ./Fixed_Padded
  python ue4_localization_toolkit.py csv2txt --input ./Fixed_Padded --output ./Endnd
  python ue4_localization_toolkit.py import --dir ./ChinesePatch_P --tool path/to/UE4localizationsTool.exe
"""

import os
import csv
import re
import sys
import shutil
import subprocess
import argparse
from pathlib import Path


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def walk_files(root, ext=None):
    """递归遍历目录，返回文件绝对路径列表，可选按扩展名过滤。"""
    results = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if ext is None or f.endswith(ext):
                results.append(os.path.join(dirpath, f))
    results.sort()
    return results


def read_lines(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.readlines()


def write_lines(path, lines):
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.writelines(lines)


def ensure_trailing_newline(path):
    """确保文件末尾有换行符（修复工具需要）。"""
    with open(path, 'rb+') as f:
        f.seek(0, os.SEEK_END)
        if f.tell() == 0:
            return
        f.seek(-1, os.SEEK_END)
        if f.read(1) != b'\n':
            f.write(b'\n')


def relpath_structure(abs_path, base_dir):
    """返回相对于 base_dir 的路径，保持目录结构。"""
    return os.path.relpath(abs_path, base_dir)


# ─────────────────────────────────────────────
# 子命令实现
# ─────────────────────────────────────────────

# ── 1. Export ──

def cmd_export(args):
    """用 UE4LocalizationsTool 从 .uasset 导出文本到 .txt。"""
    tool = args.tool
    target_dir = args.dir
    output_root = args.output
    subfolder = args.subfolder
    filelist = args.filelist

    def scan_dir(folder_path):
        paths = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.uasset'):
                    rel = os.path.relpath(os.path.join(root, file), target_dir)
                    paths.append(rel)
        return paths

    def export_one(rel_path):
        uasset_path = os.path.join(target_dir, rel_path)
        if not os.path.exists(uasset_path):
            print(f"[跳过] 不存在: {rel_path}")
            return False
        out_sub = os.path.join(output_root, os.path.dirname(rel_path))
        ensure_dir(out_sub)
        cmd = [tool, "export", uasset_path]
        print(f"[导出] {rel_path}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if r.returncode != 0:
                print(f"  失败: {r.stderr}")
                return False
            temp_txt = uasset_path + ".txt"
            if os.path.exists(temp_txt):
                target_txt = os.path.join(out_sub, os.path.basename(uasset_path) + ".txt")
                os.rename(temp_txt, target_txt)
                print(f"  输出 → {target_txt}")
                return True
            print(f"  警告: 未生成 {temp_txt}")
            return False
        except Exception as e:
            print(f"  异常: {e}")
            return False

    ensure_dir(output_root)

    if filelist:
        with open(filelist, 'r', encoding='utf-8') as f:
            paths = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    elif subfolder:
        paths = []
        for sf in subfolder:
            full_path = os.path.join(target_dir, sf)
            if not os.path.exists(full_path):
                print(f"[错误] 不存在: {full_path}")
                sys.exit(1)
            paths.extend(scan_dir(full_path))
    else:
        paths = scan_dir(target_dir)

    print(f"共 {len(paths)} 个文件")
    ok = fail = 0
    for p in paths:
        if export_one(p):
            ok += 1
        else:
            fail += 1
        print("-" * 50)
    print(f"\n完成 — 成功: {ok}  失败: {fail}")


# ── 2. Txt2Csv ──

def cmd_txt2csv(args):
    """将 key=value 格式 .txt 转换为 .csv。"""
    input_root = args.input
    output_root = args.output

    if not os.path.exists(input_root):
        print(f"[错误] 不存在: {input_root}")
        sys.exit(1)

    ensure_dir(output_root)
    txt_files = walk_files(input_root, '.txt')
    if not txt_files:
        print(f"未找到 .txt 文件")
        return

    ok = fail = 0
    for txt_path in txt_files:
        rel = relpath_structure(txt_path, input_root)
        csv_path = os.path.join(output_root, rel).replace('.txt', '.csv')
        ensure_dir(os.path.dirname(csv_path))

        rows = []
        with open(txt_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n\r')
                if not line.strip() or line.strip().startswith('#') or line.strip().startswith(';'):
                    continue
                eq = line.find('=')
                if eq == -1:
                    rows.append([line, ''])
                else:
                    rows.append([line[:eq], line[eq + 1:]])

        if not rows:
            print(f"  [跳过] 无数据: {os.path.basename(txt_path)}")
            fail += 1
            continue

        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Key', 'Value'])
            w.writerows(rows)
        print(f"  {os.path.basename(txt_path)} → {len(rows)} 行")
        ok += 1

    print(f"完成 — 成功: {ok}  失败: {fail}")


# ── 3. Filter ──

def cmd_filter(args):
    """只保留指定前缀的行，其余置空。跳过全空文件。"""
    input_dir = args.input
    output_dir = args.output

    KEEP_PREFIXES = ('TEXT', 'Btn', 'Title', 'Name', 'Description',
                     'Comment', 'FuncText', 'ChapterName', 'NextMission',
                     'Guide', 'Start', 'CharacterName', 'SkillName')

    def has_nonascii(val):
        return any(ord(c) > 127 for c in val)

    def should_keep(line):
        if not line.strip():
            return False
        # FuncText: 仅当值含非ASCII字符时才保留
        if line.startswith('FuncText'):
            _, _, val = line.partition(',')
            return has_nonascii(val.strip())
        return line.startswith(KEEP_PREFIXES)

    kept = skipped = 0
    empty_files = []

    for csv_path in walk_files(input_dir, '.csv'):
        rel = relpath_structure(csv_path, input_dir)
        lines = read_lines(csv_path)

        new_lines = [l if should_keep(l) else ',\n' for l in lines]

        # 跳过全空文件（仅剩表头+空行）
        has_content = any(
            l.strip() not in ('', ',') for l in new_lines[1:]
        )
        if not has_content:
            empty_files.append(rel)
            print(f"[跳过] {rel}")
            skipped += 1
            continue

        out_path = os.path.join(output_dir, rel)
        ensure_dir(os.path.dirname(out_path))
        write_lines(out_path, new_lines)
        print(f"[保留] {rel}")
        kept += 1

    print(f"保留: {kept}  跳过(全空): {skipped}")
    if empty_files:
        path = os.path.join(output_dir, '_skipped_empty.txt')
        print(f"跳过的文件列表已写入: {path}")
        write_lines(path, [f + '\n' for f in empty_files])

    print(f"保留: {kept}  跳过(全空): {skipped}")
    if empty_files:
        path = os.path.join(output_dir, '_skipped_empty.txt')
        print(f"跳过的文件列表已写入: {path}")
        write_lines(path, [f + '\n' for f in empty_files])


# ── 4. Restore ──

def cmd_restore(args):
    """修复 Translator++ 导出的 CSV：恢复空白行，去除引号。"""
    input_dir = args.input
    output_dir = args.output
    original_dir = args.original

    def fix_one(input_path, output_path, original_path):
        in_lines = read_lines(input_path)
        orig_lines = read_lines(original_path)
        min_n = min(len(in_lines), len(orig_lines))
        diff = len(in_lines) - len(orig_lines)
        if diff > 0:
            print(f"  ❌ 多{diff}行，需人工检查")
        elif diff < 0:
            print(f"  ⚠️ 少{-diff}行，pad可补")

        out = []
        for i in range(min_n):
            il = in_lines[i].rstrip('\n')
            ol = orig_lines[i].rstrip('\n')
            if il == '"" ,""' or il == '"",""':
                out.append(ol)
            elif il.strip():
                m = re.match(r'"([^"]*)"\s*,\s*"([^"]*)"', il)
                if m:
                    out.append(f"{m.group(1)},{m.group(2)}")
                else:
                    out.append(il)
            else:
                out.append(ol)

        ensure_dir(os.path.dirname(output_path))
        write_lines(output_path, [l + '\n' for l in out])
        print(f"  完成: {os.path.basename(input_path)}")
        return diff

    ok = fewer = more = 0
    for csv_path in walk_files(input_dir, '.csv'):
        rel = relpath_structure(csv_path, input_dir)
        out_path = os.path.join(output_dir, rel)
        orig_path = os.path.join(original_dir, rel)
        if not os.path.exists(orig_path):
            print(f"跳过 {rel}: 原始文件不存在")
            continue
        print(f"处理: {rel}")
        d = fix_one(csv_path, out_path, orig_path)
        if d > 0:
            more += 1
        elif d < 0:
            fewer += 1
        else:
            ok += 1

    print(f"\n=== 汇总: 一致 {ok}  少行(可补) {fewer}  多行(需人工) {more} ===")


# ── 5. Pad ──

def cmd_pad(args):
    """用原始文件补齐修复文件中缺失的行。"""
    orig_dir = args.original
    fixed_dir = args.fixed
    output_dir = args.output

    # 预处理：补末尾换行符
    for csv_path in walk_files(fixed_dir, '.csv'):
        ensure_trailing_newline(csv_path)

    mismatched = []
    total_pad = 0

    for csv_path in walk_files(orig_dir, '.csv'):
        rel = relpath_structure(csv_path, orig_dir)
        fixed_path = os.path.join(fixed_dir, rel)
        if not os.path.exists(fixed_path):
            print(f"  ⚠️ {rel}: 修复文件不存在")
            continue

        out_path = os.path.join(output_dir, rel) if output_dir else fixed_path
        if output_dir:
            ensure_dir(os.path.dirname(out_path))

        orig_lines = read_lines(csv_path)
        fixed_lines = read_lines(fixed_path)

        if len(fixed_lines) == len(orig_lines):
            print(f"  ✅ {rel}: 行数一致 ({len(orig_lines)})")
            if output_dir:
                write_lines(out_path, fixed_lines)
            continue

        if len(fixed_lines) < len(orig_lines):
            diff = len(orig_lines) - len(fixed_lines)
            print(f"  ⚠️ {rel}: 补齐 {diff} 行")
            padded = fixed_lines + orig_lines[-diff:]
            write_lines(out_path, padded)
            total_pad += diff
        else:
            diff = len(fixed_lines) - len(orig_lines)
            print(f"  ❌ {rel}: 多出 {diff} 行，需人工检查")
            mismatched.append((rel, diff))

    print(f"\n补齐总计: {total_pad} 行")
    if mismatched:
        print(f"需人工检查 ({len(mismatched)} 个):")
        for r, d in mismatched:
            print(f"  {r}: 多出 {d} 行")


# ── 6. Csv2Txt ──

def cmd_csv2txt(args):
    """将 .csv 转换回 key=value 格式 .txt。空白行从原始 .txt 恢复。"""
    input_root = args.input
    output_root = args.output
    origin_root = args.origin
    ensure_dir(output_root)

    for csv_path in walk_files(input_root, '.csv'):
        rel = relpath_structure(csv_path, input_root)
        txt_path = os.path.join(output_root, rel).replace('.csv', '.txt')
        ensure_dir(os.path.dirname(txt_path))

        # 读取原始 .txt（用与 txt2csv 相同的规则解析，行数才能对齐）
        orig_pairs = []
        if origin_root:
            orig_txt = os.path.join(origin_root, rel).replace('.csv', '.txt')
            if os.path.exists(orig_txt):
                for line in read_lines(orig_txt):
                    line = line.rstrip('\n\r')
                    if not line.strip() or line.strip().startswith('#') or line.strip().startswith(';'):
                        continue
                    orig_pairs.append(line)

        rows = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader, None)  # 跳过表头
            for i, row in enumerate(reader):
                if len(row) >= 2 and row[0].strip():
                    rows.append(f"{row[0]}={row[1]}")
                elif i < len(orig_pairs):
                    rows.append(orig_pairs[i])

        if rows:
            write_lines(txt_path, [l + '\n' for l in rows])
            print(f"  {rel} → {len(rows)} 行")


# ── 7. Import ──

def get_git_root(path):
    """返回 git 仓库根目录（Windows 有效路径），或 None。"""
    try:
        r = subprocess.run(
            ["git", "-C", os.path.abspath(path), "rev-parse", "--show-toplevel"],
            capture_output=True, encoding='utf-8', check=False
        )
        if r.returncode == 0:
            return os.path.normpath(r.stdout.strip())
    except Exception:
        pass
    return None


def import_one(rel, txt_dir, project_dir, output_dir, tool):
    """导入单个 .txt 到 PatchOutput。返回 True 成功 / False 失败。"""
    txt_path = os.path.join(txt_dir, rel)
    uasset_rel = rel.replace('.uasset.txt', '.uasset')
    uasset_src = os.path.join(project_dir, uasset_rel)
    if not os.path.exists(uasset_src):
        print(f"⚠️ 跳过 {rel} — 对应 .uasset 不存在")
        return False

    dst_uasset = os.path.join(output_dir, uasset_rel)
    dst_uexp = dst_uasset.replace('.uasset', '.uexp')
    dst_txt = os.path.join(output_dir, rel)
    ensure_dir(os.path.dirname(dst_uasset))
    shutil.copy2(uasset_src, dst_uasset)
    uexp_src = uasset_src.replace('.uasset', '.uexp')
    if os.path.exists(uexp_src):
        shutil.copy2(uexp_src, dst_uexp)
    shutil.copy2(txt_path, dst_txt)

    # 导入
    cmd = [tool, "import", dst_txt]
    print(f"导入: {rel}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if r.returncode == 0:
            print(f"  ✅ 成功")
            success = True
        else:
            print(f"  ❌ {r.stderr}")
            success = False
    except Exception as e:
        print(f"  ❌ {e}")
        success = False

    # 删 .txt
    if os.path.exists(dst_txt):
        os.remove(dst_txt)

    # _NEW 重命名
    for suffix in ['.uasset', '.uexp']:
        new_f = dst_uasset.replace('.uasset', f'_NEW{suffix}')
        if os.path.exists(new_f):
            target = dst_uasset if suffix == '.uasset' else dst_uexp
            if os.path.exists(target):
                os.remove(target)
            os.rename(new_f, target)

    return success


def cmd_import(args):
    """全量导入：将所有 .txt 导入回 .uasset，输出到新目录。"""
    txt_dir = args.dir
    if not os.path.exists(txt_dir):
        print(f"[错误] 不存在: {txt_dir}")
        sys.exit(1)

    ok = fail = 0
    for txt_path in walk_files(txt_dir, '.txt'):
        rel = relpath_structure(txt_path, txt_dir)
        imported = import_one(rel, txt_dir, args.project_dir, args.output, args.tool)
        if imported:
            ok += 1
        else:
            fail += 1

    print(f"\n完成 — 成功: {ok}  失败: {fail}")
    print(f"最终输出: {args.output}")


def cmd_import_changed(args):
    """增量导入：仅处理 git 变更的 .txt，从 PatchOutput 删除已移除的文件。"""
    txt_dir = args.dir
    if not os.path.exists(txt_dir):
        print(f"[错误] 不存在: {txt_dir}")
        sys.exit(1)

    repo_root = get_git_root(txt_dir)
    if not repo_root:
        print("[错误] 不是 git 仓库。请使用 `import` 命令全量导入，或使用 --force 跳过检测。")
        sys.exit(1)
    # Windows 下 git rev-parse 可能返回正斜杠路径
    repo_root = repo_root.replace('/', os.sep)

    if args.force:
        print("--force 模式: 跳过 git 检测，全量导入")
        ok = fail = 0
        for txt_path in walk_files(txt_dir, '.txt'):
            rel = relpath_structure(txt_path, txt_dir)
            imported = import_one(rel, txt_dir, args.project_dir, args.output, args.tool)
            if imported:
                ok += 1
            else:
                fail += 1
        print(f"\n完成 — 成功: {ok}  失败: {fail}")
        return

    txt_abs = os.path.abspath(txt_dir)
    txt_rel = os.path.relpath(txt_abs, repo_root).replace('\\', '/')
    if not txt_rel.endswith('/'):
        txt_rel += '/'

    since = args.since

    def git_out(cmd):
        """运行 git 命令，返回 stdout（utf-8 解码）。"""
        r = subprocess.run(cmd, capture_output=True, encoding='utf-8', cwd=repo_root, check=False)
        return r

    # 检查 Txts_ready 是否被 git 跟踪
    r_check = git_out(["git", "ls-files", txt_rel])
    tracked = bool(r_check.stdout.strip())
    if not tracked and not args.force:
        print(f"[警告] git 中没有跟踪 {txt_rel} 中的文件。运行 `git add Txts_ready` 后提交可修复。")

    # 新增/修改
    r_am = git_out(["git", "diff", "--name-only", "--diff-filter=AM", since, "--", txt_rel])
    if r_am.returncode != 0:
        print(f"[错误] git diff 失败: {r_am.stderr}")
        sys.exit(1)
    changed = [l.strip() for l in r_am.stdout.splitlines() if l.strip().endswith('.txt')]

    # 删除
    r_d = git_out(["git", "diff", "--name-only", "--diff-filter=D", since, "--", txt_rel])
    deleted = [l.strip() for l in r_d.stdout.splitlines() if l.strip().endswith('.txt')]

    if not changed and not deleted:
        print("无变更，跳过")
        return

    # 从 PatchOutput 删除对应 .uasset/.uexp
    for rel in deleted:
        uasset_rel = rel.replace('.uasset.txt', '.uasset')
        for ext in ['.uasset', '.uexp']:
            p = os.path.join(args.output, uasset_rel.replace('.uasset', ext))
            if os.path.exists(p):
                os.remove(p)
                print(f"🗑️ 删除: {rel} ({ext})")

    # 新增/修改
    ok = fail = 0
    for rel in changed:
        imported = import_one(rel, txt_dir, args.project_dir, args.output, args.tool)
        if imported:
            ok += 1
        else:
            fail += 1

    summary = f"\n完成 — 成功: {ok}  失败: {fail}"
    if deleted:
        summary += f"  从 PatchOutput 移除: {len(deleted)} 个文件"
    print(summary)


# ── 8. Prepare (chou) ──

def cmd_prepare(args):
    """将 .txt 及相关 .uasset/.uexp 复制到目标目录。"""
    txt_dir = args.txt_dir
    uasset_dir = args.uasset_dir
    output_dir = args.output
    overwrite = args.overwrite

    def should_skip(dst):
        return not overwrite and os.path.exists(dst)

    stats = {ext: {'copied': 0, 'skipped': 0, 'missing': 0} for ext in ['txt', 'uasset', 'uexp']}

    for txt_path in walk_files(txt_dir, '.txt'):
        base = os.path.basename(txt_path)[:-4]  # 去掉 .txt
        rel = relpath_structure(txt_path, txt_dir)

        # .txt
        dst_txt = os.path.join(output_dir, rel)
        ensure_dir(os.path.dirname(dst_txt))
        if should_skip(dst_txt):
            stats['txt']['skipped'] += 1
        else:
            shutil.copy2(txt_path, dst_txt)
            stats['txt']['copied'] += 1

        # .uasset
        src_uasset = os.path.join(uasset_dir, rel).replace('.txt', '')
        dst_uasset = os.path.join(output_dir, rel).replace('.txt', '')
        for ext, key in [('.uasset', 'uasset'), ('.uexp', 'uexp')]:
            src = src_uasset + ext
            dst = dst_uasset + ext
            if os.path.exists(src):
                if should_skip(dst):
                    stats[key]['skipped'] += 1
                else:
                    ensure_dir(os.path.dirname(dst))
                    shutil.copy2(src, dst)
                    stats[key]['copied'] += 1
            else:
                if key != 'uexp':  # .uexp 缺失不报错
                    stats[key]['missing'] += 1

    print("准备完成报告:")
    print(f"  .txt:    复制 {stats['txt']['copied']}  跳过 {stats['txt']['skipped']}")
    print(f"  .uasset: 复制 {stats['uasset']['copied']}  跳过 {stats['uasset']['skipped']}  缺失 {stats['uasset']['missing']}")
    print(f"  .uexp:   复制 {stats['uexp']['copied']}  跳过 {stats['uexp']['skipped']}  缺失 {stats['uexp']['missing']}")


# ── 9. Clean Txt ──

def cmd_clean_txt(args):
    """递归删除指定目录下所有 .txt 文件。"""
    target = args.dir
    if not os.path.exists(target):
        print(f"错误: 不存在 {target}")
        return
    count = 0
    for root, _, files in os.walk(target):
        for f in files:
            if f.endswith('.txt'):
                os.remove(os.path.join(root, f))
                count += 1
    print(f"删除 {count} 个 .txt 文件")


# ── 10. Rename New ──

def cmd_rename_new(args):
    """将 _NEW.uasset / _NEW.uexp 重命名为 .uasset / .uexp。"""
    src_dir = args.input
    out_dir = args.output
    ensure_dir(out_dir)

    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith('_NEW.uasset') or f.endswith('_NEW.uexp'):
                new_name = f.replace('_NEW.uasset', '.uasset').replace('_NEW.uexp', '.uexp')
                rel = relpath_structure(root, src_dir)
                dst = os.path.join(out_dir, rel, new_name)
                ensure_dir(os.path.dirname(dst))
                shutil.copy2(os.path.join(root, f), dst)
                print(f"{f} → {new_name}")

    print(f"输出: {out_dir}")


# ── 11. Gen File List ──

def cmd_gen_filelist(args):
    """生成 PAK 打包文件清单（../../../相对路径 格式）。"""
    root_dir = args.dir
    out_path = args.output

    with open(out_path, 'w', encoding='utf-8') as f:
        for file_path in walk_files(root_dir):
            rel = relpath_structure(file_path, root_dir)
            virtual = f"../../../{rel}"
            f.write(f'"{file_path}" "{virtual}"\n')

    print(f"清单生成: {out_path} ({sum(1 for _ in open(out_path))} 行)")


# ── 12. Patch Analysis ──

def cmd_patch_analysis(args):
    """分析补丁目录 vs 已翻译文件清单。"""
    patch_dir = args.patch_dir
    filelist_path = args.filelist
    output_base = args.output
    ensure_dir(output_base)

    # 读取翻译清单
    with open(filelist_path, 'r', encoding='utf-8') as f:
        translated = {line.strip() for line in f if line.strip()}

    # 遍历补丁目录
    patch_files = set()
    for root, _, files in os.walk(patch_dir):
        for f in files:
            rel = relpath_structure(os.path.join(root, f), patch_dir)
            patch_files.add(rel)

    need_update = patch_files & translated
    need_review = patch_files - translated
    removed = translated - patch_files

    print(f"已翻译: {len(translated)}  补丁中: {len(patch_files)}")
    print(f"需更新翻译: {len(need_update)}  需审查: {len(need_review)}  已移除: {len(removed)}")

    # 输出分类文件
    for name, items in [('need_update', need_update), ('need_review', need_review), ('removed', removed)]:
        with open(os.path.join(output_base, f"{name}.txt"), 'w', encoding='utf-8') as f:
            for p in sorted(items):
                f.write(p + '\n')

    # 复制需更新文件
    update_dir = os.path.join(output_base, "need_update_files")
    for rel in need_update:
        src = os.path.join(patch_dir, rel)
        dst = os.path.join(update_dir, rel)
        ensure_dir(os.path.dirname(dst))
        shutil.copy2(src, dst)

    print(f"输出: {output_base}")


# ── 13. Search Text ──

def cmd_search_text(args):
    """在 .uasset/.uexp 中搜索文本（UTF-16-LE 和 UTF-8 编码）。"""
    text = args.text
    search_dir = args.dir
    bytes_u16 = text.encode('utf-16-le')
    bytes_utf8 = text.encode('utf-8')

    found = 0
    for root, _, files in os.walk(search_dir):
        for f in files:
            if f.endswith('.uasset') or f.endswith('.uexp'):
                path = os.path.join(root, f)
                try:
                    with open(path, 'rb') as fh:
                        content = fh.read()
                        if bytes_u16 in content or bytes_utf8 in content:
                            print(f"命中: {path}")
                            found += 1
                except Exception:
                    pass

    print(f"扫描完成，共 {found} 个文件包含 [{text}]")


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UE4 本地化工作流工具集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # 1. export
    p = sub.add_parser('export', help='从 .uasset 导出文本到 .txt')
    p.add_argument('--dir', required=True, help='.uasset 目录')
    p.add_argument('--tool', required=True, help='UE4localizationsTool.exe 路径')
    p.add_argument('--output', required=True, help='输出目录')
    p.add_argument('--subfolder', action='append', help='扫描子文件夹（相对路径），可多次指定')
    p.add_argument('--filelist', help='文件清单（每行一个相对路径）')

    # 2. txt2csv
    p = sub.add_parser('txt2csv', help='.txt (key=value) → .csv')
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)

    # 3. filter
    p = sub.add_parser('filter', help='只保留 TEXT/Btn/Title/Name 等前缀行，其余置空')
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)

    # 4. restore
    p = sub.add_parser('restore', help='修复 Translator++ 导出 CSV')
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--original', required=True, help='原始 CSV 目录')

    # 5. pad
    p = sub.add_parser('pad', help='补齐修复文件的行数')
    p.add_argument('--original', required=True)
    p.add_argument('--fixed', required=True)
    p.add_argument('--output', help='输出目录（默认覆盖 fixed）')

    # 6. csv2txt
    p = sub.add_parser('csv2txt', help='.csv → .txt (key=value)，空白行从原始 .txt 恢复')
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--origin', help='原始导出 .txt 目录（用于恢复空白行）')

    # 7. import
    p = sub.add_parser('import', help='.txt 导入回 .uasset，输出新目录，不修改原文件')
    p.add_argument('--dir', required=True, help='含 .uasset.txt 的目录（如 ./Txts_ready）')
    p.add_argument('--tool', required=True, help='UE4localizationsTool.exe 路径')
    p.add_argument('--project-dir', required=True, help='原始 .uasset 项目目录（如 ./gohellgo）')
    p.add_argument('--output', required=True, help='输出目录（仅含替换过的文件）')

    # 7b. import-changed
    p = sub.add_parser('import-changed', help='增量导入：仅处理 git 变更的 .txt，删除已移除文件')
    p.add_argument('--dir', required=True, help='含 .uasset.txt 的目录（如 ./Txts_ready）')
    p.add_argument('--tool', required=True, help='UE4localizationsTool.exe 路径')
    p.add_argument('--project-dir', required=True, help='原始 .uasset 项目目录（如 ./gohellgo）')
    p.add_argument('--output', required=True, help='PatchOutput 持久化目录')
    p.add_argument('--since', default='HEAD', help='git diff 对比基线（默认 HEAD，对比工作区）')
    p.add_argument('--force', action='store_true', help='跳过 git 检测，全量导入')

    # 8. prepare
    p = sub.add_parser('prepare', help='复制 .txt+.uasset+.uexp 配对文件')
    p.add_argument('--txt-dir', required=True, help='翻译后 .txt 目录')
    p.add_argument('--uasset-dir', required=True, help='源 .uasset 目录')
    p.add_argument('--output', required=True, help='输出目录')
    p.add_argument('--overwrite', action='store_true', help='覆盖已有文件')

    # 9. clean-txt
    p = sub.add_parser('clean-txt', help='删除目录下所有 .txt')
    p.add_argument('--dir', required=True)

    # 10. rename-new
    p = sub.add_parser('rename-new', help='_NEW 文件重命名')
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)

    # 11. gen-filelist
    p = sub.add_parser('gen-filelist', help='生成 PAK 打包文件清单')
    p.add_argument('--dir', required=True)
    p.add_argument('--output', required=True)

    # 12. patch-analysis
    p = sub.add_parser('patch-analysis', help='分析补丁差异')
    p.add_argument('--patch-dir', required=True)
    p.add_argument('--filelist', required=True, help='已翻译文件清单')
    p.add_argument('--output', required=True)

    # 13. search-text
    p = sub.add_parser('search-text', help='在 .uasset/.uexp 中搜索文本')
    p.add_argument('--text', required=True)
    p.add_argument('--dir', required=True)

    # ── 分发 ──
    cmd_map = {
        'export': cmd_export,
        'txt2csv': cmd_txt2csv,
        'filter': cmd_filter,
        'restore': cmd_restore,
        'pad': cmd_pad,
        'csv2txt': cmd_csv2txt,
        'import': cmd_import,
        'import-changed': cmd_import_changed,
        'prepare': cmd_prepare,
        'clean-txt': cmd_clean_txt,
        'rename-new': cmd_rename_new,
        'gen-filelist': cmd_gen_filelist,
        'patch-analysis': cmd_patch_analysis,
        'search-text': cmd_search_text,
    }

    args = parser.parse_args()
    cmd_map[args.command](args)


if __name__ == '__main__':
    main()
