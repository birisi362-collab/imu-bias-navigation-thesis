# İlk gerçek veri çalıştırması — 27 Ekim 2026

Kaynak: UrbanNav-HK-Medium-Urban-1. İki veri dosyası indirildi; tam IMU kaydı
ve tam referans dosyası üzerinde `inspect_urbannav.py` başarıyla çalıştırıldı.
Yalnızca başlangıç kesiti değil, dosyaların tamamı incelendi.

## Gözlenen sonuçlar

| Kontrol | Sonuç |
|---|---:|
| IMU örneği | 314.194 |
| Referans örneği | 787 |
| IMU medyan örnekleme frekansı | 400,3345 Hz |
| Referans medyan örnekleme frekansı | 1 Hz |
| Ortak zaman kapsamı | 785,4514 s |
| Tekrarlı / geriye giden IMU zaman adımı | 0 / 0 |
| Sonlu olmayan ölçüm değeri | 0 |
| Üç medyan örnek aralığını aşan IMU boşluğu | 4 |
| En büyük IMU zaman aralığı | 10,2179 ms |
| Ortak kapsam içindeki referans anları | 786 |
| 10 ms toleransla en yakın IMU eşleşmesi | 786 / 786 |
| Eşleşmelerde en büyük mutlak zaman uzaklığı | 1,9450 ms |

Referansın ilk anı IMU kaydından önce geldiği için eşleme tablosuna alınmadı.
Q kodları: 1 → 56 satır, 2 → 590 satır, 3 → 125 satır, 4 → 16 satır.
Bu kodların sayılması, hepsinin yeterli doğrulukta olduğu anlamına gelmez.

## Tekrar üretim

```powershell
python -m pip install -r requirements.txt
python download_data.py
python inspect_urbannav.py --imu data/raw/medium/xsense_imu_medium_urban1.csv --reference data/raw/medium/UrbanNav_TST_GT_raw.txt --output outputs/medium
python -m unittest discover -s tests -v
```

Otomatik kontroller: **9 test geçti**. NumPy 2.3.5, pandas 2.2.3,
Matplotlib 3.10.8 ile çalıştırıldı. Üç grafikte eksenler, birimler ve yerel
yörünge görsel olarak incelendi.

İndirilen dosyaların SHA-256 değerleri (yayımlayıcı doğruluk sertifikası değil,
bu çalıştırmadaki veri sürümünün parmak izi):

```text
xsense_imu_medium_urban1.csv
6a3e0ab0209e032296dc750a491e27a4919473c875c5ec8f2dcd1bd3d796537d

UrbanNav_TST_GT_raw.txt
9d48bb497878aafbd17290789560394c72ecafec20c9e0eaff448418695d92bf
```

## Henüz doğrulanmayanlar

Saat ofseti/drifti, gerçek eksen ve montaj dönüşümleri, Q kodlarının anlamı,
referansın her bölümdeki fiziksel doğruluğu ve bias kestirilebilirliği.
Görülen zaman yakınlığı, bunların doğrulandığı anlamına gelmez.

Bu sürüm bir navigasyon başarımı veya öğrenilmiş bias sonucu raporlamıyor.
Sonraki adım kaynak konvansiyonlarını doğrulayıp klasik yönelim hesabını kurmak.
