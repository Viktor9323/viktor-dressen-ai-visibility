# Шаблон JSON-LD для сайта клиента

Вставляется в `<head>` главной страницы. Подтип `@type` выбери под нишу: BeautySalon, HairSalon, MedicalClinic, Dentist, Restaurant, AutoRepair, HealthClub, LocalBusiness (по умолчанию). Все значения бери из карточки; чего нет — удали поле, не выдумывай.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BeautySalon",
  "name": "[Название]",
  "description": "[1–2 предложения с фактами: что делают, оборудование, для кого]",
  "url": "https://[сайт]",
  "telephone": "+7 XXX XXX-XX-XX",
  "image": "https://[сайт]/photo.jpg",
  "priceRange": "[от 500 до 9 000 ₽]",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "[улица, дом, этаж/офис]",
    "addressLocality": "[город]",
    "addressRegion": "[регион]",
    "postalCode": "[индекс]",
    "addressCountry": "RU"
  },
  "geo": {"@type": "GeoCoordinates", "latitude": 0.0, "longitude": 0.0},
  "openingHoursSpecification": [
    {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"], "opens": "10:00", "closes": "22:00"}
  ],
  "sameAs": ["https://yandex.ru/maps/org/[id]/", "https://vk.com/[...]", "https://t.me/[...]"],
  "hasOfferCatalog": {
    "@type": "OfferCatalog",
    "name": "Услуги",
    "itemListElement": [
      {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "[услуга]"}, "price": "1200", "priceCurrency": "RUB"}
    ]
  }
}
</script>
```

Рейтинг (AggregateRating) с данными Яндекса не размечай: Google считает разметку собственных отзывов из чужих источников нарушением.

Для страницы FAQ — отдельный блок `FAQPage` с парами вопрос/ответ, которые реально видны на странице.
