# Uzun duruşlarda eşit süreli ofset incelemesi

## Veri ve protokol

9 Kasım 2026: FIRST_RUN.md ile aynı UrbanNav Medium-Urban-1 dosyaları.

Bu deney referans destekli, çevrim dışı keşif analizidir. Model eğitim/test deneyi
veya IMU tabanlı canlı duruş algılama değildir. Referansın tamamıyla seçim yapılır.

- Referans hız büyüklüğü <=0,05 m/s olan kesintisiz bölümler bulunur.
- 1,5 s üzeri referans boşluğu duruşu böler; kısa hareketler birleştirilmez.
- En az 5 s referans zaman açıklığı ve ilk yönelime göre en çok 0,1° fark aranır.
- Özgün IMU boşluğu 20 ms üzerindeyse duruş adayı reddedilir.
- Uzun her adayda başlangıçtan 1 s sonra ilk 20 s seçilir. Sonunda en az 1 s kalmalı.
- Dolayısıyla en az 22 s aday gerekir; 33/48/62/27 s adayların dördü de kullanılır.
- Her pencerede yaklaşık 8.000 IMU örneği vardır. IMU aralığı sağdan açıktır.
- Dünya dönüşü pencerenin ilk referans enlem/yönelimiyle gövdeye taşınıp ortalamadan ayrılır.
- Duruş boyunca yönelim yaklaşık sabit kabul edilir; küçük gerçek dönüşler ofsette kalabilir.
- Aynı 20 s içindeki ilk ve ikinci 10 s ortalamaları ayrıca hesaplanır.
- Hiçbir pencere, ofsetin büyüklüğüne veya elde edilen yönelim farkına göre seçilmez.

## Kayıttaki sonuçlar

9 duruş adayı, toplam 226 s referans zaman açıklığı.
1 Hz referans kontrolü yüksek frekanslı hareket/titreşim yokluğunu kanıtlamaz.

| Duruş | Başlangıç (s) | Bitiş (s) | Süre (s) | Eşit pencere |
|---|---:|---:|---:|---|
| 1 | 0.451 | 5.451 | 5 | too_short |
| 2 | 35.451 | 68.451 | 33 | analyzed |
| 3 | 141.451 | 189.451 | 48 | analyzed |
| 4 | 250.451 | 264.451 | 14 | too_short |
| 5 | 298.451 | 307.451 | 9 | too_short |
| 6 | 394.451 | 456.451 | 62 | analyzed |
| 7 | 557.451 | 584.451 | 27 | analyzed |
| 8 | 645.451 | 655.451 | 10 | too_short |
| 9 | 687.451 | 705.451 | 18 | too_short |

Dünya dönüşü ayrılmış ofset adayları (derece/saniye):

| Pencere başlangıcı (s) | x | y | z |
|---|---:|---:|---:|
| 36.451 | -0.115002 | -0.005628 | -0.145370 |
| 142.451 | -0.107487 | 0.012101 | -0.139814 |
| 395.451 | -0.082782 | 0.007043 | -0.153783 |
| 558.451 | -0.075156 | 0.007408 | -0.153728 |

İkinci 10 s eksi ilk 10 s (derece/saniye); bunlar güven aralığı değildir:

| Pencere başlangıcı (s) | x | y | z |
|---|---:|---:|---:|
| 36.451 | 0.022570 | -0.011983 | -0.035828 |
| 142.451 | -0.003367 | 0.008000 | -0.005681 |
| 395.451 | -0.001659 | 0.009936 | -0.020284 |
| 558.451 | 0.022420 | 0.002512 | 0.004561 |

## Yorum ve sonraki adım

Ortalamalar duruşlar arasında farklı, fakat aynı duruşun iki yarısı da değişebiliyor.
Örneğin x ortalaması ilk/son pencerede yaklaşık -0,115 ve -0,075°/s; bazı
pencerelerin iki yarısı yaklaşık 0,022°/s farklı. Bu değerler yalnız fiziksel bias
driftine bağlanamaz. Gürültü/titreşim, küçük hareket, referans, zaman/montaj
ve sensör hataları ayrıştırılmadı. Standart sapmadan bağımsız örnek varsayarak
std/sqrt(N) güvenilirliği iddia edilmez. Sıcaklık kaydı yoktur.

Grafikte mavi noktalar 20 s ortalaması, turuncu çarpılar iki 10 s yarıdır.
Noktalar arasında sürekli bias değişimi varmış gibi bir eğri uydurulmadı.
Üstte yeşil duruş adayları, mavi seçilen pencereler gösterilir.

Sıradaki çalışma: zaman/montaj ve hareket tutarlılığını kontrol etmek; ardından
yalnız tamamlanmış geçmiş pencereden yapılan sabit düzeltmeyi sonraki aralıkta
değerlendirmek. Referans yardımlı seçimi kullanırsak bunun çevrim dışı tanı
olduğunu koruyacağız. Öğrenilmiş yöntemin genellemesi için farklı kayıtlar,
Allan/sıcaklık karakterizasyonu için uygun ek sabit kayıt gerekir.

## Çıktılar ve doğrulama

- stop_inventory.csv: bulunan bölümler, kabul/red, eşit pencere uygunluğu.
- equal_window_statistics.csv: ortalama, Dünya katkısı, örnek std, iki yarı farkı.
- stationary_windows_report.json: parametreler, kaynak yolları, kalite kodları ve sınırlar.
- stationary_windows.png: referans hız ve üç eksen ofset adayları.

32 test geçti. Yeni kontroller: duruşların ayrılması, eşit süre/kenarlar, bilinen
ofsette Dünya dönüşünün bir kez çıkarılması, dönme/IMU boşluğu reddi, referans
boşluğunun köprülenmemesi, pencere sonrasının istatistikleri değiştirmemesi,
geçersiz zaman ve parametrelerin reddi. Gerçek kayıt grafiği görsel olarak kontrol edildi.
