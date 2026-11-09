"""Fixed Indonesian replies. The LLM never writes these, so an attacker cannot shape them."""

SECURITY_REFUSAL_MESSAGE = (
    "Maaf, permintaan ini tidak bisa saya proses karena berkaitan dengan akses atau keamanan data. "
    "Silakan ajukan pertanyaan lain seputar unit, kontrak, tagihan, pembayaran, atau denda."
)

GIVE_UP_MESSAGE = (
    "Maaf, saya belum berhasil menyusun jawaban untuk pertanyaan ini setelah beberapa kali "
    "mencoba. Coba ulangi dengan pertanyaan yang lebih spesifik, misalnya sebutkan nama customer, "
    "nomor unit, atau periodenya."
)

# Neutral on purpose: it must not reveal whether the data exists for another agent
SALES_EMPTY_MESSAGE = "Tidak ditemukan data yang sesuai dalam data yang dapat Anda akses."

CLARIFY_FALLBACK_MESSAGE = (
    "Bisa tolong jelaskan pertanyaannya lebih rinci, misalnya nama customer, nomor unit, "
    "atau periodenya?"
)
