import sys
import types
import tempfile
from pathlib import Path

# Provide a dummy sounddevice module to avoid PortAudio dependency
sd_stub = types.ModuleType('sounddevice')
sd_stub.default = types.SimpleNamespace(device=None, samplerate=None)
sd_stub.rec = lambda *args, **kwargs: None
sd_stub.wait = lambda *args, **kwargs: None
sd_stub.playrec = lambda *args, **kwargs: None
sd_stub.play = lambda *args, **kwargs: None
sys.modules.setdefault('sounddevice', sd_stub)

from irma.session import RecordingSession


def test_save_and_load_rtype():
    session = RecordingSession(session_id='test', rtype='sweep')
    with tempfile.TemporaryDirectory() as tmpdir:
        metadata_file = Path(tmpdir) / 'metadata.yaml'
        session.save_metadata(metadata_file)
        loaded = RecordingSession.load_metadata(metadata_file)
        assert loaded.rtype == session.rtype
