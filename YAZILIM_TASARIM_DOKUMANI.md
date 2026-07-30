# Fitopatoloji Arşivi — Yazılım Tasarım Dokümanı

## Amaç
Windows 7 SP1 x64 ile uyumlu, çevrimdışı çalışan bilimsel fitopatoloji bilgi yönetim sistemi.

## Mimari
Python, Tkinter, SQLite ve PyInstaller. Veriler `Data` altında; dışa aktarımlar `Exports`, yedekler `Backups` altında tutulur.

## Ana veri varlıkları
- Hastalık kaydı ve zengin metin alanları
- Taksonomi kataloğu ve etmen ayrıntıları
- Konukçu kataloğu ile çoktan çoğa hastalık–konukçu ilişkileri
- Normalize edilmiş sinonimler ve eski adlar
- Literatür kataloğu ve hastalık–literatür ilişkileri
- Fotoğraflar, kategoriler, metadata ve sıralama
- Özel bilimsel notlar, geçmiş ve taslaklar

## Arama
Ana arama; hastalık alanları, yapılandırılmış konukçular, normalize sinonimler ve fotoğraf metadatasını kapsar.

## Çıktılar
Rich Text biçimleri HTML/PDF raporlarına aktarılır. Dijital monografi; kapak, içindekiler, hastalık bölümleri, fotoğraflar, yapılandırılmış literatür, ortak kaynakça ve bilimsel indeks üretir.

## Sürüm yolu
RC7.1 bilimsel bilgi sistemi tamamlamaları; RC8 soru bankası ve çalışma/sınav modu; 2.0 Final kararlılık, performans ve dokümantasyon.
