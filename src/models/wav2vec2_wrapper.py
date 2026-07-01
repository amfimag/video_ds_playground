"""
Обёртка для Wav2Vec2 (HuggingFace Transformers).

Установка:
    pip install transformers torchaudio

Задание (docs/tasks/03_transcription.md):
    Реализуйте метод load() и predict() используя подсказки ниже.
"""
from __future__ import annotations

import time
from typing import Any

from src.core.base import ModelWrapper
from src.core.registry import register_model


@register_model("wav2vec2-xlsr-ru")
@register_model("wav2vec2-ru-golos")
class Wav2Vec2Wrapper(ModelWrapper):
    """
    CTC-модель Wav2Vec2 для транскрибации.

    Предобученные модели для русского языка:
        - bond005/wav2vec2-large-ru-golos       (хорошая, рекомендуется)
        - jonatasgrosman/wav2vec2-large-xlsr-53-russian
        - facebook/wav2vec2-large-xlsr-53       (многоязычная)

    Требования к аудио:
        - float32 тензор формы [1, T]
        - sample_rate = 16000
        - нормализован (значения примерно в диапазоне -1...+1)
    """

    MODEL_NAMES = {
        "wav2vec2-xlsr-ru": "jonatasgrosman/wav2vec2-large-xlsr-53-russian",
        "wav2vec2-ru-golos": "bond005/wav2vec2-large-ru-golos",
    }

    def load(
        self,
        model_name: str = "wav2vec2-xlsr-ru",
        device: str = "cpu",
        **kwargs,
    ) -> None:
        """
        TODO: Реализуйте загрузку модели и процессора.

        Подсказка:
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
            import torch

            hf_name = self.MODEL_NAMES.get(model_name, model_name)
            self.processor = Wav2Vec2Processor.from_pretrained(hf_name)
            self.model = Wav2Vec2ForCTC.from_pretrained(hf_name)
            self.model.to(device)
            self.model.eval()
            self._device = device
        """
        from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
        hf_name = self.MODEL_NAMES.get(model_name,model_name)
        self.processor = Wav2Vec2Processor.from_pretrained(hf_name)
        self.model = Wav2Vec2ForCTC.from_pretrained(hf_name)
        self.model.to(device)
        self.model.eval()
        self._device = device
        # raise NotImplementedError(
        #     "Реализуйте метод load().\n"
        #     "Смотрите подсказку выше и задание в docs/tasks/03_transcription.md"
        # )

    def predict(self, audio_path: str, **kwargs) -> dict:
        """
        TODO: Реализуйте инференс.

        Шаги:
        1. Загрузить аудио: torchaudio.load(audio_path)
        2. Если нужно — ресемплировать до 16000 Гц
        3. Нормализовать через processor
        4. Получить логиты: model(**inputs).logits
        5. Декодировать: processor.batch_decode(predicted_ids)
        6. Вернуть {"text": str, "segments": [], "language": "ru"}

        Подсказка для шагов 3–5:
            import torchaudio, torch

            waveform, sr = torchaudio.load(audio_path)
            if sr != 16000:
                resampler = torchaudio.transforms.Resample(sr, 16000)
                waveform = resampler(waveform)

            inputs = self.processor(
                waveform.squeeze().numpy(),
                sampling_rate=16000,
                return_tensors="pt",
                padding=True
            )
            with torch.no_grad():
                logits = self.model(**inputs.to(self._device)).logits
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = self.processor.batch_decode(predicted_ids)[0]
        """
        import torch, torchaudio
        # 1
        waveform, sample_rate = torchaudio.load(audio_path)
        # 2
        target_sample_rate = self.processor.feature_extractor.sampling_rate
        # target_sample_rate = 16000
        if sample_rate != target_sample_rate:
            transform = torchaudio.transforms.Resample(sample_rate, target_sample_rate)
            waveform = transform(waveform)
        # 3
        inputs = self.processor(
            waveform.squeeze().numpy(),
            sampling_rate=target_sample_rate,
            return_tensors='pt',
            padding=True
        )
        # 4
        # отключаем вычисление градиента
        with torch.no_grad():
            # получаем сырые предсказания
            logits = self.model(**inputs.to(self._device)).logits
        # 5 
        # получаем наиболее вероятные классы
        predicted_ids = torch.argmax(logits,-1)
        # преобразуем токены в понятный текст
        transcripts = self.processor.batch_decode(predicted_ids)[0]
        # 6
        result = {
            "text": transcripts, 
            "segments": [], 
            "language": "ru"
        }
        return result
        
        # raise NotImplementedError(
        #     "Реализуйте метод predict().\n"
        #     "Смотрите подсказку выше и задание в docs/tasks/03_transcription.md"
        # )
