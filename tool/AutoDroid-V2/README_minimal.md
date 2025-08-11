# Runnning an Experiment with Minimal Setup
Running experiment sacross all apps is time-consuming and expensive.Therefore, we provide a minimal example using the simplest app — App Launcher. You can execute the entire pipeline for this app by following README_minimal.md to verify script functionality.

## Minimal Required Setup
The settings that must be cofigured are the following:
1. First install all project dependencies by running:
```bash
pip install -r requirements.txt
```
2. To run experiments with the fine-tuned model we provide, please download the model [here](https://huggingface.co/BlitherBoom/AutoDroid-V2). Save the model files in the following directory: **step_4_accuracy_validation/model/autodroidv2**
2. Install ADB
Android Debug Bridge (adb) is a versatile command-line tool that lets you communicate with a device. You can download it from [here](https://developer.android.com/tools/releases/platform-tools) and follow the guide to set it up.
3. Setup an **Android Emulator Device** e.g. [AVD](https://developer.android.com/studio/run/managing-avds) 
- It is recommended to use **Pixel 6** device with **API 31 Level** as this is the main device we used for experiments.
- Please set the name of the device to: **pixel_6a_api31**
- Install the "App Launcher" application by simply drag and drop of the apk (found at **step_4_accuracy_validation/minimal_setup/apks/applauncher.apk**) to the emulated device screen.
- Create a snapshot of the device. The snapshot is used for loading/restoring device state between tasks execution. To create a snapshot please follow the [official guide](https://developer.android.com/studio/run/emulator-snapshots).   
- After the emulator setup is done, please change the device settings in the configuration file: **step_4_accuracy_validation/minimal_setup/config.py**. Change the `EMULATOR_CONTROLLER_AGRS` and `AVD_NAME` variables according to your emulator settings. The default port of the device is **5554**. To double-check on what port the device is running, use the command **adb devices**.
4. Define your Open AI API key and password in order to use the GPT model.

## Running minimal experiment
- Ensure you are inside of **step_4_accuracy_validation** directory.
```bash
cd step_4_accuracy_validation
``` 
- Use the following command to run the minimal experiment:
```bash
python run_minimal_experiment.py
```
- To see the output of the experiment results, check the following folder defined in the config file: **step_4_accuracy_validation/minimal_experiment_output/autodroidv2**
