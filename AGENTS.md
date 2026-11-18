# Agent Guidelines for VHDX Ventoy Creator & Manager

Benvenuto nel repository di **VHDX Ventoy Creator & Manager**. Questo documento (`AGENTS.md`) definisce l'architettura del progetto, i vincoli operativi, le linee guida di sviluppo e le best practice per agenti di coding autonomi (Antigravity, Cursor, Claude Code, GitHub Copilot, ecc.).

---

## 1. Project Overview & Purpose

**VHDX Ventoy Creator & Manager** è un'applicazione desktop Windows sviluppata in **Python** e **PySide6 (Qt6)**.
Lo scopo principale è automatizzare completamente il processo di creazione e configurazione di dischi virtuali **VHDX per Native Boot** (avvio bare-metal di Windows direttamente da VHDX senza hypervisor), ottimizzati per l'avvio da chiavette o SSD USB tramite **Ventoy** e il plugin `ventoy_vhdboot`.

### Principali funzionalità gestite:
- **Master VHDX Creation**: Creazione automatica di VHDX con partizionamento UEFI/GPT (FAT32 EFI da 300MB, MSR da 16MB, NTFS per l'OS), applicazione dell'immagine Windows (`.wim` / `.esd`) tramite DISM e iniezione del bootloader UEFI con `bcdboot`.
- **Differential VHDX**: Creazione istantanea di dischi figli differenziali (Parent/Child) per ambienti di test usa-e-getta.
- **Ventoy Integration**: Rilevamento unità USB Ventoy, verifica e download/copia del plugin `ventoy_vhdboot.img`.
- **Driver Injection & Tweaks**: Iniezione offline di driver INF e opzioni di configurazione bootloader (es. disabilitazione Driver Signature Enforcement - DSE).

---

## 2. Technology Stack & Tools

- **Linguaggio**: Python 3.10+ (compatibile fino a 3.12+)
- **GUI Framework**: PySide6 (Qt 6.x)
- **Windows System Tooling**: `diskpart`, `dism`, `bcdboot`, `bcdedit`, `powershell`, Windows Management Instrumentation (via `psutil`)
- **Testing**: `pytest` (mocking intensivo di subprocess e I/O di sistema)
- **Compilazione / Packaging**: Nuitka (`build_nuitka.bat`) e PyInstaller (`build_pyinstaller.bat`)

---

## 3. Architecture & Directory Structure

Il progetto segue una netta separazione delle responsabilità (Separation of Concerns):

```
VHDX-Ventoy-Creator-Manager/
├── core/                     # Logica di business e integrazione di sistema (NO dipendenze dirette dalla UI)
│   ├── dism_engine.py        # Parsing WIM/ESD, DISM apply-image, iniezione driver INF
│   ├── system_executor.py    # Subprocess execution sicura con streaming real-time e cancel token
│   ├── ventoy_engine.py      # Rilevamento unità USB Ventoy e gestione plugin ventoy_vhdboot
│   └── vhd_engine.py         # Scripting diskpart, layout GPT/EFI, attach/detach VHDX, bcdboot, bcdedit
├── ui/                       # Interfaccia grafica (PySide6)
│   ├── main_window.py        # MainWindow con tab widget e log globali
│   ├── style.py              # Dark theme QSS
│   ├── tabs/                 # Schede per funzionalità (Master, Differenziale, Ventoy)
│   ├── widgets/              # Widget riutilizzabili (LogConsole, PathPicker, ecc.)
│   └── workers/              # QThread asincroni per non bloccare la UI durante operazioni DISM/Diskpart
├── utils/                    # Utility ausiliarie
│   ├── admin.py              # Rilevamento privilegi elevati UAC ed elevazione via ShellExecuteExW
│   ├── constants.py          # Costanti di default, dimensioni partizioni, GUID
│   └── disk_info.py          # Rilevamento lettere disco libere e calcolo spazio storage
├── tests/                    # Test unitari (pytest) con mock completi dei comandi di sistema
├── main.py                   # Entry point applicativo con controllo elevation
├── requirements.txt          # Dipendenze Python
└── AGENTS.md                 # Questo file (linee guida operative per agenti)
```

---

## 4. Critical Operational Safety & Guidelines

> [!WARNING]
> Questo software interagisce direttamente con dischi, partizioni e bootloader di sistema (`diskpart`, `dism`, `bcdboot`). Quando operi come agent coding assistant, segui tassativamente queste regole di sicurezza:

1. **MAI ESEGUIRE COMANDI DI SISTEMA DISTRUTTIVI REALI**:
   - Non eseguire comandi `diskpart`, `format`, o `dism` reali sul computer host durante la generazione di test o verifiche.
   - Tutti i test unitari devono isolare ed eseguire il **mock** delle funzioni in `core.system_executor.run_command` o delle chiamate OS/subprocess.

2. **TESTING E FLAG `--no-elevation`**:
   - `main.py` richiede privilegi di amministratore per default.
   - Per testare o ispezionare l'interfaccia da CLI o ambienti non interattivi, esegui sempre con il flag `--no-elevation`:
     ```powershell
     python main.py --no-elevation
     ```

3. **NON-BLOCKING UI (BACKGROUND THREADS)**:
   - Qualsiasi operazione I/O intensiva o chiamata a comandi esterni (DISM, Diskpart, download Ventoy, bcdboot) **deve** essere eseguita all'interno di un worker `QThread` dedicato (`ui/workers/`).
   - La comunicazione con la UI deve avvenire esclusivamente tramite i segnali Qt (`Signal`), per garantire la fluidità dell'interfaccia e il corretto aggiornamento di progress bar e log console.

4. **CLEANUP & GESTIONE ECCEZIONI**:
   - Le operazioni su VHDX montano dischi virtuali nel sistema operativo host. Se una procedura fallisce o viene annullata dall'utente (`cancel_event`), il codice deve **sempre** garantire la procedura di distacco (`detach_vhdx`) per evitare che il file VHDX rimanga bloccato dal processo `System` di Windows.

5. **LOCALIZZAZIONE E ROBUSTEZZA DEL PARSING**:
   - I comandi CLI di Windows (`dism`, `diskpart`, `bcdedit`) restituiscono output localizzati nella lingua di sistema dell'utente (es. italiano o inglese).
   - I parser (es. in `dism_engine.py` e `vhd_engine.py`) devono utilizzare espressioni regolari e logiche resilienti in grado di identificare sia pattern inglesi che italiani (es. "Percentuale", "Percent", "Operazione completata con successo", "The operation completed successfully").

---

## 5. Development & Testing Commands

- **Creazione / Attivazione Ambiente Virtuale**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  pip install -r requirements.txt
  ```

- **Esecuzione Test Suite**:
  ```powershell
  pytest -v tests/
  ```

- **Esecuzione Test Singolo Modulo**:
  ```powershell
  pytest -v tests/test_vhd_engine.py
  ```

- **Avvio Applicazione in Sviluppo**:
  ```powershell
  python main.py --no-elevation
  ```

- **Compilazione Standalone (Nuitka)**:
  ```powershell
  .\build_nuitka.bat
  ```

---

## 6. Coding Standards for Agents

- **Stile**: Python pulito e moderno (PEP 8), con Type Hints espliciti per parametri e valori di ritorno.
- **Disaccoppiamento**: Il modulo `core/` deve rimanere totalmente agnostico rispetto all'interfaccia grafica (nessuna importazione di `PySide6.QtWidgets` o dipendenze GUI in `core/`).
- **Test-Driven / Regression Prevention**: Quando si aggiunge una nuova funzionalità a `core/` o si corregge un bug, creare o aggiornare i test unitari in `tests/` verificando:
  - Il caso di successo standard.
  - La gestione degli errori (exit code != 0, output inatteso).
  - La cancellazione tempestiva tramite `threading.Event` / cancel flag.
- **Messaggi e Log**: Fornire messaggi di log chiari e informativi attraverso la callback `on_line` o i segnali Qt, per dare feedback continuo all'utente.
