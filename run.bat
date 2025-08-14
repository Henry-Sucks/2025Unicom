python main.py ^
  --execute ^
  --task "Book a flight ticket from Beijing to Shanghai for tomorrow" ^
  --ui-tree-file ".\data\ui_tree_graph\Unicom App.json" ^
  --target-apk ".\apks\unicom.apk"



@REM python main.py ^
@REM   --explore ^
@REM   --target-apk "C:\Projects\2025Unicom\apks\unicom.apk"


@REM git filter-branch --force --index-filter \ ^
@REM   "git rm --cached --ignore-unmatch docs/演示视频/订明天从北京飞往上海的机票.mp4" \ ^
@REM   --prune-empty --tag-name-filter cat -- --all ^

