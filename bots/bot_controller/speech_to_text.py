import logging
import os

from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource,
)


logger = logging.getLogger(__name__)

API_KEY = os.getenv("DEEPGRAM_API_KEY")

def transcribe_audio(audio_file: str):
    deepgram = DeepgramClient(api_key=API_KEY)

    with open(audio_file, "rb") as file:
        buffer_data = file.read()

    payload: FileSource = {
        "buffer": buffer_data,
    }

    options = PrerecordedOptions(
        model="nova-3",
        smart_format=True,
        detect_language=True,
    )

    response = deepgram.listen.rest.v("1").transcribe_file(payload, options)

    logger.info(f"{response.to_json(indent=4)}")

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
