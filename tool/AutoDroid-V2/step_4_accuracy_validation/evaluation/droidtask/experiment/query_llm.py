from lxml import etree
def _get_all_element_names(doc):
    all_elements_desc = ''
    element_num = 0
    for screen, screen_data in doc.items():
        for element_name, element_data in screen_data['elements'].items():
            all_elements_desc += f"{element_name}, "
            element_num += 1
    return all_elements_desc, element_num

def make_solution_prompt_droidtask_tune(doc, task, app_name, first_screen_elements=None):
    all_elements_desc, num = _get_all_element_names(doc)
    first_screen_instruction = "" if not first_screen_elements else f"3. Current screen elements: The elements in the current screen, which you can start to interact with. "
    first_screen_statement = '' if not first_screen_elements else f"\nCurrent screen elements: \n{first_screen_elements}\n"
    # tasks_desc = '\t\n'.join([f'{i+1}. {task}' for i, task in enumerate(tasks)])
    return f'''Imagine that you are a robot operating a smartphone to use the {app_name} app. Like how humans operate the smartphone, you can tap, long tap, input text, scroll, and get attributes of the UI elements in the {app_name} app. You need to write scripts to manipulate the UI elements (buttons, text fields, scrollers, element_lists, etc) in the app. 

**Your ultimate task is: {task}**

In the script, you can use the following APIs:
- <element_selector>.tap()
- <element_selector>.tap(<child_element)
- <element_selector>.set_text(<text>)
- <element_selector>.scroll(<direction>)
- <element_selector>.get_text()
- <element_selector>.get_attributes()
- back()

The <element_selector> primitive is used to select an element, possible ways of selection include:
- $<element id>
- <element_list>[<idx>]

The <element_list> primitive is used to select a list of elements, possible ways of selection include:
- <element_selector>:
- <element_list>.match(<text or attribute dict>)

You can use the following important UI elements:
{all_elements_desc}

The current UI screen contains the following elements:
{first_screen_statement}

Your answer should follow this JSON format:

{{
    "plan": "<a high level plan to complete task 1>",
    "script": "<the python script to complete task 1>"
}}

**Note that you should only output the JSON content.**'''

def make_solution_prompt_droidtask_tune_without_eles(doc, task, app_name, first_screen_elements=None):
    all_elements_desc, num = _get_all_element_names(doc)
    first_screen_instruction = "" if not first_screen_elements else f"3. Current screen elements: The elements in the current screen, which you can start to interact with. "
    first_screen_statement = '' if not first_screen_elements else f"\nCurrent screen elements: \n{first_screen_elements}\n"
    # tasks_desc = '\t\n'.join([f'{i+1}. {task}' for i, task in enumerate(tasks)])
    return f'''Imagine that you are a robot operating a smartphone to use the {app_name} app. Like how humans operate the smartphone, you can tap, long tap, input text, scroll, and get attributes of the UI elements in the {app_name} app. You need to write scripts to manipulate the UI elements (buttons, text fields, scrollers, element_lists, etc) in the app. 

**Your ultimate task is: {task}**

In the script, you can use the following APIs:
- <element_selector>.tap()
- <element_selector>.tap(<child_element)
- <element_selector>.set_text(<text>)
- <element_selector>.scroll(<direction>)
- <element_selector>.get_text()
- <element_selector>.get_attributes()
- back()

The <element_selector> primitive is used to select an element, possible ways of selection include:
- $<element id>
- <element_list>[<idx>]

The <element_list> primitive is used to select a list of elements, possible ways of selection include:
- <element_selector>:
- <element_list>.match(<text or attribute dict>)

The current UI screen contains the following elements:
{first_screen_statement}

Your answer should follow this JSON format:

{{
    "plan": "<a high level plan to complete task 1>",
    "script": "<the python script to complete task 1>"
}}

**Note that you should only output the JSON content.**'''

def get_available_elements(doc, screen_html, screen_name, use_dash=True):
    # tree = etree.HTML(screen_html)
    # element_tree = etree.ElementTree(tree)
    parser = etree.HTMLParser()
    element_tree = etree.fromstring(screen_html, parser)

    available_elements = []
    for element_name, element_data in doc[screen_name]['elements'].items():
        ele_xpaths = element_data['xpath']
        if not ele_xpaths:
            continue
        for ele_xpath in ele_xpaths:
            try: 
                element = element_tree.xpath(ele_xpath)
            except:
                print(f'Error in xpath: {ele_xpath}')
                continue
            if len(element) > 0:
                new_element_name = element_name.replace(':', '__') if use_dash else element_name
                available_elements.append(new_element_name)
                break
    return available_elements