import yaml
import json
import os
import glob
from pathlib import Path

def find_tag_by_state_str(state_str, search_dir):
    """在指定目录中查找匹配state_str的JSON文件并返回tag"""
    # 构造匹配模式，查找所有state_*.json文件
    pattern = os.path.join(search_dir, "state_*.json")
    
    for json_file in glob.glob(pattern):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("state_str") == state_str:
                    return data.get("tag")
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error reading {json_file}: {e}")
            continue
    
    return None

def augment_yaml_with_tags(input_yaml, output_yaml, search_dir):
    """读取YAML文件，补充tag字段，并输出到新文件"""
    with open(input_yaml, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if 'records' not in data:
        print("No 'records' field found in YAML")
        return
    
    for record in data['records']:
        if 'state_str' in record:
            tag = find_tag_by_state_str(record['state_str'], search_dir)
            if tag:
                record['tag'] = tag
            else:
                print(f"No matching JSON found for state_str: {record['state_str']}")
    
    with open(output_yaml, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

# 使用示例
if __name__ == "__main__":
    input_yaml = r"C:\Projects\2025Unicom\tools\AutoDroid-V2\step_1_doc_generation\data\test\data\calendar\log.yaml"  # 输入的YAML文件路径
    output_yaml = "output.yaml"  # 输出的YAML文件路径
    search_dir = r"C:\Projects\2025Unicom\tools\AutoDroid-V2\step_1_doc_generation\data\test\data\calendar\states"  # 存放JSON文件的目录
    
    augment_yaml_with_tags(input_yaml, output_yaml, search_dir)
    print(f"Processed YAML saved to {output_yaml}")