import re
from bs4 import BeautifulSoup, Tag, NavigableString
from lxml import etree
import argparse
import os
import copy

import tools as tools

def parse_args():
    parser = argparse.ArgumentParser(description='Build xpath for each state')
    parser.add_argument('--descriptions_file_name', type=str, required=True, help='path to the screen descriptions json file')
    # parser.add_argument('--screen_descriptions_path', type=str, required=True, help='path to the screen descriptions json file')
    # parser.add_argument('--tag_states_path', type=str, required=True, help='path to the tag states json file')
    parser.add_argument('--elements_path', type=str, required=True, help='path to the tag states json file')
    parser.add_argument('--output_organized_document_path', type=str, required=True, help='path to the output json file')
    return parser.parse_args()


class ScreenSkeletonBuilder:
    def __init__(self, screen_descriptions_path, tag_states_path):
        self.screen_descriptions = tools.load_json_file(screen_descriptions_path)
        self.tag_states = tools.load_json_file(tag_states_path)
        for tag, state_desc in self.tag_states.items():
            self.tag_states[tag] = self.remove_ids(state_desc)
        self.mismatched_screen_names = []
    
    def remove_ids(self, html: str):
        '''
        use bs4 to remove all id attribute from html description
        '''
        def _remove_ids_from_soup(soup):
            for tag in soup.find_all(True):
                if 'id' in tag.attrs:
                    del tag.attrs['id']
            return soup

        soup = BeautifulSoup(html, 'html.parser')
        cleaned_soup = _remove_ids_from_soup(soup)
        return cleaned_soup.prettify()

    def _count_ele_num(self, tag: Tag):
        '''
        count the number of elements in the tag
        '''
        count = 1
        for child in tag.children:
            if isinstance(child, Tag):
                count += self._count_ele_num(child)
        return count
    
    def extract_skeleton_of_one_screen(self, screen):
        '''
        get all states from one screen, extract the skeleton of the states
        '''
        if isinstance(screen, str):
            screen = self.screen_descriptions[screen]

        screen_states = []
        tags = screen['tags']
        for tag in tags:
            screen_states.append(self.tag_states[tag])
        
        if len(screen_states) == 1:
            cleaned_html = tools.clean_attributes(screen_states[0])
            simplified_skeleton = tools.clean_repeated_siblings(cleaned_html)
            return simplified_skeleton
        else:
            common_skeleton_str, common_skeleton = tools.extract_common_structure(screen_states[0], screen_states[1], clean_redundant_attributes=True, clean_siblings=True)
            max_common_ele_num = self._count_ele_num(common_skeleton)

            if screen['api_name'] == 'display_size_and_text_screen':
                print(common_skeleton_str)
            for i in range(2, len(screen_states)):
                
                common_skeleton_str, common_skeleton = tools.extract_common_structure(common_skeleton_str, screen_states[i], clean_redundant_attributes=True, clean_siblings=True)
                common_ele_num = self._count_ele_num(common_skeleton)
                if common_ele_num > max_common_ele_num:
                    max_common_ele_num = common_ele_num

                if screen['api_name'] == 'display_size_and_text_screen':
                    print(tags[i], common_skeleton_str)
                
                if common_ele_num < max_common_ele_num * 0.6:
                    if screen['api_name'] == 'display_size_and_text_screen':
                        print(f'common_ele_num: {common_ele_num}, max_common_ele_num: {max_common_ele_num}, tag: {tags[i]}')
                    self.mismatched_screen_names.append(screen['api_name'])
                    print(f'warning, the number of common elements in the screen {screen["api_name"]} is less than 60% of the maximum common elements')
                    break
                # print(i)
                # print(self.screen_descriptions['main_screen']['tags'][i])
                # print(common_skeleton_str)
            # ele_num = self._count_ele_num(common_skeleton)
            # if ele_num <= 3:
            #     self.mismatched_screen_names.append(screen['api_name'])
            #     print(f'warning, the number of common elements in the screen {screen["api_name"]} is less than 3')
            cleaned_html = tools.clean_attributes(common_skeleton_str)
            simplified_skeleton = tools.clean_repeated_siblings(cleaned_html)
            return simplified_skeleton

    def extract_skeleton_of_all_screens(self):
        '''
        extract the skeleton of all screens
        '''
        for screen_id, (screen_api_name, screen_data) in enumerate(self.screen_descriptions.items()):
            # print(screen_id, '/', len(self.screen_descriptions))
            screen_skeleton = self.extract_skeleton_of_one_screen(screen_data)
            self.screen_descriptions[screen_api_name]['skeleton'] = screen_skeleton
    

