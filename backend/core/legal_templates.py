"""Starter legal texts (EN + KM). TEMPLATES ONLY: a qualified Cambodian lawyer must review them
before real guests use the system. Published versions are immutable; edit by publishing a new version."""

NOTICE_EN = '> **Template notice:** this text is a starter draft pending legal review.\n\n'
NOTICE_KM = '> **ចំណាំ៖** អត្ថបទនេះជាគំរូដំបូង ដែលត្រូវការការពិនិត្យផ្លូវច្បាប់មុនប្រើប្រាស់ជាផ្លូវការ។\n\n'

TEMPLATES = {
    'TERMS': {
        'en': ('Terms and Conditions', """# Terms and Conditions

1. **Who we are.** Luma Haven ("the Hotel") operates this website and booking service in Phnom Penh, Cambodia.
2. **Bookings.** A booking is confirmed only when the required payment is received and a confirmation is shown. Prices are quoted in the displayed currency and are valid for the quote period shown.
3. **Guest duties.** You must give accurate information, present valid identification at check-in when requested, and respect hotel rules and other guests.
4. **Occupancy.** Rooms may be occupied only by the registered number of guests. Damage caused by guests may be charged to the folio.
5. **Liability.** The Hotel is not liable for loss of valuables not deposited with reception, except where the law requires otherwise.
6. **Changes.** We may update these terms. The version you accepted at booking applies to that booking.
7. **Governing law.** The laws of the Kingdom of Cambodia apply; disputes are first handled by good-faith discussion.
"""),
        'km': ('លក្ខខណ្ឌប្រើប្រាស់', """# លក្ខខណ្ឌប្រើប្រាស់

1. **អ្នកផ្តល់សេវា។** Luma Haven («សណ្ឋាគារ») គ្រប់គ្រងគេហទំព័រ និងសេវាកក់បន្ទប់នេះនៅភ្នំពេញ ព្រះរាជាណាចក្រកម្ពុជា។
2. **ការកក់។** ការកក់ត្រូវបានបញ្ជាក់ លុះត្រាតែទទួលបានការទូទាត់ត្រឹមត្រូវ ហើយមានការបង្ហាញលេខបញ្ជាក់។ តម្លៃមានសុពលភាពក្នុងរយៈពេលដែលបានបង្ហាញ។
3. **កាតព្វកិច្ចភ្ញៀវ។** អ្នកត្រូវផ្តល់ព័ត៌មានត្រឹមត្រូវ បង្ហាញអត្តសញ្ញាណនៅពេលចូលស្នាក់នៅ (ប្រសិនបើស្នើសុំ) និងគោរពច្បាប់សណ្ឋាគារ។
4. **ចំនួនអ្នកស្នាក់។** បន្ទប់អាចស្នាក់បានតែចំនួនភ្ញៀវដែលបានចុះឈ្មោះប៉ុណ្ណោះ។ ការខូចខាតដែលបណ្តាលដោយភ្ញៀវអាចត្រូវគិតលើវិក្កយបត្រ។
5. **ការទទួលខុសត្រូវ។** សណ្ឋាគារមិនទទួលខុសត្រូវចំពោះការបាត់ទ្រព្យមានតម្លៃដែលមិនបានដាក់នៅការិយាល័យទទួលភ្ញៀវទេ លើកលែងតែច្បាប់កំណត់ផ្សេង។
6. **ការផ្លាស់ប្តូរ។** យើងអាចធ្វើបច្ចុប្បន្នភាពលក្ខខណ្ឌនេះ។ កំណែដែលអ្នកបានទទួលយកពេលកក់ ត្រូវអនុវត្តចំពោះការកក់នោះ។
7. **ច្បាប់អនុវត្ត។** ច្បាប់នៃព្រះរាជាណាចក្រកម្ពុជាត្រូវអនុវត្ត ហើយវិវាទត្រូវដោះស្រាយដោយការពិភាក្សាដោយស្មោះត្រង់ជាមុន។
"""),
    },
    'PRIVACY': {
        'en': ('Privacy Policy', """# Privacy Policy

**What we collect.** Name, email, phone (optional), booking and stay details, service requests, and payment references. We do **not** store card numbers. Government ID details are collected only when required for check-in and registration.

**Why.** To manage your booking and stay, take payment, send verification codes and confirmations, meet accounting and legal duties, and improve hotel operations.

**Who receives it.** Hosting and database providers (Supabase, Singapore), email delivery, and the payment provider (Bakong / your bank) only as needed. We do not sell personal data.

**How long we keep it.**
- Accounting records (folios, payments, refunds): 10 years.
- Guest profile (name, email, phone): anonymised 3 years after your last stay.
- ID details: only for the stay and legal registration, at most 1 year.
- One-time codes and expired quotes: deleted within 24 hours.

**Your rights.** You may ask for access, a copy, correction or deletion of your data from your booking page or by contacting the hotel. We answer within 30 days. Accounting records we must keep are retained in anonymised form.

**Security.** Access is role-based, sessions use secure cookies, and sensitive actions are logged.

**Contact.** Use the hotel contact details on the website.
"""),
        'km': ('គោលការណ៍ឯកជនភាព', """# គោលការណ៍ឯកជនភាព

**ទិន្នន័យដែលយើងប្រមូល។** ឈ្មោះ អ៊ីមែល ទូរស័ព្ទ (ស្រេចចិត្ត) ព័ត៌មានកក់ និងការស្នាក់នៅ សំណើសេវា និងលេខយោងការទូទាត់។ យើង **មិន** រក្សាទុកលេខកាតទេ។ ព័ត៌មានអត្តសញ្ញាណត្រូវប្រមូលតែពេលចាំបាច់សម្រាប់ការចុះឈ្មោះចូលស្នាក់នៅប៉ុណ្ណោះ។

**ហេតុផល។** ដើម្បីគ្រប់គ្រងការកក់ និងការស្នាក់នៅ ទទួលការទូទាត់ ផ្ញើលេខកូដផ្ទៀងផ្ទាត់ និងការបញ្ជាក់ បំពេញកាតព្វកិច្ចគណនេយ្យ និងច្បាប់ និងកែលម្អប្រតិបត្តិការ។

**អ្នកទទួលទិន្នន័យ។** អ្នកផ្តល់សេវាបណ្តាញ/មូលដ្ឋានទិន្នន័យ (Supabase សិង្ហបុរី) សេវាផ្ញើអ៊ីមែល និងអ្នកផ្តល់សេវាទូទាត់ (Bakong / ធនាគារ) តែតាមការចាំបាច់។ យើងមិនលក់ទិន្នន័យផ្ទាល់ខ្លួនទេ។

**រយៈពេលរក្សាទុក។**
- កំណត់ត្រាគណនេយ្យ (វិក្កយបត្រ ការទូទាត់ ការសងប្រាក់)៖ ១០ ឆ្នាំ។
- ប្រវត្តិរូបភ្ញៀវ (ឈ្មោះ អ៊ីមែល ទូរស័ព្ទ)៖ លុបអត្តសញ្ញាណបន្ទាប់ពី ៣ ឆ្នាំ ក្រោយការស្នាក់នៅចុងក្រោយ។
- ព័ត៌មានអត្តសញ្ញាណ៖ សម្រាប់ការស្នាក់នៅ និងការចុះឈ្មោះតាមច្បាប់ យូរបំផុត ១ ឆ្នាំ។
- លេខកូដម្តងប្រើ និងសម្រង់តម្លៃផុតកំណត់៖ លុបក្នុងរយៈពេល ២៤ ម៉ោង។

**សិទ្ធិរបស់អ្នក។** អ្នកអាចស្នើសុំចូលមើល ចម្លង កែតម្រូវ ឬលុបទិន្នន័យ តាមទំព័រការកក់ ឬទាក់ទងសណ្ឋាគារ។ យើងឆ្លើយតបក្នុងរយៈពេល ៣០ ថ្ងៃ។ កំណត់ត្រាគណនេយ្យដែលត្រូវរក្សាទុក នឹងត្រូវរក្សាក្នុងទម្រង់គ្មានអត្តសញ្ញាណ។

**សុវត្ថិភាព។** ការចូលប្រើផ្អែកលើតួនាទី សម័យប្រើខូគីសុវត្ថិភាព ហើយសកម្មភាពរសើបត្រូវបានកត់ត្រា។

**ទំនាក់ទំនង។** សូមប្រើព័ត៌មានទំនាក់ទំនងរបស់សណ្ឋាគារនៅលើគេហទំព័រ។
"""),
    },
    'CANCELLATION': {
        'en': ('Booking and Cancellation Policy', """# Booking and Cancellation Policy

- **Hold:** an unpaid booking is held for 15 minutes, then released.
- **Check-in / check-out:** times are shown on your booking. Valid identification may be required.
- **Cancellation:** cancel unpaid bookings any time. For paid bookings, contact the hotel; refund eligibility is decided by the hotel under the rate conditions shown at booking.
- **No-show:** a booking not checked in by the end of the arrival day may be marked no-show and the room released.
- **Refunds:** refunds are reviewed by two hotel staff members and returned through the original payment method where possible.
"""),
        'km': ('គោលការណ៍កក់ និងលុបចោល', """# គោលការណ៍កក់ និងលុបចោល

- **រក្សាទុក៖** ការកក់ដែលមិនទាន់បង់ប្រាក់ ត្រូវបានរក្សាទុក ១៥ នាទី រួចដោះលែង។
- **ចូល/ចេញ៖** ម៉ោងបង្ហាញលើការកក់របស់អ្នក។ អាចត្រូវការអត្តសញ្ញាណត្រឹមត្រូវ។
- **ការលុបចោល៖** អាចលុបការកក់ដែលមិនទាន់បង់ប្រាក់គ្រប់ពេល។ សម្រាប់ការកក់ដែលបានបង់ សូមទាក់ទងសណ្ឋាគារ ហើយសិទ្ធិសងប្រាក់ត្រូវសម្រេចតាមលក្ខខណ្ឌតម្លៃពេលកក់។
- **មិនមកដល់៖** ការកក់ដែលមិនចូលស្នាក់នៅមុនចុងថ្ងៃមកដល់ អាចត្រូវកត់ត្រាថាមិនមកដល់ ហើយបន្ទប់ត្រូវដោះលែង។
- **ការសងប្រាក់៖** ត្រូវពិនិត្យដោយបុគ្គលិកពីរនាក់ ហើយសងតាមមធ្យោបាយទូទាត់ដើមនៅពេលអាចធ្វើបាន។
"""),
    },
    'COOKIES': {
        'en': ('Cookie Notice', """# Cookie Notice

We use only **strictly necessary** cookies: a session cookie to keep your booking access and a CSRF cookie to protect forms. We do not use advertising or analytics cookies. If that changes, we will ask for your consent first.
"""),
        'km': ('សេចក្តីជូនដំណឹងអំពីខូគីស', """# សេចក្តីជូនដំណឹងអំពីខូគីស

យើងប្រើតែខូគីស **ចាំបាច់ប៉ុណ្ណោះ**៖ ខូគីសសម័យដើម្បីរក្សាសិទ្ធិចូលមើលការកក់ និងខូគីស CSRF ដើម្បីការពារទម្រង់បែបបទ។ យើងមិនប្រើខូគីសផ្សព្វផ្សាយ ឬវិភាគទេ។ ប្រសិនបើមានការផ្លាស់ប្តូរ យើងនឹងសុំការយល់ព្រមជាមុន។
"""),
    },
    'PAYMENT': {
        'en': ('Payment Terms', """# Payment Terms

- Payments are made by QR code through supported Cambodian banking apps (Bakong KHQR) when enabled.
- The amount and currency shown at checkout are final. A QR code expires after a short time; scan only the QR shown on your booking page.
- A booking is confirmed only after the hotel server verifies the payment. If a payment arrives after a hold expires, the hotel will contact you to rebook or refund.
- We never ask for your banking password or PIN.
"""),
        'km': ('លក្ខខណ្ឌទូទាត់', """# លក្ខខណ្ឌទូទាត់

- ការទូទាត់ធ្វើឡើងតាម QR code តាមកម្មវិធីធនាគារកម្ពុជា (Bakong KHQR) នៅពេលបើកដំណើរការ។
- ចំនួនទឹកប្រាក់ និងរូបិយប័ណ្ណដែលបង្ហាញពេលទូទាត់ជាចុងក្រោយ។ QR code ផុតកំណត់ក្នុងរយៈពេលខ្លី សូមស្កែនតែ QR ដែលបង្ហាញលើទំព័រការកក់របស់អ្នក។
- ការកក់ត្រូវបានបញ្ជាក់ក្រោយពេលម៉ាស៊ីនបម្រើសណ្ឋាគារផ្ទៀងផ្ទាត់ការទូទាត់ប៉ុណ្ណោះ។ ប្រសិនបើការទូទាត់មកដល់ក្រោយការរក្សាទុកផុតកំណត់ សណ្ឋាគារនឹងទាក់ទងអ្នកដើម្បីកក់ឡើងវិញ ឬសងប្រាក់។
- យើងមិនដែលសុំពាក្យសម្ងាត់ ឬលេខ PIN ធនាគាររបស់អ្នកទេ។
"""),
    },
    'STAFF_AGREEMENT': {
        'en': ('Staff Acceptable Use and Confidentiality Agreement', """# Staff Acceptable Use and Confidentiality Agreement

- Use your own account only; never share passwords or sessions.
- Access guest data only when needed for your role. Do not copy, photograph or export guest data for personal use.
- Never ask guests for card numbers or banking passwords.
- Report suspected data exposure or lost devices to a manager immediately.
- Your actions are logged. Confidentiality duties continue after your employment ends.
"""),
        'km': ('កិច្ចព្រមព្រៀងប្រើប្រាស់ និងរក្សាការសម្ងាត់សម្រាប់បុគ្គលិក', """# កិច្ចព្រមព្រៀងប្រើប្រាស់ និងរក្សាការសម្ងាត់សម្រាប់បុគ្គលិក

- ប្រើតែគណនីផ្ទាល់ខ្លួន មិនចែករំលែកពាក្យសម្ងាត់ ឬសម័យប្រើប្រាស់។
- ចូលមើលទិន្នន័យភ្ញៀវតែពេលចាំបាច់តាមតួនាទី។ មិនចម្លង ថតរូប ឬនាំចេញទិន្នន័យភ្ញៀវសម្រាប់ប្រើផ្ទាល់ខ្លួនទេ។
- មិនសុំលេខកាត ឬពាក្យសម្ងាត់ធនាគារពីភ្ញៀវទេ។
- រាយការណ៍ភ្លាមៗទៅអ្នកគ្រប់គ្រង ប្រសិនបើសង្ស័យថាទិន្នន័យលេចធ្លាយ ឬបាត់ឧបករណ៍។
- សកម្មភាពរបស់អ្នកត្រូវបានកត់ត្រា។ កាតព្វកិច្ចរក្សាការសម្ងាត់បន្តក្រោយពេលឈប់ធ្វើការ។
"""),
    },
}
