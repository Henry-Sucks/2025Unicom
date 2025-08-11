# iterate over output_mind2web_llama directory, and for each app, iterate over each task
import argparse
import os
import time
import yaml
from evaluation.droidtask.config import BASE_EXPERIMENT_PATH, BASELINE_PATH, GROUNDTRUTH_PATH, TASKS_GROUNDTRUTH_PATH, EMULATOR_AGRS
from evaluation.droidtask.experiment.test_all_tasks import run_all_tasks
import tools as tools
from dotenv import load_dotenv

load_dotenv()

def get_element(html_str, id):
    from lxml import etree
    try:
        # Parse the HTML string
        parser = etree.HTMLParser()
        tree = etree.fromstring(html_str, parser)

        # Find the element with id='3'
        element = tree.xpath(f"//*[@id='{id}']")[0]

        # Create a new element with only the desired node (without its children)
        element_without_children = etree.Element(element.tag, attrib=element.attrib)

        # remove all attributes except for text and alt
        for key in element_without_children.attrib:
            if key not in ['text', 'alt']:
                element_without_children.attrib.pop(key)
        element_without_children.text = element.text  # 保留text属性

        # Convert back to string (optional)
        result_str = etree.tostring(element_without_children, pretty_print=True).decode()
        return result_str
    except:
        # Parse the HTML string
        parser = etree.HTMLParser()
        tree = etree.fromstring(html_str, parser)

        # Find the element with id='3'
        element = tree.xpath(f'//*[@id="{id}"]')[0]

        # Create a new element with only the desired node (without its children)
        element_without_children = etree.Element(element.tag, attrib=element.attrib)

        # remove all attributes except for text and alt
        for key in element_without_children.attrib:
            if key not in ['text', 'alt']:
                element_without_children.attrib.pop(key)
        
        element_without_children.text = element.text  # 保留text属性

        # Convert back to string (optional)
        result_str = etree.tostring(element_without_children, pretty_print=True).decode()
        return result_str

def get_action_desc(html, id, action_type, input_text):
    if 'scroll' in action_type.lower():
        return action_type
    element = get_element(html, id)
    if action_type == 'set_text' or action_type == 'input_text':
        return f'Tap: {element} Input Text: {input_text}'
    elif action_type.lower() != 'touch':
        return 'match/get_text/__next__/__index__'
    else:
        return f'Tap: {element}'

all_tasks_gt = tools.load_json_file(TASKS_GROUNDTRUTH_PATH)

