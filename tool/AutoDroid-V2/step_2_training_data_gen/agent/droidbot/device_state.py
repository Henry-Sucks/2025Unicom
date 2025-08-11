import copy
import math
import os
import json
import re
import tools as tools

from lxml import etree

from .utils import md5
from .input_event import TouchEvent, LongTouchEvent, ScrollEvent, SetTextEvent, KeyEvent

class DeviceState(object):
    """
    the state of the current device
    """

    def __init__(self, device, views, foreground_activity, activity_stack, background_services, tag=None, screenshot_path=None):
        self.device = device
        self.foreground_activity = foreground_activity
        self.activity_stack = activity_stack if isinstance(activity_stack, list) else []
        self.background_services = background_services
        if tag is None:
            from datetime import datetime
            tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.tag = tag
        self.screenshot_path = screenshot_path
        self.views = self.__parse_views(views)
        self.view_tree = {}
        self.__assemble_view_tree(self.view_tree, self.views)
        self.__generate_view_strs()
        self.state_str_ = self.__get_state_str()[:6]
        self.structure_str_ = self.__get_content_free_state_str()[:6]
        self.search_content = self.__get_search_content()
        
        self.text_representation = self.get_text_representation()
        self.possible_events = None
        if self.device is not None:
            self.width = device.get_width(refresh=True)
            self.height = device.get_height(refresh=False)
            self.is_popup = self.is_popup_window()
            self.parent_state = None

    @property
    def state_str(self):
        if self.is_popup and self.parent_state is not None:
            return f'{self.parent_state.state_str}/{self.state_str_}'
        else:
            return self.state_str_
        
    @property
    def structure_str(self):
        if self.is_popup and self.parent_state is not None:
            return f'{self.parent_state.structure_str}/{self.structure_str_}'
        else:
            return self.structure_str_

    @property
    def activity_short_name(self):
        return self.foreground_activity.split('.')[-1]
    
    @property
    def root_view_bounds(self):
        return self.views[0]['bounds']
    
    def is_popup_window(self):
        root_view = self.views[0]
        root_width = DeviceState.get_view_width(root_view)
        root_height = DeviceState.get_view_height(root_view)
        if root_width < self.width or root_height < self.height:
            return True
        return False

    def to_dict(self):
        state = {'tag': self.tag,
                 'state_str': self.state_str,
                 'state_str_content_free': self.structure_str,
                 'foreground_activity': self.foreground_activity,
                 'activity_stack': self.activity_stack,
                 'background_services': self.background_services,
                 'width': self.width,
                 'height': self.height,
                 'views': self.views}
        return state

    def to_json(self):
        import json
        return json.dumps(self.to_dict(), indent=2)

    def __parse_views(self, raw_views):
        views = []
        if not raw_views or len(raw_views) == 0:
            return views

        for view_dict in raw_views:
            # # Simplify resource_id
            # resource_id = view_dict['resource_id']
            # if resource_id is not None and ":" in resource_id:
            #     resource_id = resource_id[(resource_id.find(":") + 1):]
            #     view_dict['resource_id'] = resource_id
            views.append(view_dict)
        return views

    def __assemble_view_tree(self, root_view, views):
        if not len(self.view_tree): # bootstrap
            if not len(views): # to fix if views is empty
                return
            self.view_tree = copy.deepcopy(views[0])
            self.__assemble_view_tree(self.view_tree, views)
        else:
            children = list(enumerate(root_view["children"]))
            if not len(children):
                return
            for i, j in children:
                root_view["children"][i] = copy.deepcopy(self.views[j])
                self.__assemble_view_tree(root_view["children"][i], views)

    def __generate_view_strs(self):
        for view_dict in self.views:
            self.__get_view_str(view_dict)
            # self.__get_view_structure(view_dict)

    @staticmethod
    def __calculate_depth(views):
        root_view = None
        for view in views:
            if DeviceState.__safe_dict_get(view, 'parent') == -1:
                root_view = view
                break
        DeviceState.__assign_depth(views, root_view, 0)

    @staticmethod
    def __assign_depth(views, view_dict, depth):
        view_dict['depth'] = depth
        for view_id in DeviceState.__safe_dict_get(view_dict, 'children', []):
            DeviceState.__assign_depth(views, views[view_id], depth + 1)

    def __get_state_str(self):
        state_str_raw = self.__get_state_str_raw()
        return md5(state_str_raw)

    def __get_state_str_raw(self):
        if self.device is not None and self.device.humanoid is not None:
            import json
            from xmlrpc.client import ServerProxy
            proxy = ServerProxy("http://%s/" % self.device.humanoid)
            return proxy.render_view_tree(json.dumps({
                "view_tree": self.view_tree,
                "screen_res": [self.device.display_info["width"],
                               self.device.display_info["height"]]
            }))
        else:
            view_signatures = set()
            for view in self.views:
                view_signature = DeviceState.__get_view_signature(view)
                if view_signature:
                    view_signatures.add(view_signature)
            return "%s{%s}" % (self.foreground_activity, ",".join(sorted(view_signatures)))

    def __get_content_free_state_str(self):
        if self.device is not None and self.device.humanoid is not None:
            import json
            from xmlrpc.client import ServerProxy
            proxy = ServerProxy("http://%s/" % self.device.humanoid)
            state_str = proxy.render_content_free_view_tree(json.dumps({
                "view_tree": self.view_tree,
                "screen_res": [self.device.display_info["width"],
                               self.device.display_info["height"]]
            }))
        else:
            view_signatures = set()
            for view in self.views:
                view_signature = DeviceState.__get_content_free_view_signature(view)
                if view_signature:
                    view_signatures.add(view_signature)
            state_str = "%s{%s}" % (self.foreground_activity, ",".join(sorted(view_signatures)))
        import hashlib
        return hashlib.md5(state_str.encode('utf-8')).hexdigest()

    def __get_search_content(self):
        """
        get a text for searching the state
        :return: str
        """
        words = [",".join(self.__get_property_from_all_views("resource_id")),
                 ",".join(self.__get_property_from_all_views("text"))]
        return "\n".join(words)

    def __get_property_from_all_views(self, property_name):
        """
        get the values of a property from all views
        :return: a list of property values
        """
        property_values = set()
        for view in self.views:
            property_value = DeviceState.__safe_dict_get(view, property_name, None)
            if property_value:
                property_values.add(property_value)
        return property_values

    def save2dir(self, output_dir=None):
        try:
            if output_dir is None:
                if self.device.output_dir is None:
                    return
                else:
                    output_dir = os.path.join(self.device.output_dir, "states")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            dest_state_json_path = "%s/state_%s.json" % (output_dir, self.tag)
            if self.device.adapters[self.device.minicap]:
                dest_screenshot_path = "%s/screen_%s.jpg" % (output_dir, self.tag)
            else:
                dest_screenshot_path = "%s/screen_%s.png" % (output_dir, self.tag)
            state_json_file = open(dest_state_json_path, "w")
            state_json_file.write(self.to_json())
            state_json_file.close()
            import shutil
            shutil.copyfile(self.screenshot_path, dest_screenshot_path)
            self.screenshot_path = dest_screenshot_path
            # from PIL.Image import Image
            # if isinstance(self.screenshot_path, Image):
            #     self.screenshot_path.save(dest_screenshot_path)
        except Exception as e:
            self.device.logger.warning(e)

    def save_view_img(self, view_dict, output_dir=None):
        try:
            if output_dir is None:
                if self.device.output_dir is None:
                    return
                else:
                    output_dir = os.path.join(self.device.output_dir, "views")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            view_str = view_dict['view_str']
            if self.device.adapters[self.device.minicap]:
                view_file_path = "%s/view_%s.jpg" % (output_dir, view_str)
            else:
                view_file_path = "%s/view_%s.png" % (output_dir, view_str)
            if os.path.exists(view_file_path):
                return view_file_path
            from PIL import Image
            # Load the original image:
            view_bound = view_dict['bounds']
            original_img = Image.open(self.screenshot_path)
            # view bound should be in original image bound
            view_img = original_img.crop((min(original_img.width - 1, max(0, view_bound[0][0])),
                                          min(original_img.height - 1, max(0, view_bound[0][1])),
                                          min(original_img.width, max(0, view_bound[1][0])),
                                          min(original_img.height, max(0, view_bound[1][1]))))
            view_img.convert("RGB").save(view_file_path)
        except Exception as e:
            self.device.logger.warning(e)
        return view_file_path

    def is_different_from(self, another_state):
        """
        compare this state with another
        @param another_state: DeviceState
        @return: boolean, true if this state is different from other_state
        """
        return self.state_str != another_state.state_str

    @staticmethod
    def __get_view_signature(view_dict):
        """
        get the signature of the given view
        @param view_dict: dict, an element of list DeviceState.views
        @return:
        """
        if 'signature' in view_dict:
            return view_dict['signature']

        view_text = DeviceState.__safe_dict_get(view_dict, 'text', "None")
        if view_text is None or len(view_text) > 50:
            view_text = "None"

        signature = "[class]%s[resource_id]%s[visible]%s[text]%s[%s,%s,%s]" % \
                    (DeviceState.__safe_dict_get(view_dict, 'class', "None"),
                     DeviceState.__safe_dict_get(view_dict, 'resource_id', "None"),
                     DeviceState.__safe_dict_get(view_dict, 'visible', "False"),
                     view_text,
                     DeviceState.__key_if_true(view_dict, 'enabled'),
                     DeviceState.__key_if_true(view_dict, 'checked'),
                     DeviceState.__key_if_true(view_dict, 'selected'))
        view_dict['signature'] = signature
        return signature

    @staticmethod
    def __get_content_free_view_signature(view_dict):
        """
        get the content-free signature of the given view
        @param view_dict: dict, an element of list DeviceState.views
        @return:
        """
        if 'content_free_signature' in view_dict:
            return view_dict['content_free_signature']
        content_free_signature = "[class]%s[resource_id]%s[visible]%s" % \
                                 (DeviceState.__safe_dict_get(view_dict, 'class', "None"),
                                  DeviceState.__safe_dict_get(view_dict, 'resource_id', "None"),
                                  DeviceState.__safe_dict_get(view_dict, 'visible', "False"))
        view_dict['content_free_signature'] = content_free_signature
        return content_free_signature

    def __get_view_str(self, view_dict):
        """
        get a string which can represent the given view
        @param view_dict: dict, an element of list DeviceState.views
        @return:
        """
        if 'view_str' in view_dict:
            return view_dict['view_str']
        view_signature = DeviceState.__get_view_signature(view_dict)
        parent_strs = []
        for parent_id in self.get_all_ancestors(view_dict):
            parent_strs.append(DeviceState.__get_view_signature(self.views[parent_id]))
        parent_strs.reverse()
        child_strs = []
        for child_id in self.get_all_children(view_dict):
            child_strs.append(DeviceState.__get_view_signature(self.views[child_id]))
        child_strs.sort()
        view_str = "Activity:%s\nSelf:%s\nParents:%s\nChildren:%s" % \
                   (self.foreground_activity, view_signature, "//".join(parent_strs), "||".join(child_strs))
        import hashlib
        view_str = hashlib.md5(view_str.encode('utf-8')).hexdigest()
        view_dict['view_str'] = view_str
        bounds = view_dict['bounds']
        view_dict['bound_box'] = f'{bounds[0][0]},{bounds[0][1]},{bounds[1][0]},{bounds[1][1]}'
        return view_str

    def __get_view_structure(self, view_dict):
        """
        get the structure of the given view
        :param view_dict: dict, an element of list DeviceState.views
        :return: dict, representing the view structure
        """
        if 'view_structure' in view_dict:
            return view_dict['view_structure']
        width = DeviceState.get_view_width(view_dict)
        height = DeviceState.get_view_height(view_dict)
        class_name = DeviceState.__safe_dict_get(view_dict, 'class', "None")
        children = {}

        root_x = view_dict['bounds'][0][0]
        root_y = view_dict['bounds'][0][1]

        child_view_ids = self.__safe_dict_get(view_dict, 'children')
        if child_view_ids:
            for child_view_id in child_view_ids:
                child_view = self.views[child_view_id]
                child_x = child_view['bounds'][0][0]
                child_y = child_view['bounds'][0][1]
                relative_x, relative_y = child_x - root_x, child_y - root_y
                children["(%d,%d)" % (relative_x, relative_y)] = self.__get_view_structure(child_view)

        view_structure = {
            "%s(%d*%d)" % (class_name, width, height): children
        }
        view_dict['view_structure'] = view_structure
        return view_structure

    @staticmethod
    def __key_if_true(view_dict, key):
        return key if (key in view_dict and view_dict[key]) else ""

    @staticmethod
    def __safe_dict_get(view_dict, key, default=None):
        value = view_dict[key] if key in view_dict else None
        return value if value is not None else default

    @staticmethod
    def get_view_center(view_dict):
        """
        return the center point in a view
        @param view_dict: dict, an element of DeviceState.views
        @return: a pair of int
        """
        bounds = view_dict['bounds']
        return (bounds[0][0] + bounds[1][0]) / 2, (bounds[0][1] + bounds[1][1]) / 2

    @staticmethod
    def get_view_width(view_dict):
        """
        return the width of a view
        @param view_dict: dict, an element of DeviceState.views
        @return: int
        """
        bounds = view_dict['bounds']
        return int(math.fabs(bounds[0][0] - bounds[1][0]))

    @staticmethod
    def get_view_height(view_dict):
        """
        return the height of a view
        @param view_dict: dict, an element of DeviceState.views
        @return: int
        """
        bounds = view_dict['bounds']
        return int(math.fabs(bounds[0][1] - bounds[1][1]))

    def get_all_ancestors(self, view_dict):
        """
        Get temp view ids of the given view's ancestors
        :param view_dict: dict, an element of DeviceState.views
        :return: list of int, each int is an ancestor node id
        """
        result = []
        parent_id = self.__safe_dict_get(view_dict, 'parent', -1)
        if 0 <= parent_id < len(self.views):
            result.append(parent_id)
            result += self.get_all_ancestors(self.views[parent_id])
        return result

    def get_all_children(self, view_dict):
        """
        Get temp view ids of the given view's children
        :param view_dict: dict, an element of DeviceState.views
        :return: set of int, each int is a child node id
        """
        children = self.__safe_dict_get(view_dict, 'children')
        if not children:
            return set()
        children = set(children)
        for child in children:
            children_of_child = self.get_all_children(self.views[child])
            children.union(children_of_child)
        return children

    def get_app_activity_depth(self, app):
        """
        Get the depth of the app's activity in the activity stack
        :param app: App
        :return: the depth of app's activity, -1 for not found
        """
        depth = 0
        for activity_str in self.activity_stack:
            if app.package_name in activity_str:
                return depth
            depth += 1
        return -1

    def get_possible_input(self):
        """
        Get a list of possible input events for this state
        :return: list of InputEvent
        """
        if self.possible_events:
            return [] + self.possible_events
        possible_events = []
        enabled_view_ids = []
        touch_exclude_view_ids = set()
        for view_dict in self.views:
            # exclude navigation bar if exists
            if self.__safe_dict_get(view_dict, 'enabled') and \
                    self.__safe_dict_get(view_dict, 'visible') and \
                    self.__safe_dict_get(view_dict, 'resource_id') not in \
               ['android:id/navigationBarBackground',
                'android:id/statusBarBackground']:
                enabled_view_ids.append(view_dict['temp_id'])
        # enabled_view_ids.reverse()

        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'clickable'):
                possible_events.append(TouchEvent(view=self.views[view_id]))
                touch_exclude_view_ids.add(view_id)
                touch_exclude_view_ids.union(self.get_all_children(self.views[view_id]))

        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'scrollable'):
                possible_events.append(ScrollEvent(view=self.views[view_id], direction="up"))
                possible_events.append(ScrollEvent(view=self.views[view_id], direction="down"))
                possible_events.append(ScrollEvent(view=self.views[view_id], direction="left"))
                possible_events.append(ScrollEvent(view=self.views[view_id], direction="right"))

        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'checkable'):
                possible_events.append(TouchEvent(view=self.views[view_id]))
                touch_exclude_view_ids.add(view_id)
                touch_exclude_view_ids.union(self.get_all_children(self.views[view_id]))

        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'long_clickable'):
                possible_events.append(LongTouchEvent(view=self.views[view_id]))

        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'editable'):
                possible_events.append(SetTextEvent(view=self.views[view_id], text="Hello World"))
                touch_exclude_view_ids.add(view_id)
                # TODO figure out what event can be sent to editable views
                pass

        for view_id in enabled_view_ids:
            if view_id in touch_exclude_view_ids:
                continue
            children = self.__safe_dict_get(self.views[view_id], 'children')
            if children and len(children) > 0:
                continue
            possible_events.append(TouchEvent(view=self.views[view_id]))

        # For old Android navigation bars
        # possible_events.append(KeyEvent(name="MENU"))

        self.possible_events = possible_events
        return [] + possible_events

    def get_text_representation(self, merge_buttons=False):
        """
        Get a text representation of current state
        """
        enabled_view_ids = []
        for view_dict in self.views:
            # exclude navigation bar if exists
            if self.__safe_dict_get(view_dict, 'visible') and \
                self.__safe_dict_get(view_dict, 'resource_id') not in \
               ['android:id/navigationBarBackground',
                'android:id/statusBarBackground']:
                enabled_view_ids.append(view_dict['temp_id'])
        

        view_descs = []
        indexed_views = []
        # available_actions = []
        removed_view_ids = []
        element_tree = None
        element_attr = {}
        for view_id in enabled_view_ids:
            view = self.views[view_id]
            idx = view.get('temp_id', -1)
            child_ids = view.get('children', [])
            ele_attr = EleAttr(idx, child_ids, view, self.views,  enabled_view_ids=enabled_view_ids)
            element_attr[view_id] = ele_attr
            ele_attr.set_type('div')
            if view_id in removed_view_ids:
                continue
            # print(view_id)
            clickable = self._get_self_ancestors_property(view, 'clickable')
            self_clickable = self.__safe_dict_get(view, 'clickable')
            scrollable = self.__safe_dict_get(view, 'scrollable')
            class_type = self.__safe_dict_get(view, 'class')
            checkable = self._get_self_ancestors_property(view, 'checkable')
            long_clickable = self._get_self_ancestors_property(view, 'long_clickable')
            editable = self.__safe_dict_get(view, 'editable')
            actionable = clickable or scrollable or checkable or long_clickable or editable
            checked = self.__safe_dict_get(view, 'checked', default=False)
            selected = self.__safe_dict_get(view, 'selected', default=False)
            content_description = self.__safe_dict_get(view, 'content_description', default='')
            view_text = self.__safe_dict_get(view, 'text', default='')
            view_class = self.__safe_dict_get(view, 'class').split('.')[-1]
            view_bounds = self.__safe_dict_get(view, 'bound_box')
            if not content_description and not view_text and not scrollable and not self_clickable and class_type != "android.widget.Switch":  # actionable?
                continue
            ele_attr.set_click_longclick_checkable(clickable, long_clickable, checkable)
            # text = self._merge_text(view_text, content_description)
            # view_status = ''
            view_local_id = str(len(view_descs))
            if editable:
                ele_attr.set_type('input')
            elif checkable:
                ele_attr.set_type('checkbox')
            elif clickable:  # or long_clickable
                ele_attr.set_type('button')
                if merge_buttons:
                    # below is to merge buttons, led to bugs
                    clickable_ancestor_id = self._get_ancestor_id(view=view, key='clickable')
                    if not clickable_ancestor_id:
                        clickable_ancestor_id = self._get_ancestor_id(view=view, key='checkable')
                    clickable_children_ids = self._extract_all_children(id=clickable_ancestor_id)
                    if view_id not in clickable_children_ids:
                        clickable_children_ids.append(view_id)
                    view_text, content_description = self._merge_text(clickable_children_ids)
                    checked = self._get_children_checked(clickable_children_ids)
                    for clickable_child in clickable_children_ids:
                        if clickable_child in enabled_view_ids and clickable_child != view_id:
                            removed_view_ids.append(clickable_child)
            elif scrollable:
                ele_attr.set_type('scrollbar')
            else:
                ele_attr.set_type('p')
            

            short_view_text = view_text.replace('\n', ' \\ ')
            short_view_text = view_text[:50] if len(view_text) > 50 else view_text
            ele_attr.content = short_view_text
            if content_description:
                ele_attr.alt = content_description
            ele_attr.local_id = view_local_id

            allowed_actions = ['touch']
            status = []
            if editable:
                allowed_actions.append('set_text')
            if checkable:
                allowed_actions.extend(['select', 'unselect'])
                allowed_actions.remove('touch')
            if scrollable:
                allowed_actions.extend(['scroll up', 'scroll down', 'scroll left', 'scroll right'])
                allowed_actions.remove('touch')
            if long_clickable:
                allowed_actions.append('long_touch')
            if checked or selected:
                status.append('selected')
            view['allowed_actions'] = allowed_actions
            ele_attr.action.extend(allowed_actions)
            view['status'] = status
            view['local_id'] = view_local_id
            ele_attr.status = status
            view_descs.append(ele_attr.view_desc)
            view['full_desc'] = ele_attr.full_desc
            view['desc'] = ele_attr.desc
            indexed_views.append(view) # deprecated
            ele_attr.view = view
            element_attr[view_id] = ele_attr
            
        state_desc = '\n'.join(view_descs)
        element_tree = ElementTree(ele_attrs=element_attr,views=self.views, valid_ele_ids=[view['temp_id'] for view in indexed_views])
        return state_desc, indexed_views, element_tree

    def _get_self_ancestors_property(self, view, key, default=None):
        all_views = [view] + [self.views[i] for i in self.get_all_ancestors(view)]
        for v in all_views:
            value = self.__safe_dict_get(v, key)
            if value:
                return value
        return default

    def _merge_text(self, children_ids):
        texts, content_descriptions = [], []
        for childid in children_ids:
            if not self.__safe_dict_get(self.views[childid], 'visible') or \
                self.__safe_dict_get(self.views[childid], 'resource_id') in \
               ['android:id/navigationBarBackground',
                'android:id/statusBarBackground']:
                # if the successor is not visible, then ignore it!
                continue          

            text = self.__safe_dict_get(self.views[childid], 'text', default='')
            if len(text) > 50:
                text = text[:50]

            if text != '':
                # text = text + '  {'+ str(childid)+ '}'
                texts.append(text)

            content_description = self.__safe_dict_get(self.views[childid], 'content_description', default='')
            if len(content_description) > 50:
                content_description = content_description[:50]

            if content_description != '':
                content_descriptions.append(content_description)

        merged_text = '<br>'.join(texts) if len(texts) > 0 else ''
        merged_desc = '<br>'.join(content_descriptions) if len(content_descriptions) > 0 else ''
        return merged_text, merged_desc
    
    def get_scrollable_elements(self):
        scrollable_views, scrollable_view_properties = [], []
        enabled_view_ids = []
        for view_dict in self.views:
            # exclude navigation bar if exists
            if self.__safe_dict_get(view_dict, 'visible') and \
                self.__safe_dict_get(view_dict, 'resource_id') not in \
               ['android:id/navigationBarBackground',
                'android:id/statusBarBackground']:
                enabled_view_ids.append(view_dict['temp_id'])
        for view_id in enabled_view_ids:
            view = self.views[view_id]
            clickable = self._get_self_ancestors_property(view, 'clickable')
            scrollable = self.__safe_dict_get(view, 'scrollable')
            checkable = self._get_self_ancestors_property(view, 'checkable')
            long_clickable = self._get_self_ancestors_property(view, 'long_clickable')
            editable = self.__safe_dict_get(view, 'editable')
            
            bound_box = self.__safe_dict_get(view, 'bound_box')
            view_class = self.__safe_dict_get(view, 'class')
            resource_id = self.__safe_dict_get(view, 'resource_id')
            content_description = self.__safe_dict_get(view, 'content_description')

            scrollable_view_properties.append({
                'resource_id': resource_id,
                'class_name': view_class,
                'content_description': content_description,
                'bound_box': bound_box,
            })
            
            if scrollable and not clickable and not checkable and not long_clickable and not editable:
                scrollable_views.append(view)
        return scrollable_views, scrollable_view_properties

