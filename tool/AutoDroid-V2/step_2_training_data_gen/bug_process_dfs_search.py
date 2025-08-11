import argparse 
from lxml import etree
import argparse
from copy import deepcopy
from typing import List
import pandas
import os
import re
import sys
import json
import time
import logging
import traceback
import pkg_resources
import shutil
import subprocess
from agent.droidbot.device import Device
from agent.droidbot.app import App
from agent.droidbot.input_event import RestartAppEvent
from agent.environment import AsyncEnv, AsyncDroidBotEnv
from agent import tools

from agent.script_utils.ui_apis import CodeConfig, CodeStatus, Verifier, ElementList, regenerate_script, _save2log # ElementList is important for exec scripts
from agent.script_utils import tools
from agent.script_utils.bug_processor import BugProcessorV3
from agent.script_utils.api_doc import ApiDoc
from agent.script_utils.err import XPathError, APIError, ActionError, NotFoundError, TaskNotCompletedError
from dotenv import load_dotenv

load_dotenv()

'''
Tree Search
'''
def get_available_elements(doc_path, screen_html, screen_name, use_dash=False):
  # tree = etree.HTML(screen_html)
  # element_tree = etree.ElementTree(tree)
  doc = tools.load_json_file(doc_path)
  parser = etree.HTMLParser()
  element_tree = etree.fromstring(screen_html, parser)
  available_elements = []
  for element_name, element_data in doc[screen_name]['elements'].items():
      ele_xpaths = element_data['xpath']
      if not ele_xpaths:
          continue
      for ele_xpath in ele_xpaths:
          try: 
              element = element_tree.xpath(ele_xpath)
          except:
              print(f'Error in xpath: {ele_xpath}')
              continue
          if len(element) > 0:
              new_element_name = element_name.replace(':', '__') if use_dash else element_name
              available_elements.append(new_element_name)
              break
  return available_elements

def simplify_state(first_state, doc_path):
  # get the name of the first UI state by matching the skeleton structure
  doc = tools.load_json_file(doc_path)
  max_matched_elements, max_matched_screen_name = 0, ''
  for screen_name, screen_data in doc.items():
      screen_skeleton = screen_data['skeleton']
      common_layout_str, common_ui = tools.extract_common_structure(first_state, screen_skeleton, clean_redundant_attributes=True)
      if not common_ui:
          continue
      matched_elements = tools.count_ele_num(common_ui)
      if matched_elements > max_matched_elements:
          max_matched_elements = matched_elements
          max_matched_screen_name = screen_name
  available_elements = get_available_elements(doc_path, first_state, max_matched_screen_name, use_dash=True)
  return available_elements



class SubscribableAsyncDroidBotEnv(AsyncDroidBotEnv):
  '''
  能够监听单步执行情况的环境。
  '''

  def __init__(self, device: Device, app: App):
    super().__init__(device, app)
    self.listeners = []

  def add_event_listener(self, listener):
    self.listeners.append(listener)

  def execute_action(self, action: dict) -> None:
    result = super().execute_action(action)
    # import pdb; pdb.set_trace()
    for listener in self.listeners:
      try:
        state = self.get_state(wait_to_stabilize=True).element_tree.get_str()
      except Exception as e:
        traceback.print_exc()
        print(e)
        state = ''
      listener.update(state)
    return result

class TreeBugProcessor(BugProcessorV3):
  '''
  特化版 bug processor, 为了 sample 出多个不同的解决方案
  '''
  def __init__(self, app_name: str, task: str, doc: ApiDoc, error_info: dict, code: str, err: Exception, generated_codes=None, states_list=None):
    super().__init__(app_name, task, doc, error_info, code, err)
    self.generated_codes = generated_codes # 已经生成过的 solution，需要产生更加 diverse 的
    self.states_list = states_list
  def make_prompt(self, env: AsyncEnv):
    base_prompt = super().make_prompt(env)
    states_str = "\n".join([f"State {str(idx + 1)} of last recent {len(self.states_list)} states" + (" (This is the final state after the last action)" if (idx + 1) == len(self.states_list) else "") + ": This state has the following elements: \n" + f'{simplify_state(state, self.doc.doc_path)}' for idx, state in enumerate(self.states_list)])
    history_prompt = f'''
The last recent {len(self.states_list)} history states during the code execution process is shown here, you can refer this to find some potential bug in the code:
{states_str}
'''
    
    diverse_prompt = f'''
NOTE:
1. You have tried to generated the following solution code, please try to give another answer that are different with them.
{self.generated_codes}
2. Don't use `try` and `except` clause in your code.
BEGIN!
'''
    final_prompt = base_prompt + history_prompt + diverse_prompt
    return final_prompt

