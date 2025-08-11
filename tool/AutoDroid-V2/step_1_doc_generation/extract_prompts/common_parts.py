input_state = '''  - Full XML Markup of the UI screen.
  - Screenshot of the device's screen representing the UI elements.'''

user_interaction = '''  - Full notation of the action in the of '<element_selector>.tap()', '<element_selector>.long_tap()', '<element_selector>.set_text(<text>)', '<element_selector>.scroll(<direction>)', '<element_selector>.get_text()', '<element_selector>.get_attributes()', 'back()', etc.
  (get_text is used to get the text of the element, get_attributes is used to get the attributes of the element as a dict, dict keys include "selected", "checked", "scrollable", dict values are boolean. )'''

user_interaction_format = f'''  {{
      "element": String, // The element that the user interacted with.
      "name": String, // The name of the element that the user interacted with, must appear in the "elements" field.
      "description": String, // A brief description of the user interaction.
      "effect": String, // You can summarize the effect of the element based on the user interaction and Description of the UI state after interaction. You need to point out the next screen name after the user interaction. You should be general and avoid specific content and details, such as "tap to navigate to the change_font_size_popup, which is a popup window that includes checkboxes including 90%, 100%, and 110% font size, and showing the current font size. ".  
  }}'''

new_ui_elements_format = f'''      {{
          "id": int, // The id of the extracted elemenet.
          "type": String, // The type of the element (e.g. button, scroller, p, input, element_list, etc.).
          "options": List of Strings, // List of options for the element_list. If the element is not an element_list or the options are dynamic, this field should be set to None. 
          "name": String, // Concise API name that is unique. Include the Given UI screen API Name as prefix separated by ':' (e.g. ui_screen_name:element_name). 
          "description": String, // Description of the purpose of the element. Please be as detailed as possible. 
      }}'''

avoid_specific_content = '''1. **Avoid Specific Content in element names, descriptions, and user_interaction:**
  - All descriptions must avoid specific content and details. Use general terms to describe elements and interactions.
  - Examples:
    - "a date button" instead of "a button labeled 'Sun, Oct 15'".
    -  "the comment is updated according to the user input" instead of "the comment is updated to 'this picture is great'".
    - "The form data includes values set for date and direction" instead of "The form data includes date ('20th Sunday')".
    - for user interaction, use general terms to describe the action, such as "set text to update the search input field" instead of "The search input field is updated with the text 'eve'"'''

convenient_for_code_calling = f'''  - The document you build will be used for generating script to complete a task. An example of the script is: 
    ```python
    # task: Delete the recipe 'Pie' from the Broccoli app
    current_recipes = $main_screen:recipe_card_list
    current_recipes.match('Pie').tap()
    $recipe_details_screen:more_options_button.tap()
    $recipe_details_more_options_popup:delete_button.tap()
    $delete_confirmation_dialog:delete_button.tap()
    ```

    So the described UI elements should be able to be used to generate code even without knowing the specific UI. You should consider: 
    - **Static and dynamic elements**: For static elements that remain constant in the app, you only need to summarize its name, such as 'calendar_more_options_button'; Dynamic elements contain content can change based on context, such as a note title that varies at differen times. **Thus, for dynamic elements, you must generalize the name without including specific details that may change (e.g. note_title_Dec_15_Dairy_Note -> instead write note_title only, Dec_15_Dairy_Note is too specific as the title can change anytime)**
    - **Element list**:  Represents a collection of elements that can be indexed or filtered, for example, a list of dates, times, contact names, note names. Most of times, we do not directly interact with the element list, but we interact with the elements inside it. The list itself is an abstract representation that allows for indexing or filtering to interact with individual items within it.
      - `<element_list>[<idx>]`: Supports indexing into lists of elements, facilitating iteration and specific element targeting. eg. $my_items[1]
      - `<element_list>.match(<text or attribute dict>)`: Enables filtering elements based on text or attributes, offering flexibility in selecting specific elements within a list. eg. $my_items.match("key words") or $my_items.match({{"selected": true}}), and can use len(<element_list>) to get the total number of items in an element list.
    - **Element list options**: 
      - some element list options are static and doesn't change anytime, such as a list of checkboxes representing to set the font size to 90%, 100%, 110%, in this case, you should list the options ['90%', '100%', '110%']. **DON'T** describe all these checkboxes as seperate elements, just list the options in the 'options' field of a element_list instead.
      - Other element list options are dynamic, such as dates, times, contact names, you should set the options to `None`, and you can describe the element list items as one abstract element/element_list, such as 'calendar_date_picker:dates_button' or 'contact_list:contact_info_list'. These abstract elements/element_lists are children elements of the element lists.
    - **If one element list contains another element or element list as its children, you must explicitly show that one element is a child of another element in the `description` field, such as: This is an individual recipe card within the recipe_card_list, which contains the recipe name, image, and description.**
'''

