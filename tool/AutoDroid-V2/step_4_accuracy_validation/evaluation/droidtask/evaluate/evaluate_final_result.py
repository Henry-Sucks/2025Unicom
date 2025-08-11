OUTPUT_DIR = 'data/autoscript_results/llama3-8b'
import os
import tools as tools
all_results = {}
correct_num, all_num = 0, 0
folders = [f for f in os.listdir(OUTPUT_DIR) if os.path.isdir(os.path.join(OUTPUT_DIR, f)) and '-bk' not in f]
for folder in folders:
    result_path = os.path.join(OUTPUT_DIR, folder, 'result.json')
    if os.path.exists(result_path):
        result = tools.load_json_file(result_path)
        acc = result['acc']
        all_results[folder] = acc
        correct_num += acc[0]
        all_num += acc[1]
print(all_results)
print(correct_num/all_num)