class EleAttr(object):

    def __init__(self, idx: int, child_ids: list[int], view, views, enabled_view_ids=[]):
        '''
        @use_class_name: if True, use class name as the type of the element, otherwise use the <div>
        '''
        self.id = idx
        self.children = child_ids

        self.resource_id = view.get('resource_id', '')
        self.class_name = view.get('class', '')
        self.text = view.get('text', '')
        self.content_description = view.get('content_description', '')
        self.bound_box = view.get('bound_box', '')
        
        self.action = []
        # element representation
        self.local_id = None
        self.type = None
        self.alt = view.get('content_description', '')
        self.status = None
        self.content = None
        
        # for checking the status of the element
        self.selected = view.get('selected', False)
        self.checked = view.get('checked', False)

        self.scrollable = view.get('scrollable', False)
        self.editable = view.get('editable', False)
        self.clickable, self.long_clickable, self.checkable = False, False, False

        self.type_ = self.class_name.split('.')[-1] if self.class_name else 'div'  # only existing init
        
        self.view = view
        
        self.is_visible = view.get('visible', False)
        # used for removing the invalid children
        self.enabled_view_ids = enabled_view_ids
        for child in self.children:
            valid = self.check_if_el_is_valid(views, child)
            if not valid:
                self.children.remove(child)

    def check_if_el_is_valid(self, views, id):
        valid = id in self.enabled_view_ids
        if valid:
            return True
        
        for child in views[id].get('children', []):
            child_valid = child in self.enabled_view_ids
            if child_valid:
                return True
            
        return False
    
    def set_click_longclick_checkable(self, clickable, long_clickable, checkable):
        self.clickable = clickable
        self.long_clickable = long_clickable
        self.checkable = checkable

    def dict(self, only_original_attributes=False):
        checked = self.checked or self.selected
        if only_original_attributes:
            return {
                'resource_id': self.resource_id,
                'class_name': self.class_name,
                'text': self.text,
                'content_description': self.content_description,
                'checked': checked,
                'scrollable': self.scrollable,
                'editable': self.editable,
                'clickable': self.clickable,
                'long_clickable': self.long_clickable,
            }
        return {
            'id': self.id,
            'resource_id': self.resource_id,
            'class_name': self.class_name,
            'text': self.text,
            'content_description': self.content_description,
            'bound_box': self.bound_box,
            'children': self.children,
            'full_desc': self.full_desc,
        }

    def get_attributes(self):
        checked = self.checked or self.selected
        return {
            'id': self.id,
            'resource_id': self.resource_id,
            'class_name': self.class_name,
            'text': self.text,
            'content_description': self.content_description,
            'bound_box': self.bound_box,
            'checked': checked,
            'selected': checked,
            'scrollable': self.scrollable,
            'editable': self.editable,
            'clickable': self.clickable,
            'long_clickable': self.long_clickable,
            'checkable': self.checkable
        }

    def set_type(self, typ: str):
        self.type = typ
        if typ in ['button', 'checkbox', 'input', 'scrollbar', 'p']:
            self.type_ = self.type

    def _match_content(self, value: str):
        if self.alt != None and value.lower() == self.alt.strip().lower():
            return True
        if self.content != None and value.lower() == self.content.strip().lower():
            return True
        if self.text != None and value.lower() == self.text.strip().lower():
            return True
        return False
    
    def is_match_dict(self, value: dict):
        for k in value.keys():
            if k in ['text', 'alt', 'content']:
                if self._match_content(value[k]):
                    return True
                
        ele_dict = self.dict()
        return all(ele_dict[key] == value for key, value in value.items())

    def is_match(self, value: str):  # todo::
        if not value:
            return False
        value_lower = value.strip().lower()
        if self._match_content(value):
            return True
        if self.resource_id != None and value_lower == self.resource_id.strip().lower():
            return True
        if self.class_name != None and value_lower == self.class_name.strip().lower():
            return True
        return False

    # compatible with the old version
    @property
    def view_desc(self) -> str:
        return '<' + self.type + \
            (f' id={self.local_id}' if self.local_id else '') + \
            (f' alt=\'{self.alt}\'' if self.alt else '') + \
            (f' status={",".join(self.status)}' if self.status and len(self.status)>0 else '') + \
            (f' bound_box={self.bound_box}' if self.bound_box else '') + '>' + \
            (self.content if self.content else '') + \
            self.desc_end

    # compatible with the old version
    @property
    def full_desc(self) -> str:
        return '<' + self.type + \
            (f' alt=\'{self.alt}\'' if self.alt else '') + \
            (f' status={",".join(self.status)}' if self.status and len(self.status)>0 else '') + \
            (f' bound_box={self.bound_box}' if self.bound_box else '') + '>' + \
            (self.content if self.content else '') + \
            self.desc_end

    # compatible with the old version
    @property
    def desc(self) -> str:
        return '<' + self.type + \
            (f' alt=\'{self.alt}\'' if self.alt else '') + \
            (f' bound_box={self.bound_box}' if self.bound_box else '') + '>' + \
            (self.content if self.content else '') + \
            self.desc_end

    # compatible with the old version
    @property
    def desc_end(self) -> str:
        return f'</{self.type}>'

    # generate the html description
    @property
    def desc_html_start(self) -> str:
        # add double quote to resource_id and other properties
        if self.resource_id:
            resource_id = self.resource_id.split('/')[-1]
        else:
            resource_id = ''
        resource_id = tools.escape_xml_chars(resource_id)
        typ = tools.escape_xml_chars(self.type_)
        alt = tools.escape_xml_chars(self.alt)
        status = None if not self.status else [tools.escape_xml_chars(s) for s in self.status]
        content = tools.escape_xml_chars(self.content)
        return '<' + typ + f' id=\'{self.id}\'' + \
            (f" resource_id='{resource_id}'" if resource_id else '') + \
            (f' alt=\'{alt}\'' if alt else '') + \
            (f' status=\'{",".join(status)}\'' if status and len(status)>0 else '') + '>' + \
            (content if content else '')

    # generate the html description
    @property
    def desc_html_end(self) -> str:
        return f'</{tools.escape_xml_chars(self.type_)}>'
    
    @property
    def desc_visible_html_start(self) -> str:
        # add double quote to resource_id and other properties
        typ = tools.escape_xml_chars(self.type_)
        alt = tools.escape_xml_chars(self.alt)
        status = None if not self.status else [tools.escape_xml_chars(s) for s in self.status]
        content = tools.escape_xml_chars(self.content)
        return '<' + typ + \
            (f' id=\'{self.id}\'' if self.id else '') + \
            (f' alt=\'{alt}\'' if alt else '') + \
            (f' status=\'{",".join(status)}\'' if status and len(status)>0 else '') + '>' + \
            (content if content else '')

    def set_type(self, typ: str):
        self.type = typ
        if typ in ['button', 'checkbox', 'input', 'scrollbar', 'p']:
            self.type_ = self.type

