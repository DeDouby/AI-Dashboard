#include "esp_watch.h"
#include "hardware_init.h"   // für recoverI2C()

#define DS3231_TIME_REG 0x00
#define EEPROM_ADDR     0x57

// Hilfsfunktionen
static uint8_t dec2bcd(uint8_t val) { return ((val / 10 * 16) + (val % 10)); }
static uint8_t bcd2dec(uint8_t val) { return ((val / 16 * 10) + (val % 16)); }

// ==================== BEGIN ====================
bool ESPWatch::begin(TwoWire &wire, uint8_t addr) {
    bus = &wire; // Wir merken uns den übergebenen Bus (I2C_RTC)
    _addr = addr;

    // Wir rufen hier KEIN bus->begin() auf, das haben wir schon in hardware_init erledigt
    // Wir prüfen nur, ob die RTC antwortet
    bus->beginTransmission(_addr);
    return (bus->endTransmission() == 0);
}

// ==================== HEALTH ====================
bool ESPWatch::isRTCHealthy() {
    if (!bus) return false;
    bus->beginTransmission(_addr);
    byte error = bus->endTransmission();
    return (error == 0);
}

// ==================== SYNC FROM RTC ====================
bool ESPWatch::syncFromRTC() {
    if (!bus) return false;

    bus->beginTransmission(_addr);
    bus->write(0x00); // Start-Register
    if (bus->endTransmission() != 0) return false;

    bus->requestFrom(_addr, (uint8_t)7);
    if (bus->available() < 7) return false;

    uint8_t sec   = bcd2dec(bus->read() & 0x7F);
    uint8_t min   = bcd2dec(bus->read());
    uint8_t hour  = bcd2dec(bus->read());
    bus->read(); // weekday ignorieren
    uint8_t day   = bcd2dec(bus->read());
    uint8_t month = bcd2dec(bus->read());
    uint8_t year  = bcd2dec(bus->read());

    struct tm t = {};
    t.tm_sec   = sec;
    t.tm_min   = min;
    t.tm_hour  = hour;
    t.tm_mday  = day;
    t.tm_mon   = month - 1;
    t.tm_year  = year + 100;   // Jahre seit 1900

    time_t epoch = mktime(&t);
    struct timeval tv = {epoch, 0};
    settimeofday(&tv, nullptr);

    Serial.printf("RTC Sync OK → %02d:%02d:%02d\n", hour, min, sec);
    return true;
}

// Die anderen Funktionen (writeToRTC, Backup etc.) kannst du später ergänzen.
// Für jetzt reicht erstmal syncFromRTC.

bool ESPWatch::writeToRTC() {
    if (!bus) return false;

    struct tm ti;
    if (!getLocalTime(&ti)) {
        Serial.println("RTC Write: Fehler! Keine Systemzeit vorhanden.");
        return false;
    }

    bus->beginTransmission(_addr);
    bus->write(DS3231_TIME_REG); // Start bei Register 0x00

    // Konvertiere Systemzeit in BCD Format für den Chip
    bus->write(dec2bcd(ti.tm_sec));
    bus->write(dec2bcd(ti.tm_min));
    bus->write(dec2bcd(ti.tm_hour));
    bus->write(dec2bcd(ti.tm_wday + 1)); // DS3231 nutzt 1-7
    bus->write(dec2bcd(ti.tm_mday));
    bus->write(dec2bcd(ti.tm_mon + 1));  // tm_mon ist 0-11, RTC will 1-12
    bus->write(dec2bcd(ti.tm_year - 100)); // Jahre seit 2000

    if (bus->endTransmission() == 0) {
        Serial.printf("RTC Schreiben erfolgreich: %02d:%02d:%02d\n", ti.tm_hour, ti.tm_min, ti.tm_sec);
        return true;
    }
    
    Serial.println("RTC Write: I2C Fehler");
    return false;
}

void ESPWatch::forceRTCAsTimebase() { syncFromRTC(); }
void ESPWatch::writeBackupU32(uint16_t memAddr, uint32_t value) {}
uint32_t ESPWatch::readBackupU32(uint16_t memAddr) { return 0; }
void ESPWatch::markBoot(uint32_t rev) {}
uint32_t ESPWatch::getBootCounter() { return 0; }