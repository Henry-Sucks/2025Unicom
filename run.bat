@REM python main.py ^
@REM   --execute ^
@REM   --task "Book a flight ticket from Beijing to Shanghai for tomorrow" ^
@REM   --ui-tree-file ".\data\ui_tree_graph\Unicom App.json" ^
@REM   --target-apk ".\apks\unicom.apk"



@REM python main.py ^
@REM   --explore ^
@REM   --target-apk "C:\Projects\2025Unicom\apks\unicom.apk"


git filter-branch --force --index-filter \ ^
  "git rm --cached --ignore-unmatch docs/演示视频/订明天从北京飞往上海的机票.mp4" \ ^
  --prune-empty --tag-name-filter cat -- --all ^

