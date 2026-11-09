# Güncellik ve ortalama süresini ayırma

## Soru ve önceden belirlenen protokol

POST_STOP.md'deki ilk 5 s/güncel 20 s karşılaştırmasında hem veri yaşı hem
ortalama süresi değişiyordu. Burada 2x2 kontrol yapılır:

| Yöntem | Duruş | Ortalama süresi |
|---|---|---:|
| old_short | İlk uzun duruş (sabit) | 5 s |
| old_long | İlk uzun duruş (sabit) | 20 s |
| recent_short | Son tamamlanan uzun duruş | 5 s |
| recent_long | Son tamamlanan uzun duruş | 20 s |

Eski kalibrasyon artık kaydın ilk 5 saniyesi değildir. STATIONARY_WINDOWS.md'deki
ilk uzun duruş ID 2, yaklaşık t=35,451–68,451 s kullanılır. Başlangıç kenarı 1 s;
kısa pencere [36,451;41,451), uzun [36,451;56,451) s. Bu eski değerler sonraki
bütün deneylerde sabit tutulur. Güncel pencereler kendi duruşlarının başlangıcından
aynı 1 s kenarla seçilir. Sonuç küçültmek için pencere aranmaz.

Dört yöntemde de Dünya dönüşü kalibrasyon anındaki enlem/yönelimle ortalamadan
ayrılır. Sonraki aynı 60 s için aynı başlangıç referans yönelimi ve Dünya dönüşü
modeli kullanılır; referansla aralık içinde sıfırlama veya ofset güncelleme yoktur.
Eksik kapsam/boşlukta süre kısaltılmaz. Her ofset değerlendirme başlamadan hazırdır.

İlk uzun duruşta eski ve güncel aynıdır; bağımsız iyileşme deneyi sayılmaz.
Sonraki üç uygun duruş ID 3/6/7 sonrası hareket aralıkları karşılaştırılır.

## Referansın rolü ve ölçütler

SPAN-CPT + Inertial Explorer yönelimi referanstır. Başlangıç yönelimi bir kez
buradan alınır; sonraki referans yönelimleri yalnız hata ölçümünde kullanılır.
Duruş seçimi referans hız/yönelim yardımıyla çevrim dışı yapılır. Bu canlı IMU
duruş algılayıcısı veya GNSS kesintisi performans deneyi değildir.

Toplam fark inverse(q_reference) ⊗ q_estimate dönüşünün en kısa 3B açısıdır.
Son açı ve 1 Hz referans anlarındaki RMS açı raporlanır. Ground truth adıyla
sunulan referans da bir kestirimdir; fiziksel sensör bias etiketi yoktur.

## Yorum sınırları

- Aynı sürede eski/güncel karşılaştırması güncellik etkisini inceler.
- Aynı duruşta 5/20 s karşılaştırması ortalama süresi etkisini inceler.
- 5 s penceresi 20 s'nin içindedir; bağımsız tekrar değildir.
- Tek kayıttaki üç aralık istatistiksel genelleme veya bias driftinin fiziksel kanıtı değildir.
- Gürültü/titreşim, küçük hareket, referans, zaman/montaj etkileri ofsette kalabilir.
- Enlem başlangıçta sabitlenir; taşıma hızı hâlâ modellenmez.
- Sonraki adım aynı protokolü başka kayıtta, parametreleri sonuca göre değiştirmeden sınamaktır.

## Çıktılar ve kontroller

- calibration_factors_report.json: eski/güncel kalibrasyon pencereleri, parametreler,
  başlangıçlar, tam süre ve dört yöntemin raporları.
- calibration_factors_summary.csv: deney başına dört son açı ve RMS.
- calibration_factors_at_reference_epochs.csv: bütün quaternion'lar/farklar/zamanlar.
- calibration_factors_comparison.png: solda 5 s, sağda 20 s; mavi eski, turuncu güncel.
  Aynı satırdaki iki panel aynı y ölçeğini kullanır.

39 test geçti. Yeni kontroller: eski pencerenin farklı deneylerde sabit kalması,
5/20 s süre ve zaman ayrımı, bilinen sentetik ofset, gelecek referansın tahmini
ve kalibrasyonu değiştirememesi, ilk uzun duruşun iyileşme sayılmaması ve geçersiz süreler.

## Gerçek kayıt — 9 Kasım 2026

FIRST_RUN.md ile aynı veri dosyaları. Üç sonraki aralık tam 60 s; atlanan deney yok.
İlk uzun duruşun kendisi bağımsız karşılaştırma sayılmadı.

| Duruş / hareket başlangıcı | Eski 5 s son açı | Eski 20 s son açı | Güncel 5 s son açı | Güncel 20 s son açı |
|---|---:|---:|---:|---:|
| 3 / 190.451 s | 0.9477° | 0.6182° | 1.7480° | 1.0890° |
| 6 / 457.451 s | 1.3997° | 0.6172° | 1.7075° | 1.4632° |
| 7 / 585.451 s | 3.3843° | 2.3730° | 1.1838° | 0.5093° |

| Duruş | Eski 5 s RMS | Eski 20 s RMS | Güncel 5 s RMS | Güncel 20 s RMS |
|---|---:|---:|---:|---:|
| 3 | 0.7001° | 0.3566° | 0.8766° | 0.5788° |
| 6 | 0.8008° | 0.5566° | 1.1515° | 0.9864° |
| 7 | 2.0799° | 1.4870° | 0.6752° | 0.4789° |

Aynı süreyle güncel/eski karşılaştırmasında duruş 3 ve 6 sonrası eski, duruş 7
sonrası güncel ofset daha düşük son açı ve RMS verdi. 20 s/5 s karşılaştırmasında
üç aralığın tamamında hem eski hem güncel 20 s ofset daha düşük son açı ve RMS verdi.
Bu örneklemde ortalama süresinin faydası güncellemenin faydasından daha tutarlıdır.
POST_STOP.md gözlemi geçerlidir, ancak onun 5/20 s kıyasından genel güncelleme
üstünlüğü çıkarılamayacağını bu kontrol somutlaştırdı. Fiziksel bias sabit/değişken
kararı verilemez; bu bir kayıt içi keşif sonucudur. Grafik görsel olarak kontrol edildi.