class CodeNode:
  '''
  The node for code script.
  '''
  def __init__(self, goal, code, error_info=None, err=None, done=False):
    self.goal = goal
    self.code = code
    self.error_info = error_info
    self.err = err
    self.done = done
    self.children: List[CodeNode] = []
    self.parent = None

  def append_child(self, child):
    self.children.append(child)
    child.parent = self


def todict(obj, classkey=None):
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = todict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast())
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey)) 
            for key, value in obj.__dict__.items() 
            if not callable(value) and not key.startswith('_') and key != 'parent'])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj

def process_error_info(original_script, compiled_script, traceback, error,
                       line_mappings):
  print(f"Exception caught: {error}")
  print("Traceback details:")
  print(traceback)

  # extract the line number of the error
  tb_lines = traceback.split('\n')

  error_line_number_in_compiled_script = -1
  error_line_number_in_original_script = -1
  error_line_in_compiled_script = compiled_script.split('\n')[error_line_number_in_compiled_script]
  error_line_in_original_script = original_script.split('\n')[error_line_number_in_original_script]

  for line in tb_lines:
    if 'File "<string>"' in line:
      print(line.strip())
      match = re.search(r'line (\d+)', line)
      if match:  # localized the error line number
        try:
          line_number = match.group(1)
          print(f'The line number is: {line_number}')
          error_line_number_in_compiled_script = int(
              line_number
          ) - 1  # the line number of the error info often starts from 1, but in the mappings, it starts from 0
          error_line_number_in_original_script = line_mappings[
              error_line_number_in_compiled_script]
          error_line_in_compiled_script = compiled_script.split(
              '\n')[error_line_number_in_compiled_script]
          error_line_in_original_script = original_script.split(
              '\n')[error_line_number_in_original_script]
        except:
          print(f'Error in extracting the line number: {line_number}')
          error_line_number_in_compiled_script = None
          error_line_number_in_original_script = None
          error_line_in_compiled_script = None
          error_line_in_original_script = None
      else:
        print('No line number found')
        error_line_in_compiled_script = line
        error_line_in_original_script, error_line_number_in_compiled_script, error_line_number_in_original_script = None, None, None

  return {
      'original_script':
          original_script,
      'compiled_script':
          compiled_script,
      'traceback':
          traceback,
      'error':
          error,
      'error_line_number_in_compiled_script':
          error_line_number_in_compiled_script,
      'error_line_number_in_original_script':
          error_line_number_in_original_script,
      'error_line_in_compiled_script':
          error_line_in_compiled_script,
      'error_line_in_original_script':
          error_line_in_original_script
  }