def get_example_for_element_list(with_description=True):
  description_9 = '''
              "description": "A list of recipe_card_views presented as a Recycler View. Each recipe_card_view is presented as a CardView within the Recycler View. The recipe card view includes the recipe photo, title, description, and source.", 
'''
  description_10 = '''
              "description": "A list of recipe details including recipe_photo, recipe_title, recipe_description, and recipe_source. The recipe card view is presented as a CardView within a Recycler View.",
'''
  description_11 = '''
              "description": "The photo of the recipe presented as a button within the recipe_card_view.", 
'''
  return f'''    - Examples of the element list:
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

        You should describe the UI element as:
        [
          {{
              "id": 9,
              "type": "element_list",
              "options": None,
              "name": "recipe_details_screen:recipes_list", {description_9 if with_description else ''}
          }},  
          {{
              "id": 10,
              "type": "element_list",
              "options": None,
              "name": "recipe_details_screen:recipe_card_view", {description_10 if with_description else ''}
          }}, 
          {{
              "id": 11,
              "type": "button",
              "options": None,
              "name": "recipe_details_screen:recipe_photo", {description_11 if with_description else ''}
          }}
          ...
        ]

        // Notice that there are many elements like <FrameLayout id='0'></FrameLayout> that is meaningless when generating code or invisible to agents, so you should not include it in the UI element list answer. Besides, in the above case, you need to describe the example of one element list by interacting with its children elements. '''


user_interaction_instruction = f'''  - You should describe only the element and element_list which the user interacted with. 
  - **If the interacted element belongs to an element_list, you must set the 'name' field to the element_list name, and the 'description' field to interacting with the indexed or matched element in the element_list.**
  For example: 
    // Example 1: 
      - Current UI State: 
        <FrameLayout id='0'>
          ...
          <button id='22' alt='More options'></button>
          ...
        </FrameLayout>

      - User Interaction From Current UI State: 
        Action: <button id='22' alt='More options'></button>.tap()
        Next State Screen: The screen is a popup window appears with options including Share, Share as file, Edit, and Delete. Each option is presented as a button within a list view.
      
      - Then, the interaction should be described as:
        {{
            "element": "<button id='22' alt='More options'></button>", 
            "name": "settings_screen:more_options_button",
            "description": "recipe_details_screen:more_options_button.tap()"
            "effect": "tap to navigate to the more_options_popup, which is a popup window that includes options including Sharing the recipe, Sharing the recipe as a file, Editing the recipe, and Deleting the recipe. "
        }}
  
  // Example 2: 
      - Current State: 
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

      - User Interaction From Current UI State: 
        Action: <p id='12' resource_id='card_text_view_title'>Pie</p>.tap()
        Next State Screen: The detailed view of a saved recipe displays the recipe photo, a navigation button, a title indicating the recipe name, a button to remove from favorites, and a button for more options. Below, it shows the recipe title, servings, preparation time, description, source, ingredients, and directions. At the bottom, there is a floating action button for starting the cooking assistant.

      - Then, the interaction should be described as:
        {{
            "element": "<p id='12' resource_id='card_text_view_title'>Pie</p>",
            "name": "main_screen:recipes_list", 
            "description": "main_screen:recipes_list.match('Pie').tap()",
            "effect": "tap to open the recipe_details_page, which displays the detailed view of a saved recipe, which includes the recipe photo, a navigation button, a title, a button to remove from favorites, a more options button, a recipe title, servings, preparation time, description, source, ingredients, and directions, and a button for starting the cooking assistant."
        }}'''