#!/usr/bin/env python3
"""
=============================================================
  WHISKY MAGAZIN - Windows Aufgabenplaner Setup
=============================================================

Richtet Windows Scheduled Tasks fuer das automatische
Newsletter-System ein:

  WhiskyMagazin-Newsletter
    -> Jeden 1. des Monats, 09:00 Uhr
    -> newsletter_generator.py --auto-draft

  WhiskyMagazin-Build
    -> Jeden Montag, 03:00 Uhr
    -> main.py --build-v2  (wenn neue Artikel vorhanden)

Ausfuehren mit Administratorrechten empfohlen.
=============================================================
"""

import sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import subprocess
from pathlib import Path

PROJECT_DIR  = Path(__file__).parent
PYTHON_EXE   = sys.executable


# ============================================================
# Hilfsfunktionen
# ============================================================

def print_box(lines, width=56):
    """Gibt Text in einer ASCII-Box aus."""
    print()
    print("  +" + "=" * width + "+")
    for line in lines:
        padded = line.ljust(width - 2)
        print(f"  |  {padded}  |")
    print("  +" + "=" * width + "+")
    print()


def run_schtasks(args_list, task_name):
    """
    Fuehrt einen schtasks.exe-Befehl aus.
    Gibt True bei Erfolg, False bei Fehler zurueck.
    """
    cmd = ["schtasks"] + args_list
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            print(f"  OK: Aufgabe '{task_name}' erfolgreich eingerichtet.")
            return True
        else:
            err = result.stderr.strip() or result.stdout.strip()
            print(f"  FEHLER bei '{task_name}': {err[:200]}")
            return False
    except FileNotFoundError:
        print("  FEHLER: schtasks.exe nicht gefunden.")
        print("          Dieses Skript benoetigt Windows.")
        return False
    except Exception as exc:
        print(f"  FEHLER: {exc}")
        return False


def task_exists(task_name):
    """Prueft ob eine Aufgabe bereits im Taskplaner vorhanden ist."""
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", task_name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode == 0
    except Exception:
        return False


# ============================================================
# Aufgaben definieren
# ============================================================

TASKS = [
    {
        "name":        "WhiskyMagazin-Newsletter",
        "description": "Monatlicher Newsletter-Entwurf (1. des Monats, 09:00)",
        "schedule":    "MONTHLY",
        "day":         "1",
        "time":        "09:00",
        "command":     f'"{PYTHON_EXE}" newsletter_generator.py --auto-draft',
        "hint": (
            "Prueft WOTM, erstellt Newsletter-Entwurf und\n"
            "  sendet Benachrichtigung an rosenhefter@gmail.com."
        ),
    },
    {
        "name":        "WhiskyMagazin-Build",
        "description": "Woechentlicher Site-Build (Montags, 03:00)",
        "schedule":    "WEEKLY",
        "day":         "MON",
        "time":        "03:00",
        "command":     f'"{PYTHON_EXE}" main.py --build-v2',
        "hint": (
            "Baut die statische Website neu, damit neue\n"
            "  Artikel veroeffentlicht werden."
        ),
    },
]


# ============================================================
# Hauptfunktion
# ============================================================

def main():
    print_box([
        "WHISKY MAGAZIN - Aufgabenplaner Setup",
        "",
        "Richtet folgende Windows Scheduled Tasks ein:",
    ])

    project_str = str(PROJECT_DIR)

    for task in TASKS:
        print(f"  [{task['name']}]")
        print(f"  Zeitplan:  {task['description']}")
        print(f"  Befehl:    {task['command']}")
        print(f"  Hinweis:   {task['hint']}")
        print()

    print(f"  Projektverzeichnis: {project_str}")
    print()

    # Benutzerbestaetigung
    try:
        antwort = input("  Aufgaben jetzt einrichten? (j/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  Abgebrochen.")
        return

    if antwort not in ("j", "ja", "y", "yes"):
        print("\n  Abgebrochen. Keine Aufgaben wurden eingerichtet.")
        print()
        return

    print()
    success_count = 0

    for task in TASKS:
        name    = task["name"]
        time_   = task["time"]
        command = task["command"]

        # Bestehende Aufgabe loeschen falls vorhanden
        if task_exists(name):
            print(f"  Bestehende Aufgabe '{name}' wird ersetzt...")
            subprocess.run(
                ["schtasks", "/delete", "/tn", name, "/f"],
                capture_output=True,
            )

        # Basisargumente fuer schtasks /create
        args = [
            "/create",
            "/tn",  name,
            "/tr",  f'cmd /c "cd /d "{project_str}" && {command} >> "{project_str}\\magazin.log" 2>&1"',
            "/sc",  task["schedule"],
            "/st",  time_,
            "/f",
        ]

        # Tagesangabe je nach Zeitplan
        if task["schedule"] == "MONTHLY":
            args += ["/d", task["day"]]
        elif task["schedule"] == "WEEKLY":
            args += ["/d", task["day"]]

        ok = run_schtasks(args, name)
        if ok:
            success_count += 1

    # Ergebnis
    print()
    if success_count == len(TASKS):
        print_box([
            f"Alle {success_count} Aufgaben erfolgreich eingerichtet!",
            "",
            "Ueberpruefung im Windows Taskplaner:",
            "  taskschd.msc  ->  Aufgabenplanerbibliothek",
            "",
            "Aufgaben manuell testen:",
            "  schtasks /run /tn WhiskyMagazin-Newsletter",
            "  schtasks /run /tn WhiskyMagazin-Build",
            "",
            "Aufgaben entfernen:",
            "  schtasks /delete /tn WhiskyMagazin-Newsletter /f",
            "  schtasks /delete /tn WhiskyMagazin-Build /f",
        ])
    else:
        failed = len(TASKS) - success_count
        print_box([
            f"{success_count}/{len(TASKS)} Aufgaben eingerichtet ({failed} Fehler).",
            "",
            "Tipp: Skript als Administrator ausfuehren,",
            "falls Berechtigungsfehler auftreten.",
        ])


# ============================================================
# Eintrittspunkt
# ============================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Abgebrochen.")
        sys.exit(0)
