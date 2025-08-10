from . import tools
import json
import ast
import os


class Agent1TaskPlanner:
      def __init__(self, task_desc, ui_tree_path):
        self.task_desc = task_desc
        self.ui_tree_path = ui_tree_path
        if not os.path.isfile(ui_tree_path):
            raise FileNotFoundError(f"UI tree file not found: {ui_tree_path}")
        
      def _make_prompt(self):          
    # 定义背景信息，包含助手的角色和任务说明
            background = 'Background: \n' + '''You are a smartphone assistant to decide the navigation steps to complete a task.I will provide you with the UI tree for the application.The UI tree is a graph describing the application's nodes (id and function) and edges (navigation actions between nodes).
      Your task is to:
      1.Analyze the given task and match it with the the most relevant node in the UI tree based on 'function' parameters of the nodes. 
      2.Determine the navigation path from entry node (id: "1") to matched node based on 'edges' in the UI tree.
      3.Extract the action sequence from the UI tree based on the navigation path.
      '''
                  
    # 从example.js文件中读取UI树数据
            with open(self.ui_tree_path, 'r', encoding='utf-8') as file:
                  ui_tree_data = file.read()
                  
    # 构建UI树提示信息
            ui_tree_prompt = 'UI tree: \n' + ui_tree_data + '\n'
    # 定义具体任务
            task_prompt = 'Task: \n' + '''The given task is: Find accommodation in Tokyo for 2 people next spring\n'''
    # 定义输出请求格式和要求
            request_prompt =  'Output request: \n' + '''Your answer should always use the following JSON format:
      {
      "matched_node": {
            "id": "matched node id",
            "matching_reason": "brief explanation of node matching evidence"
      },
      "navigation_path": ["start_node_id", "intermediate_node_id", ..., "target_node_id"],
      "action_sequence": ["event_id1", "event_id2", ...]
      }
      **Note that:**
      1.All ids in "matched_node" and "navigation_path" must exactly match the 'id' parameters in the UI tree.
      2.Extract the 'id' parameters from 'edges' along the navigation path to construct "action_sequence".
      '''
    # 组合所有提示信息并返回
            prompt = background + '\n' + ui_tree_prompt + '\n' + task_prompt + '\n' + request_prompt
            return prompt

      def _get_navigation_steps(self):
            prompt = self._make_prompt()
            print('********************************** prompt: **********************************')
            print(prompt)
            print('********************************** end of prompt **********************************')
            response = tools.query_deepseek(prompt)
            print(f'response: {response}')

            # with open('ds_response.txt', 'a', encoding='utf-8') as f:
            #       f.write(f'prompt: {prompt}\n')
            #       f.write(f'response: {response}\n')
            
            action_sequence = self._extract_actions_from_response(response)
            return action_sequence

      def _extract_actions_from_response(self, v):
            navigation_actions = []
            try:
                  if isinstance(v, str):
                        v = ast.literal_eval(v)
            except:
                  print('format error: v')

            if 'action_sequence' in v and isinstance(v['action_sequence'], list):
                  navigation_actions = v['action_sequence']
            
            return navigation_actions
      
      def run(self):
        prompt = self._make_prompt()
        print("********************************** prompt **********************************")
        print(prompt)
        print("********************************** end of prompt **********************************")
        response = tools.query_deepseek(prompt)
        print(f"[Agent1] Response: {response}")

        with open('action_response', 'a', encoding='utf-8') as f:
                f.write('********************************** prompt **********************************\n')
                f.write(prompt + '\n')
                f.write('********************************** response **********************************\n')
                f.write(response + '\n')
                f.write('********************************** end **********************************\n\n')
                
        actions = self._extract_actions_from_response(response)
        return actions