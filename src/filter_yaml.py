import yaml
import os

def filter_empty_text(node):
    """递归过滤掉text为空的节点字段"""
    if isinstance(node, dict):
        # 创建新节点，不包含空text
        filtered_node = {}
        for key, value in node.items():
            if key == 'text':
                # 只有text非空时才保留
                if value and value != "null":
                    filtered_node[key] = value
            elif key == 'children':
                # 递归处理子节点
                filtered_children = [filter_empty_text(child) for child in value]
                filtered_node[key] = [child for child in filtered_children if child]  # 过滤掉None
            else:
                filtered_node[key] = value
        
        # 如果节点没有children且是空的，返回None（将被过滤掉）
        if not filtered_node.get('children') and not any(v for k, v in filtered_node.items() if k != 'class'):
            return None
        return filtered_node
    return node

def process_yaml(input_path, output_dir):
    """处理YAML文件并输出过滤后的版本"""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or []
    
    # 过滤数据
    filtered_data = [filter_empty_text(node) for node in data]
    filtered_data = [node for node in filtered_data if node]  # 移除None节点

    # 准备输出路径
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_filename = f"{base_name}_filtered.yaml"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)

    # 写入新YAML文件
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(filtered_data, f, allow_unicode=True, sort_keys=False, indent=2)

    print(f"\n✅ 过滤后的YAML已保存至：{output_path}")

if __name__ == "__main__":
    # 示例文件路径
    input_yaml = r"C:\Projects\2025Unicom\src\view_trees\state_2025-07-23_191103.view_tree.yaml"
    output_dir = r"C:\Projects\2025Unicom\src\view_trees\filtered"
    
    process_yaml(input_yaml, output_dir)