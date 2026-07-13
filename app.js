const API_STAGE1 = 'https://pager-twiddling-submersed.ngrok-free.dev';
const API_STAGE2 = 'https://anteater-purchase-turtle.ngrok-free.dev';
const API_STAGE3 = 'https://generic-audition-chaos.ngrok-free.dev';
const API_STAGE4 = 'https://unjudicial-consciencelessly-isela.ngrok-free.dev';

const stageDefinitions = {
    1: { card: 'card1', status: 'status1', node: '1' },
    2: { card: 'card2', status: 'status2', node: '2' },
    3: { card: 'card3', status: 'status3', node: '3' },
    4: { card: 'card4', status: 'status4', node: '4' }
};

function updateStatus(stage, state, text) {
    const definition = stageDefinitions[stage];
    const statusElement = document.getElementById(definition.status);
    const cardElement = document.getElementById(definition.card);
    const nodeElement = document.querySelector(`.pipeline-node[data-stage="${definition.node}"]`);

    statusElement.className = `status ${state}`;
    statusElement.innerText = text;

    cardElement.classList.toggle('active', state === 'processing' || state === 'success');
    if (nodeElement) {
        nodeElement.style.borderColor = state === 'processing'
            ? 'rgba(255, 205, 74, 0.5)'
            : state === 'success'
                ? 'rgba(45, 227, 141, 0.55)'
                : state === 'error'
                    ? 'rgba(255, 107, 138, 0.55)'
                    : 'rgba(255,255,255,0.08)';
        nodeElement.style.boxShadow = state === 'processing'
            ? '0 0 0 1px rgba(255, 205, 74, 0.12), 0 20px 30px rgba(0, 0, 0, 0.22)'
            : state === 'success'
                ? '0 0 0 1px rgba(45, 227, 141, 0.12), 0 20px 30px rgba(0, 0, 0, 0.22)'
                : state === 'error'
                    ? '0 0 0 1px rgba(255, 107, 138, 0.12), 0 20px 30px rgba(0, 0, 0, 0.22)'
                    : 'none';
    }
}

async function fetchMediaAndGetUrl(url, bypassHeader) {
    const response = await fetch(url, { headers: bypassHeader });

    if (!response.ok) {
        throw new Error(`Fetch failed with status: ${response.status}`);
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('text/html')) {
        alert(`NGROK BLOCK DETECTED!\nNgrok is blocking the file at:\n${url}`);
        throw new Error('Ngrok HTML Block');
    }

    const blob = await response.blob();
    if (blob.size < 1000) {
        alert(`CORRUPTED FILE!\nThe file downloaded from ${url} is almost empty.`);
        throw new Error('Corrupted or empty media file');
    }

    return URL.createObjectURL(blob);
}

function wirePreview() {
    const input = document.getElementById('mainVideo');
    const button = document.getElementById('startBtn');

    input.addEventListener('change', () => {
        const hasFile = Boolean(input.files && input.files[0]);
        button.disabled = !hasFile;
    });
}

async function runPipeline() {
    const videoFile = document.getElementById('mainVideo').files[0];
    if (!videoFile) {
        alert('Please upload a video file.');
        return;
    }

    const button = document.getElementById('startBtn');
    button.disabled = true;
    button.innerText = 'DeepDub running...';

    const bypassHeader = { 'ngrok-skip-browser-warning': 'true' };

    try {
        updateStatus(1, 'processing', 'Separating audio...');
        const stage1Form = new FormData();
        stage1Form.append('video', videoFile);

        const stage1Response = await fetch(`${API_STAGE1}/process_stage1`, {
            method: 'POST',
            headers: bypassHeader,
            body: stage1Form
        });

        if (!stage1Response.ok) {
            throw new Error('Stage 1 Server Failed');
        }

        const silentVideoUrl = await fetchMediaAndGetUrl(`${API_STAGE1}/get_silent_video`, bypassHeader);
        const cleanVocalsUrl = await fetchMediaAndGetUrl(`${API_STAGE1}/get_clean_vocals`, bypassHeader);

        document.getElementById('outSilentVideo').src = silentVideoUrl;
        document.getElementById('outCleanAudio').src = cleanVocalsUrl;
        updateStatus(1, 'success', 'Completed');

        updateStatus(2, 'processing', 'Transcribing and translating...');
        const cleanVocalsServerUrl = `${API_STAGE1}/get_clean_vocals`;

        const stage2Response = await fetch(`${API_STAGE2}/process_stage2_from_url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...bypassHeader },
            body: JSON.stringify({ vocals_url: cleanVocalsServerUrl })
        });

        if (!stage2Response.ok) {
            throw new Error('Stage 2 Server Failed');
        }

        const stage2Data = await stage2Response.json();
        document.getElementById('txtEnglish').innerText = stage2Data.english_text;
        document.getElementById('txtArabic').innerText = stage2Data.arabic_text;
        updateStatus(2, 'success', 'Completed');

        updateStatus(3, 'processing', 'Synthesizing target voice...');
        const stage3Response = await fetch(`${API_STAGE3}/process_stage3_tts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...bypassHeader },
            body: JSON.stringify({
                arabic_text: stage2Data.arabic_text,
                vocals_url: cleanVocalsServerUrl
            })
        });

        if (!stage3Response.ok) {
            throw new Error('Stage 3 Server Failed');
        }

        const arabicAudioUrl = await fetchMediaAndGetUrl(`${API_STAGE3}/get_arabic_audio`, bypassHeader);
        document.getElementById('outArabicAudio').src = arabicAudioUrl;
        updateStatus(3, 'success', 'Completed');

        updateStatus(4, 'processing', 'Rendering final lip sync...');
        const stage4Response = await fetch(`${API_STAGE4}/process_stage3_from_urls`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...bypassHeader },
            body: JSON.stringify({
                silent_video_url: `${API_STAGE1}/get_silent_video`,
                arabic_audio_url: `${API_STAGE3}/get_arabic_audio`
            })
        });

        if (!stage4Response.ok) {
            throw new Error('Stage 4 Server Failed');
        }

        const finalVideoUrl = await fetchMediaAndGetUrl(`${API_STAGE4}/get_final_video`, bypassHeader);
        document.getElementById('outFinalVideo').src = finalVideoUrl;
        updateStatus(4, 'success', 'Completed Successfully');
    } catch (error) {
        console.error(error);
        updateStatus(1, 'error', 'Halted');
        updateStatus(2, 'error', 'Halted');
        updateStatus(3, 'error', 'Halted');
        updateStatus(4, 'error', 'Halted');
    } finally {
        button.disabled = false;
        button.innerText = 'Initialize DeepDub';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const button = document.getElementById('startBtn');
    button.disabled = true;
    button.addEventListener('click', runPipeline);
    wirePreview();
});
