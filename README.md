# DeepDub -- AI Video Dubbing and Lip-Sync Pipeline

A distributed, end-to-end AI pipeline that translates and dubs a source video into a target language with photorealistic lip synchronization. The system runs entirely on Google Colab free-tier GPUs, using a microservices architecture to work around hardware memory constraints.

---

## Result Comparison

<table>
  <tr>
    <th align="center">Input &mdash; test.mp4</th>
    <th align="center">Output &mdash; final_output_lipsynced.mp4</th>
  </tr>
  <tr>
    <td align="center">
      <video src="test.mp4" width="420" controls></video>
    </td>
    <td align="center">
      <video src="final_output_lipsynced.mp4" width="420" controls></video>
    </td>
  </tr>
  <tr>
    <td align="center">Original English video with native speaker audio and unmodified facial motion.</td>
    <td align="center">Arabic-dubbed video with cloned voice and lip movements re-rendered by LatentSync.</td>
  </tr>
</table>

---

## Project Structure

```
Lip_sync/
|
|-- Prepare models/             # Phase 1: model download and Drive caching notebooks
|   |-- first_stage.ipynb       # Demucs audio separation -- no GPU required
|   |-- stage_two.ipynb         # Whisper large-v3 + Qwen model download and caching
|   +-- stage_three.ipynb       # LatentSync checkpoint download (latentsync_unet.pt)
|
|-- inference/                  # Phase 2: microservice inference notebooks
|   |-- Audio_Processing_inference.ipynb   # Stage 1: Demucs + noise reduction + ngrok
|   |-- Whisper_&_Qwen.ipynb               # Stage 2: Whisper STT + Qwen LLM + ngrok
|   |-- XTTS.ipynb                         # Stage 3: XTTS v2 voice cloning + ngrok
|   +-- Latent_sync_inference.ipynb        # Stage 4: LatentSync rendering + ngrok
|
|-- inference.html              # Frontend: DeepDub web UI
|-- styles.css                  # Frontend: UI stylesheet
|-- app.js                      # Frontend: orchestration logic, HTTP client for all 4 microservices
|
|-- test.mp4                    # Input: original English video
+-- final_output_lipsynced.mp4  # Output: Arabic-dubbed, lip-synced result
```

---

## Why a Distributed Microservices Architecture

Google Colab free tier provides approximately 15 GB of GPU VRAM on a T4 instance. Loading all models simultaneously -- Whisper large-v3 (~3 GB), Qwen LLM (~14 GB), XTTS v2 (~1.8 GB), and LatentSync (~3.2 GB) -- would exceed this limit by a wide margin and trigger an out-of-memory crash.

The solution is to split the pipeline into four independent microservices, each running in a separate Colab notebook with its own runtime and dedicated GPU. Each microservice:

1. Loads only the models it requires into VRAM.
2. Starts a FastAPI server bound to localhost.
3. Exposes that server to the internet via an ngrok tunnel.
4. Serves exactly one REST API endpoint to the frontend.

The frontend (`app.js`) calls each microservice in strict sequence, passing outputs from one stage as inputs to the next. This design means the combined pipeline uses only as much VRAM as a single stage at any given moment, while still producing a fully automated, end-to-end result.

---

## Phase 1: Preparing and Caching the Models

Before running any inference, the three notebooks in `Prepare models/` must be executed once to download and persist each model to Google Drive. This is a one-time step. On all subsequent runs the inference notebooks read directly from Drive, bypassing Hugging Face Hub and avoiding repeated multi-gigabyte downloads.

### first_stage.ipynb -- Audio Separation Setup

- Installs `demucs`, `noisereduce`, `librosa`, and `soundfile`.
- Mounts Google Drive and creates the project directory at `/content/drive/MyDrive/Video_Translation_Project/Stage_1`.
- Runs a test pass on a sample video to confirm the Demucs `htdemucs` model downloads and separates vocals correctly.
- Outputs `Silent_<video>.mp4`, `Clean_Vocals.wav`, and `Background_Noise.wav` to Drive.
- Does not require a GPU.

### stage_two.ipynb -- Whisper and Qwen Model Caching