def test_app_tasks(agent, app, output_dir, model_name, run_tasks_online=True):
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    if run_tasks_online:
        run_all_tasks(app, f"{BASE_EXPERIMENT_PATH}/{agent}", model_name)
    
    app_accs, all_tasks, app_correct_action_num, app_all_action_num, app_redundancies = [], [], 0, 0, []
    stats = []
    if not os.path.exists(os.path.join(output_dir, app)):
        return None, None, None
    
    for task_name in os.listdir(os.path.join(output_dir, app)):
        # import pdb;pdb.set_trace()
        if 'task' in task_name and '.yaml' in task_name and '.json' not in task_name:
            all_tasks.append(task_name)
            gt = all_tasks_gt[app][task_name]
            print(app, gt['task'], task_name)
            try: 
                print(os.path.join(output_dir, app, task_name, 'log.yaml'))
                if os.path.exists(os.path.join(output_dir, app, task_name, 'log.yaml')):
                    log = tools.load_yaml_file(os.path.join(output_dir, app, task_name, 'log.yaml'))
                else:
                    log = tools.load_yaml_file(os.path.join(output_dir, app, task_name))
            except:
                print('warning, log not found', app, task_name)
                continue
            actions = []
            if not log:
                print('warning, log empty', app, task_name)
                
            else:
                for record_id, record in enumerate(log['records']):
                    if record['Choice'] == -1:
                        continue
                    try:
                        desc = get_action_desc(record['State'], record['Choice'], record['Action'], record['Input'])
                        if 'scroll' not in desc.lower() and desc != 'match/get_text/__next__/__index__':
                            actions.append(desc.lower())
                    except:
                        print('warning, action wrong', app, task_name, record_id, record['Choice'], record['Action'], record['Input'])
            if not os.path.exists(os.path.join(GROUNDTRUTH_PATH, app, task_name)):
                print('warning, log not found', app, task_name)
                continue
            gt_log = tools.load_yaml_file(os.path.join(GROUNDTRUTH_PATH, app, task_name))
            gt_actions = []
            for record in gt_log['records']:
                if record['Choice'] == -1:
                    continue
                try:
                    desc = get_action_desc(record['State'], record['Choice'], record['Action'], record['Input'])
                    if 'scroll' not in desc.lower() and desc != 'match/get_text/__next__/__index__':
                        gt_actions.append(desc.lower())
                except:
                    print('warning, action wrong', app, task_name, record['Choice'], record['Action'], record['Input'])
            
            task_correct = True
            action_missmatch = None
            for act in gt_actions:
                if act.lower() not in actions:
                    task_correct = False
                    action_missmatch = act.lower()
                    print(f'warning, {act} not in actions')
                else:
                    app_correct_action_num += 1
                    
                # else:
                #     print(act)
            app_all_action_num += len(gt_actions)
            
            if task_correct:
                app_accs.append(task_name)
                app_redundancies.append(len(gt_actions)/len(actions))
            else:
                if os.path.exists(os.path.join(output_dir, app, task_name, 'code.txt')):
                    code = tools.load_txt_file(os.path.join(output_dir, app, task_name, 'code.txt'))
                    print(code, '\n\n')
                    if os.path.exists(os.path.join(output_dir, app, task_name, 'error.json')):
                        error_info = tools.load_json_file(os.path.join(output_dir, app, task_name, 'error.json'))
                        print(error_info['traceback'], '\n\n')
                print('\n'.join(actions), '\n', '-'*10, '\n', '\n'.join(gt_actions), '*'*40)

            stats.append({
                "app": app,
                "task": gt['task'],
                "task_name":task_name,
                "result": task_correct,
                "action_missmatch": action_missmatch
            })
            # print('-'*40)
    try:
        app_action_acc_ratio = app_correct_action_num / app_all_action_num
        if len(app_redundancies) == 0:
            app_redundancy = 0
        else:
            app_redundancy = sum(app_redundancies) / len(app_redundancies)
        result_path = os.path.join(output_dir, app, 'result.json')
        tools.dump_json_file(result_path, {'correct': app_accs, 'all_tasks': all_tasks, 'acc': [len(app_accs), len(all_tasks)], 'action_acc': [app_correct_action_num, app_all_action_num, app_action_acc_ratio], 'redundancy': [app_redundancy, app_redundancies]})
        
    except Exception as e:
        print('warning, error ', e)
    return app_accs, all_tasks, stats

