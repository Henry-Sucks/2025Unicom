
import sys
import json
import re
import logging
import random
from abc import abstractmethod
import yaml
import copy
import requests
import ast
from .input_event import *
from .utg import UTG
from .my_utg import MyUTG
import time
from .input_event import ScrollEvent


from .my_utils import *

# from memory.memory_builder import Memory
import tools
import pdb
import os
import io

from .input_event import KeyEvent, IntentEvent, TouchEvent, UIEvent, KillAppEvent
from .input_policy import InputPolicy, InputInterruptedException

# from query_lmql import prompt_llm_with_history
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Max number of restarts
MAX_NUM_RESTARTS = 5
# Max number of steps outside the app
MAX_NUM_STEPS_OUTSIDE = 1000
MAX_NUM_STEPS_OUTSIDE_KILL = 1000
# Max number of replay tries
MAX_REPLY_TRIES = 5

# Some input event flags
EVENT_FLAG_STARTED = "+started"
EVENT_FLAG_START_APP = "+start_app"
EVENT_FLAG_STOP_APP = "+stop_app"
EVENT_FLAG_EXPLORE = "+explore"
EVENT_FLAG_NAVIGATE = "+navigate"
EVENT_FLAG_TOUCH = "+touch"

FINISHED = "task_completed"
MAX_SCROLL_NUM = 2
USE_LMQL = False

# 和DFS有关的全局变量
MAX_DFS_DEPTH = 2
MAX_DFS_WAITING_TIME = 10


class MyUtgBasedInputPolicy(InputPolicy):
    """
    state-based input policy
    """

    def __init__(self, device, app):
        super(MyUtgBasedInputPolicy, self).__init__(device, app)
        # self.random_input = random_input
        self.script = None
        self.master = None
        self.script_events = []
        self.last_event = None
        self.last_state = None
        self.current_state = None
        self.utg = UTG(device=device, app=app, random_input=False)
        self.script_event_idx = 0
        if self.device.humanoid is not None:
            self.humanoid_view_trees = []
            self.humanoid_events = []

    def generate_event(self, input_manager):
        """
        generate an event
        @return:
        """

        # Get current device state
        self.current_state = self.device.get_current_state()
        if self.current_state is None:
            import time
            time.sleep(5)
            return KeyEvent(name="BACK")

        self.__update_utg()

        event = None

        # if the previous operation is not finished, continue
        if len(self.script_events) > self.script_event_idx:
            event = self.script_events[self.script_event_idx].get_transformed_event(self)
            self.script_event_idx += 1

        # First try matching a state defined in the script
        if event is None and self.script is not None:
            operation = self.script.get_operation_based_on_state(self.current_state)
            if operation is not None:
                self.script_events = operation.events
                # restart script
                event = self.script_events[0].get_transformed_event(self)
                self.script_event_idx = 1

        if event is None:
            old_state, event = self.generate_event_based_on_utg(input_manager)
            import time
            time.sleep(3)
        # update last events for humanoid
        if self.device.humanoid is not None:
            self.humanoid_events = self.humanoid_events + [event]
            if len(self.humanoid_events) > 3:
                self.humanoid_events = self.humanoid_events[1:]

        self.last_state = self.current_state if old_state is None else old_state
        self.last_event = event
        return event

    def __update_utg(self):
        self.utg.add_transition(self.last_event, self.last_state, self.current_state)

    @abstractmethod
    def generate_event_based_on_utg(self, input_manager):
        """
        generate an event based on UTG
        :return: InputEvent
        """
        # TODO: 实现基于UTG生成事件的方法
        pass


