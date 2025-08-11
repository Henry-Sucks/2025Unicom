import json
import logging
import subprocess
import time
import os
import traceback
import sys
import inspect
from lxml import etree


import tools as tools
from .utils_v1.bug_processor import BugProcessorv2
from .utils_v1.solution_generator import SolutionGenerator
from .ui_apis import *
from .input_event import EventLog
from .device_state import ElementTree
from .input_policy import UtgBasedInputPolicy, UtgNaiveSearchPolicy, UtgGreedySearchPolicy, \
                         UtgReplayPolicy, \
                         ManualPolicy, \
                         POLICY_NAIVE_DFS, POLICY_GREEDY_DFS, \
                         POLICY_NAIVE_BFS , POLICY_GREEDY_BFS, \
                         POLICY_REPLAY, POLICY_MEMORY_GUIDED, POLICY_LLM_GUIDED, \
                         POLICY_MANUAL, POLICY_MONKEY, POLICY_NONE, POLICY_CODE

DEFAULT_POLICY = POLICY_GREEDY_DFS 
DEFAULT_EVENT_INTERVAL = 1
DEFAULT_EVENT_COUNT = 100000000
DEFAULT_TIMEOUT = -1
MAX_RETRY_TIMES = 3
QUERY_FIRSTTIME = False

def get_state(frame):
    '''
    for getting the state of the current frame of the code
    '''
    state = {}
    for key, item in frame.f_locals.items():
        if isinstance(item, (bool, str, int, float, tuple, list, set, dict, type(None))):
            state[key] = item
    return state

def tracefunc(frame, event, arg):
    '''
    for tracing the code execution
    '''
    code = frame.f_code
    filename = code.co_filename
    lineno = frame.f_lineno
    func_name = code.co_name
    state = get_state(frame)
    # print(f"State: {state}; Tracing event: {event} in {func_name} at {filename}:{lineno}")
    return tracefunc

class UnknownInputException(Exception):
    pass

def process_error_info(original_script, compiled_script, traceback, error, line_mappings):
    print(f"Exception caught: {error}")
    print("Traceback details:")
    print(traceback)

    # extract the line number of the error
    tb_lines = traceback.split('\n')
    
    for line in tb_lines:
        if 'File "<string>"' in line:
            print(line.strip())
            match = re.search(r'line (\d+)', line)
            if match:  # localized the error line number
                try:
                    line_number = match.group(1)
                    print(f'The line number is: {line_number}')
                    error_line_number_in_compiled_script = int(line_number) - 1  # the line number of the error info often starts from 1, but in the mappings, it starts from 0
                    error_line_number_in_original_script = line_mappings[error_line_number_in_compiled_script]
                    error_line_in_compiled_script = compiled_script.split('\n')[error_line_number_in_compiled_script]
                    error_line_in_original_script = original_script.split('\n')[error_line_number_in_original_script]
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
        'original_script': original_script,
        'compiled_script': compiled_script,
        'traceback': traceback,
        'error': error,
        'error_line_number_in_compiled_script': error_line_number_in_compiled_script,
        'error_line_number_in_original_script': error_line_number_in_original_script,
        'error_line_in_compiled_script': error_line_in_compiled_script,
        'error_line_in_original_script': error_line_in_original_script
    }

def format_apis(input_policy, api_xpaths):
    def _recursively_get_ele_property(ele_tree: ElementTree, ele):
        ele_text = ele_tree.get_ele_text(ele)
        ele_content_desc = ele_tree.get_content_desc(ele)
        return {'text': ele_text, 'content_desc': ele_content_desc}

    def _get_ordered_ui_apis(ele_tree: ElementTree, ui_state_desc, api_xpaths):
        ui_apis = {}
        for api_name, api_xpath in api_xpaths.items():
            root = etree.fromstring(ui_state_desc)
            eles = root.xpath(api_xpath)
            if not eles:
                continue
            ele_desc = etree.tostring(eles[0], pretty_print=True).decode('utf-8') # only for father node
            id_str = re.search(r' id="(\d+)"', ele_desc).group(1)
            id = int(id_str)

            ele = ele_tree.get_ele_by_xpath(api_xpath)
            ele_children = ele_tree.get_children_by_ele(ele)
            # ele_properties = ele.dict(only_original_attributes=True)

            api_desc = {'name': api_name, 'property': _recursively_get_ele_property(ele_tree, ele), 'children': [_recursively_get_ele_property(ele_tree, child) for child in ele_children]}

            ui_apis[id] = api_desc
        
        # iterate over ui_apis to get the order of apis
        ui_apis_ordered = []
        for id in sorted(ui_apis.keys()):
            ui_apis_ordered.append(ui_apis[id])
        import pdb;pdb.set_trace()
        return ui_apis_ordered
    
    current_state = input_policy.device.get_current_state()
    element_tree = input_policy.memory._memorize_state(current_state)['element_tree']
    state_desc = element_tree.get_str(is_color=False)
    ui_apis_ordered = _get_ordered_ui_apis(element_tree, state_desc, api_xpaths)
    ui_apis_str = ''
    for ui_api in ui_apis_ordered:
        ui_apis_str += f'\nelement: {ui_api["name"]}\n'
        if ui_api['property']['text']:
            ui_apis_str += f'\tText: {ui_api["property"]["text"]}\n'
        if ui_api['property']['content_desc']:
            ui_apis_str += f'\tContent Description: {ui_api["property"]["content_desc"]}\n'
        if ui_api['children'] != []:
            ui_apis_str += '\tChildren:\n'
            for child in ui_api['children']:
                if child['text']:
                    ui_apis_str += f'\t\tChild text: {child["text"]};'
                if child['content_desc']:
                    ui_apis_str += f'\t\tChild content description: {child["content_desc"]}\n'
    return ui_apis_str

