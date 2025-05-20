import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Optional

import requests

from bots.models import Participant, Utterance, Recording

from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

logger = logging.getLogger(__name__)


def get_default_closed_caption_participant() -> 'Participant':
    """
    Returns a default Participant instance to be used for closed caption utterances.
    You can modify this to either lookup an existing default participant or create one.
    """
    # Example: try to get an existing default participant by a unique identifier.
    # You might need to adjust the lookup based on your Participant model.
    try:
        participant = Participant.objects.get(name="Closed Caption")
    except Participant.DoesNotExist:
        # Create one if not found. Adjust required fields as necessary.
        participant = Participant.objects.create(name="Closed Caption")
    return participant


def create_utterance_from_closed_caption(
        recording: Recording,
        caption_data: dict,
        created_at: Optional[datetime] = None,
        modified_at: Optional[datetime] = None,
) -> None:
    """
    Creates and saves an Utterance from closed caption data for the given Recording.

    Parameters:
      recording (Recording): The Recording instance for the utterance.
      caption_data (dict): Dictionary containing the closed caption details.
         Expected keys: "deviceId", "captionId", "text", etc.
      created_at (datetime, optional): Creation timestamp of the caption.
         Defaults to now if not provided.
      modified_at (datetime, optional): Last modified timestamp of the caption.
         Defaults to the same as created_at if not provided.

    Notes:
      - The utterance uses a dummy audio blob (empty bytes) since closed captions typically
        have no audio associated.
      - The participant is set to a default closed caption participant.
    """
    # Use provided timestamps or default to current UTC time.
    now = datetime.now()
    if created_at is None:
        created_at = now
    if modified_at is None:
        modified_at = created_at

    # Retrieve or create the default closed caption participant.
    default_participant = get_default_closed_caption_participant()

    # Build a source_uuid using a known prefix and unique identifiers
    source_uuid = f"closed_caption-{caption_data.get('deviceId')}-{caption_data.get('captionId')}"

    # Create the Utterance instance.
    utterance = Utterance(
        recording=recording,
        participant=default_participant,
        # Since closed captions don't have associated audio, we use an empty binary blob.
        audio_blob=b"",
        # Using a default audio format (PCM in this case).
        audio_format=Utterance.AudioFormat.PCM,
        # Convert timestamps to milliseconds.
        timestamp_ms=int(created_at.timestamp() * 1000),
        duration_ms=int((modified_at - created_at).total_seconds() * 1000),
        # Save the caption text as the transcription; you could also store more complex JSON.
        transcription={"text": caption_data.get("text", "")},
        source_uuid=source_uuid,
        sample_rate=None,
        # Specify that this utterance is coming from closed caption data.
        source=Utterance.Sources.CLOSED_CAPTION_FROM_PLATFORM,
    )

    utterance.save()

SERVER_URL = os.getenv("SERVER_URL")

def send_task(url, js, log):
    try:
        log.info(f"Sending transcription to server.... {url}")
        header = {'Content-Type': 'application/json'}
        response = requests.post(url=url, json=js, headers=header, timeout=20)
        if (response.status_code == 200) or (response.status_code == 201):
            log.info(f"Transcription sent to server successfully")
        else:
            log.error(f"Transcription failed to send to server. Status code: {response.status_code}")
    except Exception as e:
        log.error(f"Error sending transcription to server: {e}")

def send_transcription_to_server(path: str):
    if path:
        with open(path, "r") as f:
            lines = f.readlines()
    else:
        return

    conversation = []

    d = {
        "transcription": []
    }

    for i, line in enumerate(lines):
        if i == 0:
            d['meeting_id'] = line.split(":")[1].strip()
            continue
        parts = line.split(":", 1)
        if len(parts) == 2:
            speaker = parts[0].strip()
            message = parts[1].strip()
            d['transcription'].append({speaker: message})

    conversation.append(d)

    thread = threading.Thread(target=send_task, args=(SERVER_URL, conversation, logger))
    thread.start()

