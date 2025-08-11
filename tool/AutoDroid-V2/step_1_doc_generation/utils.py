
from bs4 import BeautifulSoup
from lxml import etree

def find_path_to_element(root, target_element_markup):
    def recursive_search(element, path):
        if "id" in target_element_markup.attrs:
            if  "id" in element.attrs and element["id"] == target_element_markup["id"]:
                    return path + [element] 
        # Some elements might not have id due to the GPT extraction missing attributes, so we use resource_id instead
        elif  "resource_id" in target_element_markup.attrs:
            if"resource_id" in element.attrs and element["resource_id"] == target_element_markup["resource_id"]:
                return path + [element] 
        for child in element.find_all(recursive=False):
            result = recursive_search(child, path + [element])
            if result:
                return result
        return None
    
    return recursive_search(root, [])

def has_unique_identifier(element):
  return "resource_id" in element.attrs and element.attrs["resource_id"] is not None

def get_action_desc(action_details, action_element, input):
    action_type = action_details["action_type"]
    if isinstance(action_element, str):
        if action_type == "open_app":
            return f"open_app({action_details['app_name']})"
        elif action_type == "navigate_back":
            return f"navigate_back()"
        elif action_type == 'scroll':
            return f"{action_element}.scroll('{action_details['direction']}')"
        elif action_type == 'click':
            return f"{action_element}.tap()"
        elif action_type == 'long_press':
            return f"{action_element}.long_tap()"
        elif action_type == 'input_text':
            return f"{action_element}.set_text('{input}')"
        elif action_type == 'back':
            return "back()"
        elif action_type == 'enter':
            return "enter()"
    else: 
        action_name = action_element.name if action_element is not None else None
        if action_type == "open_app":
            return f"open_app({action_details['app_name']})", "open_app", "", ""
        elif action_type == "navigate_back":
            return f"navigate_back()", "navigate_back", "", ""
        elif action_type == 'scroll':
            return f"scroll({action_element}, '{action_details['direction']}')", "scroll", action_element, action_name
        elif action_type == 'click':
            try: 
                return f"tap({action_element})", "click", action_element, action_name
            except:
                print(action_element)
        elif action_type == 'long_press':
            return f"long_tap({action_element})", "long_press", action_element, action_name
        elif action_type == 'input_text':
            return f"set_text({action_element}, '{input}')", "input_text", action_element, action_name
        elif action_type == 'back':
            return f"back()", "back", None, None
        elif action_type == 'enter':
            return f"enter()", "enter", None, None

def get_element_xpath(element, extra_attributes=[]):
    attributes = []
    if has_unique_identifier(element):
        attributes.append(f"@resource_id='{element['resource_id']}'")
    if "alt" in element.attrs and element["alt"] is not None:
        attributes.append(f"@alt='{element['alt']}'")
    if "type" in element.attrs and element["type"] is not None:
        attributes.append(f"@type='{element['type']}'")
    if element.name == "checkbox":
        attributes.append(f"text()='{' ,'.join(element.contents)}'")
    attributes.extend(extra_attributes)
    if len(attributes) == 0:
        return f"{element.name}"
    return f"{element.name}[{' and '.join(attributes)}]" 

def generate_xpath(item, tag_state):
    if not isinstance(item, dict):
        return ""
    
    el = item["element"]
    if el == "":
        return ""
    
    xpath = ""
    el_markup = BeautifulSoup(el, "xml").find()
    
    if "id" not in el_markup.attrs and "resource_id" not in el_markup.attrs:
        print("Warning: target element has no id")
    
    screen_state = tag_state[item["state_tag"]]
    soup = BeautifulSoup(screen_state, 'lxml').find()

    path = find_path_to_element(soup, el_markup)
    if path is None:
        print(f"Element {el_markup} not found in state {item['state_tag']}")
        return ""
    target_element = path[-1]
    xpath_postfix = []
    # Check for preceding unique sibling
    previous_sibling = target_element.find_previous_sibling()
    if previous_sibling:
        sibling_xpath = get_element_xpath(previous_sibling)
        if sibling_xpath:
            xpath_postfix.append(f"preceding-sibling::{sibling_xpath}")
    # Check for following unique sibling (less common but possible)
    next_sibling = target_element.find_next_sibling()
    if next_sibling:
        sibling_xpath = get_element_xpath(next_sibling)
        if sibling_xpath:
            xpath_postfix.append(f"following-sibling::{sibling_xpath}")

    path_string = "//".join(tag.name for tag in path[:-1] if tag.name not in ["[document]","body","html","framelayout"])

    el_xpath = get_element_xpath(el_markup,xpath_postfix)
    
    xpath = f"//{path_string}//{el_xpath}"
    
    try:
        root = etree.fromstring(str(soup))
        elements = root.xpath(xpath)
        assert len(elements) > 0, f"Xpath {xpath} returned {len(elements)} elements"
    except: 
        print(f"XPath error: {xpath}")
        return ""
    # except etree.XPathEvalError as e:
    #     print(f"XPath error: {e}, {xpath}")
        
    return xpath