class InputManager(object):
    """
    This class manages all events to send during app running
    """

    def __init__(self, device, app, policy_name, random_input,
                 event_count, event_interval,
                 script_path=None, profiling_method=None, master=None,
                 replay_output=None, task_id=0):
        """
        manage input event sent to the target device
        :param device: instance of Device
        :param app: instance of App
        :param policy_name: policy of generating events, string
        :return:
        """
        self.logger = logging.getLogger('InputEventManager')
        self.enabled = True

        self.device = device
        self.app = app
        self.policy_name = policy_name
        self.random_input = random_input
        self.events = []
        self.policy = None
        self.script = None
        self.event_count = event_count
        self.event_interval = event_interval
        self.replay_output = replay_output

        self.monkey = None
        
        self.task_id = task_id

        if script_path is not None:
            f = open(script_path, 'r')
            script_dict = json.load(f)
            from .input_script import DroidBotScript
            self.script = DroidBotScript(script_dict)

        self.policy = self.get_input_policy(device, app, master)
        self.profiling_method = profiling_method

    def get_input_policy(self, device, app, master):
        if self.policy_name == POLICY_NONE:
            input_policy = None
        elif self.policy_name == POLICY_MONKEY:
            input_policy = None
        elif self.policy_name in [POLICY_NAIVE_DFS, POLICY_NAIVE_BFS]:
            input_policy = UtgNaiveSearchPolicy(device, app, self.random_input, self.policy_name)
        elif self.policy_name in [POLICY_GREEDY_DFS, POLICY_GREEDY_BFS]:
            input_policy = UtgGreedySearchPolicy(device, app, self.random_input, self.policy_name)
        elif self.policy_name == POLICY_MEMORY_GUIDED:
            from .input_policy3 import Memory_Guided_Policy
            input_policy = Memory_Guided_Policy(device, app, self.random_input)
        elif self.policy_name == POLICY_REPLAY:
            input_policy = UtgReplayPolicy(device, app, self.replay_output)
        elif self.policy_name == POLICY_MANUAL:
            input_policy = ManualPolicy(device, app)
        else:
            self.logger.warning("No valid input policy specified. Using policy \"none\".")
            input_policy = None
        if isinstance(input_policy, UtgBasedInputPolicy):
            input_policy.script = self.script
            input_policy.master = master
        return input_policy

    def add_event(self, event):
        """
        add one event to the event list
        :param event: the event to be added, should be subclass of AppEvent
        :return:
        """
        if event is None:
            return
        self.events.append(event)

        event_log = EventLog(self.device, self.app, event, self.profiling_method)
        event_log.start()
        while True:
            time.sleep(self.event_interval)
            if not self.device.pause_sending_event:
                break
        event_log.stop()

    def start(self):
        """
        start sending event
        """
        self.logger.info("start sending events, policy is %s" % self.policy_name)

        try:
            if self.policy is not None:
                
                if os.path.exists('tmp/code.txt'):
                    for retry_time in range(MAX_RETRY_TIMES):
                        from .input_policy3 import Code_Policy
                        code_policy = Code_Policy(self.device, self.app, self.random_input, self.task_id)
                        api_xpaths = tools.load_json_file('tmp/api_xpaths_checked.json')
                        api_data = tools.load_json_file('output/notes0503/apis.json')
                        if retry_time > 0:
                            set_action_count(1) # the former code is wrong, and we start from the current UI, do not restart the app
                        else:
                            # restart the app first in case the script couldn't run and the app has not been start
                            self.add_event(RestartAppEvent(app=code_policy.app))
                            
                            if QUERY_FIRSTTIME:
                                # if there is no solution code yet at the first time, we need to generate one
                                task = tools.load_txt_file('tmp/task.txt')
                                solution_generator = SolutionGenerator('output/notes0503/apis.json')
                                formatted_apis = format_apis(code_policy, api_xpaths)
                                solution_code = solution_generator.get_solution(app_name='Notes', prompt_answer_path=os.path.join(self.device.output_dir, f'solution_{self.task_id}.json'), task=task, ui_elements=formatted_apis, enable_dependency=False, model_name='gpt-4o')
                                tools.write_txt_file('tmp/code.txt', solution_code)
                        
                        code = tools.load_txt_file('tmp/code.txt')
                        code = tools.get_combined_code('data/notes_preparation.txt', code)
                        tools.write_txt_file('tmp/combined_code.txt', code)
                        dependencies = tools.load_json_file('tmp/api_paths.json')
                        verifier = Verifier(self, code_policy, api_xpaths, api_data, dependencies)
                        code_script, line_mappings = regenerate_script(code, 'verifier', 'self.device', 'code_policy', 'api_xpaths')
                        tools.write_txt_file('tmp/compiled_code.txt', code_script)
                        tools.dump_json_file('tmp/line_mappings.json', line_mappings)
                        # in case some silly scripts include no UI actions at all, we make an empty log for batch_verifying
                        log_path = os.path.join(self.device.output_dir, f'log_{self.task_id}.yaml')
                        tools.dump_yaml_file(log_path, {'records': [], 'step_num': 0})

                        try:
                            # sys.settrace(tracefunc)
                            exec(code_script)
                            break
                        except Exception as e:
                            save_current_ui_to_log(code_policy, api_name=None)
                            tb_str = traceback.format_exc()
                            error_path = os.path.join(self.device.output_dir, f'error_task{self.task_id}_turn{retry_time}.json')
                            error_info = process_error_info(code, code_script, tb_str, str(e), line_mappings)

                            tools.dump_json_file(error_path, error_info)

                            bug_processor = BugProcessorv2(app_name='Notes', log_path=log_path, error_log_path=error_path, task=tools.load_txt_file('tmp/task.txt'), raw_solution=tools.load_txt_file('tmp/code.txt'), apis_path='output/notes0503/apis.json', api_xpath_file='tmp/api_xpaths_checked.json')

                            stuck_apis_str = format_apis(code_policy, api_xpaths)
                            script = bug_processor.process_bug(prompt_answer_path=os.path.join(self.device.output_dir, f'debug_task{self.task_id}_turn{retry_time}.json'), enable_dependency=False, model_name='gpt-4o', stuck_ui_apis=stuck_apis_str)
                            tools.write_txt_file('tmp/code.txt', script)
                    # sys.settrace(None)
                else:
                    self.policy.start(self)
            elif self.policy_name == POLICY_NONE:
                self.device.start_app(self.app)
                if self.event_count == 0:
                    return
                while self.enabled:
                    time.sleep(1)
            elif self.policy_name == POLICY_MONKEY:
                throttle = self.event_interval * 1000
                monkey_cmd = "adb -s %s shell monkey %s --ignore-crashes --ignore-security-exceptions" \
                             " --throttle %d -v %d" % \
                             (self.device.serial,
                              "" if self.app.get_package_name() is None else "-p " + self.app.get_package_name(),
                              throttle,
                              self.event_count)
                self.monkey = subprocess.Popen(monkey_cmd.split(),
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE)
                for monkey_out_line in iter(self.monkey.stdout.readline, ''):
                    if not isinstance(monkey_out_line, str):
                        monkey_out_line = monkey_out_line.decode()
                    self.logger.info(monkey_out_line)
                # may be disturbed from outside
                if self.monkey is not None:
                    self.monkey.wait()
            elif self.policy_name == POLICY_MANUAL:
                self.device.start_app(self.app)
                while self.enabled:
                    keyboard_input = input("press ENTER to save current state, type q to exit...")
                    if keyboard_input.startswith('q'):
                        break
                    state = self.device.get_current_state()
                    if state is not None:
                        state.save2dir()
        except KeyboardInterrupt:
            pass

        self.stop()
        self.logger.info("Finish sending events")

    def stop(self):
        """
        stop sending event
        """
        if self.monkey:
            if self.monkey.returncode is None:
                self.monkey.terminate()
            self.monkey = None
            pid = self.device.get_app_pid("com.android.commands.monkey")
            if pid is not None:
                self.device.adb.shell("kill -9 %d" % pid)
        self.enabled = False