def summarize_final_results(baseline_dir, output_dir):
    all_results = {}
    correct_num, all_num = 0, 0
    correct_act_num, all_act_num = 0, 0
    ratios = []
    folders = [f for f in os.listdir(baseline_dir) if os.path.isdir(os.path.join(baseline_dir, f)) and '-bk' not in f]
    for folder in folders:
        result_path = os.path.join(baseline_dir, folder, 'result.json')
        if os.path.exists(result_path):
            result = tools.load_json_file(result_path)
            acc = result['acc']
            try:
                all_results[folder] = (acc, acc[0]/acc[1], result['action_acc'][2], result['redundancy'])
            except:
                import pdb;pdb.set_trace()
            correct_num += acc[0]
            all_num += acc[1]
            correct_act_num += result['action_acc'][0]
            all_act_num += result['action_acc'][1]
            ratios += result['redundancy'][1]
    # print(all_results)
    print_str = ""
    print('success rate', 'action acc', 'redundancy ratio')
    for i in range(1, 4):
        for app_name in ['applauncher', 'calendar', 'camera', 'clock', 'contacts', 'dialer', 'filemanager', 'firefox', 'gallery', 'messenger', 'music', 'notes', 'voicerecorder']:
            print_str += f'& {app_name}: '
            # 保留3位小数
            if i == 3:
                print_str += "{:.1f}".format(all_results[app_name][i][0]*100)
            else:
                print_str += "{:.1f}".format(all_results[app_name][i]*100)
            print_str += '\% & '
        avg_sr = correct_num/all_num
        avg_act_acc = correct_act_num/all_act_num
        avg_ratio = sum(ratios) / len(ratios)
        if i == 1:
            print_str += '\nsuccess rate: '
            print_str += "{:.1f}".format(avg_sr*100)
        elif i == 2:
            print_str += '\naction acc: '
            print_str += "{:.1f}".format(avg_act_acc*100)
        else:
            print_str += '\nredundacy ratio: '
            print_str += "{:.1f}".format(avg_ratio*100)
        print_str += '\% \n'

    return print_str

# def show_app_failures(app, output_dir):
#     app_correct_info = tools.load_json_file(os.path.join(output_dir, app, 'result.json'))
#     tasks_meta_data = tools.load_json_file('tasks.json')[app]
#     for task_name in os.listdir(os.path.join(output_dir, app)):
#         if 'task' in task_name and '.yaml' in task_name:
#             try: 
#                 code = tools.load_txt_file(os.path.join(output_dir, app, task_name, 'code.txt'))
#                 if task_name in app_correct_info['correct']:
#                     print('Correct:', app, task_name)
#                 elif task_name in app_correct_info['all_tasks']:
#                     print('Incorrect:', app, task_name, tasks_meta_data[task_name]['task'])
#                     # print(code)
#                 print(code)
#                 print('-'* 30)
#             except:
#                 print('warning, code not found', app, task_name)
def parse_args():
    parser = argparse.ArgumentParser(description="This script generates solutions.")
    parser.add_argument('-a', '--agent_name', default="autodroidv2")
    parser.add_argument('-m', '--model', default="autodroidv2")
    parser.add_argument('-e', '--evaluation', default=True, action='store_true')
    args = parser.parse_args()

    return args

if __name__ == '__main__':
    # args = parse_args()

    agent = "autodroidv2_llama"
    evaluation = True
    model = "autodroidv2"
    # agent = args.agent_name
    # evaluation = args.evaluation
    # model = args.model
    baseline_dir = BASELINE_PATH[agent]

    app_list = [
        "applauncher", 
        "calendar", 
        "camera", 
        "clock", 
        "contacts", 
        "dialer", 
        "filemanager", 
        "firefox", 
        "gallery", 
        "messenger", 
        "music", 
        "notes", 
        "voicerecorder"
    ]
    all_stats = []
    for app in app_list:
        app_acc, all_tasks, stats = test_app_tasks(agent, app, baseline_dir, model, run_tasks_online=not evaluation)
        all_stats.append(stats)
        # show_app_failures(app, baseline_dir)
    stats_txt = ""
    for stats in all_stats:
        if stats != None:
            for st in stats:
                action_missmatch = f"No action found: {st['action_missmatch']}" if st['action_missmatch'] != None else ""
                stats_txt += f"{st['app']}, {st['task_name']}, {st['task']}, {st['task_name']}, {st['result']}, {action_missmatch} \n"
    
    stats_path = f"evaluation/droidtask/evaluation_output/"
    if not os.path.exists(stats_path):
        os.mkdir(stats_path)

    results = summarize_final_results(baseline_dir, stats_path)
    stats_txt += f"\n {results}"

    tools.write_txt_file(f"{stats_path}/{agent}_evaluation_results.txt",stats_txt)