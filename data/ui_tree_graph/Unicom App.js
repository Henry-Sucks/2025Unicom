var utg = 
{
  "nodes": [
    {
      "id": "1",
      "function": "Starting point - Main page"
    },
    {
      "id": "2",
      "function": "Main page with menu bar activated"
    },
    {
      "id": "3",
      "function": "The current page appears to be the homepage of a China Unicom mobile app, featuring core functions such as travel services (flights, hotels), coupons, orders, and user account management. It also includes promotional content and navigation options like search, customer service, and scanning."
    },
    {
      "id": "4",
      "function": "The current page is a travel ticket booking interface for '\u8054\u901a\u65c5\u6e38', allowing users to search for one-way or round-trip flights with options to select cities, dates, and cabin class. It also displays a list of discounted flight options."
    },
    {
      "id": "5",
      "function": "The current page provides sharing and navigation functionalities, including sharing options, feedback, and returning to the homepage or previous page."
    }
  ],
  "edges": [
    {
      "id": "1",
      "from": "1",
      "to": "2",
      "event": "<table class=\"table\">\n<tr><th>1</th><td>TouchEvent(state=3ac3661471d3fd8fd624161b99b6f9315360cf1c93790110efb000a458626219, view=NoViewStr(MainActivity/ImageView-))</td></tr>\n</table>",
    },
    {
      "id": "2",
      "from": "2",
      "to": "3",
      "event": "<table class=\"table\">\n<tr><th>2</th><td>TouchEvent(state=3ac3661471d3fd8fd624161b99b6f9315360cf1c93790110efb000a458626219, view=NoViewStr(MainActivity/TextView-\u65c5\u884c))</td></tr>\n</table>",
    },
    {
      "id": "3",
      "from": "3",
      "to": "4",

      "event": "<table class=\"table\">\n<tr><th>3</th><td>TouchEvent(state=7c65c993cab4b846b126cec0c25b8f4b65b73175702f1176c8aecf55c6f888b8, view=93ee0f231bfb9bb81bd3386d6d9788f5(MainActivity/Image-icon_plane))</td></tr>\n</table>",
    },
    {
      "id": "4",
      "from": "4",
      "to": "5",
      "event": "<table class=\"table\">\n<tr><th>4</th><td>TouchEvent(state=7c2d0e52f0133f0e54270b61037ff79fbd70971ccef1b4fd77f9b6bf84f06d68, view=c9fea49669092d15ebcea8e3f2323f49(WebDetailActivity/ImageView-))</td></tr>\n</table>",
    }
  ],
  "num_nodes": 5,
  "num_edges": 5,
  "num_effective_events": 5,
  "num_reached_activities": 2,
  "test_date": "2025-08-08 13:40:52",
  "time_spent": 158.379517,
  "num_transitions": 5,
  "device_serial": "emulator-5554",
  "device_model_number": "sdk_gphone64_x86_64",
  "device_sdk_version": 35,
  "app_sha256": "747c2e541cd60cfdfe10eb316953af4bce5f6fd4d590c77ce7ff8ba5992fbd77",
  "app_package": "com.sinovatech.unicom.ui",
  "app_main_activity": "com.sinovatech.unicom.basic.ui.activity.WelcomeClient",
  "app_num_total_activities": 197
}