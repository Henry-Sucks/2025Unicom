import yaml
import os
from datetime import datetime
from collections import deque

def compare_layouts(file1_path, file2_path, output_dir=None, classes_to_filter=None, max_difference=0):
    """
    比较两个YAML格式的安卓布局文件是否在结构上相同，
    可配置需要过滤的类及其子节点，并可选择将标准化后的布局输出到指定文件夹
    
    参数:
        file1_path: 第一个YAML文件路径
        file2_path: 第二个YAML文件路径
        output_dir: (可选)输出标准化布局的目录路径
        classes_to_filter: (可选)需要过滤的类名列表，如:
                          ['android.support.v4.view.ViewPager', 
                           'android.widget.TextView']
                          默认为None表示不过滤任何类
        max_difference: (可选)允许的最大差异组件数，默认为0表示必须完全匹配
    
    返回:
        bool: 如果布局结构差异不超过max_difference则返回True，否则返回False
    """
    # 设置默认过滤类（如果未提供）
    if classes_to_filter is None:
        classes_to_filter = []
    
    def load_and_normalize(file_path, output_prefix=None):
        """加载YAML文件并规范化布局结构"""
        with open(file_path, 'r', encoding='utf-8') as f:
            layout = yaml.safe_load(f)
        
        def normalize(node):
            if isinstance(node, list):
                return [normalize(child) for child in node if child is not None]
            elif isinstance(node, dict):
                # 检查是否是需要过滤的类
                class_name = node.get('class', '')
                if class_name in classes_to_filter:
                    return None  # 忽略整个节点及其子节点
                
                # 处理非过滤节点
                normalized = {
                    'class': class_name,
                    'resource_id': node.get('resource_id'),
                    'children': []
                }
                
                # 递归处理子节点，过滤掉None值
                if 'children' in node:
                    normalized_children = [normalize(child) for child in node['children']]
                    normalized['children'] = [child for child in normalized_children if child is not None]
                
                # 移除值为None的项
                return {k: v for k, v in normalized.items() if v is not None}
            return None
        
        normalized_layout = normalize(layout)
        
        # 如果需要输出标准化布局
        if output_prefix and output_dir and normalized_layout is not None:
            output_filename = f"{output_prefix}_normalized.yaml"
            output_path = os.path.join(output_dir, output_filename)
            
            os.makedirs(output_dir, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(normalized_layout, f, default_flow_style=False, allow_unicode=True)
            print(f"标准化布局已保存到: {output_path}")
        
        return normalized_layout
    
    def count_differences(layout1, layout2):
        """计算两个布局之间的差异组件数"""
        if layout1 == layout2:
            return 0
        
        if (layout1 is None) != (layout2 is None):
            return float('inf')  # 一方为None另一方不为None，视为无限差异
        
        if not isinstance(layout1, dict) or not isinstance(layout2, dict):
            return 1
        
        # 比较当前节点的属性
        diff_count = 0
        if layout1.get('class') != layout2.get('class'):
            diff_count += 1
        if layout1.get('resource_id') != layout2.get('resource_id'):
            diff_count += 1
        
        # 比较子节点
        children1 = layout1.get('children', [])
        children2 = layout2.get('children', [])
        
        # 使用广度优先策略比较子节点
        queue = deque()
        queue.extend(zip(children1, children2))
        
        while queue:
            child1, child2 = queue.popleft()
            if child1 == child2:
                continue
            
            if (child1 is None) != (child2 is None):
                diff_count += 1
                continue
            
            if not isinstance(child1, dict) or not isinstance(child2, dict):
                diff_count += 1
                continue
            
            # 比较当前子节点的属性
            if child1.get('class') != child2.get('class'):
                diff_count += 1
            if child1.get('resource_id') != child2.get('resource_id'):
                diff_count += 1
            
            # 将子节点的子节点加入队列
            queue.extend(zip(child1.get('children', []), child2.get('children', [])))
            
            # 如果差异已经超过允许范围，提前终止
            if diff_count > max_difference:
                return diff_count
        
        return diff_count
    
    try:
        # 获取文件名用于输出前缀
        file1_name = os.path.splitext(os.path.basename(file1_path))[0]
        file2_name = os.path.splitext(os.path.basename(file2_path))[0]
        
        norm1 = load_and_normalize(file1_path, file1_name if output_dir else None)
        norm2 = load_and_normalize(file2_path, file2_name if output_dir else None)
        
        # 处理可能全部被过滤掉的情况
        if norm1 is None and norm2 is None:
            return True
        if norm1 is None or norm2 is None:
            return max_difference >= float('inf')  # 除非max_difference为无限大
        
        # 计算差异数
        differences = count_differences(norm1, norm2)
        print(f"布局差异组件数: {differences} (允许最大差异: {max_difference})")
        return differences <= max_difference
    except Exception as e:
        print(f"比较布局时出错: {e}")
        return False

# 使用示例
if __name__ == "__main__":
    # 示例文件路径
    file1 = r"C:\Projects\2025Unicom\src\view_trees\主页面1.view_tree.yaml"
    file2 = r"C:\Projects\2025Unicom\src\view_trees\主界面5.view_tree.yaml"
    output_directory = r"C:\Projects\2025Unicom\src\normalized_layouts"
    
    # 配置需要过滤的类
    filter_classes = [
        'android.support.v4.view.ViewPager',
        'android.widget.TextView',
        'android.widget.ImageView'
    ]
    
    # 比较布局并输出标准化结果，允许最多5个组件差异
    result = compare_layouts(
        file1, 
        file2, 
        output_dir=output_directory,
        classes_to_filter=filter_classes,
        max_difference=5  # 新增参数：允许最多5个组件差异
    )
    print(f"布局是否相同(允许差异内): {result}")