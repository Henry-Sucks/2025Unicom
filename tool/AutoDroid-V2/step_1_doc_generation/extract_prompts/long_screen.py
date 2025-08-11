from extract_prompts import common_parts
def query_long_screen(screen_name, screen_description, ui_state, user_action, next_screen_description):
    next_screen_desc_line = f'* Next State Screen: {next_screen_description}' if next_screen_description else ''
    next_screen_input_desc = '    - Description of the UI state after interaction.' if next_screen_description else ''
    return f"""Imagine you are a UI annotator who has to describe concisely interactive elements of a mobile application in the form of a UI document. 

### Input Information:
- **Current UI State:**
{common_parts.input_state}
- **User Interaction:**
{common_parts.user_interaction}
{next_screen_input_desc}

### Output Format:
- **Output:** A JSON list containing the extracted important elements. The JSON list should have the following fields:
```json
[
    {{
        "id": int, // The id of the extracted elemenet.
        "type": String, // The type of the element (e.g. button, scroller, p, input, element_list, etc.).
        "options": List of Strings, // List of options for the element list. If the element is not an element list or the options are dynamic, this field should be set to None.
        "name": String, // Concise API name that is unique. Include the Given UI screen API Name as prefix separated by ':' (e.g. ui_screen_name:element_name).
    }}, 
    ...
]
```
- Example: 
```json
[
    {{
        "id": 11,
        "type": "element_list",
        "options": None,
        "name": "video_page:video_card_list",
    }}, 
    {{
        "id": 13,
        "type": "button",
        "name": "video_page:video_list_card_item", 
    }}
]
```

### Instructions:
#### General Rules:
{common_parts.avoid_specific_content}


2. **Convenient for Code Calling:**
{common_parts.convenient_for_code_calling}

{common_parts.get_example_for_element_list(with_description=False)}


### Current UI State: 
- Screen Name: {screen_name}
- Screen Function: {screen_description} 
State Elements:
{ui_state}

### User Interaction From Current UI State: 
- Action: {user_action}
{next_screen_desc_line}

Note that: 
    - Output **only** a valid JSON list in the form of the above mentioned document. Enclose every property name and value in double quotes. It must be a valid JSON response!
    - You should pay special attention to the **element list** types. When there are too many static elements with the same structure, it is better to encapsulate them in a single element list type, such as too many hour/minute checkboxes in the time picker dialog, and list the options in the 'element_list_options' field. This will make the answer short. When there are dynamic elements, such as the list of videos in the video list, it is better to list the options as None, and encapsulate them in a single element list type.
    - **DON'T describe all the date/color/time/titles buttons in a date picker/color picker/time picker/title picker, etc. Just describe the main elements and the options of the element list.**
    - **IF there are too many elements in the UI state (more than 80), please try your best to use the 'element_list' type to encapsulate the some elements (such as settings options), and list the options in the 'element_list_options' field. **
Output:"""