- Sets the environment variables `HF_HOME` and `XDG_DATA_HOME` to point at a `Models_Cache` directory inside Google Drive before any import, redirecting all Hugging Face model downloads to persistent storage.
- Downloads and caches **Whisper large-v3** via `faster-whisper`.
- Downloads and caches **Qwen** (the translation LLM) using `transformers` `AutoModelForCausalLM`.
- Requires a GPU runtime (T4).

### stage_three.ipynb -- LatentSync Checkpoint Download

- Clones the LatentSync repository.
- Downloads the primary model checkpoint `latentsync_unet.pt` (~3.2 GB) from Hugging Face and writes it to Drive under `Video_Translation_Project/Models_Cache`.
- Confirms the download with a progress bar output (100% completion verified in notebook outputs).
- Requires a GPU runtime (T4).

---

## Phase 2: Inference Pipeline

Each inference notebook starts a FastAPI microservice and exposes it through ngrok. The four public URLs produced are pasted into `app.js` as `API_STAGE1` through `API_STAGE4`, and the web UI drives the rest automatically.

### Stage 1 -- Audio Processing Microservice

**Notebook:** `inference/Audio_Processing_inference.ipynb`

- Accepts a raw video file via `POST /process_stage1`.
- Uses `ffmpeg` to strip the audio track and produce a silent video.
- Extracts audio at 16 kHz mono, runs Demucs `htdemucs` in two-stem mode to isolate vocals from background noise, then applies `noisereduce` spectral subtraction for a clean vocal track.
- Serves both files at `GET /get_silent_video` and `GET /get_clean_vocals`.
- Exposes the FastAPI server via ngrok on port 8001.

### Stage 2 -- Transcription and Translation Microservice

**Notebook:** `inference/Whisper_&_Qwen.ipynb`

- Accepts a JSON payload with `vocals_url` pointing at the Stage 1 ngrok endpoint via `POST /process_stage2_from_url`.
- Downloads the clean vocals over HTTP (with ngrok browser-warning bypass header).
- Transcribes speech to English text using **Whisper large-v3** with `beam_size=5`.
- Translates the English transcript to Arabic using **Qwen** via a system prompt that enforces Arabic-only output (no Chinese characters, no explanations).
- Post-processes the LLM output with regex to strip stray Unicode CJK characters and normalize whitespace.
- Returns a JSON object with both `english_text` and `arabic_text`.
- Exposes the FastAPI server via ngrok on port 8002.

### Stage 3 -- Voice Synthesis Microservice

**Notebook:** `inference/XTTS.ipynb`

- Runs inside a Python 3.10 environment (required by the Coqui TTS library).
- Accepts a JSON payload with `arabic_text` and `vocals_url` via `POST /process_stage3_tts`.
- Downloads the clean English vocals from Stage 1 to use as a **voice cloning reference**: XTTS v2 extracts a speaker embedding from the source speaker's voice.
- Synthesizes the Arabic text as speech in the original speaker's voice using **XTTS v2** (`TTS==0.22.0`).
- Serves the generated Arabic audio at `GET /get_arabic_audio`.
- Exposes the FastAPI server via ngrok on port 8003.

### Stage 4 -- Lip-Sync Rendering Microservice

**Notebook:** `inference/Latent_sync_inference.ipynb`

- Accepts a JSON payload with `silent_video_url` and `arabic_audio_url` via `POST /process_stage3_from_urls`.
- Downloads the silent video from Stage 1 and the synthesized Arabic audio from Stage 3.
- Runs **LatentSync**, a latent diffusion model that re-renders the mouth region of the speaker frame-by-frame to match the phonemes of the new Arabic audio track.
- Uses the cached `latentsync_unet.pt` checkpoint (~3.2 GB) loaded from Google Drive.
- Merges the rendered video with the Arabic audio using `ffmpeg`.
- Serves the final video at `GET /get_final_video`.
- Exposes the FastAPI server via ngrok on port 8004.

---

## End-to-End Pipeline Flow