class CodeAgent():
  """code agent"""

  # Wait a few seconds for the screen to stabilize after executing an action.
  WAIT_AFTER_ACTION_SECONDS = 2.0
  MAX_RETRY_TIMES = 2
  
  def __init__(self,
               env: AsyncEnv,
               app_name: str,
               doc_path: str,
               save_path: str,
               output_dir: str,
               app_path: str,
               name: str = 'CodeAgent'):

    self.env = env
    self.name = name
    app_name = app_name.strip()
    
    if not os.path.exists(doc_path):
      raise ValueError(f'Unknown doc path: {doc_path}')

    self.app_name = app_name
    self.doc = ApiDoc(doc_path)
    self.save_dir = save_path
    
    self.save_path = save_path
    self.code_config = CodeConfig(app_name, self.doc)
    self.code_status = CodeStatus()
    self.runtime_states = []
  
    self.output_dir = output_dir
    self.app_path = app_path

  def update(self, state):
    self.runtime_states.append(state)

  def get_reward(self, app_name, task, code, last_states):
    states_str = "\n".join([f"State {str(idx + 1)} of last recent {len(last_states)} states" + (" (This is the final state after the last action)" if (idx + 1) == len(last_states) else "") + ": This state has the following elements: \n" + f'{simplify_state(state, self.doc.doc_path)}' for idx, state in enumerate(last_states)])
    prompt = f'''Imagine that you are a robot operating a smartphone to use the {app_name} app. Like how humans operate the smartphone, you can tap, long tap, input text, scroll, and get attributes of the UI elements in the {app_name} app. However, unlike humans, you cannot see the screen or interact with the physical buttons on the smartphone. Therefore, you need to write scripts to manipulate the UI elements (buttons, text fields, scrollers, element_lists, etc) in the app. 
The task: 
{task}

The code you wrote:
{code}

The code has been fully executed on the app. 

The last {len(last_states)} states of the app described in HTML format:
{states_str}

Please analyze whether the task has been fully completed. You should consider whether the task has been fully completed, or it is only partly completed. If the task is only partly completed, please provide a detailed explanation of what is missing or incorrect in the code.
Note that: 
- All the code you wrote has been executed on the app, DON'T consider the code execution error. DON'T need to verify whether each code line has been executed successfully.
- You should pay attention to the last state of the app and the task description to analyze whether the task has been fully completed.
- Finally, you should respond with the following format, as the example shows:

Thought: (Your thought here.)
Answer: (True if the task has been fully completed, else False.)

'''
    answer, tokens = tools.query_gpt(prompt=prompt, model='gpt-4o')
    return {
      'reward': 'True' in answer,
      'reason': answer
    }

  def run_code(self, code, goal):
    subprocess.run(["adb", "-s", device_serial, "emu", "avd", "snapshot", "load", snapshot_name]) # load snapshot
    print('waiting...')
    time.sleep(3)
    logging.info("Starting DroidBot")

    device = Device(
        device_serial=device_serial,
        is_emulator=True,
        output_dir=self.output_dir)
    
    app = App(self.app_path, self.output_dir)
    env = SubscribableAsyncDroidBotEnv(device, app)
    device.send_event(RestartAppEvent(app=app))
    # subscribe
    self.env = env
    env.add_event_listener(self)

    self.env.execute_action(
        {
            'action_type': 'open_app',
            'app_name': self.app_name
        })
    time.sleep(self.WAIT_AFTER_ACTION_SECONDS)
    t0 = time.time()
  
    if isinstance(code, list):
      code = '\n'.join(code)
    tools.write_txt_file(f'{self.save_path}/code.txt', code)
    
    code_script, line_mappings = regenerate_script(code, 'verifier')
    tools.write_txt_file(f'{self.save_path}/compiled_code.txt', code_script)
    tools.dump_json_file(f'{self.save_path}/line_mappings.json', line_mappings)
    
    # in case some silly scripts include no UI actions at all, we make an empty log for batch_verifying
    tools.dump_yaml_file(os.path.join(self.save_path, f'log.yaml'), {'records': [], 'step_num': 0})
    
    env = self.env
    self.code_config.set(self.save_path, code, code_script, line_mappings)
    self.code_status.reset()
    self.runtime_states = []
    
    t1 = time.time()
    
    # execution
    verifier = Verifier(env, self.code_config, self.code_status)
    try:
      if "try" in code:
        raise ValueError("`try` clause is in the code! It is not supported now.")
      exec(code_script)
      done = True
      error_info = None
      err = None
      reward_info = self.get_reward(self.app_name, goal, code, self.runtime_states[-3:])
      if not reward_info['reward']:
        raise TaskNotCompletedError(f'Although the code has been executed successfully, the task is not completed. Please revise your code more carefully. Detailed reason: {reward_info["reason"]}', reason=reward_info['reason'])
    except Exception as e:
      tb_str = traceback.format_exc()
      done = False
      error_info = process_error_info(code, code_script, tb_str, str(e),
                                      line_mappings)

      error_path = os.path.join(self.save_path, f'error.json')
      tools.dump_json_file(error_path, error_info)
      err = e
        
    _save2log(
        save_path=self.save_path,
        log_file=self.code_config.log_file,
        element_tree=verifier.element_tree,
        idx=-1,
        inputs=None,
        action_type=None,
        api_name=None,
        xpath=None,
        currently_executing_code=None,
        comment='done',
        screenshot=None)

    device.disconnect()
    
    return {
      "done": done,
      "error_info": error_info,
      "code": code,
      "time": t1 - t0,
      "err": err
    }

  def fix_bug(self, goal, code, error_info, err, app_name, generated_codes=[]):
    bug_processor = TreeBugProcessor(
      app_name=app_name,
      task=goal,
      doc=self.doc,
      error_info=error_info,
      code=code,
      err=err,
      generated_codes=generated_codes,
      states_list=self.runtime_states[-3:]
    )
    
    request_retry_time = 0
    max_time = 10
    while request_retry_time < max_time:
      try:
        
        if isinstance(err, XPathError):
          bug_processor.fix_invalid_xpath(
            env=self.env, 
            api_name=err.name, 
            prompt_answer_path=os.path.join(self.save_path, f'fix_xpath.json'), 
            model_name='gpt-4o')
          
        code = bug_processor.get_fixed_solution(# re-generate code
            prompt_answer_path=os.path.join(self.save_path, f'solution.json'),
            env=self.env,
            model_name='gpt-4o')
        break
      except Exception as e:
        traceback.print_exc()
        print(e)
        request_retry_time += 1
        print(f"retrying {request_retry_time} times...")
    if request_retry_time >= max_time:
      raise ValueError("Failed to get the solution after 10 times retrying")
    return code

  def visit_node(self, node: CodeNode, beam_width, max_depth, depth):
    # update node status
    self.visit_time += 1
    print("visit time: ", self.visit_time)

    result = self.run_code(node.code, node.goal)

    node_code = node.code
    node_goal = node.goal
    # done = False
    error_info, err, done = result['error_info'], result['err'], result['done']
    
    node.error_info = deepcopy(error_info)
    node.err = str(err)
    node.done = deepcopy(done)

    if done:
      return True, "Found Solution", node.code
    
    if max_depth == depth:
      return False, "Max Depth Reached", None

    generated_codes = []
    for width_idx in range(beam_width):
      if self.visit_time >= self.max_visit_time:
        return False, "Max Visit Time Reached", None

      print('depth: ', depth, 'visit time: ', self.visit_time, "child idx: ", width_idx)

      new_code = self.fix_bug(node_goal, node_code, error_info, err, done, generated_codes=generated_codes)
      # new_code = 'awe'
      if new_code in generated_codes:
        continue
      generated_codes.append(new_code)
      
      new_node = CodeNode(node_goal, new_code, None, None, None)
      node.append_child(new_node)
      status, visit_info, child_code = self.visit_node(new_node, beam_width, max_depth, depth+1)

      if status:
        return True, visit_info, child_code

    return False, visit_info, None
    
  def run_dfs_search(self, code, goal):
    self.max_visit_time = 4
    # self.max_visit_time = 1
    # beam_width = 1
    # max_depth = 0
    
    self.visit_time = 0
    root_node = CodeNode(goal, code, None, None, None)
    status, visit_info, final_code = self.visit_node(root_node, beam_width, max_depth, 0)

    return {
      "status": status,
      "visit_info": visit_info,
      "root_node": root_node,
      "code": code,
      "final_code": final_code
    }

