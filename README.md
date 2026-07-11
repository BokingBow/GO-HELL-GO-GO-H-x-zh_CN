# _Go Hell Go_ Translation (zh_CN)

___《ゴーヘルゴー》___ 汉化补丁。  
__目前仍在测试中。很有可能出现报错。请尽可能注意存档，避免数据丢失。__  
__~~已经确认暂不支持官方发布的升级用补丁，若强行加载将导致游戏崩溃。（可能）将在未来修复。~~__已支持，请查看 Release 说明。__

请在 Release 中下载 `ChineseTest_1_P.pak` ，将其置于以下路径：  
`.\gohellgo\Content\Paks`

本汉化使用了 [霞鹜新晰黑](https://github.com/lxgw/LxgwNeoXiHei) 与 [霞鹜漫黑](https://github.com/lxgw/LxgwMarkerGothic) 。

## 目录结构

```
├── ue4_localization_toolkit.py   # 核心工具箱（CLI，子命令驱动）
├── first.bat                      # 一键增量导入变更
├── oneclick.bat                   # 全流程：导入 → 生成清单 → 打包 PAK
├── list.py                        # 生成 UnrealPak 打包清单
├── findtext.py                    # 在 uasset/uexp 中搜索残留文本
│
├── gohellgo/                      # 游戏解包目录（原始 uasset）
├── Exports/                       # 原始导出 txt 存档
├── Txts_ready/                    # 翻译后的 txt（导入源）
├── PatchOutput/                   # 导入输出的补丁文件
│
├── CSVs/                          # 导出 CSV（给翻译用）
├── CSVs_filtered/                 # 过滤后的 CSV
├── CSVs_translated/               # 翻译完成的 CSV
├── CSVs_restored/                 # 修复后的 CSV
├── CSVs_padded/                   # 补行后的 CSV
│
└── Patch/                         # 其他补丁暂存
```

## 工作流

```
export → txt2csv → filter → [外部翻译] → restore → pad → csv2txt → import → PAK
```

### 完整流程

```bash
# 1. 从 uasset 导出文本
python ue4_localization_toolkit.py export --dir ./gohellgo_1_4 --out ./Extract --tool path/to/UE4localizationsTool.exe

# 2. txt → csv（方便翻译）
python ue4_localization_toolkit.py txt2csv --input ./Extract --output ./CSVs

# 3. 过滤：只留 TEXT/Btn/Title/Name/Description 等翻译行
python ue4_localization_toolkit.py filter --input ./CSVs --output ./CSVs_filtered

# 4. [翻译] — 在 Excel/Google Sheets 中编辑 CSV

# 5. 修复 Translator++ 导出格式问题
python ue4_localization_toolkit.py restore --input ./CSVs_translated --output ./CSVs_restored --original ./CSVs

# 6. 补齐行数（确保与原文件行数一致）
python ue4_localization_toolkit.py pad --original ./CSVs --fixed ./CSVs_restored --output ./CSVs_padded

# 7. csv → txt（恢复 key=value 格式）
python ue4_localization_toolkit.py csv2txt --input ./CSVs_padded --output ./Txts_ready

# 8. 导入回 uasset
python ue4_localization_toolkit.py import --dir ./Txts_ready --tool path/to/UE4localizationsTool.exe --project-dir ./gohellgo --output ./PatchOutput/gohellgo
```

### 增量导入（日常用）

```bash
# first.bat：导入 Txts_ready 中有 git 变更的文件
python ue4_localization_toolkit.py import-changed --dir ./Txts_ready --tool "path/to/UE4localizationsTool.exe" --project-dir ./gohellgo --output ./PatchOutput/gohellgo
```

支持新文件（未跟踪的 .txt 也会自动发现）。

### 打包 PAK

```bash
# oneclick.bat：导入 → 生成清单 → UnrealPak 打包
# 输出: gohellgo/Content/Paks/ChineseTest_1_P.pak
```

## 工具命令一览

| 命令 | 说明 |
|------|------|
| `export` | 从 .uasset 导出文本到 .txt |
| `txt2csv` | .txt → .csv（合并键值对） |
| `filter` | 只保留翻译前缀行，其余置空 |
| `restore` | 修复 Translator++ 导出 CSV |
| `pad` | 补齐修复文件的行数 |
| `csv2txt` | .csv → .txt（key=value） |
| `import` | .txt 导入回 .uasset |
| `import-changed` | 增量导入（git 变更 + 新文件） |
| `prepare` | 复制 .txt+.uasset+.uexp 配对文件 |
| `clean-txt` | 删除目录下所有 .txt |
| `rename-new` | 重命名 _NEW 文件 |
| `gen-filelist` | 生成 PAK 打包清单 |
| `patch-analysis` | 分析补丁与已翻译文件差异 |
| `search-text` | 在 .uasset/.uexp 中搜索文本 |

## 依赖

- Python 3.7+
- [UE4localizationsTool](https://github.com/DrAppleXX/UE4localizationsTool)（[下载](https://github.com/DrAppleXX/UE4localizationsTool/releases)）
- UnrealPak（UE 4.27 引擎自带）

## 环境

- 游戏：ゴーヘルゴーゴー 業 つきおとしてゴー ver.1.06
- 引擎：UE 4.27
- PAK 路径：`gohellgo/Content/Paks/ChineseTest_1_P.pak`