class ElementTree(object):

    def __init__(self,
                 ele_attrs: dict[int, EleAttr],
                 views,
                 valid_ele_ids: list[int],
                 root_id: int = 0):
        # member
        self.views = views
        self.scrollable_ele_ids: list[int] = []
        # tree
        self.root, self.ele_map, self.valid_ele_ids = self._build_tree(
            ele_attrs, views, valid_ele_ids, root_id)
        self.size = len(self.ele_map)
        # result
        self.str = self.get_str()
        self.skeleton = HTMLSkeleton(self.str)

    def get_ele_by_id(self, index: int):
        return self.ele_map.get(index, None)

    def __len__(self):
        return self.size

    class node(object):

        def __init__(self, nid: int, pid: int):
            self.children: list = []
            self.id = nid
            self.parent = pid
            self.leaves = set()

        def get_leaves(self):
            for child in self.children:
                if not child.children:
                    self.leaves.add(child.id)
                else:
                    self.leaves.update(child.get_leaves())

            return self.leaves
        
        def drop_invalid_nodes(self, valid_node_ids: set):
            # If the node is a leaf, check the condition
            if not self.children:
                if self.id in valid_node_ids:
                    return True
                else:
                    return False
            
            # Recursively check and delete children
            new_children = []
            for child in self.children:
                if child.drop_invalid_nodes(valid_node_ids):
                    new_children.append(child)
            
            self.children = new_children
            
            # If after deleting children, the node becomes a leaf, check the condition
            # if not self.children and self.id in valid_node_ids:
            #     return True
            
            return True
        # def drop_invalid_nodes(self, valid_node_ids: set):
        #     in_set = self.leaves & valid_node_ids
        #     if in_set:
        #         self.leaves = in_set
        #         for child in self.children:
        #             child.drop_invalid_nodes(valid_node_ids)
        #     else:
        #         # drop
        #         self.children.clear()
        #         self.leaves.clear()

    
    def _build_tree(self, ele_map: dict[int, EleAttr],views, valid_ele_ids: list[int],
                    root_id: int) -> tuple[node, dict[int, EleAttr], set[int]]:
        _scrollable_ele_ids = set()
        _valid_ele_ids = set(valid_ele_ids)
        
        root = self.node(root_id, -1)
        queue = [root]

        def check_if_el_is_valid(id):
            attr = ele_map.get(id, None)
            if attr:
                return attr, id
            
            for child in views[id].get("children",[]):
                child_attr, valid_id = check_if_el_is_valid(child)
                if child_attr:
                    return child_attr, valid_id
                
            return None, None
        
        while queue:
            node = queue.pop(0)
            for child_id in ele_map[node.id].children:
                # some views are not in the enable views
                if node.id == 44:
                    print("OPA")
                attr, valid_id = check_if_el_is_valid(child_id)
                if valid_id == 46:
                    print("OPA")
                if not attr and not valid_id:
                    continue
                idx = ele_map[valid_id].id
                if attr.scrollable:
                    _scrollable_ele_ids.add(idx)
                child = self.node(idx, node.id)
                node.children.append(child)
                queue.append(child)

        self.scrollable_ele_ids = list(_scrollable_ele_ids & _valid_ele_ids)
        # get the leaves
        root.get_leaves()
        root.drop_invalid_nodes(_valid_ele_ids)

        return root, ele_map, _valid_ele_ids

    def get_str(self, is_color=False) -> str:
        '''
    use to print the tree in terminal with color
    '''

        # output like the command of pstree to show all attribute of every node
        def _str(node, depth=0):
            attr = self.ele_map[node.id]
            end_color = '\033[0m'
            if attr.type != 'div':
                color = '\033[0;32m'
            else:
                color = '\033[0;30m'
            if not is_color:
                end_color = ''
                color = ''
            if len(node.children) == 0:
                return color + f'{"  "*depth}{attr.desc_html_start}{attr.desc_html_end}\n' + end_color
            ret = color + f'{"  "*depth}{attr.desc_html_start}\n' + end_color
            for child in node.children:
                ret += _str(child, depth + 1)
            ret += color + f'{"  "*depth}{attr.desc_html_end}\n' + end_color
            return ret

        return _str(self.root)

    def get_str_with_visible(self, with_id=False) -> str:
        '''
    use to print the tree in terminal with color
    '''

        # output like the command of pstree to show all attribute of every node
        def _str(node, depth=0):
            attr = self.ele_map[node.id]
            if (len(node.children) == 0 or attr.content_description or
                    attr.scrollable) and attr.is_visible:
                if len(node.children) == 0:
                    return f'{"  "*depth}{attr.desc_visible_html_start}{attr.desc_html_end}\n'
                ret = f'{"  "*depth}{attr.desc_visible_html_start}\n'
                for child in node.children:
                    ret += _str(child, depth + 1)
                ret += f'{"  "*depth}{attr.desc_html_end}\n'
            else:
                ret = ''
                for child in node.children:
                    ret += _str(child, depth)
            return ret

        html_view = _str(self.root)
        if not with_id:
            html_view = re.sub(r"id='\d+'", '', html_view)
        return html_view

    def _get_ele_by_xpath(self, xpath: str) -> EleAttr | None:
        html_view = self.str
        root = etree.fromstring(html_view)
        eles = root.xpath(xpath)
        if not eles:
            return None
        ele_desc = etree.tostring(
            eles[0], pretty_print=True).decode('utf-8')  # only for father node
        id_str = re.search(r' id="(\d+)"', ele_desc).group(1)
        try:
            id = int(id_str)
        except Exception as e:
            print('fail to analyze xpath, err: {e}')
            raise e  # todo:: add a better way to handle this
        # print('found element with id', id)
        return self.ele_map.get(id, None)

    def get_ele_by_xpath(self, xpath: list[str] | str):
        target_ele = None
        if isinstance(xpath, list):
            for xp in xpath:
                try:
                    target_ele = self._get_ele_by_xpath(xp)
                    if target_ele:
                        break
                except:
                    continue
        else:
            target_ele = self._get_ele_by_xpath(xpath)

        return target_ele

    def match_str_in_children(self, ele: EleAttr, key: str):
        eles = self.get_children_by_ele(ele)
        return [e for e in eles if e.is_match(key)]

    def get_children_by_ele(self, ele: EleAttr) -> list[EleAttr]:
        if ele.id not in self.ele_map:
            return []
        que = [self.root]
        target = None
        while len(que) > 0:
            node = que.pop(0)
            if node.id == ele.id:
                target = node
                break
            for child in node.children:
                que.append(child)
        if target == None:
            return []
        # only for valid children, the sort is ascending order of the id
        return [self.ele_map[idx] for idx in sorted(target.leaves)]

    def get_children_by_idx(self, ele: EleAttr, idx: int):
        for childid, child in enumerate(ele.children):
            if childid == idx:
                return self.ele_map[child]
        return None

    def match_str_in_children(self, ele: EleAttr, key: str):
        eles = self.get_children_by_ele(ele)
        return [e for e in eles if e.is_match(key)]

    def get_ele_text(self, ele):
        '''
        recursviely get the text of the element, including the text of its children
        '''
        if ele.text:
            return ele.text
        for child in ele.children:
            child_text = self.get_ele_text(self.eles[child])
            if child_text is not None:
                return child_text
        return None

    def get_content_desc(self, ele):
        '''
        recursviely get the content_description of the element, including the content_description of its children
        '''
        if ele.content_description:
            return ele.content_description
        for child in ele.children:
            child_content = self.get_content_desc(self.eles[child])
            if child_content is not None:
                return child_content
        return None

    def get_text(self, ele):
        ele_text = self.get_ele_text(ele)
        if ele_text:
            return ele_text
        ele_content_description = self.get_content_desc(ele)
        if ele_content_description:
            return ele_content_description

    # def get_all_children_by_ele(self, ele: EleAttr):
    #     if len(ele.children) == 0:
    #         return [ele]
    #     result = []
    #     for child_id in ele.children:
    #         ele = self.ele_map.get(child_id, None)
    #         if not ele:
    #             continue
    #         result.extend(self.get_all_children_by_ele(ele))

    #     return result

    def get_ele_descs_without_text(self):
        ele_descs = []
        for ele_id, ele in self.eles.items():
            ele_dict = ele.dict()
            ele_desc = ''
            for k in [
                    'resource_id', 'class_name', 'content_description',
                    'bound_box'
            ]:
                if ele_dict[k]:
                    ele_desc += f'{k}={ele_dict[k]} '
            ele_descs.append(ele_desc)
        return ele_descs

    def get_ele_by_properties(self, key_values: dict):
        for _, ele in self.ele_map.items():
            ele_dict = ele.dict()
            matched = True
            for k, v in key_values.items():
                if k not in ele_dict.keys() or ele_dict[k] != v:
                    matched = False
                    break
            if matched:
                return ele
        return None

    def get_ele_text(self, ele):
        if ele.text:
            return ele.text
        for child in ele.children:
            child_text = self.get_ele_text(self.ele_map[child])
            if child_text is not None:
                return child_text
        return None

    def get_content_desc(self, ele):
        if ele.content_description:
            return ele.content_description
        for child in ele.children:
            child_content = self.get_content_desc(self.ele_map[child])
            if child_content is not None:
                return child_content
        return None

    def get_text(self, ele):
        ele_text = self.get_ele_text(ele)
        if ele_text:
            return ele_text
        ele_content_description = self.get_content_desc(ele)
        if ele_content_description:
            return ele_content_description

    # def get_all_children_by_ele(self, ele: EleAttr):
    #     try:
    #         result = [self.ele_map[child] for child in ele.children]
    #     except:
    #         import pdb
    #         pdb.set_trace()
    #     if not result:
    #         return []
    #     for child in ele.children:
    #         result.extend(self.get_all_children_by_ele(self.ele_map[child]))
    #     return result

    def get_ele_descs_without_text(self):
        ele_descs = []
        for ele_id, ele in self.ele_map.items():
            ele_dict = ele.dict()
            ele_desc = ''
            for k in [
                    'resource_id', 'class_name', 'content_description',
                    'bound_box'
            ]:
                if ele_dict[k]:
                    ele_desc += f'{k}={ele_dict[k]} '
            ele_descs.append(ele_desc)
        return ele_descs

    def get_ele_id_by_properties(self, key_values: dict):
        for ele_id, ele in self.ele_map.items():
            ele_dict = ele.dict()
            matched = True
            for k, v in key_values.items():
                if k not in ele_dict.keys() or ele_dict[k] != v:
                    matched = False
                    break
            if matched:
                return ele.id
        return -1
    
    def extract_subtree(self, ele_id: int):
        ele = self.ele_map.get(ele_id, None)
        if not ele:
            return None

        _ele_attr = {}
        que = [ele_id]
        while que:
            idx = que.pop(0)
            ele = self.ele_map.get(idx, None)
            if not ele:
                continue
            _ele_attr[idx] = ele
            for child in ele.children:
                que.append(child)

        _valid_ele_ids = list(_ele_attr.keys() & self.valid_ele_ids)
        return ElementTree(
            ele_attrs=_ele_attr,views=self.views, valid_ele_ids=_valid_ele_ids, root_id=ele_id)


