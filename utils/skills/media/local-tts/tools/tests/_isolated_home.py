"""Imported first by every test module: point LOCAL_TTS_HOME at a throwaway folder before local_tts
loads, so no test can read or delete the user's real voices, profiles or caches."""

import atexit
import os
import shutil
import tempfile

HOME = tempfile.mkdtemp(prefix="local-tts-test-home-")
os.environ["LOCAL_TTS_HOME"] = HOME
os.environ.pop("PRESENTER_TTS_HOME", None)
atexit.register(shutil.rmtree, HOME, ignore_errors=True)
