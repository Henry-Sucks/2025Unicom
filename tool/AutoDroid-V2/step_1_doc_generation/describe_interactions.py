import copy
import json
import os
import pickle
from bs4 import BeautifulSoup
from requests import Timeout
import requests
from utils import get_action_desc
from tools import load_yaml_file, dump_json_file,debug_query_gptv2, load_json_file, convert_gpt_answer_to_json
import base64
MAX_RETRY = 3

def prepare_data_legal_for_json(described_data):
   for state_title, state_data in described_data.items():
       for interaction in state_data["interactions"]:
            if isinstance(interaction['element'], str):
                continue
            interaction["element"] = interaction["element"].prettify() if interaction["element"] else None
   return described_data

def fix_input_parsing(soup):
    for input_tag in soup.find_all('input'):
        if input_tag.next_sibling:
            new_tag = soup.new_tag("input", type="text")
            new_tag.string = input_tag.next_sibling
            new_tag["id"] = input_tag["id"]
            if "resource_id" in input_tag.attrs:
                new_tag["resource_id"] = input_tag["resource_id"]
            if "alt" in input_tag.attrs:
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

def define_description_prompt_per_node(ui_descriptions, action_descriptions, step_history, data, max_history_steps=20, last_step_is_open_app=False):

    actions_data = "" if len(action_descriptions) > 0 else "None" 
    for api_name in action_descriptions:
        value = action_descriptions[api_name]
        effect = value["effect"]
        action_type = value["action_type"]
        
        actions_data += f"{action_type}({api_name})\n- {effect}\n\n"
        
    ui_data = "" if len(ui_descriptions) > 0 else "None" 
    for idx, api_name in enumerate(ui_descriptions):
        ui = ui_descriptions[api_name]
        ui_data += f"UI:{idx} ({api_name})\n- {ui['description']}\n\n"

    step_history_desc = "" if len(step_history) > 0 else "None"
    relative_step_id = 0
    for stepid, step in step_history.items():
        if stepid >= len(step_history) - max_history_steps:
            step_history_desc += f"Step {relative_step_id}: \nUI: {step['ui']} \nAction: {step['action']} \n\n"
            relative_step_id += 1
    if last_step_is_open_app:
        step_history_desc = "Open App\n"

    current_state = data["state"]
    interaction = data["interaction"]
    interactions_data = ""
    action = f"* Action: {interaction['action']}"
    input = f"* Input (Optional): {interaction['input']}"
    to_state_screenshot = f"* Next State Screenshot: {interaction['next_state']['image']}."
    elements_text = f"* State Elements: \n{interaction['next_state']['xml']}"
    interactions_data += f"{action}\n{input}\n{to_state_screenshot}\n{elements_text}"
    #TODO: Consider adjusting the instruction for generating an API name of the UI screen to be think of more generic API namse, similar to the elements
    prompt = f"""You are a UI annotator who has to describe concisely interactive elements of a mobile application in the form of a UI document.  
# History Information Provided:
* Previously Described UI Screens. Each description includes:
    - UI Screen API Name
    - UI Description
* Previously Described UI Interactions. Each description includes:
    - Action type with API name
    - Action effect
    
# Input Information provided:
- The current UI state of the application (current_ui_state), containing:
    * Full XML Markup notation of the UI screen.
    * Screenshot of the Device's Screen representing the UI state's elements.
- User interaction representing an action taken at the current UI state, including information as follows:
    * Full notation of the action represented in the form of 'action(element)'.
    * Any input text given by the user. Can be empty if the interaction did not involve human input.
    * Screenshot of the Device's Screen representing the UI screen after interaction.
    * Full XML Markup notation of the UI state's elements after interaction.

# Instructions:
## General Rule: Avoid Specific Content
    * All descriptions must avoid specific content and details. Use general terms to describe elements and interactions.
    * Examples:
        - Instead of "a button labeled 'Sun, Oct 15'", use "a date button".
        - Instead of "the comment is updated to 'this picture is great'", use "the comment is updated according to the user input".
        - Instead of "The form data includes date ('20th Sunday')", use "The form data includes values set for date and direction".
        - Instead of "the comment is updated to 'this picture is great'", use "the comment is updated according to the user input".

## Step 1: Describe the current UI state into a definition of a UI screen and decide whether the screens have been already explored or not.
    1. Describe the purpose of this UI state in natural language by looking at the attached image, the given XML markup notation, and the interaction history for that state. Be as detailed as possible when describing: include information about every element and its state.
    2. Avoid content-specific information by following the general rule.
    3. To avoid repetitiveness, compare the descriptions of previously explored UI screens in your analysis by looking at the history. UI states might be considered the same UI screen if they share the same core functionality and layout, even if they have:
        * Minor differences in the number of elements (e.g., additional elements appearing conditionally)
        * Variations in element content (e.g., text updates based on user input)
            - When encountering a UI state with these minor variations, analyze if it offers significantly different functionality or user experience than previously explored screens.
            - If the variations primarily involve element states (selection, content) and match a screen that is already documented (similar elements, layout, purpose), consider them variations of the same UI screen and use the ID plus the API name of the existing UI screen.
    
## Step 2: Assign the API name of each described UI screen from the previous step.
    1. The API name must be concise and informative regarding the screen's purpose. 
    2. The API name must be unique for each explored screen. Please revise previously explored UI screens in order to prevent duplications.
    
## Step 3: Describe the effect of the given interaction by comparing the current UI with the one after the interaction. This analysis reveals how the element changes the application's UI and the other elements on the screen.
    1. Mention the purpose of the interaction in the effect description  (e.g., related to the registration procedure, video playing page, file searching, etc.).
    2. Avoid content-specific information by following the general rule.
    3. Consider static and dynamic elements when describing other parts of the UI screen: 
        * Effect for Static Elements Example: "Touching a button labeled "More options" opens a popup window containing a list of buttons; Each item is a button for an option, including rename a note, share, create a shortcut, lock note, open file, export as a file, print, delete note, settings, about."
        * Effect for Dynamic Elements Examples: 
            - Bad Example: "A screen is shown that displays the route information including arrival time ('5 hours'), traffic jams ('No current traffic jams'), destination name ('Paris') , km left ('500km')" 
            - Good Example: "A screen is shown that displays the route information including arrival time, traffic jams, destination name, km left" 

## Step 4: Assign a detailed API name to the element that was interacted with, according to the description of the current screen and the effect that this element has.
    1. The API name is fundamental as it allows the element to be referenced later in automation procedures, hence, the focus must be on the element and the purpose of the interaction.
    2. The API name must tell what the element is and what is its purpose. Consider including general context from the effect and the UI screen the element appears at.
    3. Consider static and dynamic elements. Dynamic elements contain content that can change anytime, hence, do not include any specific UI context (e.g. note_title_my_notes -> instead write note_title only, my_notes is too specific as the title can change anytime)
    4. In a similar fashion as the UI screen descriptions, to avoid repetitiveness, consider revising already defined API names:
        * If the action has a different effect make sure that the given API name is unique! 
        * If the action has a similar effect and leads to the same UI screens, make sure to reuse the already given API name from the list! 
    5. Follow the snake_case naming convention, with every word in lowercase separated by "_".
    6. Include the API name of the UI screen in which the element resides as a prefix to the element API name. 

## Step 5: Describe the next UI state after interaction (interaction_screen) into a definition of a UI screen and decide whether this screen have been already explored or not.
    1. Describe the purpose of this UI state in natural language by looking at the attached image and the given XML markup notation for that state. Be as detailed as possible when describing: include information about every element and its state.
    2. Avoid content-specific information by following the general rule.
    3. To avoid repetitiveness, compare the descriptions of previously explored UI screens in your analysis by looking at the history. UI state might be considered the same UI screen if they share the same core functionality and layout, even if they have:
        * Minor differences in the number of elements (e.g., additional elements appearing conditionally)
        * Variations in element content (e.g., text updates based on user input)
            - When encountering a UI state with these minor variations, analyze if it offers significantly different functionality or user experience than previously explored screens.
            - If the variations primarily involve element states (selection, content) and match a screen that is already documented (similar elements, layout, purpose), consider them variations of the same UI screen and use the ID plus the API name of the existing UI screen. 

# Output Format: 
The information for the descriptions must be delivered in the following JSON format:
{{
    "current_screen":{{
        "description": String; // Very detailed description for the UI Screen. When an already explored UI is found, please write the explored description. If the current interaction has more details about the UI screen, replace the description with a better one combining previous and current one.
        "api_name": String; // Concise API name that is unique and can be used to reference the UI Screen.
    }},
    "interaction_effect":{{
        "action": String; // The full action plus element markup notation.
        "description":  String; // Detailed description of element's purpose in the current UI screen.  
        "effect": String; // Detailed description of the effect of the interaction. 
        "api_name": String; // Detailed API name that is unique and can be used to reference the element. Include the current screen API name as prefix separated by ':' (e.g. ui_screep_api:element_api).
    }},
    "interaction_screen":{{
        "description": String; // Very detailed description for the UI Screen.  When an already explored UI is found, please write the explored description. If the current interaction has more details about the UI screen, replace the description with a better one combining previous and current one.
        "api_name": String; // Concise API name that is unique and can be used to reference the UI Screen.
    }},
}}

# History: The following are previously explored UI screens and actions:
## Described UI Screens: 
{ui_data}

## Described UI Interactions:
{actions_data}

## User interaction history from the initial screen to the current screen:
{step_history_desc}

# Please analyze the following UI state and interaction with it:

## Current UI State:
* State Screenshot: {current_state['image']}. 
* State Elements:
{current_state['xml']}

## User Interaction From Current UI State: 
{interactions_data}

Output **only** a valid JSON response in the form of the above mentioned document. Enclose every property name and value in double quotes. It must be a valid JSON response!
Output:
```json
```
"""
    return prompt

