"""
Replace Name_* and Description_* lines by line position, not by key.
All rows share same GUID key, so position-based matching is correct.
"""

EXPORTS = r"Exports/Content/Anzu/DataTable/ADV/DT_AnzuScenarioMaster.uasset.txt"
TXTS_READY = r"Txts_ready/Content/Anzu/DataTable/ADV/DT_AnzuScenarioMaster.uasset.txt"

with open(EXPORTS, 'r', encoding='utf-8') as f:
    exports_lines = f.readlines()

with open(TXTS_READY, 'r', encoding='utf-8') as f:
    txts_lines = f.readlines()

replaced = 0
for i in range(min(len(exports_lines), len(txts_lines))):
    export_line = exports_lines[i].rstrip('\n').rstrip('\r')
    txts_line = txts_lines[i].rstrip('\n').rstrip('\r')
    if (export_line.startswith("Name_") or export_line.startswith("Description_")) and export_line != txts_line:
        txts_lines[i] = exports_lines[i]  # keep original newline from Exports
        replaced += 1

print(f"Replaced {replaced} lines")

with open(TXTS_READY, 'w', encoding='utf-8', newline='\n') as f:
    f.writelines(txts_lines)

print("Done")
