from extract_prompts import common_parts
def query_a_screen_first_time(screen_name, screen_description, ui_state, user_action, next_screen_description, next_screen_name):
    next_screen_desc_line = f'* Next State Screen Name: {next_screen_name}\n\tDescription: {next_screen_description}' if next_screen_description else ''
    next_screen_input_desc = '  - Description of the UI state after interaction.' if next_screen_description else ''
    prompt = f"""Imagine you are a UI annotator who has to describe interactive elements of a mobile application in the form of a UI document. 

### Input Information:
- **Current UI State:**
{common_parts.input_state}
- **User Interaction:**
{common_parts.user_interaction}
{next_screen_input_desc}
  
### Output Requirement:
- **Output:** A JSON object containing the extracted important elements and user interaction information. The JSON object should have the following fields:

```json
{{
  "elements": 
  [
{common_parts.new_ui_elements_format}, 
      ...
  ]
  "user_interaction": 
{common_parts.user_interaction_format}
}}
```
- Example: 
```json
{{
    "elements": 
    [
        {{
            "id": 11,
            "type": "element_list",
            "options": None,
            "name": "video_page:video_card_list",
            "description": "Container for the list of video_list_card_items.", 
        }}, 
        {{
            "id": 13,
            "type": "button",
            "name": "video_page:video_list_card_item", 
            "description": "An individual video in the video_page:video_card_list, displaying a photo used for navigating to details page.", 
        }}
    ], 
    "user_interaction": 
    {{
        "element": "<button id='13' alt='Video Card'>Pats</button>",
        "name": "video_page:video_card_list",
        "description": "video_page:video_card_list.match('Pats').tap()",
        "effect": "tap to navigate to the video_details_page, where the you can check the video's details: title, description, source, and play the video."
    }}
}}
```

### Instructions:
#### General Rules:
{common_parts.avoid_specific_content}

2. **Convenient for Code Calling:**
{common_parts.convenient_for_code_calling}

{common_parts.get_example_for_element_list(with_description=True)}

3. **Analyze the effect of the UI element on the UI state after the user interaction:**
{common_parts.user_interaction_instruction}
    
// End of the requirements and instructions. 


### Current UI State: 
- Screen Name: {screen_name}
- Screen Function: {screen_description}
- State Screenshot: The First attached image. 
- State Elements:
{ui_state}

### User Interaction From Current UI State: 
- Action: {user_action}
{next_screen_desc_line}

Note that: 
    - Output **only** a valid JSON list in the form of the above mentioned document. Enclose every property name and value in double quotes. It must be a valid JSON response!
    - You should pay special attention to the **element list** types. When there are too many static elements with the same structure, it is better to encapsulate them in a single element list type, such as too many hour/minute checkboxes in the time picker dialog, and list the options in the 'element_list_options' field. This will make the answer short. When there are dynamic elements, such as the list of videos in the video list, it is better to list the options as None, and encapsulate them in a single element list type.
    - **DON'T describe all the date/color/time/titles buttons in a date picker/color picker/time picker/title picker, etc. Just describe the main elements and the options of the element list.**
    - **IF there are too many elements in the UI state (more than 80), please try your best to use the 'element_list' type to encapsulate the some elements (such as settings options), and list the options in the 'element_list_options' field. **
Output:
```json
```
"""
    return prompt
