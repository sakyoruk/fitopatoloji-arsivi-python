# Fitopatoloji Arşivi 2.0 RC3

Windows 7 SP1 64 bit hedefli, tamamen yerel çalışan fitopatoloji kayıt ve bilimsel çalışma uygulaması.

Teknoloji: Python 3.8, Tkinter, SQLite ve PyInstaller. Hedef bilgisayarda Python veya SQLite kurulumu gerekmez.

## 2.0 RC3 yenilikleri

- DOSYA, KAYIT, FOTOĞRAF, ANALİZ ve YARDIM sekmeli yeni komut şeridi
- Seçili kayıt için kayıt bütünlüğü ve eksik bilgi önerileri
- Yeni açılış ekranı ve Hakkında penceresi
- Mevcut fotoğraf, rapor, monografi, çalışma alanı, bilgi ağı ve bakım araçlarıyla bütünleşik kullanım

## GitHub Actions ile derleme

GitHub deposunda **Actions** sekmesine girin, **Fitopatoloji Arsivi 2.0 RC3 derle** iş akışını seçin ve **Run workflow** düğmesine basın. Başarılı çalışmanın artifact bölümünden `FitopatolojiArsivi-2.0-RC3-Windows` paketini indirin.

İş akışı önce bütün Python modüllerini derleme kontrolünden geçirir, ardından veritabanı CRUD, gelişmiş arama, teşhis ve SQLite yedekleme self-testlerini çalıştırır.

> Bu sürüm Release Candidate niteliğindedir. Gerçek arşivle kullanmadan önce mevcut `Data`, `Images`, `Documents` ve `Backups` klasörlerinizi yedekleyin.


## RC3 güvenlik ve tanılama
RC3, şema yükseltmesinden önce otomatik veritabanı kopyası oluşturur ve kişisel içerik eklemeyen tanılama paketi hazırlayabilir. Ayrıntılar için `KULLANIM_KILAVUZU.md` dosyasına bakın.

## RC3 veri modeli

Konukçu araması artık hastalık açıklama metnindeki kelimelere göre değil, `host_catalog` ve `disease_hosts` tablolarındaki açık ilişkilere göre yapılır. Taksonomi ve konukçu katalogları sol ana menüden açılır.
