def find_clickable_buttons(view):
    clickable_buttons = []
    
    # 检查当前视图是否可点击且有文本
    if view.get('clickable', False):
        text = view.get('text', None)
        if text:  # 只有当有文本时才收集
            clickable_buttons.append({
                'text': text,
                'view': view
            })
    
    # 递归检查子视图
    for child in view.get('children', []):
        clickable_buttons.extend(find_clickable_buttons(child))
    
    return clickable_buttons

def extract_text_views(view_dict, result=None):
    """
    递归遍历视图字典，提取所有text不为空的视图对象及其文本内容
    
    参数:
        view_dict: 包含视图信息的字典
        result: 用于存储结果的列表(递归时使用)
    
    返回:
        包含所有非空text视图对象及其文本的列表，格式为[(view_object, text), ...]
    """
    if result is None:
        result = []
    
    # 检查当前视图是否有非空的text属性
    if 'text' in view_dict and view_dict['text'] is not None and view_dict['text'] != '':
        result.append((view_dict, view_dict['text']))
    
    # 递归处理所有子视图
    if 'children' in view_dict and isinstance(view_dict['children'], list):
        for child_view in view_dict['children']:
            extract_text_views(child_view, result)
    
    return result