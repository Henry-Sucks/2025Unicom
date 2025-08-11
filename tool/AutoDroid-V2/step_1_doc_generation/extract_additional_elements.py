import copy
import json
import os
import pickle
import re
from bs4 import BeautifulSoup
from requests import Timeout
import requests
from extract_prompts import long_screen
from extract_prompts import long_screen_descriptions
from extract_prompts import normal_length_after
from extract_prompts import normal_length_first
from utils import get_action_desc
from tools import load_yaml_file, dump_json_file,debug_query_gptv2, load_json_file, convert_gpt_answer_to_json, write_jsonl_file, safe_get_value
import base64
MAX_RETRY = 3

def fix_input_parsing(soup):
    for input_tag in soup.find_all('input'):
        if input_tag.next_sibling:
            new_tag = soup.new_tag("input", type="text")
            new_tag.string = input_tag.next_sibling
            new_tag["id"] = input_tag["id"]
            new_tag["resource_id"] = input_tag["resource_id"]
            new_tag["alt"] = input_tag["alt"] if "alt" in input_tag.attrs else "" 

            input_tag.replace_with(new_tag)
            new_tag.next_sibling.extract()
    return soup

def prettify_state(state):
    soup = BeautifulSoup(''.join(state), features="lxml")
    soup = fix_input_parsing(soup)
    return soup

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def get_action_notation(action_details,prettified_state,choice,input):
    # if isinstance(prettified_state, str):
    #     prettified_state = prettify_state(prettified_state)
    # action_element = copy.deepcopy(prettified_state.find(id=choice))
    # for child in action_element.find_all(recursive=False):
    #     child.extract()
    action_element = _extract_element_without_children(prettified_state, {"id": str(choice)})
    return get_action_desc(action_details, action_element, input)

    
    # elif input != "":
    #     return f"{action_type}({action_element}, '{input}')", action_type, action_element, action_element.name
    # else:    
    #     return f"{action_type}({action_element})",action_type, action_element, action_element.name

def get_state_image(states_path,state_tag):
    image_path = f"{states_path}/screen_{state_tag}.png"
    if os.path.exists(image_path):
        return encode_image(image_path)
    else:
        return None

def tag_exists(tags,tag_to_check):
    for tag in tags:
        if tag == tag_to_check:
            return True
    return False

def add_screen_to_final_data(data, screen, interaction=None):
    screen_api_name = screen["api_name"] 
    if screen_api_name in data:
        existing_data = data[screen_api_name]

        if not tag_exists(existing_data["tags"],screen["tag"]):
            existing_data["tags"].append(screen["tag"])

        existing_data["description"] = screen["description"]

        if interaction is not None:
            # for action in existing_data["interactions"]:
            #     if interaction['api_name'] == action["api_name"]:
            #         if action['next_screen_api_name'] != interaction['to_screen']:
            #             action['effect'] += interaction['effect']
            #             action['description'] += interaction['description']
            existing_data["interactions"].append(interaction)
    else:
        data[screen_api_name] = {
            "api_name": screen["api_name"],
            "description": screen["description"],
            "tags": [screen["tag"]],
            "interactions": [interaction] if interaction is not None else []
        }

def get_existing_result(output_file_name):
    if os.path.exists(f"{output_file_name}.json") and os.path.exists(f"{output_file_name}_states.json"):
        data = load_json_file(f"{output_file_name}.json")
        tag_states = load_json_file(f"{output_file_name}_states.json")
        return data,tag_states
    return None,None

def get_tag_screen(descriptions):
    '''
    descriptions: dict{screen_name: {tags: [tag1,tag2], description: <str>}}, we want to get a dict {tag: {screen_name, screen_description}}
    '''
    tag_screen = {}
    for screen_name, screen_data in descriptions.items():
        for tag in screen_data["tags"]:
            if tag not in tag_screen:
                tag_screen[tag] = {
                    "screen_name": screen_name,
                    "screen_description": screen_data["description"]
                }
    return tag_screen

def _find_max_id(string):
    pattern = r"id=['\"](\d+)['\"]"
    matches = re.findall(pattern, string)
    max_id = max(int(match) for match in matches)
    return max_id

