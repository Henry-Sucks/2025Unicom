# CHANGEABLE
AVD_NAME = "pixel_6a_api31"
EMULATOR_AGRS = {
    "snapshot" : "snap_2024-11-12_14-17-11",
    "port" : "5554",
    # "no-window" : "true",  # Change this to "true" to run the emulator without GUI.
}

# NO NEED TO CHANGE
DOC_PATH = "evaluation/droidtask/docs"
FIRST_SCREEN_ELEMENTS_PATH = 'evaluation/droidtask/experiment/first_screen_elements'
BASE_APK_PATH = 'evaluation/droidtask/apks'

TASKS_PATH = 'evaluation/droidtask/experiment/tasks/tasks.json'
TASKS_GROUNDTRUTH_PATH = 'evaluation/droidtask/experiment/tasks/tasks-gt.json'

DEBUG_MODE = True
BASE_EXPERIMENT_PATH = "evaluation/droidtask/experiment/output"
BASELINE_PATH = {
    "autodroidv1_llama": "evaluation/droidtask/data/autodroidv1_llama_results",
    "autodroidv1_gpt": "evaluation/droidtask/data/autodroidv1_gpt_results",
    "autodroidv2_llama": "evaluation/droidtask/data/autodroidv2_llama_results",      
    "autodroidv2_gpt": "evaluation/droidtask/data/autodroidv2_gpt_results",      
    "mind2web_llama": "evaluation/droidtask/data/mind2web_llama_results",
    "mind2web_gpt": "evaluation/droidtask/data/mind2web_gpt_results",
    "seeclick": "evaluation/droidtask/data/seeclick_results",
    "cogagent": "evaluation/droidtask/data/cogagent_results",
}
GROUNDTRUTH_PATH = 'evaluation/droidtask/data/groundtruth'
