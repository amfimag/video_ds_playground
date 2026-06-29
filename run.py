#!/usr/bin/env python3
"""
Точка входа для запуска пайплайна из командной строки.

Использование:
    # Полный пайплайн
    python run.py --config config/default_pipeline.yaml --video data/raw_videos/sample.mp4

    # Пропустить уже выполненные этапы (использовать кеш)
    python run.py --config config/default_pipeline.yaml --video data/raw_videos/sample.mp4 \\
        --skip fetch,audio_extract

    # Показать список зарегистрированных этапов и моделей
    python run.py --list

    # Запустить только указанные этапы
    python run.py --config config/default_pipeline.yaml --video ... \\
        --only audio_extract,vad,transcription
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Video DS Playground — запуск пайплайна обработки видео",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--config", "-c", help="Путь к YAML-конфигурации")
    parser.add_argument("--video", "-v", help="Путь к видеофайлу или облачный URI")
    parser.add_argument("--skip", help="Этапы для пропуска (через запятую): fetch,audio_extract")
    parser.add_argument("--only", help="Запустить только эти этапы (через запятую)")
    parser.add_argument("--output", "-o", help="Сохранить результат в JSON-файл")
    parser.add_argument("--list", action="store_true", help="Показать доступные этапы и модели")
    parser.add_argument("--debug", action="store_true", help="Подробное логирование")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Регистрируем все компоненты
    import src.stages  # noqa
    import src.models  # noqa

    if args.list:
        from src.core.registry import list_stages, list_models
        print("\n📦 Зарегистрированные ЭТАПЫ:")
        for s in list_stages():
            print(f"  • {s}")
        print("\n🤖 Зарегистрированные МОДЕЛИ:")
        for m in list_models():
            print(f"  • {m}")
        print()
        return

    if not args.config:
        parser.error("Укажите --config (или --list для просмотра компонентов)")
    if not args.video:
        parser.error("Укажите --video")

    if not Path(args.config).exists():
        log.error(f"Конфиг не найден: {args.config}")
        sys.exit(1)

    from src.core.pipeline import Pipeline

    pipeline = Pipeline(args.config)

    # Фильтрация этапов по --only
    if args.only:
        only_stages = [s.strip() for s in args.only.split(",")]
        pipeline.stages = [s for s in pipeline.stages if s.name in only_stages]
        log.info(f"Активные этапы: {[s.name for s in pipeline.stages]}")

    skip_stages = [s.strip() for s in args.skip.split(",")] if args.skip else []

    log.info(pipeline.describe())
    load_dotenv()

    try:
        result = pipeline.run(args.video, skip_stages=skip_stages)
    except Exception as e:
        log.error(f"Пайплайн завершился с ошибкой: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Вывод ключевых результатов
    print("\n" + "=" * 55)
    print("РЕЗУЛЬТАТЫ")
    print("=" * 55)
    if "metrics" in result:
        m = result["metrics"]
        print(f"SNR:           {m.get('snr_db', 'N/A')} дБ")
        print(f"Доля речи:     {m.get('speech_ratio', 'N/A')}")
    if "transcription_model" in result:
        print(f"Модель:        {result['transcription_model']}")
    if "transcription" in result:
        preview = result["transcription"][:200].replace("\n", " ")
        print(f"Транскрипция:  {preview}...")
    if "postprocess_stats" in result:
        st = result["postprocess_stats"]
        print(f"Удалено фрагм: {st.get('removed_segments', 0)} / {st.get('total_segments', 0)}")
    if "num_speakers" in result:
        print(f"Спикеров:      {result['num_speakers']}")

    # Генерация отчёта
    from src.utils.report_generator import generate_report
    report_path = generate_report(result)
    print(f"\n📄 Отчёт: {report_path}")

    # Сохранение JSON
    if args.output:
        serializable = {}
        for k, v in result.items():
            try:
                json.dumps(v)
                serializable[k] = v
            except (TypeError, ValueError):
                pass
        Path(args.output).write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"💾 JSON: {args.output}")

    print()


if __name__ == "__main__":
    main()
