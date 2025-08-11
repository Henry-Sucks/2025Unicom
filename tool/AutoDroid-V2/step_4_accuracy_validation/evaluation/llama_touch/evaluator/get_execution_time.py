import json
import os


data_folders = ["data/final/general", "data/final/googleapps", "data/final/install"]
all_times = []
for folder in data_folders:
    for trace in os.listdir(folder):
        runtime = json.load(open(f"{folder}/{trace}/agent_logs/runtime.json"))
        if len(runtime) == 0:
            continue
        execution_time = runtime[0]["execution"]
        actions_save_time = json.load(open(f"{folder}/{trace}/agent_logs/agent_actions_save_time.json"))
        for action in actions_save_time:
            execution_time = execution_time - action["log_time"]
        all_times.append(execution_time)

print(len(all_times))