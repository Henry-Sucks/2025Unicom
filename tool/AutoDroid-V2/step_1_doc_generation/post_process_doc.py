from tools import load_json_file, dump_json_file

def post_process(doc_path):
    doc = load_json_file(doc_path)
    new_doc = {}
    for screen in doc:
        new_doc[screen] = {
            "elements": {},
            "skeleton": doc[screen]["skeleton"]
        }
        for element in doc[screen]["elements"]:
            new_name = element.replace(":","__")
            new_el = doc[screen]["elements"][element]
            new_el["name"] = new_name
            new_el_paths = []
            if "paths" in new_el:
                for path in new_el["paths"]:
                    new_paths = []
                    for step in path:
                        new_step = step.replace(":","__")
                        new_paths.append(new_step)
                    new_el_paths.append(new_paths)
                new_el["paths"] = new_el_paths
            new_doc[screen]["elements"][new_name] = new_el
    dump_json_file(doc_path,new_doc)

if __name__ == '__main__':
    doc_path = "llama_touch/docs/new/Spotify.json"
    post_process(doc_path)