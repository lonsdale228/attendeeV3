import logging
import os
import subprocess
import time
from datetime import datetime
from typing import Optional

from bots.bot_controller.speech_to_text import transcribe_audio
from bots.models import Participant, Utterance, Recording

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

class ScreenAndAudioRecorder:
    def __init__(self, file_location):
        self.file_location = file_location
        self.ffmpeg_proc = None
        self.screen_dimensions = (1920, 1080)

    def start_recording(self, display_var, virt_cable_token):
        logger.info(
            f"Starting screen recorder for display {display_var} with dimensions {self.screen_dimensions} and file location {self.file_location}")
        # ffmpeg_cmd = ["ffmpeg", "-y", "-thread_queue_size", "4096", "-framerate", "30", "-video_size", f"{self.screen_dimensions[0]}x{self.screen_dimensions[1]}", "-f", "x11grab", "-draw_mouse", "0", "-probesize", "32", "-i", display_var, "-thread_queue_size", "4096", "-f", "pulse", "-i", "default", "-vf", "crop=1920:1080:10:10", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-g", "30", "-c:a", "aac", "-strict", "experimental", "-b:a", "128k", self.file_location]
        # ffmpeg_cmd = ["ffmpeg", "-y", "-thread_queue_size", "4096", "-framerate", "30", "-video_size", f"1280x720", "-f", "x11grab", "-draw_mouse", "0", "-probesize", "32", "-i", ":0.0", "-thread_queue_size", "4096", "-f", "pulse", "-i", "default", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-g", "30", "-c:a", "aac", "-strict", "experimental", "-b:a", "128k", self.file_location]
        # ffmpeg_cmd = ["ffmpeg", "-y", "-thread_queue_size", "4096", "-framerate", "30", "-video_size",
        #               f"1920x1080", "-f", "x11grab", "-draw_mouse", "0",
        #               "-probesize", "32", "-i", ":0", "-thread_queue_size", "4096", "-f", "pulse", "-vf", "crop=1920:1080:10:10", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt",
        #               "yuv420p", "-g", "30", "-c:a", "aac", "-strict", "experimental", "-b:a", "128k",
        #               self.file_location]
        # "-f", "pulse",

        # subprocess.run([
        #     "", "-D", "--exit-idle-time=-1", "--system"
        # ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # subprocess.Popen([
        #     "pactl", "load-module", "module-null-sink", f"sink_name={virt_cable_token}"
        # ])

        logger.info(f"Start montoring on: {virt_cable_token} token")

        # audio and video
        # ffmpeg_cmd = [
        #     "ffmpeg", "-y",
        #     "-thread_queue_size", "4096",
        #     "-framerate", "30",
        #     "-video_size", f"{self.screen_dimensions[0]}x{self.screen_dimensions[1]}",
        #     "-f", "x11grab",
        #     "-draw_mouse", "0",
        #     "-probesize", "32",
        #     "-i", display_var,
        #     "-ac", "2",
        #     "-ar", "44100",
        #     "-f", "pulse",
        #     "-i", f"{virt_cable_token}.monitor",
        #     "-vf", "crop=1920:1080:10:10",
        #     "-c:v", "libx264",
        #     "-preset", "ultrafast",
        #     "-pix_fmt", "yuv420p",
        #     "-g", "30",
        #     "-c:a", "aac",
        #     "-strict", "experimental",
        #     "-b:a", "128k",
        #     self.file_location
        # ]

        # audio only
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-thread_queue_size", "4096",
            "-f", "pulse",
            "-ac", "2",
            "-ar", "44100",
            "-i", f"{virt_cable_token}.monitor",
            "-c:a", "aac",
            "-b:a", "128k",
            self.file_location
        ]

        logger.info(f"Starting FFmpeg command: {' '.join(ffmpeg_cmd)}")
        self.ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # self.stop_recording()

    def stop_recording(self):
        if not self.ffmpeg_proc:
            return
        self.ffmpeg_proc.terminate()
        self.ffmpeg_proc.wait()
        logger.info(
            f"Stopped debug screen recorder for display with dimensions {self.screen_dimensions} and file location {self.file_location}")

    def get_seekable_path(self, path):
        """
        Transform a file path to include '.seekable' before the extension.
        Example: /tmp/file.webm -> /tmp/file.seekable.webm
        """
        base, ext = os.path.splitext(path)
        return f"{base}.seekable{ext}"

    def cleanup(self):
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

        transcribe_audio(input_path)

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
