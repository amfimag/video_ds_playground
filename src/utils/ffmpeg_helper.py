"""
Вспомогательные функции для работы с ffmpeg.

Задание (docs/tasks/02_audio_extract.md):
    Реализуйте функции extract_audio() и get_media_info().
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def extract_audio(
    video_path: str,
    output_path: str,
    sample_rate: int = 16000,
    channels: int = 1,
    audio_format: str = "wav",
) -> str:
    """
    Извлекает аудио из видеофайла с помощью ffmpeg.

    Args:
        video_path:   Путь к видеофайлу.
        output_path:  Путь для сохранения аудио.
        sample_rate:  Частота дискретизации (16000 для ASR).
        channels:     Количество каналов (1 = моно).
        audio_format: Формат выходного файла (wav, flac).

    Returns:
        Путь к созданному аудиофайлу.

    TODO: Реализуйте эту функцию.

    Подсказка (вариант 1 — через subprocess):
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn",                     # без видео
            "-acodec", "pcm_s16le",    # PCM 16-bit
            "-ar", str(sample_rate),
            "-ac", str(channels),
            "-y",                      # перезаписать если существует
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    Подсказка (вариант 2 — через ffmpeg-python):
        import ffmpeg
        (
            ffmpeg
            .input(video_path)
            .output(output_path, acodec="pcm_s16le", ar=sample_rate, ac=channels)
            .overwrite_output()
            .run(quiet=True)
        )
    """
    if Path(output_path).exists():
        return output_path

    # --- Ваш код здесь ---   
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-y",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        print(e)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg завершился с ошибкой:\n{result.stderr}"
        )
    return output_path


def get_media_info(file_path: str) -> dict:
    """
    Получает метаданные медиафайла через ffprobe.

    Returns:
        dict с ключами: duration_sec, sample_rate, channels, format, bit_rate

    TODO: Дополните парсинг для извлечения оригинального кодека.

    Подсказка:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            file_path
        ]
        output = subprocess.check_output(cmd)
        info = json.loads(output)
        # info["streams"][0] — первый поток
        # info["format"]["duration"] — длительность
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        file_path,
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        info = json.loads(output)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {"error": "ffprobe недоступен или файл повреждён"}

    audio_stream = next(
        (s for s in info.get("streams", []) if s.get("codec_type") == "audio"),
        {}
    )
    fmt = info.get("format", {})

    return {
        "duration_sec": float(fmt.get("duration", 0)),
        "sample_rate": int(audio_stream.get("sample_rate", 0)),
        "channels": int(audio_stream.get("channels", 0)),
        "format": Path(file_path).suffix.lstrip("."),
        "codec": audio_stream.get("codec_name", "unknown"),
        "bit_rate": int(fmt.get("bit_rate", 0)),
        "size_bytes": int(fmt.get("size", 0)),
    }


def cut_audio(
    audio_path: str,
    output_path: str,
    start_sec: float,
    end_sec: float,
) -> str:
    """Нарезает аудио по временному интервалу."""
    cmd = [
        "ffmpeg", "-i", audio_path,
        "-ss", str(start_sec),
        "-to", str(end_sec),
        "-c", "copy",
        "-y", output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def apply_vad_cut(
    audio_path: str,
    speech_intervals: list[dict],
    output_path: str,
    sample_rate: int = 16000,
) -> str:
    """
    Создаёт аудио только из речевых сегментов (убирает тишину).
    Полезно для ускорения транскрибации.
    """
    import tempfile
    import os

    chunks = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for i, ivl in enumerate(speech_intervals):
            chunk_path = os.path.join(tmpdir, f"chunk_{i:04d}.wav")
            cut_audio(audio_path, chunk_path, ivl["start"], ivl["end"])
            chunks.append(chunk_path)

        if not chunks:
            return audio_path

        # Создаём список файлов для ffmpeg concat
        list_path = os.path.join(tmpdir, "concat.txt")
        with open(list_path, "w") as f:
            for chunk in chunks:
                f.write(f"file '{chunk}'\n")

        cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-ar", str(sample_rate), "-ac", "1",
            "-y", output_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    return output_path
