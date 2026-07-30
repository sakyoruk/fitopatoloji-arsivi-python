# Fitopatoloji Arşivi 2.0 RC2 Kullanıcı Kılavuzu

## İlk çalıştırma
Uygulamayı yazma izni bulunan bir klasörde çalıştırın. `Data`, `Images`, `Documents`, `Backups` ve `Exports` klasörleri otomatik oluşturulur. Eski veritabanı algılanırsa şema yükseltmesinden önce `Backups` klasörüne `PreMigration_RC2_...db` adıyla güvenlik kopyası alınır.

## Temel kayıt işlemleri
`Ctrl+N` yeni kayıt, `Ctrl+S` kaydetme, `Ctrl+F` arama ve `Ctrl+K` komut paletidir. Silinen kayıtlar önce Çöp Kutusuna gider. Kayıt geçmişi önceki sürümlere dönmeyi sağlar.

## Fotoğraflar
Fotoğraf Yöneticisi üzerinden çoklu ekleme, başlık/açıklama, ana fotoğraf, sıralama ve anotasyon işlemleri yapılır. Eksik bağlantılar Bakım ve Tanılama Merkezinde listelenir.

## Rapor ve monografi
İncele ekranından tek kayıt PDF/HTML çıktısı; Monografi Oluşturucudan çoklu hastalık kitabı hazırlanır.

## Yedekleme ve bakım
Düzenli olarak Yedekleme komutunu kullanın. Sistem Bakımı ekranında bütünlük kontrolü ve optimizasyon yapılabilir. `VACUUM` işleminden önce ayrıca manuel yedek önerilir.

## Sorun bildirme
`Sorun Bildir` ekranı açıklamanızı, sürüm/işletim sistemi bilgisini, SQLite sağlık özetini ve seçerseniz son hata günlüklerini ZIP dosyasına koyar. Hastalık kayıtları, veritabanı, fotoğraflar ve belgeler pakete eklenmez.

## RC sürümü uyarısı
Bu sürüm bir Release Candidate'dır. Üretim verileriyle kullanmadan önce güncel yedek alın ve temel iş akışlarınızı bir kopya üzerinde deneyin.
