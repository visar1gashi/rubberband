import base64, io, os, tempfile, json, numpy as np
import soundfile as sf
import librosa, subprocess
import runpod

SR = 48000  # output sample rate

def b64mp3_to_wav_array(b64, sr=SR):
    data = base64.b64decode(b64)
    y, _ = librosa.load(io.BytesIO(data), sr=sr, mono=True)
    return y, sr

def write_wav(path, y, sr=SR):
    sf.write(path, y, sr, format='WAV', subtype='PCM_16')

def read_wav(path):
    y, sr = sf.read(path, always_2d=False)
    if y.ndim > 1: y = y[:,0]
    return y, sr

def rubberband_stretch_file(in_wav, out_wav, ratio):
    # ratio > 1.0 => faster (shorter). Example: 2.0s -> 1.5s needs 2.0/1.5 = 1.333
    subprocess.run(['rubberband', '-t', f'{ratio}', in_wav, out_wav], check=True)

def handler(event):
    """
    Expects event['input'] with:
      {
        "audioChunks": [ base64_mp3, ... ],
        "contentType": "audio/mp3",
        "alignment": { "segments": [{ "start": float, "end": float, "text": str }], "words": [...]? }
      }
    """
    inp = event.get('input', {})
    chunks = inp.get('audioChunks') or []
    alignment = inp.get('alignment') or {}
    segments = alignment.get('segments') or []

    if not chunks or not segments or len(chunks) != len(segments):
        return { "error": "Segment audio mismatch" }

    out_arrays = []
    with tempfile.TemporaryDirectory() as td:
        for i, b64 in enumerate(chunks):
            # decode mp3 chunk to WAV array
            y, sr = b64mp3_to_wav_array(b64, sr=SR)
            src_dur = len(y) / sr
            tgt_dur = max(0.01, float(segments[i]['end']) - float(segments[i]['start']))
            ratio = max(0.25, min(4.0, src_dur / tgt_dur))

            in_path  = os.path.join(td, f'in_{i}.wav')
            out_path = os.path.join(td, f'out_{i}.wav')
            write_wav(in_path, y, sr)
            rubberband_stretch_file(in_path, out_path, ratio)
            y_st, _ = read_wav(out_path)
            out_arrays.append(y_st.astype(np.float32))

    if out_arrays:
        y_out = np.concatenate(out_arrays)
    else:
        y_out = np.zeros(1, dtype=np.float32)

    buf = io.BytesIO()
    sf.write(buf, y_out, SR, format='WAV', subtype='PCM_16')
    audio_b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return { "audioBase64": audio_b64, "contentType": "audio/wav" }

runpod.serverless.start({"handler": handler})
