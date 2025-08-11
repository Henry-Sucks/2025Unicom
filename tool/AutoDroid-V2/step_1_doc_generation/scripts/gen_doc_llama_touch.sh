#!/bin/bash


RAW_LOG_PATHS=(
    'data/llama_touch/explore_data/clock'
    'data/llama_touch/explore_data/contacts'
    'data/llama_touch/explore_data/gmail'
    'data/llama_touch/explore_data/google_chrome'
    'data/llama_touch/explore_data/google_maps'
    'data/llama_touch/explore_data/google_photos'
    'data/llama_touch/explore_data/google_play'
    'data/llama_touch/explore_data/google_calendar'
    'data/llama_touch/explore_data/settings'
    'data/llama_touch/explore_data/youtube'
)

OUTPUT_FILE_NAMES=(
    'output/llama_touch/clock_0321'
    'output/llama_touch/contacts_0321'
    'output/llama_touch/gmail_0321'
    'output/llama_touch/google_chrome_0321'
    'output/llama_touch/google_maps_0321'
    'output/llama_touch/google_photos_0321'
    'output/llama_touch/google_play_0321'
    'output/llama_touch/google_calendar_0321'
    'output/llama_touch/settings_0321'
    'output/llama_touch/youtube_0321'
)


APPNAMES=(
    "Clock"
    "Contacts"
    "Gmail"
    "Google Chrome"
    "Google Maps"
    "Google Photos"
    "Google Play Store"
    "Google Calendar"
    "Settings"
    "YouTube"
)

if [ ${#RAW_LOG_PATHS[@]} -ne ${#APPNAMES[@]} ] || [ ${#RAW_LOG_PATHS[@]} -ne ${#OUTPUT_FILE_NAMES[@]} ]; then
    echo "Error: Arrays have different lengths."
    exit 1
fi

for i in "${!RAW_LOG_PATHS[@]}"; do
    python gen_doc.py -d "${RAW_LOG_PATHS[$i]}" \
                        -m gpt-4o \
                        -t 0321 \
                        -a "${APPNAMES[$i]}" \
                        -o "${OUTPUT_FILE_NAMES[$i]}" &
done

wait
