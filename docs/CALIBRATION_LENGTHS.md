# Başlangıç düzeltmesinin kalibrasyon süresine duyarlılığı

## Soru ve önceden belirlenen protokol

İlk 5 saniyeyi kullanmak yerine ilk 3 veya 10 saniyeyi kullansaydık sabit
başlangıç düzeltmesi ne kadar değişirdi? Süreler 3/5/10 saniye, değerlendirme
60 saniye olarak deneyden önce belirlendi; sonuç küçülsün diye ayarlanmadı.

- Her pencere ilk IMU zamanından başlar, sağ ucu hariçtir.
- Önceki duruş adayı eşikleri aynen uygulanır: referans hız <=0,05 m/s,
  referans yönelim değişimi <=0,1°, en az 3 referans, en az %60 zaman kapsamı.
- En uzun İSTENEN pencerenin bitişinden sonraki ilk referans anı ortak başlangıçtır.
  En uzun pencere reddedilse de başlangıç değiştirilmez.
- Ham ve kabul edilen bütün düzeltmeler aynı referans quaternion'undan bir kez
  başlar; sonraki referans yönelimleri yalnız değerlendirmede kullanılır.
- Ofset hesaplamak için değerlendirmedeki IMU veya referans kullanılmaz.
- Yalnız eski sabit ortalama yöntemi karşılaştırılır. Dünya dönüşü ayrıca
  uygulanmaz; bu, süre etkisini ayrı inceleyen bir deneydir.

## Gerçek kayıt — 9 Kasım 2026

FIRST_RUN.md'deki aynı SHA-256 değerlerine sahip UrbanNav Medium-Urban-1 dosyaları.
Ortak değerlendirme başlangıcı UTC Unix 1621218786 s, süre 60 s.
İlk IMU'dan yaklaşık 10,451365 s sonra; önceki 5 saniyelik düzeltme deneyinden
5 s daha geç başlanır. Yeni ve eski deneyin son açıları doğrudan karşılaştırılmaz.

| Kalibrasyon | Durum | Ortak 60 saniye sonunda fark |
|---|---|---:|
| Yok | Ham karşılaştırma | 10,784649° |
| İlk 3 s | Duruş adayı kabul | 2,646858° |
| İlk 5 s | Duruş adayı kabul | 1,844626° |
| İlk 10 s | Duruş adayı eşikleri aşıldı | Hesaplanmadı |

| Ortalama (rad/s) | x | y | z |
|---|---:|---:|---:|
| İlk 3 s | -0,001736503 | +0,000115155 | -0,001776958 |
| İlk 5 s | -0,002030731 | -0,000208674 | -0,001997960 |

İlk 10 s içindeki en büyük referans hız 2,679016 m/s, yönelim değişimi
0,688326°; her ikisi de duruş adayı eşiğini aşıyor.

Grafik görsel olarak kontrol edildi: sabit düzeltmeli eğriler hamdan daha düşük,
3 saniye eğrisi bu kesitte 5 saniyeden daha yüksek farkla bitiyor.

## Çıkarım ve çıkaramayacağımız sonuçlar

Başlangıç ortalamasının seçimi sonucu etkiliyor. Bu kesitte 5 s düzeltmesi
3 s'den daha düşük fark verdi; 5 s'nin genel olarak en iyi süre olduğu sonucuna
varılamaz. Sonuçlara göre en iyi süreyi seçip aynı kaydı bağımsız test diye sunmayız.
10 s adayının reddi, daha çok örnek toplamanın tek başına yeterli olmadığını gösterir:
ortalama alınan aralığın hareket bakımından uygunluğu da gerekir.

3 s ile 5 s pencereleri iç içedir; bağımsız deney veya güven aralığı değildir.
Ortalama farkları gürültü, küçük hareket, sensör hataları ve diğer etkilerden
kaynaklanabilir. Bias'ın zamanla değiştiğini veya çevrim içi öğrenmenin gerekli
olduğunu kanıtlamaz. Kalan yönelim farkı fiziksel bias etiketi değildir.

## Dosyalar ve kontroller

- calibration_lengths_comparison.png: üstte ham ve kabul edilmiş düzeltmeler;
  altta yalnız düzeltmeli eğriler.
- calibration_lengths_at_reference_epochs.csv: quaternion'lar, fark vektörleri,
  toplam farklar, aynı zamanlar ve referans kalite kodları.
- calibration_lengths_report.json: kabul/red, kalibrasyon istatistikleri,
  gerçek başlangıç/süre, parametreler ve sınırlar.

27 test geçti. Yeni kontroller: bilinen sabit ofset, ortak başlangıç/yönelim,
reddedilen uzun pencerenin başlangıcı kaydırmaması, ileri referansın tahmini veya
kalibrasyonu değiştirememesi, geçersiz sürelerin reddi.