from bs4 import BeautifulSoup, Tag, NavigableString

class HTMLSkeleton():

    def __init__(self, html: str | BeautifulSoup, is_formatted=False):
        if isinstance(html, str):
            self.soup = BeautifulSoup(html, 'html.parser')
        else:
            self.soup = html

        if not is_formatted:
            self._remove_attributes()
            self._clean_repeated_siblings()

        self.str = self.soup.prettify()

    def _remove_attributes(self):
        '''
    use bs4 to remove all other attributes except for the tag name and resource_id from the html
    '''

        soup = self.soup
        for tag in soup.find_all(True):
            # Remove all attributes except for 'resource_id'
            attributes = tag.attrs.copy()
            for attr in attributes:
                if attr != 'resource_id':
                    del tag.attrs[attr]

            # Remove all text nodes within tags
            for content in tag.contents:
                if isinstance(content, NavigableString):
                    content.extract()

    def _clean_repeated_siblings(self):
        '''
    use bs4 to remove all repeated siblings from the html
    '''

        def _remove_repeated_siblings(tag):
            if not isinstance(tag, Tag):
                return
            unique_children = []
            seen_tags = set()
            for child in tag.find_all(recursive=False):
                child_signature = (child.name,
                                   tuple(sorted(child.attrs.items())))
                if child_signature not in seen_tags:
                    unique_children.append(child)
                    seen_tags.add(child_signature)
            tag.clear()
            for child in unique_children:
                tag.append(child)
                _remove_repeated_siblings(child)

        _remove_repeated_siblings(self.soup)

    def count(self):
        """
    Count the number of tags in the HTML skeleton.
    For comparing the complexity of two HTML skeletons.
    """
        return len(self.soup.find_all(recursive=True))

    def extract_common_skeleton(self, skeleton):
        '''
    Extract the common structure from two HTMLSkeleton, return the 
    common structure as a new HTMLSkeleton.
    '''

        def compare_and_extract_common(node1, node2):
            if not (node1 and node2):
                return None
            if node1.name != node2.name:
                return None
            common_node = Tag(name=node1.name)
            for attr in node1.attrs:
                if attr in node2.attrs and node1.attrs[attr] == node2.attrs[
                        attr]:
                    common_node[attr] = node1.attrs[attr]
            common_children = []
            for child1, child2 in zip(
                    node1.find_all(recursive=False),
                    node2.find_all(recursive=False)):
                common_child = compare_and_extract_common(child1, child2)
                if common_child:
                    common_children.append(common_child)
            common_node.extend(common_children)
            return common_node

        soup1 = self.soup
        soup2 = skeleton.soup

        common_structure = compare_and_extract_common(soup1.contents[0],
                                                      soup2.contents[0])
        if not common_structure:
            return HTMLSkeleton('', is_formatted=False)
        return HTMLSkeleton(common_structure, is_formatted=True)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, HTMLSkeleton):
            return False
        return self.soup == value.soup

    def __ne__(self, value: object) -> bool:
        return not self.__eq__(value)

    def __hash__(self) -> int:
        return hash(self.str)    