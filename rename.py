import os
import re
import argparse
import sys
from pathlib import Path

# Estensioni consentite (Video e Sottotitoli) per evitare di toccare .nfo, .txt, ecc.
ALLOWED_EXTENSIONS = {
    '.mkv', '.mp4', '.avi', '.mov', '.flv', '.webm', '.ogm', '.m4v', '.ts', # Video
    '.srt', '.ass', '.sub' # Sottotitoli
}

def clean_name(stem):
    """Applica le trasformazioni al nome del file (senza estensione)."""
    # 1. Sostituisce underscore con spazi
    name = stem.replace('_', ' ')
    
    # 2. Sostituisce i punti con spazi, MA SOLO SE:
    # - Non sono adiacenti a spazi bianchi (evita di toccare "02. Tokyo" o "fright. Plus")
    # - Non sono punti decimali (evita "2.5")
    # - Non sono parte di un'ellissi (evita "..", "...")
    name = re.sub(r'(?<!\s)(?<!\.)(?!(?<=\d)\.(?=\d))\.(?!\.)(?!\s)', ' ', name)
    
    # 3. Corregge eventuali doppi punti accidentali (es. "more.." diventa "more.")
    # ma preserva i tre punti "..." se presenti nel nome
    name = re.sub(r'(?<!\.)\.\.(?!\.)', '.', name)
    
    # 4. Rimuove tag di release comuni (risoluzioni, audio, sorgenti, codec)
    tags_pattern = re.compile(
        r'\b(1080p|720p|480p|2160p|4k|'
        r'bluray|blu-ray|bdrip|web-dl|webdl|webrip|hdtv|dvdrip|'
        r'x264|x265|h264|h265|hevc|'
        r'dual[- ]?audio|multi[- ]?audio|'
        r'10[- ]?bit|8[- ]?bit)\b', 
        re.IGNORECASE
    )
    name = tags_pattern.sub(' ', name)
    
    # 5. Rimuove eventuali parentesi rimaste vuote dopo la rimozione dei tag (es. "[ ]" o "( )")
    name = re.sub(r'\[\s*\]|\(\s*\)', ' ', name)
    
    # 6. Spazia i trattini se usati come separatori (es. "Anime- 01" -> "Anime - 01")
    # Caso A: C'è già uno spazio su almeno un lato del trattino
    name = re.sub(r'\s+-\s*|\s*-\s+', ' - ', name)
    
    # Caso B (Ottimizzato senza look-behind variabili): Separa lettera e numero
    # 1. Almeno due cifre seguite da trattino e lettera (es: "03-It's" -> "03 - It's")
    name = re.sub(r'(\d{2,})-([a-zA-Z])', r'\1 - \2', name)
    # 2. Una cifra seguita da trattino e lettera MAIUSCOLA (es: "6-S00E09" -> "6 - S00E09")
    # Questo preserva parole composte in romaji come "2-banme" o "3-gatsu"
    name = re.sub(r'(\d)-([A-Z])', r'\1 - \2', name)
    # 3. Una lettera seguita da trattino e numero (es: "Anime-01" -> "Anime - 01")
    name = re.sub(r'([a-zA-Z])-(\d)', r'\1 - \2', name)
    
    # Regex per parentesi tonde o quadre SOLO all'inizio o alla fine
    # Gestisce più gruppi di parentesi consecutivi (es: [Fansub][1080p]...)
    start_pattern = re.compile(r'^(\s*(\[.*?\]|\(.*?\))\s*)+')
    end_pattern = re.compile(r'(\s*(\[.*?\]|\(.*?\))\s*)+$')
    
    # 7. Rimuove i blocchi di parentesi a inizio e fine
    name = start_pattern.sub('', name)
    name = end_pattern.sub('', name)
    
    # 8. Trim finale e pulizia spazi doppi interni
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)
    
    return name

def main():
    # Configurazione Argparse
    parser = argparse.ArgumentParser(description="Anime Renamer ricorsivo nella cartella corrente.")
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Esegue rinomina reale. Senza questo flag, viene eseguito solo un test (dry-run)."
    )
    args = parser.parse_args()

    # Prende la cartella corrente (Current Working Directory)
    root_path = Path.cwd()
    script_name = Path(__file__).name # Nome di questo script per non rinominare se stesso

    print(f"Cartella di lavoro: {root_path}")
    if args.force:
        print("--- MODALITÀ ESECUZIONE REALE ---\n")
    else:
        print("--- MODALITÀ DRY-RUN (Nessuna modifica) ---\n")
        print("Usa il flag --force per applicare le modifiche.\n")

    count_renamed = 0

    # rglob('*') naviga ricorsivamente
    for file_path in root_path.rglob('*'):
        # Processa solo file video/sottotitoli consentiti, ignora lo script stesso
        if (file_path.is_file() and 
            file_path.name != script_name and 
            file_path.suffix.lower() in ALLOWED_EXTENSIONS):
            
            original_full_name = file_path.name
            extension = file_path.suffix
            
            # Pulisce il nome
            new_stem = clean_name(file_path.stem)
            
            # Se dopo la pulizia il nome è vuoto (es. il file era solo [Parentesi].mkv), 
            # meglio non fare nulla per sicurezza
            if not new_stem:
                continue

            final_name = f"{new_stem}{extension}"
            
            # Procedi solo se il nome è cambiato
            if final_name != original_full_name:
                count_renamed += 1
                if args.force:
                    new_path = file_path.with_name(final_name)
                    try:
                        # Gestione conflitti (se il file esiste già)
                        if new_path.exists():
                            print(f"[SALTO] Esiste già: {final_name}")
                        else:
                            file_path.rename(new_path)
                            print(f"[OK] {original_full_name} -> {final_name}")
                    except Exception as e:
                        print(f"[ERRORE] Su {original_full_name}: {e}")
                else:
                    print(f"[DRY-RUN] {original_full_name} -> {final_name}")

    if count_renamed == 0:
        print("Nessun file da rinominare trovato.")
    else:
        print(f"\nOperazione completata. File elaborati: {count_renamed}")

if __name__ == "__main__":
    main()
