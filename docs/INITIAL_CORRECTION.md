# Sabit başlangıç jiroskop düzeltmesi

Amaç: Öğrenme eklemeden önce, başlangıç duruş adayından alınan sabit bir ortalamanın
sonraki yönelim hesabına katkısını ölçmek. Quaternion konvansiyonları ve ortak
sınırlamalar `ORIENTATION.md` ile aynıdır.

## Önceden belirlenen protokol

1. İlk IMU zamanından itibaren ilk 5 saniye kullanılır; aralık sağdan açıktır.
2. Bu aralık içindeki referans hızları en fazla 0,05 m/s, ilk referansa göre en
   büyük 3B yönelim değişimi en fazla 0,1 derece olmalı. En az 3 referans anı ve
   aralık süresinin en az %60'ını kapsayan ilk-son referans uzaklığı istenir.
3. Kalibrasyondaki özgün IMU aralıkları 20 ms'yi aşmamalı. Kontrol, son sınırı
   kapsayan özgün aralığı da içerir. Referans kapsamı/hareket kontrolü başarısızsa
   otomatik düzeltme uygulanmaz. Bu eşikler doğrulanmış bir duruş algılayıcısı değildir.
4. Üç eksenin örnek ortalaması çıkarılır. Standart sapma, iki yarının ayrı
   ortalamaları ve farkı da kaydedilir. Korelasyon nedeniyle `std/sqrt(N)` ile
   doğruluk garantisi verilmez.
5. Düzeltme aralığı bittikten sonraki ilk uygun referans anında iki hesap da aynı
   referans quaternion'undan başlatılır. Bu andan itibaren 60 saniye değerlendirilir.
6. İki hesap aynı zamanları, IMU aralıklarını, yönelim konvansiyonunu ve başlangıcı
   kullanır; tek fark birinde sabit ortalamanın çıkarılmasıdır. Referansla yeniden
   başlangıç yapılmaz. Sonraki veriler başlangıç ortalamasına giremez.

Süreler komut satırından değiştirilebilir; değerlendirme sonucunu küçültmek amacıyla
ayar yapılmamalıdır. Bu çalıştırmada varsayılan 5/60 saniye ve sabit eşikler kullanıldı.
Referansın başlangıç verisi yalnız duruş adayı kontrolüne ve başlangıç yönelimine
yardımcı olur; bu düzen gerçek donanımda otomatik duruş algılamayı çözmüş değildir.

## Gerçek kayıt gözlemleri — 27 Ekim 2026

`FIRST_RUN.md` ile aynı UrbanNav Medium-Urban-1 dosyaları:

| Başlangıç aralığı | Sonuç |
|---|---:|
| IMU örneği | 2.000 |
| Referans anı | 5 |
| En büyük referans hız büyüklüğü | 0,0167631 m/s |
| En büyük referans yönelim değişimi | 0,00553292 derece |
| Jiroskop x ortalaması | −0,00203073112 rad/s |
| Jiroskop y ortalaması | −0,000208674386 rad/s |
| Jiroskop z ortalaması | −0,00199795966 rad/s |
| Jiroskop x/y/z örnek standart sapması | 0,02418 / 0,01006 / 0,01118 rad/s |

Referans ölçümleri duruş varsayımını destekliyor; düşük hız/yönelim değişimi,
yüksek frekanslı titreşim veya küçük hareketlerin bulunmadığını kanıtlamaz.

- Düzeltme aralığının bitişi: UTC Unix `1621218780.548635005` s (hariç).
- Ortak değerlendirme başlangıcı: UTC Unix `1621218781` s.
- Süre: 60 s, 61 referans anı.
- Ham jiroskopla son toplam 3B yönelim farkı: **10,4131 derece**.
- Sabit başlangıç düzeltmesiyle son toplam 3B yönelim farkı: **1,6042 derece**.

Önceki ham deneyin 10,0624 derecelik sonucu farklı başlangıç aralığına aittir;
bu karşılaştırmada esas alınan ham sonuç 10,4131 derecedir. 19 otomatik test geçti;
gerçek karşılaştırma grafiği görsel olarak incelendi.

## Yorumun sınırı

Bu aralıkta basit sabit düzeltme yönelim farkını küçülttü. Bu gözlem, öğrenilen
modelin karşılaştırılacağı klasik yaklaşımın ham jiroskoptan daha güçlü olması
gerektiğini gösterir. Gerçek fiziksel biasın bulunduğunu, kalan farkın bias
değişimi olduğunu veya çevrim içi öğrenmenin zorunlu olduğunu göstermez.

Çıkarılan ortalama Dünya dönüşü ve küçük hareketleri de içerebilir. Dünya dönüşü
gövde eksenlerinde araç döndükçe değişeceği için, başlangıçtaki sabit ortalamayı
çıkarmak Dünya dönüşünü fiziksel olarak doğru modellemenin yerine geçmez.
Saat/montaj konvansiyonları, Dünya dönüşü/taşıma hızı ve daha uzun/farklı kayıtlar
incelenmeden kalan 1,6042 derece öğrenilecek bias etiketi olarak kullanılmamalıdır.
Bu aşama Allan analizi veya tam kalibrasyon değildir.

## Çalıştırma

```powershell
python compare_initial_correction.py --imu data/raw/medium/xsense_imu_medium_urban1.csv --reference data/raw/medium/UrbanNav_TST_GT_raw.txt --output outputs/medium/initial_correction
```

- `initial_correction_comparison.png`: üstte ham/sabit düzeltmeli toplam fark;
  altta yalnız sabit düzeltmeli hesabın fark dönüş vektörü. Bunlar Euler açı hataları değildir.
- `initial_correction_at_reference_epochs.csv`: iki hesabın quaternion'ları ve farkları.
- `initial_correction_report.json`: başlangıç istatistikleri, eşikler, iki rapor ve sınırlar.
