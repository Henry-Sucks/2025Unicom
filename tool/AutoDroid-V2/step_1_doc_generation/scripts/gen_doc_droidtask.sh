#!/bin/bash


RAW_LOG_PATHS=(
    'doc_generation/data/droidtask/explore_data/applauncher'
    'doc_generation/data/droidtask/explore_data/calendar'
    'doc_generation/data/droidtask/explore_data/camera'
    'doc_generation/data/droidtask/explore_data/clock'
    'doc_generation/data/droidtask/explore_data/contacts'
    'doc_generation/data/droidtask/explore_data/dialer'
    'doc_generation/data/droidtask/explore_data/filemanager'
    'doc_generation/data/droidtask/explore_data/gallery'
    'doc_generation/data/droidtask/explore_data/messenger'
    'doc_generation/data/droidtask/explore_data/music'
    'doc_generation/data/droidtask/explore_data/notes'
    'doc_generation/data/droidtask/explore_data/firefox'
    'doc_generation/data/droidtask/explore_data/voicerecorder'
)

OUTPUT_FILE_NAMES=(
    'doc_generation/output/droidtask/applauncher_0814'
    'doc_generation/output/droidtask/calendar_0814'
    'doc_generation/output/droidtask/camera_0814'
    'doc_generation/output/droidtask/clock_0814'
    'doc_generation/output/droidtask/contacts_0814'
    'doc_generation/output/droidtask/dialer_0814'
    'doc_generation/output/droidtask/filemanager_0814'
    'doc_generation/output/droidtask/gallery_0814'
    'doc_generation/output/droidtask/messenger_0814'
    'doc_generation/output/droidtask/music_0814'
    'doc_generation/output/droidtask/notes_0814'
    'doc_generation/output/droidtask/firefox_0814'
    'doc_generation/output/droidtask/voicerecorder_0814'
)


APPNAMES=(
    "App Launcher"
    "Calendar"
    "Camera"
    "Clock"
    "Contacts"
    "Dialer"
    "File Manager"
    "Gallery"
    "Messenger"
    "Music"
    "Notes"
    "FireFox"
    "Voice Recorder"
)

if [ ${#RAW_LOG_PATHS[@]} -ne ${#APPNAMES[@]} ] || [ ${#RAW_LOG_PATHS[@]} -ne ${#OUTPUT_FILE_NAMES[@]} ]; then
    echo "Error: Arrays have different lengths."
    exit 1
fi

for i in "${!RAW_LOG_PATHS[@]}"; do
    python gen_doc.py -d "${RAW_LOG_PATHS[$i]}" \
                        -m gpt-4o \
                        -t 0814 \
                        -a "${APPNAMES[$i]}" \
                        -o "${OUTPUT_FILE_NAMES[$i]}" &
done

wait
