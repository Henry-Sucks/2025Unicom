import networkx as nx
from pyvis.network import Network
import re
import os
from collections import deque
import argparse

import tools as tools

def parse_args():
    parser = argparse.ArgumentParser(description='Build dependency graph')
    parser.add_argument('--raw_log_path', type=str, default='explore_data/output_merge_calendar/log.yaml', help='path to the raw log file')
    parser.add_argument('--structured_elements_path', type=str, default='data/doc/calendar_0718_add_history/organized_document.json', help='path to the structured elements file')
    parser.add_argument('--tag_elements_path', type=str, default='data/doc/calendar_0718_add_history/extractionsv3_tag_elements.json', help='path to the structured elements file')
    parser.add_argument('--steps_description_path', type=str, default='data/doc/calendar_0718_add_history/descriptions_0718_step_history.json', help='path to the steps description file')
    return parser.parse_args()


class DependencyGraph:
    def __init__(self, raw_log_path, structured_elements_path, tag_elements_path, steps_description_path) -> None:
        self.raw_log = tools.load_yaml_file(raw_log_path)
        self.raw_log_path = raw_log_path
        self.structured_elements_path = structured_elements_path
        self.structured_elements = tools.load_json_file(structured_elements_path)
        self.tag_elements = tools.load_json_file(tag_elements_path)
        self.steps_description = tools.load_json_file(steps_description_path)
        # assert len(self.steps_description) == len(self.raw_log['records']) - 1, "the number of steps description should be one less than the number of records"
        self.G = nx.DiGraph()
        self.build_dep_graph()
    
    def get_action_desc(self, action_details, action_element, input, screen_name=None):
        action_type = action_details["action_type"]
        if action_type == "open_app":
            return f"open_app({action_details['app_name']})"
        elif action_type == "navigate_back":
            return f"{screen_name}:back()"
        elif action_type == 'scroll':
            return f"{action_element}.scroll('{action_details['direction']}')"
        elif action_type == 'click':
            return f"{action_element}.tap()"
        elif action_type == 'long_press':
            return f"{action_element}.long_tap()"
        elif action_type == 'input_text':
            return f"{action_element}.set_text('{input}')"
        elif action_type == 'enter':
            return f"enter()"
        elif action_type == 'back':
            return f"back()"

    
    # def reorganize_elements(self):
    #     '''
    #     reorganize the structured elements in the structure of {tag: {elements: {element_api_name: element_data}, skeleton: <skeleton>}} in the document
    #     '''
    #     all_elements = {}
    #     for screen, screen_data in self.structured_elements.items():
    #         for element_name, element_data in screen_data['elements'].items():
    #             tag = element_data['state_tag']
    #             if tag not in all_elements:
    #                 all_elements[tag] = {'elements': {}, 'skeleton': screen_data['skeleton'], 'screen_name': screen}
    #             ele_full_name = f"{screen}:{element_name}"
    #             all_elements[tag]['elements'][ele_full_name] = element_data
    #     return all_elements

    def build_dep_graph(self):

        for record_id in range(len(self.raw_log['records']) - 1):
            # we exclude the open_app actions' UI elements
            if self.raw_log['records'][record_id]['Action'] == 'open_app' or self.raw_log['records'][record_id+1]['Action'] == 'open_app':
                continue
            this_tag = self.raw_log['records'][record_id]['tag']
            next_tag = self.raw_log['records'][record_id + 1]['tag']
            if next_tag not in self.tag_elements.keys():
                if record_id == len(self.raw_log['records']) - 2:
                    break
                try:
                    next_action_element = self.tag_elements[next_tag]['user_interaction']['name']
                except:
                    print(f"next_tag: {next_tag} not in tag_elements {self.structured_elements_path}")
                next_state_elements = [next_action_element]
            else:
                try:
                    next_state_elements = self.tag_elements[next_tag]['elements']
                except:
                    import pdb;pdb.set_trace()
            try: 
                next_state_elements.append(f"{self.steps_description[str(record_id+1)]['ui']}:back()")
            except:
                print(f"record_id+1: {record_id+1} not in steps_description for {self.raw_log_path}", '*'*500)
                continue

            if self.raw_log['records'][record_id]['Action'] == 'navigate_back':
                action_element = f"{self.steps_description[str(record_id)]['ui']}:back()"
            else:
                action_element = self.tag_elements[this_tag]['user_interaction']['name']
            action_desc = self.get_action_desc(self.raw_log['records'][record_id]['ActionDetails'], action_element, self.raw_log['records'][record_id]['Input'], screen_name=self.steps_description[str(record_id)]['ui'])
            for next_ele_name in next_state_elements:
                if action_element != None and next_ele_name != None:
                    self.G.add_edge(action_element, next_ele_name, label=action_desc)

    def show_graph(self, path, disable_edges=True):
        # mark the nodes without parent nodes as red
        no_parent_nodes = [node for node, degree in self.G.in_degree() if degree == 0]

        net = Network(notebook=True, directed=True)

        # add nodes and edges to the Network object
        for node in self.G.nodes:
            if node in no_parent_nodes:
                print(f"{node} has no parent")
                net.add_node(node, color='red', size=10)
            else:
                net.add_node(node, size=10)

        for edge in self.G.edges:
            net.add_edge(edge[0], edge[1])

        if disable_edges:
            for edge in net.edges:
                edge['title'] = ''
            
        # Enable the search feature
        # net.show_buttons(filter_=['search'])

        net.show(os.path.join(path, "dependency_graph.html"))

    def bfs_paths_within_steps(self, target_node, max_steps=10):
        '''
        get all the paths that could lead to the target_node within the max_steps
        '''
        queue = deque([(target_node, [])])
        visited = {target_node}
        paths = []

        while queue:
            current_node, edge_labels = queue.popleft()

            if len(edge_labels) >= max_steps:
                continue

            for predecessor in self.G.predecessors(current_node):
                if predecessor not in visited:
                    visited.add(predecessor)
                    new_edge = self.G[predecessor][current_node]['label']
                    new_path = [new_edge] + edge_labels
                    paths.append(new_path)
                    queue.append((predecessor, new_path))

        return paths
    
    def get_all_elements_paths(self):
        '''
        for all elements in structured_elements, get all the paths that could lead to the element within 10 steps, save structured_elements with the paths
        '''
        for ui_api_name, ui_data in self.structured_elements.items():
            for element_api_name, element_data in ui_data['elements'].items():
                if not self.G.has_node(element_api_name):
                    print(f"{element_api_name} not in the graph")
                    self.structured_elements[ui_api_name]['elements'][element_api_name]['paths'] = []
                    continue
                # full_ele_api_name = f'{ui_api_name}:{element_api_name}'
                paths = self.bfs_paths_within_steps(element_api_name, max_steps=10)
                self.structured_elements[ui_api_name]['elements'][element_api_name]['paths'] = paths
        tools.dump_json_file(self.structured_elements_path, self.structured_elements)
        

if __name__ == '__main__':
    args = parse_args()
    dep_graph = DependencyGraph(args.raw_log_path, args.structured_elements_path, args.tag_elements_path, args.steps_description_path)
    dep_graph.show_graph()
    dep_graph.get_all_elements_paths()