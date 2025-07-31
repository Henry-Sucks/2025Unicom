import json
import os
import sys
import yaml  # 需要安装PyYAML库

def build_view_tree(views):
    view_dict = {view["temp_id"]: view for view in views}
    for view in views:
        child_ids = view.get("children", [])
        view["child_nodes"] = [view_dict[child_id] for child_id in child_ids if child_id in view_dict]
    root_nodes = [view for view in views if view.get("parent") == -1]
    return root_nodes

def view_to_dict(view):
    node = {
        'class': view.get("class", "UnknownClass"),
        'text': view.get("text", ""),
        'resource_id': view.get("resource_id", ""),
        'id': view.get("temp_id", "?")
    }
    children = [view_to_dict(child) for child in view.get("child_nodes", [])]
    if children:
        node['children'] = children
    return node

def main(json_path, output_dir):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    views = data.get("views", [])
    if not views:
        print("No views found in the JSON file.")
        return

    root_nodes = build_view_tree(views)
    
    # 转换为适合YAML输出的结构
    yaml_data = [view_to_dict(root) for root in root_nodes]

    # 生成输出路径
    base_name = os.path.splitext(os.path.basename(json_path))[0]
    output_filename = f"{base_name}.view_tree.yaml"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)

    # 写入YAML文件
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, allow_unicode=True, sort_keys=False)

    print(f"\n✅ 视图树已保存至：{output_path}")

if __name__ == "__main__":
    json_file_path = r"C:\Projects\2025Unicom\src\states\小说界面.json"
    output_folder = r"C:\Projects\2025Unicom\src\view_trees"
    main(json_file_path, output_folder)