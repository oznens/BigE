# Entry kalite/güven hafızası — kanıt sınırı

Tweet '2064005426710986769', Kalite Motoru'nun setup'ı entry bölgesine gelene
kadar sürekli takip ettiğini ve puanların değişebildiğini açıkça anlatır.
Bu nedenle ilk tespit puanı ile gerçek işlem anındaki puan aynı kabul edilemez.

Yeni kayıt akışında fiyat entry'ye ilk kez dokunduğunda o andaki kalite ve
güven değeri 'entry_kalite' / 'entry_guven' snapshot'ı olarak saklanır.
Result Memory yalnız bu gerçek snapshot bulunan TP/STOP sonuçlarını motor
bazında kalite ve güven bandında gösterir. Eski kayıtlar geriye dönük
etiketlenmez.

Arşiv güven puanının kesin performans bantlarını veya otomatik işlem eşiğini
açıklamaz. Onluk güven bantları yalnız BigE gözlem kovasıdır ve
'BigE-observation-bucket-not-Miraz-threshold' olarak işaretlenir.
Bu hafıza otomatik filtre üretmez.
