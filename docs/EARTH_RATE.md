# Dünya dönüşünü başlangıç ortalamasından ayırma

Amaç: Kalan farkı doğrudan değişen bias kabul etmeden önce bilinen bir fiziksel
etkinin katkısını aynı koşullarda ölçmek. Bu sabit başlangıç enlemi deneyidir;
taşıma hızı ve enlem değişimi yoktur. Tam INS mekanizasyonu değildir.

## Model

WGS 84 nominal Dünya açısal hızı Ω = 7,292115e-5 rad/s.
Başlangıç enlemi φ için Doğu/Kuzey/Yukarı bileşenleri:

`omega_earth_ENU = [0, Ω cos(φ), Ω sin(φ)]`.

Gövde→ENU quaternion'ında gövde dönüşü sağdan, çerçeve dönüşü soldan uygulanır:

`q_next = Exp(-omega_earth_ENU * dt) ⊗ q ⊗ Exp(omega_gyro * dt)`.

Burada Exp, dönüş vektörünü birim quaternion'a çeviren fonksiyondur.
Gövde hızı için önceki aralık ortalaması ve zaman/boşluk kontrolleri korunur.
Enlem ilk kalibrasyon referansından bir kez alınır. Sonraki referansın
konumu/yönelimi integrasyona girmez. Başlangıç konum/yönelim kaynağı referanstır;
bağımsız başlatma veya sıfır gecikmeli canlı uygulama iddiası yoktur.

## Aynı Dünya dönüşünü iki kez çıkarmamak

İlk 5 saniyedeki ortalama m zaten başlangıçtaki Dünya dönüşünü içerir.
Kalibrasyonun ilk referans yönelimi q_cal ve duruş adayı varsayımıyla:

`earth_body_initial = R(q_cal)^T * omega_earth_ENU`

`offset_earth_separated = m - earth_body_initial`.

İlk kalibrasyon yönelimi kısa aralık boyunca sabit kabul edilir. Hareket veya
montaj hatası varsa bu ayrım da hatalı olabilir; elde edilen ofset saf bias etiketi değildir.
Duruş adayı eşikleri önceki deneyle aynıdır; sonuçlara göre ayarlanmaz.

| Eğri | Jiroskoptan çıkarılan | Soldan çerçeve düzeltmesi |
|---|---|---|
| raw | 0 | yok |
| fixed | m | yok |
| earth_only | 0 | Dünya dönüşü |
| fixed_earth | m - earth_body_initial | Dünya dönüşü |

Kalibrasyon ve değerlendirme zamanları ayrıdır. Dört hesap aynı başlangıç,
süre, örnekler ve referans anlarını kullanır. Çıktı CSV her hesabın quaternion'ını,
fark vektörünü ve toplam açısını içerir; JSON model ve ofsetleri kaydeder.

## Doğrulama

- Ekvator ve iki kutupta ENU bileşenleri.
- Farklı başlangıç yöneliminde Dünya'ya göre duran ideal jiroskop:
  çerçeve düzeltmesiyle yönelim sabit, ham fark Ωt.
- Birbiriyle değişmeli olmayan gövde ve çerçeve dönüşleriyle analitik kontrol.
- Sabit bias eklenmiş, kalibrasyondan sonra dönen sentetik araç: bias ayrımı,
  düzeltmenin iki kez çıkarılmaması ve ilerideki referansın tahmini değiştirememesi.
- Önceki 19 kontrol dahil toplam 23 test geçti.

## Fiziksel ölçek ve sınırlar

60 saniyede Ωt ≈ 0,250685°, 600 saniyede ≈ 2,506845°.
Bunlar Dünya dönüşünün açı ölçeğidir; belirli bir eksen hatası veya her eğri için
beklenen iyileşme değildir. Dünya dönüşü tek başına 60 saniyedeki ~10° ham farkı açıklamaz.
Düzeltmenin son farkı artırması fiziksel modelin yanlış olduğunu tek başına göstermez;
birden fazla hata vektörü birbirini kısmen telafi ediyor olabilir.

Hareketli yerel ENU taşıma hızı, saat ofseti/drifti, gerçek montaj hizası,
ölçek/ısı hataları ve referans belirsizliği henüz çözülmedi. Daha uzun veya farklı
kayıtlarda deney, bu yaklaşımı tam mekanizasyon hâline getirmez.

## Gerçek kayıt — 9 Kasım 2026

FIRST_RUN.md ile aynı SHA-256 değerlerine sahip UrbanNav Medium-Urban-1 dosyaları
tekrar indirildi. Önceki 5/60 saniye protokolü değişmedi. Başlangıç enlemi:
22.301199858333334 derece.

| Hesap | 60 saniye sonunda toplam yönelim farkı |
|---|---:|
| Ham | 10,413098° |
| Eski sabit ortalama | 1,604151° |
| Yalnız Dünya dönüşü | 10,421600° |
| Dünya dönüşünden ayrılmış ofset + Dünya dönüşü | 1,635617° |

Eski ham ve sabit düzeltmeli sonuçlar yeniden üretildi. Dünya modeli bu kesitte
son farkı küçültmedi. Bu, fiziksel modelin yanlış olduğunun veya bias'ın değiştiğinin
kanıtı değildir. Yalnız son noktaya göre yöntem seçilmemeli. Grafikte sabit düzeltmeli
iki eğri birbirine yakın; ham iki eğri yaklaşık 10,4°'ye ulaşıyor.

## Kaynaklar

- [NGA WGS 84](https://earth-info.nga.mil/index.php?action=wgs84&dir=wgs84): nominal Dünya dönüşü.
- [NASA model sabitleri](https://ntrs.nasa.gov/api/citations/20150001264/downloads/20150001264.pdf): Ω sayısal değeri.
- [VectorNav jiroskop ve gyrocompassing](https://www.vectornav.com/resources/inertial-navigation-primer/theory-of-operation/theory-gyros): Dünya hızının yatay/düşey bileşenleri.
- Gövde/ENU ve IE konvansiyonları: ORIENTATION.md.
