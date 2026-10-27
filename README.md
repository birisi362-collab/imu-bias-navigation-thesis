# IMU Bias Navigation Thesis

Kara araçlarında öğrenme tabanlı IMU bias modelleme ve GNSS/INS navigasyonu için
adım adım geliştirilen tez uygulaması.

**Mevcut sürüm: Aşama 01 — gerçek veriyi okuma, zaman kontrolü ve grafikler.**
Henüz bias öğrenen ağ, mekanizasyon, ESKF veya GNSS kesintisi değerlendirmesi yok.
Bu sürümün amacı, bu hesapları kuracağımız veriyi doğru anlamak.

## İlk çalıştırma — Windows / VS Code

Python 3.11 veya üzeriyle proje klasöründe terminal açın:

```powershell
python -m pip install -r requirements.txt
python download_data.py
python inspect_urbannav.py --imu data/raw/medium/xsense_imu_medium_urban1.csv --reference data/raw/medium/UrbanNav_TST_GT_raw.txt --output outputs/medium
```

Sanal ortam zorunlu değildir. Kullanıyorsanız önce onu etkinleştirin. İndirme ve
inceleme iki ayrı adımdır; yerel dosyalarla inceleme internet istemez.
Bu aşama ROS veya GPU gerektirmez. Birden fazla Python kurulumu varsa komutları
VS Code'da seçtiğiniz aynı yorumlayıcı ile çalıştırın.

İndirme betiği yalnızca IMU CSV ve referans TXT dosyasını alır; onlarca GB boyutundaki
kamera/LiDAR ROS bag dosyasını indirmez. Kayıt dosyaları ve çıktılar Git'e eklenmez.
Mevcut dosyaları yenilemek için `python download_data.py --force` kullanılır.

### Dosyaları elle indirmek isterseniz

