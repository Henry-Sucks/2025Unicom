import json
# load jsonl file
def load_jsonl_file(jsonl_path):
    data = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

task_solutions = load_jsonl_file('merge_origin_pre_task_solution_format.jsonl')
print(f'Loaded {len(task_solutions)} task solutions')
new_task_solutions = []
for id in range(0, len(task_solutions), 6):
    new_task_solutions.append(task_solutions[id])
print(f'Filtered {len(new_task_solutions)} task solutions'  )

# save new jsonl file
with open('new_task_solutions.jsonl', 'w') as f:
    for task_solution in new_task_solutions:
        json_str = json.dumps(task_solution)
        f.write(json_str + '\n')