# 1. Setup Virtual Device

To ensure the virtual device runs correctly on your desktop, please follow these steps:  

### **System Requirements**  
1. The system image is based on the **x86_64 architecture**, so your desktop must support the same.  
2. Currently, **Linux** is the only supported operating system.  
3. Update the version of [Android SDK Platform tools](https://developer.android.com/tools/releases/platform-tools)  to:  
   - **Android Debug Bridge version 1.0.41**  
   - **Version 35.0.2-12147458**  

### **Setup Instructions**  
1. Download the ZIP file and unzip it. You will get the following files:  
   - `Pixel_6_API_31.avd`  
   - `Pixel_6_API_31.ini`  
2. Place these files in your AVD directory (e.g., `/home/xx/.android/avd`).  

3. Update the following configurations:  

#### **`Pixel_6_API_31.ini`**  
- Replace `/home/airaiot/.android/avd` with your AVD path (e.g., `/home/xx/.android/avd`).  

#### **`Pixel_6_API_31.avd/config.ini`**  
- Replace `/media/airaiot/Workspace/android` with the path to your **Android SDK Location**.  
   - *(In Android Studio, you can find this path under `File -> Settings -> Languages & Frameworks -> Android SDK`).*  
- Replace `/home/airaiot/.android/avd` with your AVD path (e.g., `/home/xx/.android/avd`).  

#### **`Pixel_6_API_31.avd/hardware-qemu.ini`**  
- Replace all instances of `/media/airaiot/Workspace/android` with your **Android SDK Location**.  
- Replace all instances of `/home/airaiot/.android/avd` with your AVD path.  


### **Running the Virtual Device**  
After completing the above steps, you can launch the Android virtual device. On the first run, you can save a snapshot for future use in case your agent changes the apps data.  

# 2. Install Droidbot
### Prerequisite
1. Python

2. Java

3. Android SDK

4. Add platform_tools directory in Android SDK to PATH

### Install


```
download the apks from https://cloud.tsinghua.edu.cn/f/eeea64534064438abbc4/, unzip the apks.zip and put the apks under apks folder
git clone https://github.com/MobileLLM/AutoDroid-V2.git
cd AutoDroid-V2/step_4_accuracy_validation
pip install -e .
```