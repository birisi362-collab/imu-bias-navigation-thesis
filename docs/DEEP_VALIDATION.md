# İkinci kayıt: Deep-Urban-1 kontrolü

## Amaç ve veri seçimi

Medium-Urban-1 üzerinde geliştirilen güncellik/süre karşılaştırmasını farklı bir
kayıtta, sonuçlara göre parametre değiştirmeden yinelemek. Öğrenilmiş model yok;
bu klasik yöntemin kayıtlar arası keşif karşılaştırmasıdır.

Kaynaklar (9 Kasım 2026 kontrolü):

- https://github.com/IPNL-POLYU/UrbanNavDataset#urbannav-hk-deep-urban-1
- https://github.com/IPNL-POLYU/UrbanNavDataset/blob/master/UrbanNav-HK-Deep-Urban-1/extrinsic.yaml
- https://www.dropbox.com/s/pet3up4vka61jop/xsense_imu_deep_urban1.csv?dl=1
- https://www.dropbox.com/s/ej2mkue2w3r36s2/UrbanNav_whampoa_raw.txt?dl=1

Yalnız Xsens IMU CSV (yaklaşık 214,80 MB) ve referans TXT (0,274 MB) indirildi.
Kamera/LiDAR ROS bag indirilmedi. İndirmeler tam dosya, HTML/kısmi içerik ve
boyut kontrolünden geçti. Yerel veri/çıktılar git dışında tutulur.

## Zaman ve nominal eksen kontrolleri

IMU sensör zaman damgası tamsayı nanosaniye, referans UTCTime kullanıldı.
GPS haftası/içi saniye UTC yerine kullanılmadı. Otomatik saat kaydırma yapılmadı.
SPAN-CPT/IE başlık ve birimleri Medium ile aynı 20 alanlı okuyucuyla doğrulandı.
İki extrinsic.yaml dosyasında gövde x-sağ/y-ileri/z-yukarı ve body_T_SPAN
dönmesi nominal birim matris. Öteleme 0,14 m; yalnız yönelim deneyinde uygulanmaz.
Gerçek küçük montaj ve fiziksel saat ofseti/drifti bununla kalibre edilmiş sayılmaz.

İlk uzun duruşun seçilen 20 s penceresinde özgül kuvvet ortalaması yaklaşık
[-0,39428; 0,11009; 9,78217] m/s²; referans yöneliminden 9,81 büyüklükle
beklenen yerçekimi kaynaklı değer [-0,36321; 0,09487; 9,80281] m/s².
Bu yalnız kaba işaret/büyüklük tutarlılığıdır; kesin eksen/montaj kalibrasyonu değildir.

| Kalite kontrolü | Değer |
|---|---:|
| IMU örneği | 614782 |
| Referans örneği | 1539 |
| Ortak kapsam | 1536.933121 s |
| IMU medyan frekansı | 400.487313 Hz |
| En büyük IMU aralığı | 9.376049 ms |
| Tekrarlı/geriye giden zamanlar | 0 / 0 |
| Sonlu olmayan değerler | 0 |
| 10 ms eşlemede referans anları | 1537 / 1537 |
| En büyük eşleme uzaklığı | 1.398086 ms |

Referans Q kodlarının sayımı: {"2.0": 796, "1.0": 525, "3.0": 103, "4.0": 87, "5.0": 28}.
Hiçbir Q grubu gizlice elenmedi; kodlar burada doğruluk garantisi kabul edilmedi.

## Değiştirilmeyen protokol

- Hız <=0,05 m/s, ilk yönelime fark <=0,1°, en az 5 s referans açıklığı.
- IMU boşluğu <=20 ms; referans boşluğu <=1,5 s. Süre kısaltılarak eksik veri gizlenmez.
- Uzun pencere 20 s, kısa 5 s, duruş kenarı 1 s.
- Eski kalibrasyon bu kaydın ilk uygun uzun duruşunda sabitlenir.
- Bu ilk duruş iyileşme deneyi sayılmaz; sonraki her uygun uzun duruş sonrası tam 60 s.
- Dört yöntemde aynı tek başlangıç referansı ve aynı Dünya dönüşü modeli.
- Değerlendirme sırasında ofset güncelleme veya referansla sıfırlama yok.
- CALIBRATION_FACTORS.md ile aynı ayarlar; sonuçlara göre ayarlanmadı.

18 duruş adayı, toplam 474 s; 8 eşit 20 s pencere.
Bir başka düşük hızlı bölüm yönelim eşiğini aşınca reddedildi.

