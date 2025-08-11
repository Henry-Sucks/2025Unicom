import json
import os
docs_dir = 'data/droidtask/docs'
docs_path = [d for d in os.listdir(docs_dir) if os.path.isdir(os.path.join(docs_dir, d))]

target_dir = 'data/droidtask/formatted_docs'
os.makedirs(target_dir, exist_ok=True)
for doc_path in os.listdir(docs_dir):
  doc_data = json.load(open(os.path.join(docs_dir, doc_path), 'r'))
  
  # screen_name -> elements, skeleton
  for k, v in doc_data.items():
    _elements = {}
    for k1, v1 in v['elements'].items():
      k1 = k1.replace(":", "__")
      v1["name"] = v1["name"].replace(":", "__")
      xpath = v1["xpath"]
      if xpath:
        if isinstance(xpath, list):
          for i, x in enumerate(xpath):
            x = x.replace("resource-id", "resource_id").replace('\n', "")
            if x.startswith('/') and x.startswith('//') == False:
              x = '/' + x
            xpath[i] = x
        else:
          xpath = xpath.replace("resource-id", "resource_id").replace('\n', "")
      v1["xpath"] = xpath
      if 'paths' in v1:
        _all_paths = []
        for paths in v1['paths']:
          _paths = []
          for p in paths:
            if 'open_app' in p:
              continue
            _paths.append(p.replace(":", "__"))
          _all_paths.append(_paths)
        v1['paths'] = _all_paths
      
      _elements[k1] = v1
    
    doc_data[k]['elements'] = _elements
  
  json.dump(doc_data, open(os.path.join(target_dir, doc_path), 'w'), indent=2)