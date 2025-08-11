# Generation of a Document from Exploration Traces

## Overview  
This project enables the generation of structured documents from exploration traces of an application. The process involves extracting information from application states and logs, then compiling them into a meaningful document format.  

This README provides details on the required input format, how to obtain example exploration traces, and instructions for generating documents using provided scripts.  

---

## 1. Required Exploration Traces  
To generate a document, exploration traces from an application must follow the directory structure below:  
```
<application_path>/
├── log.yaml
├── states
│   ├── screen_<tag1>.png
│   ├── screen_<tag2>.png
│   ├── ...
│   ├── state_<tag1>.json
│   ├── state_<tag2>.json
│   ├── ...
```
## 2. Existing Exploration Traces  
If you want to use pre-collected exploration traces, you can find example datasets in the **`doc_generation/data`** folder.  

This folder includes:  
- **Pre-generated documents** for evaluation benchmarks.  
- **The corresponding exploration data** used to generate those documents.  

You can analyze these examples to better understand the expected input format.  

---

## 3. Generating Documents  

### Generating Documents for DroidTask Dataset  
To generate documents for applications in the **DroidTask dataset**, run the following command:  

```sh
sh scripts/gen_doc_droidtask.sh
```

### Generating Documents for AitW Dataset  
To generate documents for applications in the AitW dataset, run the following command:

```sh
sh scripts/gen_doc_llama_touch.sh
```

These scripts process the exploration traces and produce structured documents based on the extracted information.

## 4. Additional Notes
Ensure that the required dependencies are installed before running the scripts.
The scripts automatically process the data in the respective folders, so ensure that your exploration traces are correctly structured before executing the commands.
If you encounter issues, check the log.yaml file and verify that the required .json state files are present.
---
