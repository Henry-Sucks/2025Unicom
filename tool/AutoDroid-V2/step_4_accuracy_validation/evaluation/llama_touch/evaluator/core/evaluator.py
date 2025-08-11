import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Tuple

import pandas as pd

from .agent import MobileAgent
from .task_trace import DatasetHelper


class FailedReason(Enum):
    GR_TRACE_NOT_FOUND = "ground-truth trace not found"
    EXEC_TRACE_NOT_FOUND = "execution trace not found"
    REF_TRACE_NOT_FOUND = "reference trace not found"
    STEP_CHECK_FAILED = "step checking failed"
    UI_POSITIONS_NOT_FOUND = "ui positions not found"


class BaseEvaluator(ABC):
    def __init__(
        self,
        agent: MobileAgent,
        epi_metadata_path: str,
        gr_dataset_path: str,
        options: Dict = None,
    ) -> None:
        logging.basicConfig(level=logging.INFO)
        self.logger = None
        self.agent: MobileAgent = agent
        self.evaluator_name: str = None
        self.helper = DatasetHelper(
            epi_metadata_path=epi_metadata_path, gr_dataset_path=gr_dataset_path
        )
        self.episode_completion: Dict[str, Tuple[bool, str]] = {}
        # evaluation options: by default, all episodes will be evaluated
        #   - "categories": [TaskCategory.GENERAL, TaskCategory.GOOGLEAPPS, ...]
        #                 only evaluate episodes in target categories
        #   - "first_n": only evaluating the first_n episodes
        #   - "episodes": [episode_1, episode_2, ...]
        #                 only evaluate target episodes
        self.options = options if options else None

    def run_evaluation(self) -> None:
        target_episodes = self.helper.get_all_episodes()

        if self.options:
            if "categories" in self.options:
                target_episodes = [
                    epi
                    for category in self.options["categories"]
                    for epi in self.helper.get_episodes_by_category(category)
                ]
            elif "episodes" in self.options:
                target_episodes = self.options["episodes"]
            elif "first_n" in self.options:
                first_n = int(self.options["first_n"])
                target_episodes = self.helper.get_all_episodes()[:first_n]

        for epi in target_episodes:
            completeness, failed_reason = self.eval_episode(epi)
            app = self.helper.get_task_app_by_episode(epi)
            path = self.helper.get_task_path_by_episode(epi)
            if failed_reason is not None:
                # users may pass string or FailedReason enum as parameter
                # accept and record both of them
                failed_reason_str = (
                    failed_reason.value
                    if isinstance(failed_reason, FailedReason)
                    else failed_reason
                )
                self.episode_completion[epi] = (completeness, failed_reason_str, app, path)
            else:
                self.episode_completion[epi] = (completeness, "", app, path)

    def eval_episode(self, episode: str) -> Tuple[bool, Optional[FailedReason]]:
        # self.logger.info(f"Evaluating episode: {episode}")
        task_description = self.helper.get_task_description_by_episode(episode)
        try:
            ret = self.eval_impl(episode, task_description)
        except Exception as e:
            
            self.logger.error(f"Failed to evaluate episode {episode}: {str(e)}")
            # TODO: add FailedReason for this case
            return False, FailedReason.UI_POSITIONS_NOT_FOUND
        return ret

    @abstractmethod
    def eval_impl(
        self, episode: str, task_description: str
    ) -> Tuple[bool, Optional[FailedReason]]:
        pass

    def report_stats(
        self,
        human_eval_path: str = None,
        only_human_eval_positive: bool = False,
        suffix: str = "",
    ) -> None:
        exec_dict = {
            epi: completed for epi, (completed, _, _, _) in self.episode_completion.items()
        }
        exec_df = pd.DataFrame(exec_dict.items(), columns=["episode", "execution"])
        if not human_eval_path:
            exec_positive = (exec_df["execution"] == 1).sum()
            exec_negative = (exec_df["execution"] == 0).sum()
            print(f"Completed tasks: {exec_positive}, failed tasks: {exec_negative}")
            self._dump_stats(exec_positive, exec_negative )
        else:
            with open(human_eval_path, "r") as f:
                human_df = pd.read_csv(f)
            eval_df = human_df.merge(exec_df, on="episode", how="inner")
            if only_human_eval_positive:
                eval_df = eval_df[eval_df[eval_df.columns[1]] == 1]
            total = eval_df.shape[0]
            if only_human_eval_positive and total < 1:
                total = 1

            human_positive = (eval_df[eval_df.columns[1]] == 1).sum()
            exec_positive = (eval_df["execution"] == 1).sum()
            exec_negative = total - exec_positive
            for comp in eval_df["execution"] == 1:
                print(comp)
            print(f"Completed tasks: {exec_positive}, failed tasks: {exec_negative}")
            tp = (eval_df[eval_df.columns[1]] == eval_df["execution"]).sum()
            self._dump_stats(
                metric=(total, human_positive, exec_positive, tp),
                suffix=suffix,
            )

    def _dump_stats(
        self,
        exec_positive = None,
        exec_negative = None,
        suffix: str = "",
    ) -> None:
        stats = [
            f"{epi},{success},{reason}, {app}, {path} \n"
            for epi, (success, reason, app ,path) in self.episode_completion.items()
        ]

        stats.append(f"Completed tasks: {exec_positive}, failed tasks: {exec_negative}")

        if not os.path.exists("evaluation/llama_touch/evaluation_output"):
            os.mkdir("evaluation/llama_touch/evaluation_output")
        # construct stats file using current time, evaluator name, and agent name
        # time format: {yyyy}-{mm}-{dd}-{hh}-{mm}-{ss}
        if suffix:
            file_name = f"evaluation/llama_touch/evaluation_output/{self.evaluator_name}_{self.agent.agent_name}_{datetime.now().strftime('%Y-%m-%d-%H:%M:%S')}_{suffix}.csv"
        else:
            file_name = f"evaluation/llama_touch/evaluation_output/{self.evaluator_name}_{self.agent.agent_name}.csv"
        with open(file_name, "w") as f:
            f.writelines(stats)
        print(f"Evaluation results were dumped to file {file_name}")