def get_action_notation(action_details,prettified_state,choice,input):
    if isinstance(prettified_state, str):
        prettified_state = prettify_state(prettified_state)
    if choice != -1 and choice != None:
        action_element = copy.deepcopy(prettified_state.find(id=choice))
        for child in action_element.find_all(recursive=False):
            child.extract()
    else: 
        action_element = None
    try:
        return get_action_desc(action_details, action_element, input)
    except Exception as e:
        print(e)
        import pdb;pdb.set_trace()

    
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

def describe(annotation_log_path, annotation_states_path, output_file_name, model="gpt-4o", prompt_answer_path='temp/prompt_answers.json', include_image=True):
    existing_data,existing_states = get_existing_result(output_file_name)
    if existing_data is not None:
        return existing_data,existing_states
    
    data = load_yaml_file(annotation_log_path)["records"]
    described_data = {}
    prompt_history = {"prompts":[],"answers":[]}
    step_history = {}
    last_step_is_open_app = False

    ui_descriptions = {}
    action_descriptions = {}
    tag_state = {}
    iteration = 0

    intermediate_path = f"{output_file_name}_intermediate.pkl"
    prompt_answers = {}
    
    prompt_answers_dir = os.path.dirname(prompt_answer_path)
    if prompt_answers_dir:  # Ensure there's a directory component
        os.makedirs(prompt_answers_dir, exist_ok=True)

    # This is added in case the API fails
    if os.path.exists(intermediate_path):
        with open(intermediate_path, 'rb') as file:
            doc_intermediate = pickle.load(file)
            iteration = doc_intermediate["iteration"]
            described_data = doc_intermediate["doc"]
            ui_descriptions = doc_intermediate["uis"]
            action_descriptions = doc_intermediate["actions"]
            tag_state = doc_intermediate["tags"]
            prompt_history = doc_intermediate["prompt_history"]
            step_history = doc_intermediate["step_history"]
            last_step_is_open_app = doc_intermediate["last_step_is_open_app"]

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
            # step_history = []
            last_step_is_open_app = True
            iteration+=1
            continue

        choice = record["Choice"]
        input = record["Input"]
        action_details = record["ActionDetails"]

        # prettified_state = prettify_state(record["State"])
        prettified_state = record["State"]
        try: 
            full_action, action_type, action_element, element_type = get_action_notation(action_details,prettified_state,choice,input)
        except:
            print(f"Error in getting action notation for iteration {iteration} {output_file_name}")

        current_ui = {
            "xml": str(prettified_state),
            "image": "The First attached image"
        }
        
        if include_image:
            state_image = get_state_image(annotation_states_path,tag)
            next_state_image = get_state_image(annotation_states_path,next_tag)
        else: 
            state_image = None
            next_state_image = None

        # next_state_elements = prettify_state(next_state["State"])
        next_state_elements = next_state["State"]
        interaction = {
            "element_id": choice,
            "action": full_action,
            "input":input,
            "next_state": {
                "xml": str(next_state_elements),
                "image": "The Second attached image"
            }
        }
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
        
        if next_state_image is not None:
            prompt.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{next_state_image}",
                }
            })
            interaction["next_state"]["image"] = "The Second attached image" if state_image is not None else "The First attached image"
        else: 
            interaction["next_state"]["image"] = "No image available."

        prompt_text = define_description_prompt_per_node(
            ui_descriptions, 
            action_descriptions, 
            step_history, 
            {"state":current_ui,"interaction":interaction}, 
            last_step_is_open_app=last_step_is_open_app, 
        )
        last_step_is_open_app = False

        prompt.insert(0,{
                "type": "text",
                "text": prompt_text,
            })
        
        prompt_answers[iteration] = {
            "prompt": prompt_text,
            "tag": tag, 
            "answer": ""}
        dump_json_file(prompt_answer_path, prompt_answers)

        retry = 0
        result = None
        while not result and retry < MAX_RETRY:
            try:
                print(f"##################          Executing Prompt {iteration}:          ##################")
                # print(prompt_text)
                print(f"Current State Image: {tag if state_image is not None else 'Not found!'}")
                print(f"Next State Image: {next_tag if next_state_image is not None else 'Not found!'}")

                if not include_image:
                    prompt = prompt_text
                    
                res = debug_query_gptv2(prompt, model)   
                prompt_answers[iteration]["answer"] = res
                dump_json_file(prompt_answer_path, prompt_answers)
                res =  res.replace("```json", "").replace("```", "")
                
                print(f"##################          Prompt Result: Iteration {iteration}:          ##################")
                print(res)

                result = convert_gpt_answer_to_json(res, model, default_value={"default": "format wrong"})
            
            except json.JSONDecodeError as e:
                print(f"JSON decoding error: {e}")
                print("Retrying...")
                result = None
            except Timeout as e:
                print(f"API call timed out: {e}")
                print("Retrying...")
                result = None
            except requests.RequestException as e:
                print(f"API request error: {e}")
                print("Retrying...")
                result = None

        result["interaction_effect"]["current_screen"] = result["current_screen"]["api_name"]
        result["interaction_effect"]["next_screen"] = result["interaction_screen"]["api_name"]
        result["interaction_effect"]["element"] = action_element
        result["interaction_effect"]["element_type"] = element_type
        result["interaction_effect"]["input"] = input
        result["interaction_effect"]["action_type"] = action_type
        result["interaction_effect"]["state_tag"] = tag

        result["current_screen"]["tag"] = tag
        result["interaction_screen"]["tag"] = next_tag
        
        # Maintain the history for the prompt
        ui_descriptions[result['current_screen']["api_name"]] = result["current_screen"]
        action_descriptions[result["interaction_effect"]["api_name"]] = result["interaction_effect"]
        action_desc = get_action_desc(action_details, result['interaction_effect']['api_name'], input)
        step_history[iteration] = {'ui': result['current_screen']['api_name'], 'action': action_desc, 'next_ui': result['interaction_screen']['api_name']}
        
        prompt_history["prompts"].append(prompt_text)
        prompt_history["answers"].append(result)

        add_screen_to_final_data(described_data, result["current_screen"], result["interaction_effect"])

        tag_state[tag] = prettified_state  # .body.decode_contents()
        
        iteration += 1
        with open(intermediate_path, 'wb') as file:
                pickle.dump({
                    "doc":described_data,
                    "uis":ui_descriptions, 
                    "actions":action_descriptions,
                    "tags":tag_state, 
                    "prompt_history":prompt_history, 
                    "iteration":iteration, 
                    "step_history":step_history, 
                    "last_step_is_open_app":last_step_is_open_app
                }, file)
    
    tag_state[data[-1]['tag']] = data[-1]['State']  # get the last tag-state because it does not appear in the former loop
    described_data = prepare_data_legal_for_json(described_data)
    dump_json_file(f"{output_file_name}.json", described_data)
    dump_json_file(f"{output_file_name}_states.json", tag_state)
    dump_json_file(f"{output_file_name}_step_history.json", step_history)

    with open(f"{output_file_name}_q_a_task.json", "w") as f:
        for i, (q, a) in enumerate(zip(prompt_history["prompts"], prompt_history["answers"])):
            f.write(json.dumps({"group_id": i, "prompt": q, "answer": a}) + "\n")
            
    return described_data, tag_state