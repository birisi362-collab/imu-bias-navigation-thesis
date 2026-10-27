# Quaternion ile ilk yönelim deneyi

Bu aşamanın amacı, üç eksen ham jiroskopla sürekli yönelim ilerletmeyi kurmaktır.
Henüz kalibre edilmiş bir INS veya öğrenilmiş bias deneyi değildir.

## Konvansiyonlar ve dayanak

- Quaternion Hamilton çarpımıyla, skaler bileşen önce: `[w, x, y, z]`.
- Aktif dönüşüm: gövde koordinatlarındaki vektörü yerel ENU'ya taşır.
- UrbanNav'ın nominal gövdesi: x-sağ, y-ileri, z-yukarı.
- Referans dönüşümü: `R_body_to_ENU = Rz(-heading) Rx(pitch) Ry(roll)`.
  Bu standart XYZ Euler dönüşümü değildir. Heading pozitif saat yönündedir;
  roll y, pitch x çevresindedir. Matris çarpımı sütun vektörlere uygulanır.
- Kaynak kalibrasyonda `body_T_SPAN` dönmesi birim matristir; nominal yön hizası
  kullanılır. Yayınlanan 0,14 m öteleme yönelim dönüşümü oluşturmaz. Konum/hız
  hesabında referans çıktı noktasını doğrulayıp ötelemeyi ayrıca uygulamak gerekir.

Birincil kaynaklar (27 Ekim 2026'da kontrol edildi):

1. [UrbanNav Medium-Urban-1 extrinsic.yaml](https://github.com/IPNL-POLYU/UrbanNavDataset/blob/master/UrbanNav-HK-Medium-Urban-1/extrinsic.yaml):
   eksenler, nominal yön hizası ve montaj ötelemeleri.
2. [Inertial Explorer 8.60 resmi kılavuzu](https://hexagondownloads.blob.core.windows.net/public/Novatel/assets/Documents/Waypoint/Downloads/InertialExplorer860_Manual/InertialExplorer860_Manual.pdf),
   basılı s.50: gövdeden yerel sisteme `R3(yaw) R1(pitch) R2(roll)`.
3. [NovAtel Output Variables](https://docs.novatel.com/Waypoint/Content/Appendix/Output_Variables.htm):
   heading, yaw'ın negatifidir; gövde hızları ve işlenmiş ivmelerin tanımları.
4. [Güncel Waypoint kılavuzu](https://docs.novatel.com/Waypoint/Content/PDFs/Waypoint_Software_User_Manual_D100513.pdf),
   basılı s.90: montaj dönmeleri ve gövde eksenleri. Kayıtta kullanılan IE sürümü
   ve özgün export profili bu dosyalarla kesin olarak belirlenmiş değildir.

## Hesap

İlk ortak referans anındaki quaternion bir kez başlangıç koşulu yapılır. Ham
jiroskopların tamamı gerçek nanosaniye farklarıyla işlenir. IMU örnekleri arasına
düşen referans anları, mevcut aralıkları böler; yalnız gözlenen kapsam içinde
açısal hızlara doğrusal ara değer uygulanır. Her alt aralığın ortalama hızıyla
hesaplanan dönüş quaternion'u mevcut quaternion'un sağına çarpılır ve normalize edilir.
Bu ortalama hız yöntemi sonlu örnekleme yaklaşımıdır; yüksek mertebe coning
düzeltmesi değildir. Çevrim dışı integrasyon, sıfır gecikmeli canlı giriş iddiası taşımaz.

Referansın sonraki yönelimleri yalnız karşılaştırmada kullanılır. Her saniye
yeniden başlangıç yapılmaz. Sonuç 1 Hz'de kaydedilir, entegrasyon 1 Hz'e düşürülmez.
Varsayılan 20 ms'den büyük özgün IMU boşluğunda deney hata verir; boşluklar
uydurma ölçümlerle doldurulmaz. Sınır kontrolü, başlangıç/bitişi kapsayan özgün
IMU aralıklarına da uygulanır.

Üst grafikteki değer, `inverse(q_reference) * q_estimate` dönüşümünün 0–180 derece
arasındaki en kısa açısıdır. Alt grafik bunun referans gövde eksenlerindeki dönüş
vektörüdür; bu bileşenler bağımsız roll/pitch/heading hataları olarak okunmamalıdır.
`q` ve `-q` aynı yönelimi temsil eder ve sıfır fark verir.

## Çalıştırma ve ilk gözlem

```powershell
python evaluate_orientation.py --imu data/raw/medium/xsense_imu_medium_urban1.csv --reference data/raw/medium/UrbanNav_TST_GT_raw.txt --output outputs/medium/orientation
```

27 Ekim 2026, `docs/FIRST_RUN.md` ile aynı ham dosyalar:

| Gözlem | Değer |
|---|---:|
| Başlangıç UTC Unix saniyesi | 1621218776 |
| Süre | 60 s |
| Referans anı | 61 |
| Kapalı aralıkta gerçek IMU örneği | 24.000 |
| Son üç boyutlu yönelim farkı | 10,0624 derece |
| En büyük quaternion norm sapması | yaklaşık 2,22e-16 |

15 otomatik test geçti. Yeni kontroller: yön ve eğim örnekleri, dönmelerin sıra
bağımlılığı, farklı başlangıç yönelimi ve örnek arasındaki sınırlar, q/-q eşdeğerliği,
referansın sonraki değerlerinin tahmini sıfırlayamaması, boşluk ve kapsam reddi.
Gerçek çalıştırma grafiği görsel olarak incelendi.

Kaydın ilk 5 saniyesindeki özgül kuvvet ortalaması yaklaşık
`[0,2645; 0,0901; 9,7869] m/s²`. İlk ortak referans yöneliminden, 9,81 m/s²
büyüklükle beklenen duruş özgül kuvveti yaklaşık `[0,2975; 0,0755; 9,8052]`.
Bu bir işaret/büyüklük tutarlılık kontrolüdür; kısa aralığın tam durağanlığı veya
montaj doğruluğu kanıtlanmış değildir, farklar bias etiketi değildir.

## Sınırlar

- Bias, ölçek faktörü, sıcaklık ve montaj hatası düzeltilmedi.
- Dünya dönüşü ile yerel çerçevenin taşıma hızı henüz çıkarılmadı. Dünya'ya bağlı
  ENU referansı ile ham açısal hız integrasyonu bu nedenle tam eşdeğer değildir.
- Saatlerin fiziksel ofseti/drifti kalibre edilmedi. Yakın zaman damgaları yeterli kanıt değildir.
- Nominal IMU-SPAN yön hizası kullanıldı; gerçek küçük montaj farkları bilinmiyor.
- Q kodlarına göre eleme yapılmadı; referans da bir GNSS/INS kestirimidir.
- 60 s'lik farklar nihai navigasyon performansı veya fiziksel bias doğruluğu değildir.

Sonraki adımlar: zaman ve yön tutarlılığını başka hareketlerle kontrol etmek,
Dünya dönüşü/yerel çerçeve modelini eklemek, ardından doğrulanmış duruş aralığından
başlangıç jiroskop düzeltmesini aynı koşullarda karşılaştırmak.
