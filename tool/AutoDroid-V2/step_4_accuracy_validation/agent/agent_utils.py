"""Utilities for agents."""

import ast
import os
import numpy as np
import json
import yaml
import re

from typing import Any, Optional

from lxml import etree
from PIL import Image
import logging

from agent.droidbot.device_state import EleAttr, DeviceState

def extract_json(s: str) -> Optional[dict[str, Any]]:
  """Extracts JSON from string.

  Args:
    s: A string with a JSON in it. E.g., "{'hello': 'world'}" or from CoT:
      "let's think step-by-step, ..., {'hello': 'world'}".

  Returns:
    JSON object.
  """
  pattern = r'\{.*?\}'
  match = re.search(pattern, s)
  if match:
    try:
      return ast.literal_eval(match.group())
    except (SyntaxError, ValueError) as error:
      print('Cannot extract JSON, skipping due to error %s', error)
      return None
  else:
    return None

def save_to_yaml(save_path: str, html_view: str, tag: str, action_type: str,
                 action_details: dict, choice: int | None, input_text: str,
                 width: int, height: int):
  if not save_path:
    return

  file_name = os.path.join(save_path, 'log.yaml')

  if not os.path.exists(file_name):
    tmp_data = {'step_num': 0, 'records': []}
    with open(file_name, 'w', encoding='utf-8') as f:
      yaml.dump(tmp_data, f)

  with open(file_name, 'r', encoding='utf-8') as f:
    old_yaml_data = yaml.safe_load(f)
  new_records = old_yaml_data['records']
  new_records.append({
      'State': html_view,
      'Action': action_type,
      'ActionDetails': action_details,
      'Choice': choice,
      'Input': input_text,
      'tag': tag,
      'width': width,
      'height': height,
      'dynamic_ids': []
  })
  data = {
      'step_num': len(list(old_yaml_data['records'])),
      'records': new_records
  }
  with open(file_name, 'w', encoding='utf-8') as f:
    yaml.dump(data, f)


def save_screenshot(save_path: str, tag: str, pixels: np.ndarray):
  if not save_path:
    return

  output_dir = os.path.join(save_path, 'states')
  if not os.path.exists(output_dir):
    os.makedirs(output_dir)
  file_path = os.path.join(output_dir, f"screen_{tag}.png")
  image = Image.fromarray(pixels)
  image.save(file_path, format='JPEG')

def convert_action(action_type: str, ele: EleAttr, text: str):

  action_details = {"action_type": "wait"}
  if action_type in ["touch", "long_touch", "set_text"]:
    x, y = DeviceState.get_view_center(ele.view)
    x, y = int(x), int(y)
    action_details['x'] = x
    action_details['y'] = y
    if action_type == "touch":
      action_details["action_type"] = "click"
    elif action_type == "long_touch":
      action_details["action_type"] = "long_press"
    elif action_type == "set_text":
      action_details["action_type"] = "input_text"
      action_details['text'] = text
    return action_details
  elif "scroll" in action_type:
    action_details["action_type"] = "scroll"
    direction = action_type.split(' ')[-1]
    action_details['view'] = ele.view
    action_details['direction'] = direction
    return action_details
  return action_details