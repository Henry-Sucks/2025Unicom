# Deploy AutoDroid-V2 with llama.cpp

Clone and install [llama.cpp](https://github.com/ggerganov/llama.cpp) following the official instruction to [install](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md).

Download the [model](https://huggingface.co/BlitherBoom/AutoDroid-V2), convert and quantize it using llama.cpp (you can also download, convert, and quantize it on your computer first, then transfer the output file to your phone):
```bash
cd llama.cpp
python convert_hf_to_gguf.py ./AutoDroid-V2 --outfile ./AutoDroid-V2.gguf --outtype f16
./build/bin/llama-quantize AutoDroid-V2.gguf AutoDroid-V2-Q8_0.gguf Q8_0
```

Then config the test app and the model path in `./run_infer.py`:
```python
app_name = 'App Launcher' # set app name
llama_cli_path = "build/bin/llama-cli" # set llama-cli path
prompt_path = "all_prompts.json" # set test prompt, for autodroid baseline, replace with "autodroid_all_prompts.json"   
model_path = "AutoDroid-V2-Q8_0.gguf" # set model path
```

Now run the test script:
```bash
python run_infer.py
```

The average total time is printed (in ms):
```bash
Total time average: ...
```

# Optimizing Mobile Phone for Local LLM Inference

When running a large language model (LLM) locally on a mobile phone, optimizing system resources can improve inference speed. This guide explains how to maximize RAM usage, disable power-saving strategies, and ensure optimal performance.

## 1. Increase Available RAM
### a) Enable Developer Options
1. Go to **Settings** > **About phone**.
2. Find **Build number** and tap it **7 times** to enable Developer Options.
3. Navigate to **Settings** > **Developer Options**.

### b) Increase Background Process Limit
1. In **Developer Options**, scroll down to **Background process limit**.
2. Set it to **No background processes** to free up RAM.

### c) Use a RAM Expansion Feature (If Available)
Some Android phones allow you to use virtual RAM:
1. Go to **Settings** > **Memory & Storage**.
2. Look for an option like **RAM Boost** or **Memory Extension**.
3. Enable it and allocate additional memory.

## 2. Disable Power-Saving Strategies
Power-saving features may throttle CPU and GPU performance, slowing down inference.

### a) Disable Battery Optimization
1. **Settings** > **Battery** > **Battery Optimization**.
2. Find your LLM app and set it to **Don't optimize**.

### b) Disable CPU Throttling
1. **Settings** > **Developer Options**.
2. Find **Disable CPU thermal throttling** (if available) and enable it.

### c) Set Performance Mode
1. **Settings** > **Battery** > **Performance Mode**.
2. Choose **High Performance** or **Game Mode** if available.

## 3. Free Up System Resources
### a) Close Unnecessary Apps
- Use the **Recent Apps** button and clear background applications.
- Uninstall or disable apps that consume RAM in the background.

### b) Disable Animations (Optional)
1. **Settings** > **Developer Options**.
2. Set **Window animation scale**, **Transition animation scale**, and **Animator duration scale** to **Off**.

### c) Use a Lightweight LLM Model
- Opt for **quantized models** (e.g., GGML, GPTQ) to reduce memory usage.
- Run inference on GPU if supported (e.g., via Metal on iOS or Vulkan on Android).

## 4. Keep Your Device Cool
Running an LLM can generate heat, leading to thermal throttling. To prevent slowdowns:
- Place the phone on a **cool surface**.
- Use a **cooling fan** or external heat dissipation methods if available.
