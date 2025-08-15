import streamlit as st
import whisper
import tempfile
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

# Load Whisper model
@st.cache_resource
def load_model():
    return whisper.load_model("small")

model = load_model()

st.title("🎬 Auto Two-Word Captions")
st.write("Upload a video and get instant two-word captions in Montserrat Semi-Bold.")

uploaded_file = st.file_uploader("Upload your video", type=["mp4", "mov", "mkv"])

if uploaded_file:
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(uploaded_file.read())
        video_path = tmp.name

    st.video(video_path)

    if st.button("Generate Captions"):
        with st.spinner("Transcribing with Whisper..."):
            result = model.transcribe(video_path)
        
        segments = result["segments"]
        words = []
        for seg in segments:
            words.extend(seg["text"].strip().split())

        # Break into 2-word chunks
        chunks = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]

        # Make captions folder
        captions_dir = tempfile.mkdtemp()

        font_path = "montserrat.ttf"  # Upload Montserrat Semi-Bold font in repo
        font = ImageFont.truetype(font_path, 48)

        # Create PNG for each chunk
        for idx, text in enumerate(chunks):
            img = Image.new("RGBA", (1280, 200), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            w, h = draw.textsize(text, font=font)
            draw.text(((1280-w)/2, (200-h)/2), text, font=font, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0,0,0,255))
            img.save(os.path.join(captions_dir, f"{idx}.png"))

        # Generate FFmpeg commands to overlay each caption
        filter_complex = ""
        time_per_caption = len(segments) / len(chunks) * 2  # Rough timing estimate

        for idx in range(len(chunks)):
            start_time = idx * time_per_caption
            end_time = start_time + time_per_caption
            filter_complex += f"[0:v][{idx+1}:v] overlay=(W-w)/2:H-250:enable='between(t,{start_time},{end_time})'[tmp{idx}];"
            if idx < len(chunks)-1:
                filter_complex = filter_complex.replace(f"[tmp{idx}]", f"[0:v]" if idx == 0 else f"[tmp{idx-1}]")

        inputs = ["-i", video_path]
        for idx in range(len(chunks)):
            inputs += ["-i", os.path.join(captions_dir, f"{idx}.png")]

        output_path = os.path.join(tempfile.gettempdir(), "captioned_video.mp4")

        ffmpeg_cmd = ["ffmpeg"] + inputs + [
            "-filter_complex", filter_complex.rstrip(";"),
            "-map", "0:a?", "-c:a", "copy", output_path
        ]

        subprocess.run(ffmpeg_cmd, check=True)

        st.success("✅ Captions added!")
        st.video(output_path)
        with open(output_path, "rb") as f:
            st.download_button("Download Captioned Video", f, file_name="captioned.mp4")