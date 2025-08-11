## Traces requirements
The traces that the agent must produce in order to be evaluated later by the llama-touch evaluator are the following:
 - actions
 - activities: Ex: com.google.android.apps.nexuslauncher/.NexusLauncherActivity (0.activity)
 - installed_apps: Ex: com.google.android.youtube, com.android.internal.display.cutout.emulation.corner; Separated by new line ( installed_apps.txt)
 - screenshots: Ex: 0.png
 - view hierarchy ( in JSON for each view ): Ex: 0.json (array of view properties for each view)
    - Properties:
        ```json 
        "id": 0,
        "class": "android.widget.TextView",
        "text": "Wed, Jan 17",
        "resource-id": "com.google.android.apps.nexuslauncher:id/date",
        "content-desc": "Wed, Jan 17",
        "bounds": "[99,246][1023,308]",
        "enabled": true,
        "checked": false,
        "checkable": false,
        "visible": true,
        "selected": false,
        "focused": false,
        "focusable": true,
        "clickable": true,
        "long-clickable": false,
        "password": false,
        "scrollable": false
        ```
 - xml of each view: Ex: 0.xml ( the whole xml representation of the view )