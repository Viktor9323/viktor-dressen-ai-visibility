#!/usr/bin/env python3
"""Подсчёт индексов AI Visibility Audit (методика Виктора Дрессена).

Использование: python3 score.py audit.json
Формат audit.json — см. references/scoring.md.
"""
import json
import sys

WEIGHTS = {
    "Карты": {
        "rating": 20, "reviews_volume": 15, "reviews_specificity": 5,
        "owner_replies": 10, "price_completeness": 10, "price_facts": 5,
        "description": 5, "features": 5, "categories": 10, "posts": 5,
        "trust": 5, "photos": 5,
    },
    "Алиса / Нейро": {
        "rating": 12, "reviews_volume": 8, "reviews_specificity": 10,
        "owner_replies": 4, "price_completeness": 8, "price_facts": 14,
        "description": 8, "features": 5, "categories": 6, "posts": 8,
        "trust": 7, "query_coverage": 10,
    },
    "ChatGPT / Perplexity": {
        "website": 25, "website_content": 15, "schema": 10,
        "web_findable": 15, "citations": 15, "nap": 5, "social_text": 5,
        "query_coverage": 10,
    },
}

LABELS = {
    "rating": "Рейтинг и число оценок",
    "reviews_volume": "Количество и свежесть отзывов",
    "reviews_specificity": "Конкретика в отзывах",
    "owner_replies": "Ответы владельца",
    "price_completeness": "Полнота прайса",
    "price_facts": "Факты в описаниях услуг",
    "description": "Описание организации",
    "features": "Особенности/атрибуты",
    "categories": "Рубрики",
    "posts": "Новости/экспертные посты",
    "trust": "Подтверждение владельцем, награды",
    "photos": "Фото",
    "website": "Собственный сайт",
    "website_content": "Контент сайта (прайс, FAQ)",
    "schema": "Разметка Schema.org",
    "web_findable": "Находится в веб-поиске",
    "citations": "Присутствие на площадках",
    "nap": "Единые название/адрес/телефон",
    "social_text": "Текстовые посты в соцсетях",
    "query_coverage": "Покрытие карты запросов",
}

VERDICT = [
    (3, "нейросеть почти не назовёт"),
    (6, "назовёт иногда, в общих запросах"),
    (8, "хорошие шансы"),
    (10, "сильный кандидат в рекомендации"),
]


def clamp(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, v))


def main(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    factors = {k: clamp(v) for k, v in data.get("factors", {}).items()}

    print(f"# {data.get('name', 'Организация')} — {data.get('city', '')}\n")
    losses = {}
    for index, weights in WEIGHTS.items():
        total = sum(weights.values())
        score = sum(w * factors.get(k, 0.0) for k, w in weights.items())
        score = score / total * 100
        if index.startswith("ChatGPT") and factors.get("website", 0.0) == 0:
            score = min(score, 30)
        ten = round(score / 10)
        verdict = next(t for lim, t in VERDICT if ten <= lim)
        print(f"{index}: {score:.0f}/100 → {ten}/10 ({verdict})")
        for k, w in weights.items():
            lost = w * (1 - factors.get(k, 0.0)) / total * 100
            losses[k] = max(losses.get(k, 0.0), lost)

    missing = [k for k in LABELS if k not in data.get("factors", {})]
    print("\nГлавные потери баллов (макс. по индексам):")
    for k, lost in sorted(losses.items(), key=lambda x: -x[1]):
        if lost >= 1:
            print(f"  -{lost:4.1f}  {LABELS.get(k, k)}")
    if missing:
        print("\nНет данных (посчитано как 0): " + ", ".join(LABELS[m] for m in missing))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