def code_bug_fixing(app_name, code, task_id, goal, tree_output_dir):
    output_dir = f"{tree_output_dir}/{task_id}"
    if os.path.exists(output_dir):
      shutil.rmtree(output_dir)
    # app_name = "contacts"
    doc_name = f"{doc_dir}/{app_name}_0814.json"
    app_path = f"{apk_dir}/{app_name}.apk"
    if output_dir is not None:
      if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
      html_index_path = pkg_resources.resource_filename("droidbot", "resources/index.html")
      stylesheets_path = pkg_resources.resource_filename("droidbot", "resources/stylesheets")
      target_stylesheets_dir = os.path.join(output_dir, "stylesheets")
      if os.path.exists(target_stylesheets_dir):
        shutil.rmtree(target_stylesheets_dir)
      shutil.copy(html_index_path, output_dir)
      shutil.copytree(stylesheets_path, target_stylesheets_dir)

    try:
      code_agent = CodeAgent(None, app_name, doc_name, output_dir, output_dir=output_dir, app_path=app_path)
      
      print(task_id)
      code_agent.MAX_RETRY_TIMES = 2
      code_agent.code_config.enable_dependency = False # now document don't support dependency format
      
      # run task
      result = code_agent.run_dfs_search(code, goal)
      root_node = result['root_node']
      tree_full_output_dir = f"{tree_output_dir}/{task_id}/trees/"
      if not os.path.exists(tree_full_output_dir):
        os.makedirs(tree_full_output_dir)
      tree_dict = todict(root_node)
      tools.dump_json_file(f'{tree_full_output_dir}/tree.json', tree_dict)
      result['root_node'] = tree_dict
      print(result['status'], result['visit_info'])

    except KeyboardInterrupt:
      logging.info("Keyboard interrupt.")

      sys.exit(0)
    except Exception:
      import traceback
      traceback.print_exc()
      # run task
      tree_full_output_dir = f"{tree_output_dir}/{task_id}/trees/"
      if not os.path.exists(tree_full_output_dir):
        os.makedirs(tree_full_output_dir)

      tools.dump_json_file(f'{tree_full_output_dir}/failed.json', {})

      return {'failed': True}

    logging.info("DroidBot Stopped")

    return result