def _extract_ele_from_id(id, html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    element_id = str(id)
    element = soup.find(id=element_id)
    return element

def _get_tag_by_id(html, id_value):
    soup = BeautifulSoup(html, 'lxml')
    element = soup.find(id=id_value)
    if element:
        return element.name
    return None

def _extract_element_without_children(html, attrs):
    '''
    input: html, {'id': 'id_value'}
    output: a string of the element with the id, but without children elements
    '''
    tag = _get_tag_by_id(html, attrs['id'])
    soup = BeautifulSoup(html, 'lxml')
    element = soup.find(tag, attrs)
    
    if element:
        # get a new BeautifulSoup object that contains only the element itself，without the children elements
        element_without_children = BeautifulSoup(str(element), 'lxml').find(tag)
        element_without_children.clear()
        return element_without_children.prettify()
    return None

def _query_prompt(iteration, tag, state_image, prompt, model, prompt_answers, prompt_answer_path, answer_key="first answer", include_image=True, prompt_text=None):
    try:
        print(f"##################          Executing Prompt {iteration}:          ##################")
        # print(prompt_text)
        print(f"Current State Image: {tag if state_image is not None else 'Not found!'}")
        if not include_image:
            prompt = prompt_text
        res = debug_query_gptv2(prompt, model)   
        prompt_answers[iteration][answer_key] = res
        dump_json_file(prompt_answer_path, prompt_answers)
        res =  res.replace("```json", "").replace("```", "")
        
        print(f"##################          Prompt Result: Iteration {iteration}:          ##################")
        print(res)
        # result = json.loads(res)
        result = convert_gpt_answer_to_json(res, model, default_value={"default": "format wrong"})
        return result
    
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
        print("Retrying...")
        return None
    except Timeout as e:
        print(f"API call timed out: {e}")
        print("Retrying...")
        return None
    except requests.RequestException as e:
        print(f"API request error: {e}")
        print("Retrying...")
        return None
    


def extract_additional_elements(annotation_log_path, annotation_states_path, descriptions_file_path, output_file_name, model="gpt-4o", prompt_answer_path='temp/prompt_answers.json', include_image=True):
    # get screen_name, screen_description for each tag
    descriptions_data = load_json_file(descriptions_file_path)
    tag_screen = get_tag_screen(descriptions_data)

    # get existing data and tag_states
    existing_data,existing_states = get_existing_result(output_file_name)
    if existing_data is not None:
        return existing_data,existing_states
    
    data = load_yaml_file(annotation_log_path)["records"]
    screen_name_elements = {}  # screen_name: [elements]
    tag_elements = {}  # tag: {'elements': [elements], 'user_interaction': {element, name, description, effect}}

    intermediate_path = f"{output_file_name}_intermediate.pkl"
    prompt_answers = {}

    iteration = 0

    # This is added in case the API fails
    if os.path.exists(intermediate_path):
        with open(intermediate_path, 'rb') as file:
            doc_intermediate = pickle.load(file)
            iteration = doc_intermediate["iteration"]
            screen_name_elements = doc_intermediate["screen_name_elements"]
            tag_elements = doc_intermediate["tag_elements"]

    while iteration < len(data) - 1:
        record = data[iteration]
        next_state = data[iteration+1]
        tag = record["tag"]
        next_tag = next_state["tag"]
        if tag == next_tag:
            iteration+=1
            continue
        
        if record["Action"] == 'open_app':
            # if the action is open_app, it means one sequence of interactions is starting, we do not include the open_app state, so we skip it
            iteration+=1
            continue
        choice = record["Choice"]
        input = record["Input"]
        action_details = record["ActionDetails"]
        from lxml import etree

        def simplify_xml(xml_text):
            # Parse the input XML
            action_elements = [ "input", "button", "scrollbar", "checkbox"]
            root = etree.fromstring(xml_text)

            def clean_element(element):
                # Recursively clean child elements first
                for child in list(element):
                    clean_element(child)

                # Remove empty elements and redundant layers
                if (not element.text or len(element) == 0) and (element.tag not in action_elements):
                    element.getparent().remove(element)
                elif len(element) == 1 and (element.tag not in action_elements):
                    child = element[0]
                    element.clear()
                    element.tag = child.tag
                    element.attrib.update(child.attrib)
                    element.text = child.text
                    element.extend(child)

            clean_element(root)

            # Convert back to string
            return etree.tostring(root, pretty_print=True).decode()
        
        prettified_state = simplify_xml(record["State"])

        full_action = get_action_notation(action_details,prettified_state,choice,input)

        current_ui = {
            "xml": str(prettified_state),
            "image": "The First attached image"
        }

        if include_image:
            state_image = get_state_image(annotation_states_path,tag)
        else:
            state_image = None

        prompt = []

        if state_image is not None:
            prompt.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{state_image}",
                }
            })
        else: 
            current_ui["image"] = "No image available."
        
        if tag not in tag_screen.keys():
            dump_jsonl_file('temp/logs/missing_tag_screen.jsonl', tag)
            iteration += 1
            continue
        current_screen_name = tag_screen[tag]["screen_name"]
        current_screen_description = tag_screen[tag]["screen_description"]
        if next_tag in tag_screen.keys():
            next_screen_description = tag_screen[next_tag]["screen_description"]
            next_screen_name = tag_screen[next_tag]['screen_name']
        else:
            next_screen_description = None
            next_screen_name = None

        max_id = _find_max_id(prettified_state)

        if max_id > 90 and tag_screen[tag]['screen_name'] not in screen_name_elements.keys(): # if the UI contains too many elements, we should divide the extraction prompt into two parts to shorten answer length, firstly ask all elements, second ask elements' descriptions

            prompt_text = long_screen.query_long_screen(
                current_screen_name,
                current_screen_description,
                prettified_state, 
                full_action, 
                next_screen_description,
            )
            # print(prompt_text)
            prompt_answers[iteration] = {"first prompt": prompt_text, "tag": tag, "first answer": ""}
            dump_json_file(prompt_answer_path, prompt_answers)

            prompt.insert(0,{
                    "type": "text",
                    "text": prompt_text,
            })
            ele_names = _query_prompt(iteration, tag, state_image, prompt, model, prompt_answers, prompt_answer_path, answer_key="first answer", prompt_text=prompt_text, include_image=include_image)
            
            retry_times = 0
            while ele_names is None and retry_times < MAX_RETRY:
                ele_names = _query_prompt(iteration, tag, state_image, prompt, model, prompt_answers, prompt_answer_path, answer_key="first answer", prompt_text=prompt_text, include_image=include_image)
                retry_times += 1

            second_prompt_text = long_screen_descriptions.query_long_screen_descriptions(
                current_screen_name,
                current_screen_description,
                prettified_state, 
                full_action, 
                next_screen_description,
                ele_names, 
                next_screen_name
            )
            prompt_answers[iteration]["second prompt"] = second_prompt_text
            dump_json_file(prompt_answer_path, prompt_answers)
            prompt = [
                {
                    "type": "text",
                    "text": second_prompt_text,
                }
            ]
            if state_image is not None:
                prompt.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{state_image}",
                    }
                })
            ele_descs = _query_prompt(iteration, tag, state_image, prompt, model, prompt_answers, prompt_answer_path, answer_key="second answer", include_image=include_image, prompt_text=second_prompt_text)

            retry_times = 0
            while ele_descs is None and retry_times < MAX_RETRY:
                ele_descs = _query_prompt(iteration, tag, state_image, prompt, model, prompt_answers, prompt_answer_path, answer_key="second answer", include_image=include_image, prompt_text=second_prompt_text)
                retry_times += 1
                
            elements_attributes = []
            for ele_i in range(len(ele_names)):
                ele_api_name = ele_names[ele_i]['name']
                ele_attr = {
                    # "element": _extract_ele_from_id(ele_names[ele_i]['id'], str(prettified_state)),
                    "element": _extract_element_without_children(str(prettified_state), {"id": ele_names[ele_i]['id']}),
                    "type": ele_names[ele_i]["type"],
                    "options": ele_names[ele_i]["options"],
                    "name": ele_api_name,
                }
                if ele_api_name in ele_descs['elements'].keys():
                    ele_attr['description'] = safe_get_value(ele_descs['elements'][ele_api_name], ['description', 'Description'], None)
                    # ele_attr['example'] = safe_get_value(ele_descs['elements'][ele_api_name], ['example', 'Example'], None)
                elements_attributes.append(ele_attr)
            result = {
                'elements': elements_attributes, 
                'user_interaction': ele_descs['user_interaction']
            }
            user_interaction = ele_descs['user_interaction']

        else:

            if tag_screen[tag]['screen_name'] not in screen_name_elements.keys():
                prompt_text = normal_length_first.query_a_screen_first_time(
                    current_screen_name,
                    current_screen_description,
                    prettified_state, 
                    full_action, 
                    next_screen_description, 
                    next_screen_name
                )
            else:
                prompt_text = normal_length_after.query_a_screen_second_and_more_times(
                    current_screen_name,
                    current_screen_description,
                    prettified_state, 
                    full_action, 
                    next_screen_description,
                    screen_name_elements[tag_screen[tag]['screen_name']], 
                    next_screen_name
                )

            prompt.insert(0,{
                    "type": "text",
                    "text": prompt_text,
                })
            
            prompt_answers[iteration] = {
                "prompt": prompt_text,
                "tag": tag, 
                "answer": ""}
            dump_json_file(prompt_answer_path, prompt_answers)
            
            result = _query_prompt(iteration, tag, state_image, prompt, model, prompt_answers, prompt_answer_path, answer_key="answer", include_image=include_image, prompt_text=prompt_text)
            retry_times = 0
            while result is None and retry_times < MAX_RETRY:
                result = _query_prompt(iteration, tag, state_image, prompt, model, prompt_answers, prompt_answer_path, answer_key="answer", include_image=include_image, prompt_text=prompt_text)
                retry_times += 1

            user_interaction = result['user_interaction']

        
        if current_screen_name not in screen_name_elements.keys():
            # add tag to all the element properties
            for ele_id, element_data in enumerate(result['elements']):
                result['elements'][ele_id]['state_tag'] = tag
            screen_name_elements[current_screen_name] = result['elements']
            tag_elements[tag] = {'elements': [element["name"] for element in result['elements']], 'user_interaction': user_interaction}
        else:
            tag_elements[tag] = {'elements': [], 'user_interaction': user_interaction}
            new_elements = result['New UI Elements']
            old_elements = result['Former UI Elements']
            for new_element in new_elements:
                tag_elements[tag]['elements'].append(new_element['name'])
                for element in screen_name_elements[current_screen_name]:
                    if element['name'] == new_element['name']:
                        print(f"Element {new_element['name']} already exists in the list.")
                        break
                else: # if the loop did not break, the element is not in the list
                    screen_name_elements[current_screen_name].append(new_element)
                    # add tag to the new elements, old elements already have the tag
                    screen_name_elements[current_screen_name][-1]['state_tag'] = tag

            for old_element_api_name in old_elements.keys():
                if old_element_api_name not in tag_elements[tag]['elements']:
                    tag_elements[tag]['elements'].append(old_element_api_name)

        interacted_element_name = user_interaction['name']

        for ele_idx, element_data in enumerate(screen_name_elements[current_screen_name]):
            if element_data['name'] == interacted_element_name:
                screen_name_elements[current_screen_name][ele_idx]['effect'] = user_interaction['effect']
                break
        else:
            print(f"Element {interacted_element_name} not found in the list.")


        iteration += 1
        if not os.path.exists(output_file_name.rsplit('/', 1)[0]):
            os.makedirs(output_file_name.rsplit('/', 1)[0], exist_ok=True)
        with open(intermediate_path, 'wb') as file:
                pickle.dump({
                    'screen_name_elements': screen_name_elements,
                    'tag_elements': tag_elements, 
                    'iteration': iteration
                }, file)
    # import pdb;pdb.set_trace()
    dump_json_file(f"{output_file_name}_screen_elements.json", screen_name_elements)
    dump_json_file(f"{output_file_name}_tag_elements.json", tag_elements)
