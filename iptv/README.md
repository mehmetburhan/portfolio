# Owl IP Player — yasal canlı kanal listeleri

Bu klasör, **Owl IP Player** uygulamasının yerleşik **World Free TV** özelliği için kullanılan
kamuya açık / yasal canlı yayın M3U kaynağını barındırır.

## Ne içerir?

| Dosya | Açıklama |
|-------|----------|
| [`legal_world_by_country.m3u`](legal_world_by_country.m3u) | Ülkelere göre gruplanmış **dünya** ve **ulusal** ücretsiz / kamuya açık canlı kanallar |

- Listeler **ülke (ulusal) grupları** halinde düzenlenmiştir (ör. Turkey / Türkiye, USA / ABD, Germany / Almanya…).
- Yalnızca **yasal / kamuya açık** veya yayıncıların ücretsiz erişime sunduğu canlı yayınlar hedeflenir.
- **Ticari şifreli / abonelik zorunlu** kanallar yoktur.
- Owl IP Player bu yayınları kendi sunucusunda **barındırmaz**; yalnızca M3U adresini okur ve cihazda oynatmayı dener.

## Uygulama bağlantısı

Ham M3U (uygulama açılışında güncellenir):

```
https://raw.githubusercontent.com/mehmetburhan/portfolio/main/iptv/legal_world_by_country.m3u
```

Gizlilik / kullanım koşulları:

```
https://raw.githubusercontent.com/mehmetburhan/portfolio/main/OwlIPPlayer-privacy-policy.html
```

Uygulama bilgisi (özellikler / yasal liste açıklaması):

```
https://raw.githubusercontent.com/mehmetburhan/portfolio/main/OwlIPPlayer-app-info.html
```

## Önemli notlar

- Bazı akışlar **coğrafi kısıtlı** olabilir veya zamanla değişebilir / kapanabilir.
- Bulunduğunuz ülkede hangi yayınlara erişiminizin hukuka uygun olduğu konusunda son sorumluluk kullanıcıya aittir.
- Kaynak derlemesi: Free-TV/IPTV, iptv-org ve yayıncı HLS bağlantıları; ticari piracy listeleri değildir.

## Güncelleme

Liste güncellendiğinde bu depodaki `legal_world_by_country.m3u` dosyası değiştirilir.
Owl IP Player açılışta bu dosyayı yeniden indirir.