| Duruş | Referans duruş başlangıcı (s) | Süre (s) | Kalibrasyon başlangıcı (s) |
|---|---:|---:|---:|
| 1 | 63.874 | 35 | 64.874 |
| 2 | 153.874 | 26 | 154.874 |
| 6 | 398.874 | 53 | 399.874 |
| 7 | 484.874 | 57 | 485.874 |
| 8 | 587.874 | 56 | 588.874 |
| 11 | 758.874 | 38 | 759.874 |
| 14 | 1051.874 | 32 | 1052.874 |
| 16 | 1179.874 | 54 | 1180.874 |

## Veri parmak izleri

```text
xsense_imu_deep_urban1.csv
40ade891c52bdc0a262a92eae6d4b1376a5cee7d0b485fb729a51248737228f0
UrbanNav_whampoa_raw.txt
cb35bc9ebfb171147d290672a46b9d7426475501c922d84ae81edde92c3ba272
```

39 otomatik test geçti. Okuyucu, zaman/boşluk kontrolleri, referansın tahminleri
sıfırlayamaması ve kalibrasyon/değerlendirme ayrımı korundu.

## Gerçek karşılaştırma sonucu

7 aralık tam 60 s değerlendirildi. Atlanan deney: 0.
Bütün açılar SPAN-CPT/IE referansıyla yönelim farkıdır; sensör bias ground truth yoktur.

| Hareket başlangıcı (s) | Eski 5 s | Eski 20 s | Güncel 5 s | Güncel 20 s |
|---|---:|---:|---:|---:|
| 180.874 | 1.1624° | 1.1249° | 1.6614° | 0.4856° |
| 452.874 | 1.7183° | 1.8807° | 2.4350° | 1.1462° |
| 542.874 | 1.5831° | 1.7505° | 1.3088° | 0.9350° |
| 644.874 | 2.2757° | 2.5303° | 1.5136° | 2.1805° |
| 797.874 | 2.0787° | 2.2759° | 2.4200° | 2.6336° |
| 1084.874 | 1.3686° | 1.5678° | 1.3540° | 0.6774° |
| 1234.874 | 1.8101° | 1.9677° | 0.6930° | 1.1253° |

RMS açı (referans anlarında):

| Hareket başlangıcı (s) | Eski 5 s RMS | Eski 20 s RMS | Güncel 5 s RMS | Güncel 20 s RMS |
|---|---:|---:|---:|---:|
| 180.874 | 0.6347° | 0.5938° | 0.9109° | 0.2794° |
| 452.874 | 1.1928° | 1.2915° | 1.2916° | 0.7824° |
| 542.874 | 1.0249° | 1.1271° | 0.8244° | 0.7048° |
| 644.874 | 1.2542° | 1.4008° | 0.9849° | 1.3059° |
| 797.874 | 1.1473° | 1.2728° | 1.2657° | 1.3735° |
| 1084.874 | 0.7349° | 0.8307° | 0.6447° | 0.4463° |
| 1234.874 | 0.9688° | 1.0454° | 0.5709° | 0.7710° |

## İki kaydı birlikte okuma

| Karşılaştırma: daha düşük son açı | Medium | Deep |
|---|---:|---:|
| Eski 20 s / eski 5 s | 3/3 | 1/7 |
| Güncel 20 s / güncel 5 s | 3/3 | 4/7 |
| Güncel 5 s / eski 5 s | 1/3 | 4/7 |
| Güncel 20 s / eski 20 s | 1/3 | 6/7 |

Bu sayımlar RMS açısından da aynıdır. Bunlar bağımsız Bernoulli denemeleri veya
istatistiksel güven düzeyi değildir; aralıklar aynı kayıttan ve ortak eski ofsetten gelir.

Mediumdaki 20 s üstünlüğü Deepte her koşulda tekrarlanmadı. Güncellik etkisi de
kayıtlar arasında değişti: Deepte eşit 20 s güncel düzeltme 6/7, Mediumda 1/3
aralıkta daha iyiydi. Daha uzun veya daha yeni kalibrasyonun her zaman daha iyi
olduğu iddia edilemez. İki kayıtta hem süre hem duruş kalitesinin incelenmesi
gerektiğini gördük. Bu veri saf fiziksel bias driftini veya AI gerekliliğini kanıtlamaz.

Önceki protokol aynı çalıştı; eksen/zaman/taşıma hızı ve referans belirsizliği
sınırları sürüyor. Sonraki yöntem karşılaştırmalarında bu klasik taban çizgileri
korunmalı; test sonucuna göre en iyi kalibrasyon seçilip bağımsız başarı diye sunulmamalı.
Gerçek yedi aralığın karşılaştırma grafiği görsel olarak kontrol edildi.