- [Xsens IMU CSV](https://www.dropbox.com/s/2rh1rs15ihpf63u/xsense_imu_medium_urban1.csv?dl=1)
- [SPAN-CPT + IE referans TXT](https://www.dropbox.com/s/twsvwftucoytfpc/UrbanNav_TST_GT_raw.txt?dl=1)
- [Kaynağın güncel açıklaması ve alternatif bağlantıları](https://github.com/IPNL-POLYU/UrbanNavDataset#urbannav-hk-medium-urban-1)

Dropbox veri yerine HTML veya kısmi içerik döndürürse betik hata verir; eksik dosyayı
başarılı indirme saymaz. Tarayıcıdan indirip gerçek yerel yolları belirtebilirsiniz:

```powershell
python inspect_urbannav.py --imu "C:/Tez/Veriler/xsense_imu_medium_urban1.csv" --reference "C:/Tez/Veriler/UrbanNav_TST_GT_raw.txt" --output "C:/Tez/Sonuclar/medium"
```

## Ne üretiyor?

`outputs/medium/` içinde:

| Dosya | İçerik |
|---|---|
| `quality_report.json` | Örnek sayısı, medyan frekans, zaman sıralaması, boşluklar, ortak kapsam ve uyarılar |
| `imu_signals.png` | Üç eksen açısal hız (rad/s) ve özgül kuvvet (m/s²) |
| `reference_motion.png` | Referans roll/pitch/heading, hız büyüklüğü ve yaklaşık yerel yörünge |
| `timing.png` | Her iki dosyanın gerçek örnek aralıkları |
| `reference_epochs_with_nearest_imu.csv` | Her referans anına tolerans içinde en yakın gerçek IMU örneği |

Programın çıkış kodu başarıda `0`, geçersiz giriş veya ciddi zaman hatalarında `2`.
Sırası bozuk/tekrarlı zamanlar sessizce düzeltilmez; kalite raporu oluşturulur ve
grafik aşaması durdurulur. Zaman boşlukları ve eşlenemeyen örnekler ayrıca raporlanır.

**Eşlenmiş CSV bir bias etiket dosyası değildir.** En yakın tek IMU ölçümünü 1 Hz
referansla yan yana koyar. Mekanizasyonda iki referans anı arasındaki yaklaşık
400 IMU örneğinin tamamını işleyeceğiz; bu CSV'yi 1 Hz IMU girdisi olarak kullanmayacağız.

## Veriyle ilgili kararlarımız

- İlk kayıt **UrbanNav-HK-Medium-Urban-1**. Kaynağa göre Honda Fit üzerinde Xsens
  MTi-10 yaklaşık 400 Hz, SPAN-CPT + Inertial Explorer referansı yaklaşık 1 Hz.
- IMU'daki `field.header.stamp` nanosaniye tamsayısı olarak korunur. Saniyeye
  çevirmeden önce ortak başlangıç zamanı çıkarılır; büyük Unix zamanları yüzünden
  oluşabilecek kayan nokta hassasiyet kaybından kaçınılır.
- Referansın `UTCTime` sütunu kullanılır. `GPSTime`, GPS hafta içi saniyesidir;
  UTC ile doğrudan aynı sayı değildir. İki zaman ölçeği körlemesine birleştirilmez.
- `%time` mesaj kayıt zamanı, `field.header.stamp` ise mesajın sensör zaman damgasıdır.
  Farklı bir seçim gerekirse `--imu-time-column "%time"` açıkça belirtilir.
  Alan adının sensör zamanı olması, donanımsal senkronizasyonu tek başına kanıtlamaz.
- IMU'nun `orientation.*` alanı kendi AHRS çıktısıdır; bağımsız ground truth olarak
  kullanılmaz. Referans ayrı SPAN-CPT + IE dosyasından okunur.
- Referans enlem/boylamı derece-dakika-saniye biçiminde, üçer alan olarak okunur.
  `VelBdy*` alanları gövde eksenlerindedir; dünya ekseni hızları diye adlandırılmaz.
- Referanstaki `Q` kodu korunur ve sayılır. Kodun anlamı doğrulanmadan bir RTK
  kalite etiketi veya doğruluk garantisi kabul edilmez; hiçbir Q grubu gizlice elenmez.
- Şimdilik eksen dönüşümü, lever arm, otomatik saat kaydırma veya kalibrasyon yok.
  Grafikler birbiriyle hizalanmış yönelim hata grafiği değildir. Özellikle heading
  ile jiroskop z ekseni doğrudan eşit kabul edilmez.
- `--reference-time-offset-s` yalnızca belgelenmiş bir saat farkı için kullanılmalı;
  test hatasını düşürmek amacıyla referans üzerinde ayar yapılmamalı.
- Grafiklerde IMU çizgileri seyreltilir; rapor hesapları ve zaman boşluğu grafikleri
  bütün örnekleri kullanır. Yerel yörünge çizimi küçük alan için yaklaşık bir
  izdüşümdür; nihai konum hata ölçütü değildir.

## Dosyaları hangi sırayla inceleyelim?

1. `inspect_urbannav.py`: program akışı ve komut satırı girdileri.
2. `imu_thesis/data.py`: sütunlar, zaman ve koordinat okuma.
3. `imu_thesis/audit.py`: veri kalitesi ve zaman eşleme.
4. `imu_thesis/plots.py`: ölçümleri görünür kılma.
5. `docs/ROADMAP.md`: sonraki deneylerin kapsamı.

## Kontroller

```powershell
python -m unittest discover -s tests -v
```

Testler sentetik küçük örneklerle nanosaniye hassasiyetini, UTC/DMS okumasını,
sırası bozuk zamanları, boşlukları ve eşleme sınırlarını kontrol eder. Gerçek veri
üzerindeki çalıştırmanın gözlemleri `docs/FIRST_RUN.md` dosyasında tutulur.

## Kaynak ve atıf

Veri: [IPNL-POLYU/UrbanNavDataset](https://github.com/IPNL-POLYU/UrbanNavDataset).
Ham ölçümler bu depoda yeniden yayımlanmıyor. Veri kullanım koşulları için kaynak
deponun güncel lisansı ve açıklamaları esas alınmalı.

Hsu, L.-T., Huang, F., Ng, H.-F., Zhang, G., Zhong, Y., Bai, X., & Wen, W. (2023).
*Hong Kong UrbanNav: An open-source multisensory dataset for benchmarking urban
navigation algorithms*. NAVIGATION, 70(4). https://doi.org/10.33012/navi.602