class ScreenAndAudioRecorder:
    def __init__(self, file_location):
        self.file_location = file_location
        self.transcript_file = f"transcriptions/{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.txt"
        self.ffmpeg_proc = None
        self.screen_dimensions = (1920, 1080)
        self.exit_flag = threading.Event()

        # Initialize Deepgram client
        self.dg_client = DeepgramClient()
        self.dg_connection = None
        self.audio_thread = None
        self.transcript_file_handle = None
        self.speaker_map = {}

    def start_recording(self, display_var, virt_cable_token, meeting_id: str):
        logger.info(
            f"Starting screen recorder for display {display_var} with dimensions {self.screen_dimensions} and file location {self.file_location}")
        logger.info(f"Start monitoring on: {virt_cable_token} token")

        os.makedirs("transcriptions", exist_ok=True)
        self.transcript_file_handle = open(self.transcript_file, "a", encoding="utf-8")
        self.transcript_file_handle.write(f"meeting_id:{meeting_id}\n")

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-thread_queue_size", "4096",
            "-f", "pulse",
            "-ac", "2",
            "-ar", "44100",
            "-i", f"{virt_cable_token}.monitor",
            "-c:a", "aac", "-b:a", "96k", self.file_location,
            "-f", "s16le", "-ar", "16000", "-ac", "1", "pipe:1"
        ]

        logger.info(f"Starting FFmpeg command: {' '.join(ffmpeg_cmd)}")
        self.ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )

        # Initialize Deepgram connection
        self._start_deepgram()

    def _start_deepgram(self):
        """Initialize Deepgram connection and start processing audio"""
        try:
            self.dg_connection = self.dg_client.listen.websocket.v("1")
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)

            options = LiveOptions(
                model="nova-3",
                encoding="linear16",
                sample_rate=16000,
                channels=1,
                punctuate=True,
                interim_results=True,
                diarize=True
            )

            if not self.dg_connection.start(options):
                logger.error("Failed to connect to Deepgram")
                return

            # Start audio processing thread
            self.audio_thread = threading.Thread(target=self._process_audio)
            self.audio_thread.start()

        except Exception as e:
            logger.error(f"Deepgram initialization failed: {e}")

    def _process_audio(self):
        """Read audio from FFmpeg and send to Deepgram"""
        try:
            while not self.exit_flag.is_set() and self.ffmpeg_proc.poll() is None:
                data = self.ffmpeg_proc.stdout.read(4096)
                if data:
                    self.dg_connection.send(data)
        except Exception as e:
            logger.error(f"Audio processing error: {e}")

    def _on_transcript(self, _, result, **kwargs):
        try:
            if not result.channel.alternatives:
                return

            transcript = result.channel.alternatives[0]
            sentence = transcript.transcript

            # Skip empty transcripts
            if len(sentence.strip()) == 0:
                return

            # Get speaker information
            speaker_id = transcript.words[0].speaker if transcript.words else 0
            confidence = transcript.confidence

            # Create speaker label
            speaker_label = self._get_speaker_label(speaker_id)

            # Get timestamp
            start_time = transcript.words[0].start if transcript.words else 0
            end_time = transcript.words[-1].end if transcript.words else 0

            # Format output
            timestamp = datetime.now().strftime("%H:%M:%S")
            output = (
                f"{speaker_label}:{sentence}\n"
            )

            # Write to file
            if result.is_final and confidence > 0.5:  # Only write high-confidence final results
                self.transcript_file_handle.write(output)
                self.transcript_file_handle.flush()
                logger.info(f"Transcript saved: {output.strip()}")

        except Exception as e:
            logger.error(f"Error processing transcript: {e}")

    def _get_speaker_label(self, speaker_id):
        if speaker_id not in self.speaker_map:
            # Assign new speaker label (e.g., Speaker 1, Speaker 2)
            speaker_number = len(self.speaker_map) + 1
            self.speaker_map[speaker_id] = f"speaker {speaker_number}"
        return self.speaker_map[speaker_id]

    def stop_recording(self):
        """Stop recording and clean up resources"""
        self.exit_flag.set()

        # Stop Deepgram connection
        if self.dg_connection:
            self.dg_connection.finish()

        # Stop FFmpeg process
        if self.ffmpeg_proc:
            self.ffmpeg_proc.terminate()
            self.ffmpeg_proc.wait()

        # Wait for audio thread to finish
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join()

        logger.info(f"Stopped recorder for display with dimensions {self.screen_dimensions}")

        if self.transcript_file_handle:
            self.transcript_file_handle.close()
            logger.info(f"Transcript saved to {self.transcript_file}")

        send_transcription_to_server(self.transcript_file)

        logger.info("Speaker mapping:")
        for sid, label in self.speaker_map.items():
            logger.info(f"  {sid} => {label}")

    def get_seekable_path(self, path):
        """
        Transform a file path to include '.seekable' before the extension.
        Example: /tmp/file.webm -> /tmp/file.seekable.webm
        """
        base, ext = os.path.splitext(path)
        return f"{base}.seekable{ext}"

    def cleanup(self, meeting_id=None):
        input_path = self.file_location

        # Check if input file exists
        if not os.path.exists(input_path):
            logger.info(f"Input file does not exist at {input_path}, creating empty file")
            with open(input_path, "wb"):
                pass  # Create empty file
            return

        # if input file is greater than 3 GB, we will skip seekability
        if os.path.getsize(input_path) > 3 * 1024 * 1024 * 1024:
            logger.info("Input file is greater than 3 GB, skipping seekability")
            return

        output_path = self.get_seekable_path(self.file_location)

        # create_utterance_from_closed_caption()

        # transcribe_audio(input_path, meeting_id)

        self.make_file_seekable(input_path, output_path)

    def make_file_seekable(self, input_path, tempfile_path):
        """Use ffmpeg to move the moov atom to the beginning of the file."""
        logger.info(f"Making file seekable: {input_path} -> {tempfile_path}")
        # log how many bytes are in the file
        logger.info(f"File size: {os.path.getsize(input_path)} bytes")
        command = [
            "ffmpeg",
            "-i",
            str(input_path),  # Input file
            "-c",
            "copy",  # Copy streams without re-encoding
            "-avoid_negative_ts",
            "make_zero",  # Optional: Helps ensure timestamps start at or after 0
            "-movflags",
            "+faststart",  # Optimize for web playback
            "-y",  # Overwrite output file without asking
            str(tempfile_path),  # Output file
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        # Replace the original file with the seekable version
        try:
            os.replace(str(tempfile_path), str(input_path))
            logger.info(f"Replaced original file with seekable version: {input_path}")
        except Exception as e:
            logger.error(f"Failed to replace original file with seekable version: {e}")
            raise RuntimeError(f"Failed to replace original file: {e}")
