import datetime
import json
import logging
import os
import threading

from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource,
)
import requests

logger = logging.getLogger(__name__)

API_KEY = os.getenv("DEEPGRAM_API_KEY")
SERVER_URL = os.getenv("SERVER_URL")

def send_task(url, payload, log):
    try:
        # response = requests.post(url=url, json=payload, timeout=20, headers=headers)
        log.info(f"Sending transcription to server.... {url}")
        pl = json.loads(payload)
        response = requests.post(url=url, json=pl, timeout=20)
        if (response.status_code == 200) or (response.status_code == 201):
            log.info(f"Transcription sent to server successfully")
        else:
            log.error(f"{payload}")
            log.error(f"Transcription failed to send to server. Status code: {response.status_code}")
    except Exception as e:
        log.error(f"Error sending transcription to server: {e}")

def send_transcription_to_server(text: str, meeting_id):
    thread = threading.Thread(target=send_task, args=(SERVER_URL, text, logger))
    thread.start()



def transcribe_audio(audio_file: str, meeting_id):
    deepgram = DeepgramClient(api_key=API_KEY)

    with open(audio_file, "rb") as file:
        buffer_data = file.read()

    payload: FileSource = {
        "buffer": buffer_data,
    }

    options = PrerecordedOptions(
        model="nova-3",
        smart_format=True,
        diarize=True,
        detect_language=True,
    )

    response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
    js = response.to_json(indent=4)

    json_dict = json.loads(js)

    json_dict['meeting_id'] = str(meeting_id)

    json_str_updated = json.dumps(json_dict, indent=4)

    os.makedirs('transcriptions', exist_ok=True)

    with open(f'transcriptions/{meeting_id}_{datetime.datetime.now().strftime("%H_%M_%S")}.json', "w") as f:
        f.write(json_str_updated)

    # logger.info(f"{json_str_updated}")

    send_transcription_to_server(json_str_updated, meeting_id)

# def main():
#     try:
#         # STEP 1 Create a Deepgram client using the API key
#         deepgram = DeepgramClient()
#
#         with open(AUDIO_FILE, "rb") as file:
#             buffer_data = file.read()
#
#         payload: FileSource = {
#             "buffer": buffer_data,
#         }
#
#         #STEP 2: Configure Deepgram options for audio analysis
#         options = PrerecordedOptions(
#             model="nova-3",
#             smart_format=True,
#         )
#
#         # STEP 3: Call the transcribe_file method with the text payload and options
#         response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
#
#         # STEP 4: Print the response
#         print(response.to_json(indent=4))
#
#     except Exception as e:
#         print(f"Exception: {e}")
#
# if __name__ == "__main__":
#     main()