def run_batch(input_json_path, output_dir, app_name='calendar', process_num=3, process_id=0, eval_mode=False):
  if not eval_mode:
    if input_json_path.endswith(".jsonl"):
      df = pandas.read_json(input_json_path, orient='records', lines=True)
    elif input_json_path.endswith(".json"):
      df = pandas.read_json(input_json_path)

    offset_idx = 0
  else:
    offset_idx = 0
    with open(input_json_path, 'r') as f:
      data = json.load(f)
      task_list = []
      for key, value in data[app_name].items():
        task_list.append({
          'task': value['task'],
          'task_id': key,
          'code': 'Now there is no code.'
        })
        df = pandas.DataFrame(task_list)
  # get task from process id
  # divide df into process_num blocks and get the process_id-th block
  start_idx = process_id * (len(df) - offset_idx) // process_num + offset_idx
  end_idx = (process_id+1) * (len(df) - offset_idx) // process_num + offset_idx
  print(f"start_idx: {start_idx}, end_idx: {end_idx}")
  # import pdb; pdb.set_trace()

  result_list = []
  for idx, row in df.iterrows():

    if idx < start_idx:
      continue
    if idx > end_idx:
      continue
    
    finished_task_path = os.path.join(output_dir, app_name, 'trees')
    if os.path.exists(finished_task_path):
      finished_task = os.listdir(finished_task_path)
    else:
      finished_task = []
    print("app_name: ", app_name, ", idx: ", idx, ", finished_task: ", len(finished_task))

    if str(idx) in finished_task:
      print(f"skip {idx}")
      continue
  
    if 'status' in row and row.status:
        print(f'skip {idx}')
        result_list.append(row.to_dict())
    else:
      if "root_node" in row:
        task = row.root_node['goal']
        code = row.root_node['code']
      elif "task" in row:
        task = row.task
        if 'code' in row:
          code = row.code
        elif 'script' in row:
          code = row.script
        assert code is not None, "Code is None!"
      
      result = code_bug_fixing(app_name, code, row.task_id if eval_mode else idx, task, output_dir)
      result['idx'] = idx
      if eval_mode:
        result['task_id'] = row.task_id
      result_list.append(result)

    # result_df = pandas.DataFrame(result_list)
    # full_output_dir = os.path.join(output_dir, app_name)
    # if not os.path.exists(full_output_dir):
      # os.makedirs(full_output_dir)

    # result_df.to_json(os.path.join(full_output_dir, f'result_{process_id}.jsonl'), orient='records', lines=True)

parser = argparse.ArgumentParser()
parser.add_argument('--apk_dir', type=str, default='apks/')
parser.add_argument('--device_serial', type=str, default='emulator-5554')
parser.add_argument('--snapshot_name', type=str, required=True)
parser.add_argument('--eval_input_path', type=str, default='tasks.json')
parser.add_argument('--output_dir', type=str, default='output/tasks_eval')
parser.add_argument('--doc_dir', type=str, default='data/docs_droidtask_v3')
parser.add_argument('--process_num', type=int, default=1)
parser.add_argument('--beam_width', type=int, default=2)
parser.add_argument('--max_depth', type=int, default=2)
parser.add_argument('--max_visit_time', type=int, default=4)
parser.add_argument('--process_id', type=int, default=0)
parser.add_argument('--eval_mode', type=int, default=1)
args = parser.parse_args()

if __name__ == "__main__":

  apk_dir = args.apk_dir
  device_serial = args.device_serial
  snapshot_name = args.snapshot_name
  eval_input_path = args.eval_input_path
  output_dir = args.output_dir
  doc_dir = args.doc_dir
  beam_width = args.beam_width
  max_depth = args.max_depth
  process_id = args.process_id
  process_num = args.process_num
  eval_mode = args.eval_mode == 1
  
  print("device_serial: ", device_serial)
  print("snapshot_name: ", snapshot_name)
  print("eval_input_path: ", eval_input_path)
  print("output_dir: ", output_dir)
  print("beam_width: ", beam_width)
  print("max_depth: ", max_depth)
  print("process_id: ", process_id)
  print("process_num: ", process_num)
  print("eval mode: ", eval_mode)
  
  target_apps = ['calendar', 'firefox', 'applauncher', 'clock', 'camera', 'contacts', 'dialer', 'messenger', 'music', 'filemanager', 'voicerecorder', 'gallery', 'notes']

  for item in target_apps:
    print("item: ", item)
    try:
      run_batch(
        input_json_path=eval_input_path,
        output_dir=f'{output_dir}/{item}',
        app_name=f'{item}',
        process_num=process_num,
        process_id=process_id,
        eval_mode=eval_mode
      )
    except Exception as e:
      print(e)
      continue