class ProcessingError(Exception):
    """Something went wrong while processing a recording."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class TranscriptionError(ProcessingError):
    def __init__(self, message="Could not transcribe the audio."):
        super().__init__("transcription_failed", message)
