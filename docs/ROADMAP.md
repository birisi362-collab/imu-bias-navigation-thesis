# Çalışma planı

## 01 — Veriyi anlama (tamamlandı)

IMU ve ayrı referans okunur; örnek aralıkları, eksik veriler ve zaman kapsamı
incelenir. Çıktı: veri kontrol raporu, grafikler ve zaman eşleme tablosu.
Bu aşamadan model doğruluğu veya fiziksel bias hakkında başarı iddiası çıkarılmaz.

## 02 — Klasik yönelim hesabı (devam ediyor)

İlk ham jiroskop quaternion tanısı eklendi: `evaluate_orientation.py`.
Sabit başlangıç jiroskop ortalamasıyla aynı koşullu karşılaştırma eklendi:
`compare_initial_correction.py` ve `docs/INITIAL_CORRECTION.md`.
Nominal kaynak konvansiyonları ve başlangıç referansı bir kez kullanılır.
Fiziksel saat/montaj kalibrasyonu, Dünya dönüşü/taşıma hızı ve kapsamlı klasik
kalibrasyon henüz tamamlanmadı. Sınırlar: `docs/ORIENTATION.md`.

- Kaynağın koordinat ve yönelim konvansiyonlarını doğrulama.
- IMU ile referans arasındaki sabit montaj dönüşümünü uygulama.
- Jiroskop entegrasyonunu quaternion/dönüş matrisi ile kurma ve fiziksel kontroller.
- Aynı başlangıç yönelimiyle, referansla sürekli sıfırlamadan ilerleme.
- Düzeltmesiz ve klasik kalibrasyonlu yönelim hatalarını ölçme.

## 03 — İlk öğrenilmiş jiroskop düzeltmesi

- Geçmiş IMU penceresinden üç eksen bias düzeltmesi kestirimi.
- Referans yönelim farkına dayanan, mekanizasyondan geçen eğitim kaybı.
- Eğitim/doğrulama/test ayrımını kayıt düzeyinde yapma; örtüşen pencereleri bölmeme.
- Testte gelecekteki IMU'yu veya referansı model girdisi olarak kullanmama.
- Basit klasik kalibrasyona karşı, kısa aralık ve kesintisiz ilerleme karşılaştırması.
- Ölçülen düzeltmenin fiziksel bias dışında hangi hataları telafi ettiğini inceleme.

## 04 — İvmeölçer, konum ve GNSS/INS ESKF

- Yönelim dönüşümü ve yerçekimi hesabını doğrulama.
- Konum, hız, yönelim ve bias durumları olan klasik ESKF başlangıcını kurma.
- GNSS ham gözlemlerinden ölçüm çözümü oluşturma veya doğrulanmış çözümü kullanma.
- GNSS kalitesi ve referans belirsizliği; P/Q/R ayarlarını eğitim dışı testle karıştırmama.
- Öğrenilmiş modelle filtre bias durumlarını tutarlı bağlama; biası iki kez çıkarmama.
- Kara aracı kısıtları kullanılacaksa bütün karşılaştırmalarda aynı koşulları uygulama.

## 05 — Kullanım sırasında öğrenme

- İlk karşılaştırma: klasik yöntem / sabit ağırlıklı öğrenilmiş model / çevrim içi uyarlanan model.
- Güvenilir GNSS'den öğrenme sinyali; bağımsız değerlendirme referansını gizli tutma.
- İlk protokolde kesinti sırasında ağırlıkları dondurma, bias tahminini sürdürme.
- Yazılımla maskelenen 10/30/60 s GNSS kesintileri; referansı ve başlangıç koşullarını koruma.
- Yalnız son metre hatası değil, hata büyümesi ve tekrarlar arasındaki değişimi ölçme.

## 06 — Kendi sensörümüz

Hazır veride yöntem çalıştıktan sonra senkron kayıt düzeneği, montaj ölçüleri,
sıcaklık ve farklı gün/rota kayıtları. STIM300 şart değil. Fiziksel bias doğruluğu
iddiası için kontrollü deney gerekir; referans yörünge tek başına tam bias etiketi değildir.