```
User uploads test.mp4 via inference.html
          |
          v
  [Stage 1 - Colab Runtime A]
  Audio Processing Microservice  (port 8001, ngrok tunnel)
  Demucs htdemucs  -->  Silent Video  +  Clean Vocals (16kHz mono, noise-reduced)
          |
          v
  [Stage 2 - Colab Runtime B]
  Transcription and Translation Microservice  (port 8002, ngrok tunnel)
  Whisper large-v3  -->  English transcript
  Qwen LLM          -->  Arabic translation
          |
          v
  [Stage 3 - Colab Runtime C]
  Voice Synthesis Microservice  (port 8003, ngrok tunnel)
  XTTS v2  (speaker embedding extracted from source vocals)
           -->  Arabic speech in original speaker voice
          |
          v
  [Stage 4 - Colab Runtime D]
  Lip-Sync Rendering Microservice  (port 8004, ngrok tunnel)
  LatentSync UNet  -->  Re-rendered mouth region per frame
  FFmpeg mux       -->  final_output_lipsynced.mp4
```

---

## Frontend

The web UI (`inference.html` + `styles.css` + `app.js`) is a static HTML page that runs in any browser without a backend server.

`app.js` defines the four ngrok base URLs at the top of the file:

```js
const API_STAGE1 = 'https://<your-stage1-ngrok-url>';
const API_STAGE2 = 'https://<your-stage2-ngrok-url>';
const API_STAGE3 = 'https://<your-stage3-ngrok-url>';
const API_STAGE4 = 'https://<your-stage4-ngrok-url>';
```

When the user uploads a video and clicks **Initialize DeepDub**, the `runPipeline()` function calls each stage in sequence, updating visual status indicators for each pipeline node and rendering intermediate outputs -- silent video preview, transcription text, Arabic audio player -- as they become available. The final lip-synced video is displayed inline on completion.

The frontend also includes a guard against ngrok's browser interception page: if any response returns `text/html` instead of the expected media type, or if the downloaded file is smaller than 1 KB, the pipeline halts and alerts the user.

---

## Model Registry

| Model | Version | Approximate Size | Cached Location |
|---|---|---|---|
| Demucs htdemucs | htdemucs | ~85 MB | Runtime /content (auto-downloaded) |
| Whisper | large-v3 | ~3.1 GB | Drive/Models_Cache |
| Qwen LLM | configured variant | ~3.5 GB | Drive/Qwen_Model_Files |
| XTTS | v2 (TTS 0.22.0) | ~1.8 GB | Drive/Models_Cache |
| LatentSync UNet | latentsync_unet.pt | ~3.2 GB | Drive/Models_Cache |

---

## Steps to Reproduce

1. Run `Prepare models/first_stage.ipynb` on any Colab runtime (no GPU needed). Verify the silent video and clean vocals appear in Drive.
2. Run `Prepare models/stage_two.ipynb` on a Colab T4 GPU runtime. Wait for Whisper and Qwen to write fully to `Models_Cache` in Drive.
3. Run `Prepare models/stage_three.ipynb` on a Colab T4 GPU runtime. Confirm `latentsync_unet.pt` downloads to 100% completion in the progress bar.
4. Open four separate Colab sessions and run each inference notebook in a different runtime simultaneously:
   - `inference/Audio_Processing_inference.ipynb`
   - `inference/Whisper_&_Qwen.ipynb`
   - `inference/XTTS.ipynb`
   - `inference/Latent_sync_inference.ipynb`
5. Copy the four ngrok public URLs printed at startup by each notebook.
6. Paste them into `app.js` as `API_STAGE1` through `API_STAGE4`.
7. Open `inference.html` in a browser, upload `test.mp4`, and click **Initialize DeepDub**.
8. The pipeline completes sequentially. The final lip-synced video appears in the browser.

---

## Technologies Used

| Component | Technology |
|---|---|
| Audio source separation | Demucs (htdemucs two-stem mode) |
| Noise reduction | noisereduce spectral subtraction |
| Speech-to-text | faster-whisper Whisper large-v3 |
| Machine translation | Qwen (AutoModelForCausalLM, float16) |
| Voice cloning and TTS | Coqui XTTS v2 |
| Lip-sync rendering | LatentSync (latent diffusion UNet) |
| Video muxing | FFmpeg |
| Microservice framework | FastAPI + Uvicorn |
| Tunneling | ngrok (pyngrok) |
| Model persistence | Google Drive (HF_HOME and XDG_DATA_HOME redirect) |
| Frontend | Vanilla HTML, CSS, JavaScript |
