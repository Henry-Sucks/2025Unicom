from . import tools
import json
import ast
import os
import datetime
import re


class Agent1TaskPlanner:
      def __init__(self, task_desc, ui_tree_path, planned_task_path):
        self.task_desc = task_desc
        self.ui_tree_path = ui_tree_path
        self.planned_task_path = planned_task_path
        if not os.path.isfile(ui_tree_path):
            raise FileNotFoundError(f"UI tree file not found: {ui_tree_path}")
        
      def _make_prompt(self):          
        background = (
            'Background: \n'
            'You are a smartphone assistant to decide the navigation steps to complete a task.'
            ' I will provide you with the UI tree for the application. The UI tree is a graph describing the application\'s nodes (id and function) and edges (navigation actions between nodes).\n'
            'Your task is to:\n'
            '1. Analyze the given task and match it with the most relevant node in the UI tree based on "function" parameters of the nodes.\n'
            '2. Determine the navigation path from entry node (id: "1") to matched node based on "edges" in the UI tree.\n'
            '3. Extract the action sequence from the UI tree based on the navigation path.\n'
            '4. Provide a list "action_explanation" that explains each action in "action_sequence".\n'
        )
                  
        with open(self.ui_tree_path, 'r', encoding='utf-8') as file:
            ui_tree_data = file.read()
                  
        ui_tree_prompt = 'UI tree: \n' + ui_tree_data + '\n'
        
        task_prompt = 'Task: \n' + f'{self.task_desc}\n'
        
        request_prompt = (
            'Output request: \n'
            'Your answer should always use the following JSON format:\n'
            '{\n'
            '  "matched_node": {\n'
            '        "id": "matched node id",\n'
            '        "matching_reason": "brief explanation of node matching evidence"\n'
            '  },\n'
            '  "navigation_path": ["start_node_id", "intermediate_node_id", ..., "target_node_id"],\n'
            '  "action_sequence": ["event_id1", "event_id2", ...],\n'
            '  "action_explanation": [\n'
            '        "explanation of action 1",\n'
            '        "explanation of action 2",\n'
            '        ...\n'
            '  ]\n'
            '}\n'
            '**Note that:**\n'
            '1. All ids in "matched_node" and "navigation_path" must exactly match the "id" parameters in the UI tree.\n'
            '2. Extract the "id" parameters from "edges" along the navigation path to construct "action_sequence".\n'
            '3. The "action_explanation" array should explain each action in "action_sequence" in the same order.\n'
        )
        
        prompt = background + '\n' + ui_tree_prompt + '\n' + task_prompt + '\n' + request_prompt
        return prompt

      def _get_navigation_steps(self):
            prompt = self._make_prompt()
            print('********************************** prompt: **********************************')
            print(prompt)
            print('********************************** end of prompt **********************************')
            response = tools.query_deepseek(prompt)
            print(f'response: {response}')
            
            action_sequence = self._extract_actions_from_response(response)
            return action_sequence
      
      def _generate_planned_task_filename(self, prefix="Book_a_flight_ticket_unicom"):
            """
            生成类似于 Book_a_flight_ticket_unicom_20250811_0433.json 格式的文件名
            文件会创建在 self.planned_task_path 目录下
            """
            # 确保目录存在
            os.makedirs(self.planned_task_path, exist_ok=True)

            now = datetime.datetime.now()
            date_str = now.strftime("%Y%m%d")       # 20250811
            time_str = now.strftime("%H%M")         # 0433

            filename = f"{prefix}_{date_str}_{time_str}.json"
            full_path = os.path.join(self.planned_task_path, filename)
            return full_path

      # def _extract_actions_from_response(self, v):
      #       try:
      #             if isinstance(v, str):
      #                   v = ast.literal_eval(v)
      #       except Exception as e:
      #             print('format error:', e)
      #             return {}, [], [], []
            
      #       matched_node = v.get('matched_node', {})
      #       navigation_path = v.get('navigation_path', [])
      #       action_sequence = v.get('action_sequence', [])
      #       action_explanation = v.get('action_explanation', [])
      #       return matched_node, navigation_path, action_sequence, action_explanation


      def _extract_state_view_from_event(self, event_html):
            """
            从event字段HTML字符串提取state和view的hash，格式：
            TouchEvent(state=STATE_HASH, view=VIEW_HASH)
            返回字符串 "(STATE_HASH, VIEW_HASH)"
            """
            # 用正则提取 state= 和 view= 中的哈希值（只取括号内第一个逗号前后部分）
            state_match = re.search(r'state=([0-9a-f]+)', event_html)
            view_match = re.search(r'view=([0-9a-f]+)', event_html)
            state_hash = state_match.group(1) if state_match else "unknown_state"
            view_hash = view_match.group(1) if view_match else "unknown_view"
            return f"({state_hash}, {view_hash})"
      
      def process_planned_task(self, planned_task_json_path, ui_graph_path, task_description=None):
            """
            读取原planned_task json 和 ui_graph json，生成新格式json并写入新文件
            """

            # 1. 读取原json
            with open(planned_task_json_path, 'r', encoding='utf-8') as f:
                  planned_task = json.load(f)

            # 2. 读取ui_graph
            with open(ui_graph_path, 'r', encoding='utf-8') as f:
                  ui_graph = json.load(f)

            # 3. 取原json中的动作解释列表和动作事件id列表
            action_explanation = planned_task.get("action_explanation", [])
            action_sequence = planned_task.get("action_sequence", [])

            # 4. 建立edge id -> event html的映射
            edge_id_to_event = {}
            for edge in ui_graph.get("edges", []):
                  edge_id_to_event[edge["id"]] = edge.get("event", "")

            # 5. 生成新的instructions列表
            instructions = []
            for idx, action_id in enumerate(action_sequence):
                  explanation = action_explanation[idx] if idx < len(action_explanation) else ""
                  event_html = edge_id_to_event.get(action_id, "")
                  event_str = self._extract_state_view_from_event(event_html)
                  instructions.append({
                        "explanation": explanation,
                        "event": event_str
                  })

            # 6. task说明，如果传入了则使用，否则尝试从原json matched_node匹配reason中生成简短描述
            if task_description is None:
                  matched_node = planned_task.get("matched_node", {})
                  matching_reason = matched_node.get("matching_reason", "")
                  # 简单截断匹配原因作为task说明
                  task_description = matching_reason[:100] + ("..." if len(matching_reason) > 100 else "")

            # 7. 组装新json结构
            new_json = {
                  "task": task_description,
                  "instructions": instructions
            }

            # 8. 写入新文件，文件名添加 _processed 后缀
            dirpath, filename = os.path.split(planned_task_json_path)
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}_processed{ext}"
            new_filepath = os.path.join(dirpath, new_filename)

            with open(new_filepath, 'w', encoding='utf-8') as f:
                  json.dump(new_json, f, indent=4, ensure_ascii=False)

            print(f"Processed json saved to {new_filepath}")
            return new_filepath
      
      def run(self):
            prompt = self._make_prompt()
            print("********************************** prompt **********************************")
            print(prompt)
            print("********************************** end of prompt **********************************")
            response = tools.query_deepseek(prompt)
            print(f"[Agent1] Response: {response}")

            planned_task_filename = self._generate_planned_task_filename()
            with open(planned_task_filename, 'w', encoding='utf-8') as f:
                  f.write(response)


            processed_file = self.process_planned_task(planned_task_filename, self.ui_tree_path, self.task_desc)

            return processed_file
            
      

      #   with open('action_response', 'a', encoding='utf-8') as f:
      #           f.write('********************************** prompt **********************************\n')
      #           f.write(prompt + '\n')
      #           f.write('********************************** response **********************************\n')
      #           f.write(response + '\n')
      #           f.write('********************************** end **********************************\n\n')
                