class FunctionExplorePolicy(MyUtgBasedInputPolicy):
    def __init__(self, device, app):
        super(FunctionExplorePolicy, self).__init__(device, app)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device = device
        self.app = app
        self.action_count = 0
        self.master = None
        self.__first_event = True


        self.__nav_target = None
        self.__nav_num_steps = -1
        self.__num_restarts = 0
        self.__num_steps_outside = 0
        self.__event_trace = ""
        self.__missed_states = set()
        self.__random_explore = False



        self.my_utg = MyUTG(device=device, app=app, random_input=False)


        self.main_menu_activity = r"com.sinovatech.unicom.ui/com.sinovatech.unicom.basic.ui.activity.MainActivity"
        self.menu_bar_id= r"com.sinovatech.unicom.ui:id/unicom_home_tabbar_menu"
        self.main_menu_first_hit = False
        self.menu_phrase = True
        self.page_phrase = False

        self.current_function = None
        self.already_explored = False
        self.actions_to_explore = None

        # DFS回退过程中应该到达的状态，如果因为加载时间、页面逻辑等原因没有到达，则另外处理
        self.expected_state = None

        # 新增：记录已点击的按钮
        self.clicked_buttons = set()  # 使用集合存储已点击按钮的唯一标识
        self.current_content = ""


        # BFS相关数据结构
        self.dfs_stack = []  # 存储待探索的状态
        self.visited_states = set()  # 存储已访问的状态
        self.state_actions_map = {}  # 存储状态到可用动作的映射
        self.dfs_depth = 0

    # 根据utg得出当前state执行返回event后应该落回的状态
    def _get_expected_state(self, current_state):

        expected_state = self.my_utg.get_expected_state(current_state)
        if expected_state is None:
            self.logger.info("No expected state found for current state.")
            return None
        else:
            return expected_state.structure_str
        
    def generate_event_based_on_utg(self, input_manager):
        current_state = self.current_state
        if current_state.state_str in self.__missed_states:
            self.__missed_states.remove(current_state.state_str)

        if current_state.get_app_activity_depth(self.app) < 0:
            # If the app is not in the activity stack
            start_app_intent = self.app.get_start_intent()

            # It seems the app stucks at some state, has been
            # 1) force stopped (START, STOP)
            #    just start the app again by increasing self.__num_restarts
            # 2) started at least once and cannot be started (START)
            #    pass to let viewclient deal with this case
            # 3) nothing
            #    a normal start. clear self.__num_restarts.

            if self.__event_trace.endswith(EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP) \
                    or self.__event_trace.endswith(EVENT_FLAG_START_APP):
                self.__num_restarts += 1
                self.logger.info("The app had been restarted %d times.", self.__num_restarts)
            else:
                self.__num_restarts = 0

            # pass (START) through
            if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
                if self.__num_restarts > MAX_NUM_RESTARTS:
                    # If the app had been restarted too many times, enter random mode
                    msg = "The app had been restarted too many times. Entering random mode."
                    self.logger.info(msg)
                    self.__random_explore = True
                else:
                    # Start the app
                    self.__event_trace += EVENT_FLAG_START_APP
                    self.logger.info("Trying to start the app...")
                    return self.current_state, IntentEvent(intent=start_app_intent)
        # elif current_state.get_app_activity_depth(self.app) > 0:
        #     # If the app is in activity stack but is not in foreground
        #     self.__num_steps_outside += 1

        #     if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
        #         # If the app has not been in foreground for too long, try to go back
        #         if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE_KILL:
        #             stop_app_intent = self.app.get_stop_intent()
        #             go_back_event = IntentEvent(stop_app_intent)
        #         else:
        #             go_back_event = KeyEvent(name="BACK")
        #         self.__event_trace += EVENT_FLAG_NAVIGATE
        #         self.logger.info("Going back to the app...")
        #         return self.current_state, go_back_event
        # else:
        #     # If the app is in foreground
        #     self.__num_steps_outside = 0
            
        


        def __if_current_is_main_menu():
            # return self.current_state.compare_to_yaml(self.main_menu)
            return self.current_state.is_current_activity(self.main_menu_activity) # Activity名
        
        if not self.main_menu_first_hit:
            if not __if_current_is_main_menu():
                # 执行操作到达主页面，或者可以什么都不做？
                return self.current_state, ManualEvent()
            else:
                self.main_menu_first_hit = True
                # 生成触发主页面目录按钮的event
                # self.logger.info("Current View")
                # self.logger.info(self.current_state.views)
                time.sleep(3)
                self.current_state = self.device.get_current_state()
                self.my_utg.add_node(self.current_state, "Starting point - Main page")
                self.last_state = self.current_state
                self.device.send_event(TouchEvent(view = self.current_state.get_view_by_id(self.menu_bar_id)))
                # return self.current_state, TouchEvent(view = self.current_state.get_view_by_id(self.menu_bar_id))

        if self.menu_phrase:
            time.sleep(3)
            current_state = self.device.get_current_state()
            self.my_utg.add_node(self.current_state, "Main page with menu bar - navigation to each main function of this app")
            self.my_utg.add_transition(TouchEvent(view = self.last_state.get_view_by_id(self.menu_bar_id)), self.last_state, self.current_state, KeyEvent(name="BACK"))

            menu_view = current_state.get_view_by_id(r'com.sinovatech.unicom.ui:id/home_menu_pop_recylerView')

            if menu_view is None:
                self.logger.warning("Menu view not found!")
                return self.current_state, ManualEvent()

            clickable_buttons = extract_text_views(menu_view)
            
            if not clickable_buttons:
                self.logger.info("No clickable buttons found in menu")
                self.menu_phrase = False
                self.page_phrase = True
                return self.current_state, ManualEvent()

            # 遍历按钮，寻找未点击过的
            for button_view, button_text in clickable_buttons:
                button_str = button_view.get('view_str')
                if button_str not in self.clicked_buttons:
                    self.logger.info(f"Clicking new button: {button_text}")
                    print(button_view)
                    self.current_content = button_text
                    self.current_function = button_text
                    if button_text != "旅行":
                        continue
                    self.clicked_buttons.add(button_str)  # 标记为已点击
                    self.menu_phrase = False
                    self.page_phrase = True
                    return self.current_state, TouchEvent(view=button_view)

            # 如果所有按钮都已点击过，切换到页面阶段
            self.logger.info("All menu buttons have been clicked")
            return self.current_state, ExitEvent() 

        if self.page_phrase:
            time.sleep(5)
            self.current_state = self.device.get_current_state()

            def is_back_key_event(event):
                return isinstance(event, KeyEvent) and event.name == "BACK"
            
            if is_back_key_event(self.last_event):
                self.logger.info("The last event is a BACK")
                if self.current_state.structure_str != self.expected_state:
                    if self.expected_state is None:
                        self.logger.info("Expected state not found, skip it.")
                    
                    else:
                        waited_times = 0
                        while waited_times < MAX_DFS_WAITING_TIME:
                            self.logger.info('Current state: ' + self.current_state.structure_str)
                            self.logger.info('Expected state: ' + self.expected_state)
                            self.logger.info("Waiting for the expected state...")
                            time.sleep(1)
                            waited_times += 1
                            self.current_state = self.device.get_current_state()
                            if self.current_state.structure_str == self.expected_state:
                                break

                        raise InputInterruptedException("Waited too long, may have entered an unknown state we can't go back.")

            # 如果是第一次到达该状态，获取可用动作并加入栈
            if self.current_state.structure_str not in self.visited_states:
                self.dfs_depth += 1
                print(f"Entering a new state: {self.current_state.structure_str}")
                print(f"DFS depth: {self.dfs_depth}")

                self.visited_states.add(self.current_state.structure_str)
                current_function, actions_to_explore = self.__explore_current_state()

                if self.dfs_depth > MAX_DFS_DEPTH:
                    print("DFS depth exceeded, going back...")
                    self.dfs_depth -= 1

                    # 更新utg
                    self.my_utg.add_node(self.current_state, current_function)
                    self.my_utg.add_transition(self.last_event, self.last_state, self.current_state, KeyEvent(name="BACK"))
                    # 更新expected_state
                    self.expected_state = self._get_expected_state(self.current_state)
                    return self.current_state, KeyEvent(name="BACK")
                

                
                
                
                
                self.current_function = current_function
                self.my_utg.add_node(self.current_state, self.current_function)
                self.my_utg.add_transition(self.last_event, self.last_state, self.current_state, KeyEvent(name="BACK"))

                if len(actions_to_explore) == 0:
                    print("No actions to explore, something is wrong? Going back...")
                    self.dfs_depth -= 1
                    return self.current_state, KeyEvent(name="BACK")
                else:
                    print(f"Actions to explore: {len(actions_to_explore)}")
                self.current_function = current_function
                self.state_actions_map[self.current_state.structure_str] = actions_to_explore
                # 将状态和动作加入栈顶，实现深度优先
                actions_to_explore.append((self.current_state, KeyEvent(name="BACK")))
                for action in reversed(actions_to_explore):
                    self.dfs_stack.append((self.current_state, action))

            else:
                # 如果状态已访问过，直接返回
                print(f"State {self.current_state.structure_str} has been visited before.")
            
            # DFS探索
            while self.dfs_stack:
                current_state, action = self.dfs_stack.pop()  # 从栈顶取出元素
                
                # 尝试执行未探索的动作
                if not self.utg.is_event_explored(event=action, state=current_state):
                    print("Trying an unexplored event with DFS.")
                    print("Next event: ")
                    print(action.get_event_str(current_state))
                    print("Remaining events: ")
                    print(self.dfs_stack)
                    
                    if isinstance(action, KeyEvent) and  action.name == "BACK":
                        print("Finishing DFS exploration on this page, going back...")
                        self.dfs_depth -= 1
                    return current_state, action
                
                # 如果所有动作都已探索，继续从栈中取出下一个元素
                
                # 如果栈为空，探索结束
                if not self.dfs_stack:
                    print("DFS exploration completed.")
                    return self.current_state, KeyEvent(name="BACK")

                
                print("I am not supposed to be here, something is wrong?")





        # self.current_state = self.device.get_current_state()
        # current_function, actions_to_explore = self.__explore_current_state()
        # self.current_function = current_function

        # # 实现BFS探索
        # actions_to_explore.insert(0, KeyEvent(name="BACK"))
        # if self.menu_phrase:
        #     actions_to_explore.insert(1, TouchEvent(view = self.current_state.get_view_by_id(self.menu_bar_id)))
        # print("Actions to explore: ")
        # print(actions_to_explore)


        # next_event = None
        # for input_event in actions_to_explore:
        #     if input_event == TouchEvent(view = self.current_state.get_view_by_id(self.menu_bar_id)):
        #         # return self.current_state, input_event
        #         next_event = input_event
        #         return self.current_state, next_event
        #     if not self.utg.is_event_explored(event=input_event, state=self.current_state):
        #         self.logger.info("Trying an unexplored event.")
        #         # self.__event_trace += EVENT_FLAG_EXPLORE
        #         # return self.current_state, input_event
        #         next_event = input_event
        #         return self.current_state, next_event

        
            
            
        # target_state = self.__get_nav_target(self.current_state)
        # if target_state:
        #     navigation_steps = self.utg.get_navigation_steps(from_state=self.current_state, to_state=target_state)
        #     if navigation_steps and len(navigation_steps) > 0:
        #         self.logger.info("Navigating to %s, %d steps left." % (target_state.state_str, len(navigation_steps)))
        #         # self.__event_trace += EVENT_FLAG_NAVIGATE
        #         return self.current_state, navigation_steps[0][1]
            

        # # If couldn't find a exploration target, stop the app
        # stop_app_intent = self.app.get_stop_intent()
        # self.logger.info("Cannot find an exploration target. Trying to restart app...")
        # # self.__event_trace += EVENT_FLAG_STOP_APP
        # return self.current_state, IntentEvent(intent=stop_app_intent)
    

    def __get_nav_target(self, current_state):
        # # If last event is a navigation event
        # if self.__nav_target and self.__event_trace.endswith(EVENT_FLAG_NAVIGATE):
        #     navigation_steps = self.utg.get_navigation_steps(from_state=current_state, to_state=self.__nav_target)
        #     if navigation_steps and 0 < len(navigation_steps) <= self.__nav_num_steps:
        #         # If last navigation was successful, use current nav target
        #         self.__nav_num_steps = len(navigation_steps)
        #         return self.__nav_target
        #     else:
        #         # If last navigation was failed, add nav target to missing states
        #         self.__missed_states.add(self.__nav_target.state_str)

        reachable_states = self.utg.get_reachable_states(current_state)

        for state in reachable_states:
            # Only consider foreground states
            if state.get_app_activity_depth(self.app) != 0:
                continue
            # Do not consider missed states
            if state.state_str in self.__missed_states:
                continue
            # Do not consider explored states
            if self.utg.is_state_explored(state):
                continue
            self.__nav_target = state
            navigation_steps = self.utg.get_navigation_steps(from_state=current_state, to_state=self.__nav_target)
            if len(navigation_steps) > 0:
                self.__nav_num_steps = len(navigation_steps)
                return state

        self.__nav_target = None
        self.__nav_num_steps = -1
        return None
    
    def _scroll_to_top(self, scroller, all_views_for_mark, old_state=None):
        prefix_scroll_event = []
        if old_state is None:
            old_state = self.current_state 
        for _ in range(MAX_SCROLL_NUM):  # first scroll up to the top
            self.device.send_event(ScrollEvent(view=scroller, direction="UP"))
            scrolled_state = self.device.get_current_state()
            self.utg.add_transition(ScrollEvent(view=scroller, direction="UP"), old_state, scrolled_state)
            old_state = scrolled_state
            state_prompt, scrolled_candidate_actions, scrolled_views, _ = scrolled_state.get_described_actions()
            scrolled_new_views = []  # judge whether there is a new view after scrolling
            for scrolled_view in scrolled_views:
                if scrolled_view not in all_views_for_mark:
                    scrolled_new_views.append(scrolled_view)
                    all_views_for_mark.append(scrolled_view)
            if len(scrolled_new_views) == 0:
                break

            prefix_scroll_event.append(ScrollEvent(view=scroller, direction="UP"))
        return prefix_scroll_event
    


    def __explore_current_state(self):
        current_state = self.device.get_current_state()
        # 遍历页面，获取按钮上的关键词和页面布局，为给大模型，让大模型进行：总结页面功能，判断是否由更多值得探索的子功能，返回进一步探索方案
        time.sleep(3)
        
        # scroll to get prompt content
        scrollable_views = current_state.get_scrollable_views()
        # if len(scrollable_views) > 0:
        #     whole_state_views, whole_state_actions, whole_state_strs = [], [], []
        #     _, all_actions, current_views, _ = current_state.get_described_actions()
        #     all_views_without_id = copy.deepcopy(current_views)
        #     # all_views_without_id = [view for view in copy.deepcopy(current_views) if 'button' in view]
            
        #     for scrollerid in range(len(scrollable_views)):
        #         scroller = scrollable_views[scrollerid]
        #         prefix_scroll_event = []

        #         too_few_item_time = 0

        #         for _ in range(MAX_SCROLL_NUM):
        #             self.device.send_event(ScrollEvent(view=scroller, direction="DOWN"))
        #             scrolled_state = self.device.get_current_state()
        #             state_prompt, scrolled_candidate_actions, scrolled_views, _ = scrolled_state.get_described_actions()

        #             scrolled_new_views = []
        #             for scrolled_view_id in range(len(scrolled_views)):
        #                 scrolled_view = scrolled_views[scrolled_view_id]
        #                 if scrolled_view not in all_views_without_id:
        #                     scrolled_new_views.append(scrolled_view)
        #                     all_views_without_id.append(scrolled_view)
        #                     all_actions.append([ScrollEvent(view=scroller, direction="DOWN"), scrolled_candidate_actions[scrolled_view_id]])

        #             if len(scrolled_new_views) == 0:
        #                 break

        #             if len(scrolled_new_views) < 2:
        #                 too_few_item_time += 1
        #             if too_few_item_time >= 2:
        #                 break
                        
        #         for all_view_id in range(len(all_views_without_id)):
        #             view = all_views_without_id[all_view_id]
        #             if view not in whole_state_views:
        #                 whole_state_views.append(view)
        #                 whole_state_actions.append(all_actions[all_view_id])

        #         self._scroll_to_top(scroller, all_views_without_id, current_state)
            
        #     function_summary, actions = self._get_func_subfunc_from_views(views=whole_state_views, candidate_actions=whole_state_actions)


        
        # else:
        #     function_summary, actions = self._get_func_subfunc_from_views(current_state=current_state)

        function_summary, actions = self._get_func_subfunc_from_views(current_state=current_state)

        print(f"I am in page {function_summary}!")

        return function_summary, actions


    def _make_prompt(self, state_prompt):        
        full_state_prompt = 'Current UI state: \n' + state_prompt
        
        introduction = '''
You are a smartphone assistant to help users summarize and explore page functionalities by interacting with mobile apps. 

Given the HTML-formatted current UI state of a page, your job is to:
1. Summarize the core functions of the current page.
2. Determine whether the page contains sub-functions worth exploring.
3. If sub-functions exist, identify which UI elements in the current UI state are most likely to navigate to these sub-functions.
'''
        # request_prompt = "\nYour answer should always use the following format: { \"Summary\": \"...<concise overview of the mobile app page's core functions>\", \"SubFunctions\": { \"Exist\": \"Yes/No\", \"Description\": \"...<brief explanation of noteworthy sub-functions if any>\", \"NavigationElements\": [\"...<UI element id>\"] } } \n\n**Note that:**\n1. If no sub-functions exist (\"Exist\": \"No\"), \"NavigationElements\" should be an empty array []\n2. All ids in \"NavigationElements\" must exactly match the id attributes in the provided Current UI state\n3.Exclude elements if: contains >=3 line breaks(<br>s), has long numeric strings, or contains descriptive/non-functional text\n4. Please do not output any content other than the JSON format.**"    
        
        request_prompt = """
Your answer should always use the following format: 
{
  "Summary": "...<concise overview of the mobile app page's core functions>",
  "SubFunctions": {
    "Exist": "Yes/No",
    "Description": "...<brief explanation of noteworthy sub-functions if any>",
    "NavigationElements": ["...<UI element id>"]
  }
}

**Note that:**
1. Only include <button> elements in "NavigationElements"
2. Exclude elements from "NavigationElements" if ANY of these is true:
   - contains >=3 line breaks(count ALL: <br>, <br/>)
   - has long numeric strings with >=6 digits(e.g. "1902993047638044672")
   - is part of the MAIN FUNCTIONAL FLOW(e.g. 'Search', 'Submit')
   - contains descriptive text or state indicators
3. If no sub-functions exist ("Exist": "No"), "NavigationElements" should be an empty array []
4. All ids in "NavigationElements" must exactly match the id attributes in the provided Current UI state
5. Please do not output any content other than the JSON format.
""" 
        
        prompt = introduction + '\n' + full_state_prompt + '\n' + request_prompt
        return prompt
     
    def _get_func_subfunc_from_views(self, views=None, current_state=None, candidate_actions=None):
        # def clean_print(text):
        #     try:
        #         # 设置控制台编码为utf-8
        #         import sys
        #         import io
        #         sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        #         print(text)
        #     except UnicodeEncodeError:
        #         # 替换无法编码的字符
        #         cleaned_text = text.encode('utf-8', errors='replace').decode('utf-8')
        #         print(cleaned_text)

        if views:
            views_with_id = []
            for id in range(len(views)):
                views_with_id.append(tools.insert_id_into_view(views[id], id))
            state_prompt = '\n'.join(views_with_id)
            
            prompt = self._make_prompt(state_prompt)
        else:
            state_prompt, candidate_actions, _, _ = current_state.get_described_actions()
            prompt = self._make_prompt(state_prompt)

        # prompt = prompt.replace('\xa0', ' ')
        # prompt = prompt.replace('\ue728', ' ')
        # prompt = prompt.replace('\xa5', '¥')
        
        print('********************************** prompt: **********************************')
        # print(prompt.encode('utf-8', errors='replace').decode('utf-8'))
        print('********************************** end of prompt **********************************')
        response = tools.query_deepseek(prompt.encode('utf-8', errors='replace').decode('utf-8'))
        print(f'response: {response}')

        with open('ds_response.txt', 'a', encoding='utf-8') as f:
            f.write(f'prompt: {prompt}\n')
            f.write(f'response: {response}\n')


        function_summary = self._extract_summary_from_response(response)
        ids = self._extract_ids_from_response(response)
        # print(f'ids: {ids}')
        touch_actions = []
        # print(f'action_example: {candidate_actions[int(ids[0])]}')
        for id in ids:
            id=int(id)
            touch_actions.append(candidate_actions[id])
        # self.device.send_event(candidate_actions[int(ids[0])])
        return function_summary, touch_actions
    
    def _extract_ids_from_response(self, v):
        navigation_ids = []
        import json
        try:
            if isinstance(v, str):
                v = ast.literal_eval(v)
        except:
            print('format error: v')
                       
        if 'SubFunctions' in v:
            sub_funcs = v['SubFunctions']

            if 'NavigationElements' in sub_funcs and isinstance(sub_funcs['NavigationElements'], list):
                navigation_ids = sub_funcs['NavigationElements']
      
        return navigation_ids
    
    def _extract_summary_from_response(self, v):
        import json
        try:
            if isinstance(v, str):
                v = ast.literal_eval(v)
        except:
            print('format error: v')
                       
        if 'Summary' in v:
            summary = v['Summary']
        return summary
         




        
