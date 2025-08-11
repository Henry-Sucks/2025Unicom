import argparse
import os
from typing import List, Optional

from config import CONFIG
from core.agent import MobileAgent
from core.common.action_type import Action
from core.task_trace import Agent, DatasetHelper, TaskTrace
from core.testbed_evaluator import TestbedEvaluator
from utils import get_instructions_episodes


class BaseAgent(MobileAgent):

    def __init__(self, name, exec_trace_path) -> None:
        super().__init__()
        self.agent = name
        self.exec_trace_path = exec_trace_path
        self.epi_to_exec_trace_path = {}

    def load_predicted_action_by_episode(self, episode: str) -> Optional[List[Action]]:
        exec_trace: TaskTrace = self.load_exec_trace_by_episode(episode)
        if exec_trace:
            return [ui_state.action for ui_state in exec_trace]
        return None
   
    def load_exec_trace_by_episode(self, episode: str) -> Optional[TaskTrace]:
        helper = DatasetHelper(CONFIG.EPI_METADATA_PATH, CONFIG.GR_DATASET_PATH)
        path = helper.get_task_path_by_episode(episode)
        exec_trace_path = os.path.join(self.exec_trace_path, path)
        if not os.path.exists(exec_trace_path):
            return None
        return helper.load_testbed_trace_by_path(exec_trace_path)
    
def parse_args():
    parser = argparse.ArgumentParser(description="This script generates solutions.")
    parser.add_argument('-a', '--agent_name', default="autodroidv2")
    args = parser.parse_args()

    return args

def get_agent_config(agent_name):
    if agent_name == Agent.AUTODROID.value:
        return Agent.AUTODROID,CONFIG.AUTODROID_EXEC_TRACE_PATH
    elif agent_name == Agent.AUTODROID_V2.value:
        return Agent.AUTODROID_V2, CONFIG.AUTODROID_V2_EXEC_TRACE_PATH
    elif agent_name == Agent.SEECLICK.value:
        return Agent.SEECLICK, CONFIG.SEECLICK_EXEC_TRACE_PATH
    elif agent_name == Agent.COGAGENT.value:
        return Agent.COGAGENT, CONFIG.COGAGENT_EXEC_TRACE_PATH
    elif agent_name == Agent.MIND2WEB.value:
        return Agent.MIND2WEB, CONFIG.MIND2WEB_EXEC_TRACE_PATH

if __name__ == "__main__":
    
    args = parse_args()

    agent_name = args.agent_name
    
    agent_name, agent_exec_path = get_agent_config(agent_name)

    agent = BaseAgent(agent_name, agent_exec_path)
    instructions_fp = CONFIG.TEMP_EPI_METADATA_PATH
    episodes = get_instructions_episodes(instructions_fp)

    t = TestbedEvaluator(
        agent=agent,
        epi_metadata_path=CONFIG.EPI_METADATA_PATH,
        gr_dataset_path=CONFIG.GR_DATASET_PATH,
        options={
            "episodes":episodes,
            "check_fuzzy_match": True,
            "check_exact_match": True,
            "check_system_state": True,
        },
        
    )
    t.run_evaluation()
    t.report_stats()