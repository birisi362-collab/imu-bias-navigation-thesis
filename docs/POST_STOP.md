# Duruş sonrası hareket için sabit jiroskop düzeltmesi

## Soru ve protokol

Son tamamlanan duruştan alınan 20 s ofseti, kaydın ilk 5 s ofsetinden daha iyi
sonraki yönelim tahmini sağlıyor mu? Varsayılan 20 s kalibrasyon ve 60 s değerlendirme
önceki deneyden taşındı; sonuçlara göre ayarlanmadı.

1. STATIONARY_WINDOWS.md'deki referans destekli seçim aynen kullanılır. En az 22 s
   duran adayın başlangıcından 1 s sonra ilk 20 s alınır. Dört adayın tamamı kullanılır.
2. Her adayın bitiminden hemen sonraki referans anında hız >0,05 m/s olmalı.
   Referans boşluğu 1,5 s üzerindeyse deney atlanır; daha iyi bir aralık aranmaz.
3. Bu ilk hareket anından itibaren tam 60 s değerlendirilir. Eksik kapsam veya
   IMU/referans boşluğu varsa süre sessizce kısaltılmaz; atlama nedeni rapora yazılır.
4. Üç hesap aynı başlangıç referans quaternion'undan bir kez başlatılır:
   ofsetsiz, ilk 5 s ofseti, son duruştaki 20 s ofseti.
5. İlk 5 s ofsetinden ve güncel ofsetten kalibrasyon anındaki Dünya dönüşü ayrılır.
   Üç hesapta da değerlendirme başlangıç enlemiyle aynı Dünya dönüşü modeli vardır.
   Ofsetsiz eğri eski ham eğriyle aynı model değildir: burada Dünya dönüşü uygulanır.
6. Ofsetler değerlendirmeden önce hesaplanır ve 60 s içinde sabit kalır. Sonraki
   referans yönelimleri yalnız değerlendirme için kullanılır, tahmini sıfırlamaz.
7. Her hareket aralığı ayrı deneydir; aralıklar arasında navigasyon durumu taşınmaz.

## Çıktılar ve kontroller

- post_stop_comparison.png: her duruş için solda üç eğri, sağda iki düzeltmeli eğri.
- post_stop_at_reference_epochs.csv: deney/stop kimliği, aynı referans zamanları,
  quaternion'lar ve toplam/vektörel farklar.
- post_stop_summary.csv: son açı ve referans anlarında hesaplanan RMS açı.
  RMS, 1 Hz'deki değerlendirme örneklerinin RMS değeridir.
- post_stop_report.json: kalibrasyon, deney başlangıçları, ofsetler, model ve atlama nedenleri.

36 test geçti. Yeni kontroller: sentetik bilinen ofset değişiminin sonraki aralıkta
azaltılması, kalibrasyon/değerlendirme ayrımı, sonraki referansın tahminleri/ofsetleri
etkilememesi, sonraki IMU'nun ofseti etkilememesi, tam süre ve referans boşluğu reddi.

## Yorum sınırları

Referans destekli duruş/motion seçimi çevrim dışı keşiftir. Bu, canlı IMU duruş
algılama, kesintisiz ESKF, çevrim içi öğrenme veya bağımsız test başarımı değildir.
Referans başlangıç yönelimi de dış yardımdır.

İlk 5 s ile güncel 20 s hem zaman hem süre bakımından farklıdır. İyileşme varsa
bunu yalnız güncelliğe veya fiziksel bias driftine bağlayamayız. İlk 5 s'nin daha
kısa olması da başlangıç ortalamasının belirsizliğini etkileyebilir. Ofsetler küçük
hareket/sensör/montaj/zaman etkilerini de içerebilir; saf bias etiketi değildir.

Dünya dönüşü sabit başlangıç enlemiyle modellenir; taşıma hızı yoktur. Referans
kalite grupları gizlice elenmez. Son hata tek başına yeterli değildir; RMS ve bütün
eğriler birlikte incelenir. Tek kayıttaki dört deneyden genel üstünlük çıkarılmaz.

## Gerçek kayıt — 9 Kasım 2026

FIRST_RUN.md ile aynı SHA-256 değerli UrbanNav Medium-Urban-1 dosyaları. Dört uzun
duruşun tamamı sonrasında tam 60 s değerlendirildi; atlanan deney yok.

| Duruş | Başlangıç (s) | Ofsetsiz son açı | İlk 5 s son açı | Güncel 20 s son açı | İlk RMS | Güncel RMS |
|---|---:|---:|---:|---:|---:|---:|
| 2 | 69.451 | 10.4049° | 2.1052° | 0.6131° | 1.1837° | 0.3649° |
| 3 | 190.451 | 10.6989° | 2.1160° | 1.0890° | 1.2658° | 0.5788° |
| 6 | 457.451 | 10.6293° | 2.3116° | 1.4632° | 1.4255° | 0.9864° |
| 7 | 585.451 | 9.5603° | 3.3406° | 0.5093° | 2.0587° | 0.4789° |

Güncel duruş düzeltmesi dört aralıkta da hem son açı hem RMS açısından ilk 5 s
düzeltmesinden daha düşük fark verdi. Bu, son duruştan alınan düzeltmenin sonraki
aralıkta işe yarayabildiğine dair bu kayıt içindeki ilk gözlemimizdir. Hem süre
hem güncellik değiştiğinden fiziksel bias drifti veya çevrim içi öğrenme gerekliliği
kanıtlanmaz. Eşit süreli eski/güncel duruşlarla kontrol ve farklı kayıtlar gerekir.
Gerçek karşılaştırma grafiği görsel olarak incelendi.