class XPathBuilder:
    def __init__(self, screen_descriptions_path, tag_states_path, screen_elements_path, use_desc=False, use_text=False):
        self.screen_skeleton_builder = ScreenSkeletonBuilder(screen_descriptions_path, tag_states_path)
        self.screen_skeleton_builder.extract_skeleton_of_all_screens()
        # these screen descriptions include 'skeleton' key, which stores the skeleton of the screen
        self.screen_descriptions = self.screen_skeleton_builder.screen_descriptions
        # self.screen_descriptions = tools.load_json_file(screen_descriptions_path)
        self.tag_states = tools.load_json_file(tag_states_path)
        # self.element_data = tools.load_json_file(element_data_path)
        self.screen_elements = tools.load_json_file(screen_elements_path)
        self.screen_descriptions_path = screen_descriptions_path
        self.use_desc=use_desc
        self.use_text=use_text

    def organize_all_elements(self):
        '''
        organize all elements in the structure of {screen_api_name: {elements: {element_api_name: element_data}}} in the document
        '''
        all_elements = {}
        # for raw_ele_name, element_data in self.element_data['elements'].items():
        for ele_data in self.element_data['elements']:
            raw_ele_name = ele_data['api_name']
            screen_api_name = raw_ele_name.split(':')[0]
            element_api_name = raw_ele_name.split(':')[1]
            if screen_api_name not in all_elements:
                all_elements[screen_api_name] = {'elements': {}}
            all_elements[screen_api_name]['elements'][element_api_name] = ele_data
        return all_elements
    
    def organize_all_elements_v2(self):
        '''
        organize all elements in the structure of {screen_api_name: {elements: {element_api_name: element_data}}} in the document
        '''
        all_elements = {}
        for screen_name, elements_data in self.screen_elements.items():
            if screen_name not in all_elements:
                all_elements[screen_name] = {'elements': {}}
            for element_data in elements_data:
                element_api_name = element_data['name']
                all_elements[screen_name]['elements'][element_api_name] = element_data
        return all_elements
    
    def _get_path_from_root(self, element):
        components = []
        while element is not None:
            # 获取父元素
            parent = element.getparent()
            # 如果父元素存在，获取同一父元素下的同类元素
            if parent is not None:
                siblings = parent.findall(element.tag)
                if len(siblings) > 1:
                    index = siblings.index(element) + 1
                    components.append(f'{element.tag}[{index}]')
                else:
                    components.append(element.tag)
            else:
                components.append(element.tag)
            element = parent
        components.reverse()
        return '//' + '/'.join(components)


    def build_xpath_for_one_element(self, element_data, remove_idx=False, get_ele_desc=True):
        state_desc = self.tag_states[element_data['state_tag']]
        
        # # use re to extract the id='<int>' from the element description
        # id_match = re.search(r'id="(\d+)"', ele_desc)
        # if not id_match:
        #     id_match = re.search(r"id='(\d+)'", ele_desc)
        try:
            id = int(element_data['id'])
        except:
            ele_desc = element_data['element']
            id_match = re.search(r'id="(\d+)"', ele_desc)
            if not id_match:
                id_match = re.search(r"id='(\d+)'", ele_desc)
            if id_match:
                id = int(id_match.group(1))
            else:
                id = None
        if id:
            # id = id_match.group(1)
            # if the id is found, build the xpath for it, first check whether the resource_id exists
            soup = BeautifulSoup(state_desc, 'html.parser')
            element = soup.find(id=str(id))
            if not element:
                print(self.screen_descriptions_path, element_data)
                return None, None
            if get_ele_desc and element:
                target_element = copy.deepcopy(element)
                for child in target_element.find_all(recursive=False):
                    child.extract()
                action_desc = target_element.prettify()
            else:
                action_desc = None

            resource_id = element.get('resource_id')
            if resource_id:
                return f"//*[@resource_id='{resource_id}']", action_desc
            if self.use_desc and element.get('alt'):
                return f"//*[@alt='{element.get('alt')}']", action_desc
            if self.use_text and element.get_text():
                return f"//*[text()='{element.get_text()}']", action_desc
            # if resource_id does not exist, xpath is the path from the root to the element
            # tree = etree.HTML(state_desc)
            # element_tree = etree.ElementTree(tree)
            # element = element_tree.xpath(f"//*[@id='{id}']")
            # if not element:
            #     print(f'element {element_data["name"]} with id {id} not found in the tag {element_data["state_tag"]}')
            #     return None, action_desc
            # element = element[0]
            # xpath = element_tree.getpath(element)
            root = etree.fromstring(state_desc)
            element = root.xpath(f"//*[@id='{id}']")
            if not element:
                print(f'element {element_data["name"]} with id {id} not found in the tag {element_data["state_tag"]}')
                return None, action_desc
            element = element[0]
            xpath = self._get_path_from_root(element)

            # if the xpath exists an indexing in the end, remove the indexing
            if remove_idx and xpath[-1] == ']':
                print(f'element {element_data["name"]} with xpath {xpath} in the tag {element_data["state_tag"]} has an indexing in the xpath, the state_desc is \n{state_desc} \n')
                xpath = xpath.rsplit('[', 1)[0]
                print(f'removed the indexing, the new xpath is {xpath}')
            return xpath, action_desc

        else:
            print(f'element {element_data["name"]} has no id')
            return None, None

    def build_xpath_for_one_elementv2(self, element_data, remove_idx=False, get_ele_desc=True):
        state_desc = self.tag_states[element_data['state_tag']]
        try:
            id = int(element_data['id'])
        except:
            ele_desc = element_data['element']
            id_match = re.search(r'id="(\d+)"', ele_desc)
            if not id_match:
                id_match = re.search(r"id='(\d+)'", ele_desc)
            if id_match:
                id = int(id_match.group(1))
            else:
                id = None
        if id:
            # if the id is found, build the xpath for it, first check whether the resource_id exists
            soup = BeautifulSoup(state_desc, 'html.parser')
            element = soup.find(id=str(id))
            if not element:
                print(self.screen_descriptions_path, element_data)
                return None, None
            if get_ele_desc and element:
                target_element = copy.deepcopy(element)
                for child in target_element.find_all(recursive=False):
                    child.extract()
                action_desc = target_element.prettify()
            else:
                action_desc = None
            
            root = etree.fromstring(state_desc)
            element_xpath = root.xpath(f"//*[@id='{id}']")
            if not element:
                print(f'element {element_data["name"]} with id {id} not found in the tag {element_data["state_tag"]}')
                return None, action_desc
            element_xpath = element_xpath[0]
            path_from_root = self._get_path_from_root(element_xpath)

            for child in element_xpath.getchildren():
                element_xpath.remove(child)

            # if the xpath exists an indexing in the end, remove the indexing
            if remove_idx and path_from_root[-1] == ']':
                print(f'element {element_data["name"]} with xpath {path_from_root} in the tag {element_data["state_tag"]} has an indexing in the xpath, the state_desc is \n{state_desc} \n')
                path_from_root = path_from_root.rsplit('[', 1)[0]

            resource_id = element.get('resource_id')
            alt = element.get('alt')
            text = element.get_text().strip()
            if resource_id and alt and text:
                xpath = [
                    f"//*[@resource_id=\"{resource_id}\" and text()=\"{text}\" and @alt=\"{alt}\"]",
                    f"//*[@resource_id=\"{resource_id}\" and alt=\"{text}\"]",
                    f"//*[@resource_id=\"{resource_id}\" and text()=\"{text}\"]",
                    f"//*[@resource_id=\"{resource_id}\"]", 
                ]
            elif resource_id and alt:
                xpath = [
                    f"//*[@resource_id=\"{resource_id}\" and @alt=\"{alt}\"]",
                    f"//*[@resource_id=\"{resource_id}\"]",
                ]
            elif resource_id and text:
                xpath = [
                    f"//*[@resource_id=\"{resource_id}\" and text()=\"{text}\"]",
                    f"//*[@resource_id=\"{resource_id}\"]",
                ]
            elif resource_id:
                xpath = [f"//*[@resource_id=\"{resource_id}\"]"]

            elif alt and text:
                xpath = [f"//*[@alt=\"{alt}\" and text()=\"{text}\"]", path_from_root]
            elif alt:
                xpath = [f"//*[@alt=\"{alt}\"]", path_from_root]
            elif text:
                xpath = [f"//*[text()=\"{text}\"]", path_from_root]
            else:
                xpath = [path_from_root]

            return xpath, action_desc

        else:
            print(f'element {element_data["name"]} has no id')
            return None, None
    
    def build_xpath_for_elements(self, get_ele_desc=True):
        organized_elements = self.organize_all_elements_v2()
        for screen_api_name, screen_data in organized_elements.items():
            organized_elements[screen_api_name]['skeleton'] = self.screen_descriptions[screen_api_name]['skeleton']
            for ele_api_name, element_data in screen_data['elements'].items():
                xpath, desc = self.build_xpath_for_one_elementv2(element_data)
                organized_elements[screen_api_name]['elements'][ele_api_name]['xpath'] = xpath
                if get_ele_desc:
                    organized_elements[screen_api_name]['elements'][ele_api_name]['element'] = desc
        return organized_elements

    def save_xpath_and_skeleton_to_file(self, file_path):
        '''
        save the xpath and skeleton of all screens to a file
        '''
        data = self.build_xpath_for_elements(get_ele_desc=True)
        tools.dump_json_file(file_path, data)

if __name__ == '__main__':
    # states_data_path = 'data/doc/broccoli0718/descriptions_0718.json'
    # tag_states_path = 'data/doc/broccoli0718/descriptions_0718_states.json'
    # elements_path = 'data/doc/broccoli0718/document_0718.json'
    args = parse_args()
    screen_descriptions_path = f"{args.descriptions_file_name}.json"
    tag_states_path = f"{args.descriptions_file_name}_states.json"
    xpath_builder = XPathBuilder(screen_descriptions_path, tag_states_path, args.elements_path)
    # xpath_builder.save_xpath_and_skeleton_to_file('data/doc/broccoli0718/organized_document.json')
    xpath_builder.save_xpath_and_skeleton_to_file(args.output_organized_document_path)

    # screen_skeleton_builder = ScreenSkeletonBuilder(states_data_path, tag_states_path)

    # screen_skeleton_builder.extract_skeleton_of_all_screens()
    
    # for screen_api_name, screen_data in screen_skeleton_builder.screen_descriptions.items():
    #     print(screen_api_name)
    #     print(screen_data['skeleton'])
    #     print('------------------------------------')