# Risk Modu Audit

Arşiv tweeti `2062336764656677002`, terminalMiraz'da üç risk modunu doğrudan
açıklar: Güvenli `+1R`, Dengeli `+2R`, Riskli `+3.5R`.

Yeni Journal kayıtları setup oluşturulduğu anda seçili risk modu, hedef R değeri
ve dolar bazındaki 1R büyüklüğünü snapshot olarak saklar. Sonradan global ayar
değişse bile eski setup'ın hangi risk politikasıyla açıldığı kaybolmaz.

Panel her mod için setup sayısını, gerçekleşmiş TP/STOP dağılımını, toplam R'yi ve
dolar risk snapshot kapsamını ayrı gösterir. Legacy kayıtlar risk moduyla geriye
dönük etiketlenmez. Üç kanıtlı değer dışında kullanılan özel hedefler
`custom-bige` olarak işaretlenir ve terminalMiraz modu diye sunulmaz.
