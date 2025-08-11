# Data Generation

## Verification

To start the verification process, you should prepare the required apks, emulator, snapshot, eval task path, output_dir and the document dir.
- Download the APKs for all **DroidTask applications** from [here](https://cloud.tsinghua.edu.cn/d/cb5817c334ee4eb08abc/). Extract the files in the **training/apks** folder
- The emulator we use to run AutoDroid-V2 is `Pixel_6_API_30`. Start the emulator first:

```bash
~/Android/Sdk/emulator/emulator -avd Pixel_6_API_30
```

- Run the following command to start AutoDroid-V2 with verification:

```bash
# These are the default parameters:
BEAM_WIDTH=2 # max width for tree search
MAX_DEPTH=2 # max depth for tree search
MAX_VISIT_TIME=4 # max visit times for tree search
DEVICE_SERIAL="emulator-5554" 
SNAPSHOT_NAME="snap_2024-10-31_22-54-15" # Set as the required snapshot name
APK_DIR="apks" # put all apks in apk_dir, 
EVAL_INPUT_PATH="tasks/tasks.json" # droidtask eval path
OUTPUT_DIR="output/tasks_eval" # result path
DOC_DIR="data/droidtask_docs" # document path

python -m bug_process_dfs_search \
--beam_width $BEAM_WIDTH \
--max_visit_time $MAX_VISIT_TIME \
--max_depth $MAX_DEPTH \
--device_serial $DEVICE_SERIAL \
--snapshot_name $SNAPSHOT_NAME \
--apk_dir $APK_DIR \
--eval_input_path $EVAL_INPUT_PATH \
--output_dir $OUTPUT_DIR \
--doc_dir $DOC_DIR
```