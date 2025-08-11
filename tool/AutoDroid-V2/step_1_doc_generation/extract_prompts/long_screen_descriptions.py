from extract_prompts import common_parts
def query_long_screen_descriptions(screen_name, screen_description, ui_state, user_action, next_screen_description, ele_types_names_dict, next_screen_name):
    next_screen_desc_line = f'* Next State Screen: {next_screen_name}\n\tDescription: {next_screen_description}' if next_screen_description else ''
    next_screen_input_desc = '  - Description of the UI state after interaction.' if next_screen_description else ''
    return f"""Imagine you are a UI annotator who has to describe concisely interactive elements of a mobile application in the form of a UI document. 

### Input Information:
- **Current UI State:**
{common_parts.input_state}
- **User Interaction:**
{common_parts.user_interaction}
{next_screen_input_desc}

### Output Requirement:
- **Output:** A JSON object containing the extracted important elements and user interaction information. The JSON object should have the following fields:

{{
  "elements": {{
    "<element name 1>": {{
      "description": "<description of element 1>", // Description of the purpose of the element. Please be detailed. 
    }}, 
    "<element name 2>": {{
      "description": "<description of element 1>", 
    }}
    ...
  }}
  "user_interaction": 
{common_parts.user_interaction_format}
}}
- Example: 
```json
{{
  "elements": {{
    "video_page:video_card_list": {{
      "description": "Container for the list of video_list_card_items.", 
    }}
    "video_page:video_list_card_item": {{
      "description": "An individual video in the video_page:video_card_list, displaying a photo used for navigating to details page.", 
    }}, 
  }}, 
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

    - Examples of the element list:
        // Example 1: 
        UI State: 
            <FrameLayout id='0'>
            ...
            <p id='9' resource_id='recycler_view' alt='Recipes'>
                <CardView id='10'>
                <p id='11' resource_id='card_image' alt='Recipe photo'></p>
                <p id='12' resource_id='card_text_view_title'>Pie</p>
                <p id='13' resource_id='card_text_view_description'>make an apple pie</p>
                <p id='14' resource_id='card_text_view_source'>Google</p>
                </CardView>
            </p>
            ...
            </FrameLayout>
        The elements you need to describe:
            [
                {{
                    "id": 9,
                    "type": "element_list",
                    "options": None,
                    "name": "recipe_details_screen:recipes_list", 

                }},  
                {{
                    "id": 10,
                    "type": "element_list",
                    "options": None,
                    "name": "recipe_details_screen:recipe_card_view",

                }}, 
                {{
                    "id": 11,
                    "type": "button",
                    "options": None,
                    "name": "recipe_details_screen:recipe_photo",
                }}
                ...
            ]
        Your answer of 'elements' should be: 
        ```json
        {{
            "recipe_details_screen:recipes_list": {{
                "description": "A list of recipe_card_views presented as a Recycler View. Each recipe_card_view is presented as a CardView within the Recycler View. The recipe card view includes the recipe photo, title, description, and source.", 
            }}, 
            "recipe_details_screen:recipe_card_view": {{
                "description": "A list of recipe details including recipe_photo, recipe_title, recipe_description, and recipe_source. It is a child of the recipe_details_screen:recipes_list element.",
            }}
            "recipe_details_screen:recipe_photo": {{
                "description": "The recipe photo is presented as a photo within a CardView within a Recycler View. It is a child of the recipe_details_screen:recipe_card_view element.", 
            }}
        }}
        ```

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

## The elements you need to describe:
{ele_types_names_dict}


You should note that: 
- Output **only** a valid JSON list in the form of the above mentioned document. Enclose every property name and value in double quotes. It must be a valid JSON response!
- Output **only** the descriptions of the "The elements you need to describe:" elements, DON'T describe other elements
Output:"""


